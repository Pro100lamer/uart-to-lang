"""Ассемблер RV32I на два прохода. Выдаёт плоский образ памяти.

Умеет ровно то, что встречается в программах этой серии, и ни строчкой
больше. Это не замена настоящему тулчейну, это ответ на вопрос «а что он,
собственно, делает с моим текстом».

Два прохода:
  1. пройти по строкам, посчитать адрес каждой и запомнить, где какая метка;
  2. пройти ещё раз и закодировать, подставляя уже известные адреса.

Второй проход нужен потому, что переход вперёд ссылается на метку, которой
на момент первой встречи ещё нет. Размер каждой строки при этом известен уже
на первом проходе: единственная псевдоинструкция переменной длины это `li`,
и её длина считается по константе, а константа записана прямо в строке.

Почему образ плоский и по фиксированному адресу. Настоящий ассемблер выдаёт
объектный файл, где адреса ещё не назначены, и потому НЕ МОЖЕТ дописать `la`
до конца: он не знает, куда компоновщик положит метку. Мы можем, потому что
сразу пишем образ по 0x80000000. Это разница не в качестве, а в задаче.

Использование:
    python asm.py boot.s out.bin
    python asm.py boot.s out.bin --base 0x80000000
    python asm.py boot.s out.bin --listing     # показать, что получилось
"""

import io
import re
import struct
import sys

BASE_DEFAULT = 0x80000000

# ---------------------------------------------------------------- регистры

ABI = """zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 a6 a7
         s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6""".split()
REGS = {name: i for i, name in enumerate(ABI)}
REGS.update({"x%d" % i: i for i in range(32)})
REGS["fp"] = 8          # второе имя того же s0


def reg(tok):
    t = tok.strip().lower()
    if t not in REGS:
        raise Asm("неизвестный регистр: %s" % tok)
    return REGS[t]


class Asm(Exception):
    pass


# ------------------------------------------------------- кодировщики типов
#
# Пять форматов. Различаются они тем, как разрезано непосредственное
# значение: у процессора нет команды «взять число целиком», биты числа
# раскиданы по слову так, чтобы номера регистров всегда стояли на одних и
# тех же местах. Это удобно железу и неудобно человеку.

def enc_r(op, f3, f7, rd, rs1, rs2):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def enc_i(op, f3, rd, rs1, imm):
    if not -2048 <= imm <= 2047:
        raise Asm("значение %d не влезает в 12 бит" % imm)
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def enc_s(op, f3, rs1, rs2, imm):
    if not -2048 <= imm <= 2047:
        raise Asm("смещение %d не влезает в 12 бит" % imm)
    i = imm & 0xFFF
    return (((i >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) \
        | (f3 << 12) | ((i & 0x1F) << 7) | op


def enc_b(op, f3, rs1, rs2, imm):
    if imm & 1:
        raise Asm("нечётное смещение перехода: %d" % imm)
    if not -4096 <= imm <= 4094:
        raise Asm("переход слишком далёкий: %d" % imm)
    i = imm & 0x1FFF
    return (((i >> 12) & 1) << 31) | (((i >> 5) & 0x3F) << 25) \
        | (rs2 << 20) | (rs1 << 15) | (f3 << 12) \
        | (((i >> 1) & 0xF) << 8) | (((i >> 11) & 1) << 7) | op


def enc_u(op, rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def enc_j(op, rd, imm):
    if imm & 1:
        raise Asm("нечётное смещение перехода: %d" % imm)
    if not -1048576 <= imm <= 1048574:
        raise Asm("переход слишком далёкий: %d" % imm)
    i = imm & 0x1FFFFF
    return (((i >> 20) & 1) << 31) | (((i >> 1) & 0x3FF) << 21) \
        | (((i >> 11) & 1) << 20) | (((i >> 12) & 0xFF) << 12) | (rd << 7) | op


# --------------------------------------------------------- таблица команд
#
# Вот она, та самая «таблица кодов», ради которой всё затевалось. Вместе с
# пятью кодировщиками выше это 43 строки кода из 478, то есть меньшая часть.

OP_IMM, OP_REG, LOAD, STORE, BRANCH = 0x13, 0x33, 0x03, 0x23, 0x63
LUI, AUIPC, JAL, JALR, SYSTEM = 0x37, 0x17, 0x6F, 0x67, 0x73

I_ARITH = {"addi": 0, "slti": 2, "sltiu": 3, "xori": 4, "ori": 6, "andi": 7}
I_SHIFT = {"slli": (1, 0), "srli": (5, 0), "srai": (5, 0x20)}
R_ARITH = {"add": (0, 0), "sub": (0, 0x20), "sll": (1, 0), "slt": (2, 0),
           "sltu": (3, 0), "xor": (4, 0), "srl": (5, 0), "sra": (5, 0x20),
           "or": (6, 0), "and": (7, 0)}
LOADS = {"lb": 0, "lh": 1, "lw": 2, "lbu": 4, "lhu": 5}
STORES = {"sb": 0, "sh": 1, "sw": 2}
BRANCHES = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}

# Псевдоинструкции: чего в процессоре нет. Значение это длина в словах,
# нужна на первом проходе. У `li` длина зависит от константы, поэтому None.
PSEUDO_LEN = {"li": None, "la": 2, "mv": 1, "j": 1, "jr": 1, "ret": 1,
              "nop": 1, "beqz": 1, "bnez": 1}


def split_hi_lo(value):
    """Делит 32-битное значение на старшую и младшую части так, как этого
    требует пара lui/addi.

    Тонкость, на которой все спотыкаются: младшая часть в `addi` знаковая.
    Если её старший бит единица, `addi` вычтет 4096, и поэтому к старшей
    части надо заранее прибавить единицу. Отсюда `+ 0x800`."""
    hi = (value + 0x800) >> 12
    lo = value - (hi << 12)
    return hi & 0xFFFFF, lo


def li_len(value):
    _, lo = split_hi_lo(value)
    if -2048 <= value <= 2047:
        return 1                    # хватит одного addi
    return 1 if lo == 0 else 2      # lui, и addi только если нужен


# ------------------------------------------------------------ разбор строк

COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.S)
LABEL = re.compile(r"^([.\w$]+):\s*(.*)$")


def parse_int(tok, labels=None):
    t = tok.strip()
    try:
        return int(t, 0)
    except ValueError:
        pass
    if labels is not None and t in labels:
        return labels[t]
    raise Asm("не число и не известная метка: %s" % tok)


def unescape(s):
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            mapping = {"n": 10, "t": 9, "r": 13, "0": 0, "\\": 92, '"': 34}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
        out.extend(c.encode("utf-8"))
        i += 1
    return bytes(out)


def read_lines(path):
    """Убирает комментарии, разлепляет метки, возвращает список (номер, текст)."""
    text = COMMENT_BLOCK.sub(" ", io.open(path, encoding="utf-8").read())
    out = []
    for n, raw in enumerate(text.split("\n"), 1):
        line = raw.split("//")[0].split("#")[0].strip()
        while line:
            m = LABEL.match(line)
            if not m:
                break
            out.append((n, m.group(1) + ":"))
            line = m.group(2).strip()
        if line:
            out.append((n, line))
    return out


def operands(rest):
    """Режет операнды по запятым, не трогая то, что в кавычках."""
    parts, cur, q = [], "", False
    for ch in rest:
        if ch == '"':
            q = not q
        if ch == "," and not q:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


MEMREF = re.compile(r"^(-?\w+)?\s*\(\s*([\w$]+)\s*\)$")


def memref(tok, labels=None):
    """Разбирает `12(sp)` и `(sp)`."""
    m = MEMREF.match(tok.strip())
    if not m:
        raise Asm("не похоже на обращение к памяти: %s" % tok)
    off = parse_int(m.group(1), labels) if m.group(1) else 0
    return off, reg(m.group(2))


# ------------------------------------------------------------ два прохода

class Item(object):
    """Одна единица вывода: инструкция или кусок данных."""

    __slots__ = ("kind", "line", "text", "size", "addr", "section", "data")

    def __init__(self, kind, line, text, size, section, data=None):
        self.kind, self.line, self.text = kind, line, text
        self.size, self.section, self.data = size, section, data
        self.addr = 0


def pass1(lines, base):
    """Раскладывает всё по адресам и собирает метки.

    Секций у нас две, .text и .rodata, и идут они в этом порядке независимо
    от того, в каком порядке встретились в файле. Так же делает и скрипт
    компоновщика из первой статьи."""
    items = {"text": [], "rodata": []}
    cur = "text"
    n = 0                      # чтобы хвостовые метки не упали на пустом файле
    pending_labels = []
    labels = {}
    globls = []

    for n, line in lines:
        if line.endswith(":"):
            pending_labels.append(line[:-1])
            continue

        parts = line.split(None, 1)
        head = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if head == ".section":
            name = rest.strip().lstrip(".")
            cur = "rodata" if name.startswith("rodata") else "text"
            for lb in pending_labels:
                items[cur].append(Item("label", n, lb, 0, cur))
            pending_labels = []
            continue
        if head in (".globl", ".global"):
            globls.append(rest.strip())
            continue

        for lb in pending_labels:
            items[cur].append(Item("label", n, lb, 0, cur))
        pending_labels = []

        if head == ".string" or head == ".asciz":
            raw = rest.strip()
            if not (raw.startswith('"') and raw.endswith('"')):
                raise Asm("строка %d: .string ждёт текст в кавычках" % n)
            data = unescape(raw[1:-1]) + b"\x00"
            items[cur].append(Item("data", n, line, len(data), cur, data))
            continue
        if head == ".byte":
            data = bytes(bytearray(parse_int(t) & 0xFF for t in operands(rest)))
            items[cur].append(Item("data", n, line, len(data), cur, data))
            continue
        if head == ".word":
            vals = [parse_int(t) for t in operands(rest)]
            data = b"".join(struct.pack("<I", v & 0xFFFFFFFF) for v in vals)
            items[cur].append(Item("data", n, line, len(data), cur, data))
            continue
        if head == ".space" or head == ".zero":
            data = b"\x00" * parse_int(rest)
            items[cur].append(Item("data", n, line, len(data), cur, data))
            continue
        if head.startswith("."):
            raise Asm("строка %d: не знаю директиву %s" % (n, head))

        # Инструкция. Длина в словах.
        if head in PSEUDO_LEN:
            if head == "li":
                words = li_len(parse_int(operands(rest)[1]))
            else:
                words = PSEUDO_LEN[head]
        else:
            words = 1
        items[cur].append(Item("insn", n, line, words * 4, cur))

    for lb in pending_labels:
        items[cur].append(Item("label", n, lb, 0, cur))

    addr = base
    order = []
    for sec in ("text", "rodata"):
        addr = (addr + 3) & ~3          # секции выравниваем по слову
        for it in items[sec]:
            it.addr = addr
            if it.kind == "label":
                labels[it.text] = addr
            addr += it.size
            order.append(it)
    return order, labels, globls


def encode(line, pc, labels):
    """Кодирует одну инструкцию. Возвращает список 32-битных слов."""
    parts = line.split(None, 1)
    mn = parts[0].lower()
    ops = operands(parts[1]) if len(parts) > 1 else []

    def target(tok):
        """Смещение до метки от текущей инструкции."""
        if tok in labels:
            return labels[tok] - pc
        return parse_int(tok, labels) - pc

    # --- сначала самозванцы: то, чего в процессоре нет ---
    if mn == "nop":
        return [enc_i(OP_IMM, 0, 0, 0, 0)]
    if mn == "ret":
        return [enc_i(JALR, 0, 0, REGS["ra"], 0)]
    if mn == "jr":
        return [enc_i(JALR, 0, 0, reg(ops[0]), 0)]
    if mn == "j":
        return [enc_j(JAL, 0, target(ops[0]))]
    if mn == "mv":
        return [enc_i(OP_IMM, 0, reg(ops[0]), reg(ops[1]), 0)]
    if mn == "beqz":
        return [enc_b(BRANCH, 0, reg(ops[0]), 0, target(ops[1]))]
    if mn == "bnez":
        return [enc_b(BRANCH, 1, reg(ops[0]), 0, target(ops[1]))]
    if mn == "li":
        rd, val = reg(ops[0]), parse_int(ops[1], labels)
        if -2048 <= val <= 2047:
            return [enc_i(OP_IMM, 0, rd, 0, val)]
        hi, lo = split_hi_lo(val)
        words = [enc_u(LUI, rd, hi)]
        if lo != 0:
            words.append(enc_i(OP_IMM, 0, rd, rd, lo))
        return words
    if mn == "la":
        rd = reg(ops[0])
        delta = target(ops[1])
        hi, lo = split_hi_lo(delta)
        # auipc кладёт старшую часть, addi добавляет младшую. Обе части
        # считаются ОТ АДРЕСА auipc, поэтому второй инструкции смещение
        # пересчитывать не надо.
        return [enc_u(AUIPC, rd, hi), enc_i(OP_IMM, 0, rd, rd, lo)]

    # --- дальше настоящие ---
    if mn == "lui":
        return [enc_u(LUI, reg(ops[0]), parse_int(ops[1], labels) & 0xFFFFF)]
    if mn == "auipc":
        return [enc_u(AUIPC, reg(ops[0]), parse_int(ops[1], labels) & 0xFFFFF)]
    if mn == "jal":
        if len(ops) == 1:
            return [enc_j(JAL, REGS["ra"], target(ops[0]))]
        return [enc_j(JAL, reg(ops[0]), target(ops[1]))]
    if mn == "jalr":
        if len(ops) == 1:
            return [enc_i(JALR, 0, REGS["ra"], reg(ops[0]), 0)]
        off, rs1 = memref(ops[1], labels) if "(" in ops[1] \
            else (parse_int(ops[2], labels), reg(ops[1]))
        return [enc_i(JALR, 0, reg(ops[0]), rs1, off)]
    if mn in I_ARITH:
        return [enc_i(OP_IMM, I_ARITH[mn], reg(ops[0]), reg(ops[1]),
                      parse_int(ops[2], labels))]
    if mn in I_SHIFT:
        f3, f7 = I_SHIFT[mn]
        sh = parse_int(ops[2]) & 0x1F
        return [enc_i(OP_IMM, f3, reg(ops[0]), reg(ops[1]), (f7 << 5) | sh)]
    if mn in R_ARITH:
        f3, f7 = R_ARITH[mn]
        return [enc_r(OP_REG, f3, f7, reg(ops[0]), reg(ops[1]), reg(ops[2]))]
    if mn in LOADS:
        off, rs1 = memref(ops[1], labels)
        return [enc_i(LOAD, LOADS[mn], reg(ops[0]), rs1, off)]
    if mn in STORES:
        off, rs1 = memref(ops[1], labels)
        return [enc_s(STORE, STORES[mn], rs1, reg(ops[0]), off)]
    if mn in BRANCHES:
        return [enc_b(BRANCH, BRANCHES[mn], reg(ops[0]), reg(ops[1]),
                      target(ops[2]))]
    if mn == "wfi":
        return [0x10500073]
    if mn == "ecall":
        return [enc_i(SYSTEM, 0, 0, 0, 0)]
    if mn == "ebreak":
        return [enc_i(SYSTEM, 0, 0, 0, 1)]

    raise Asm("не знаю такой инструкции: %s" % mn)


def assemble(path, base=BASE_DEFAULT):
    order, labels, _ = pass1(read_lines(path), base)
    out = bytearray()
    listing = []
    for it in order:
        if it.kind == "label":
            continue
        if it.kind == "data":
            out.extend(it.data)
            listing.append((it.addr, it.data, it.text))
            continue
        try:
            words = encode(it.text, it.addr, labels)
        except Asm as e:
            raise Asm("строка %d: %s   (%s)" % (it.line, e, it.text))
        if len(words) * 4 != it.size:
            raise Asm("строка %d: на первом проходе насчитал %d байт, "
                      "на втором вышло %d   (%s)"
                      % (it.line, it.size, len(words) * 4, it.text))
        blob = b"".join(struct.pack("<I", w) for w in words)
        out.extend(blob)
        listing.append((it.addr, blob, it.text))
    return bytes(out), listing, labels


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2

    base = BASE_DEFAULT
    for f in flags:
        if f.startswith("--base="):
            base = int(f.split("=", 1)[1], 0)

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")

    try:
        blob, listing, labels = assemble(args[0], base)
    except Asm as e:
        print("ОШИБКА: %s" % e, file=sys.stderr)
        return 1

    io.open(args[1], "wb").write(blob)

    if "--listing" in flags:
        for addr, data, text in listing:
            hexed = " ".join("%02x" % b for b in data)
            if len(hexed) > 35:
                hexed = hexed[:32] + "..."
            print("%08x  %-35s %s" % (addr, hexed, text))
        print()
        print("метки:")
        for name in sorted(labels, key=lambda k: labels[k]):
            print("   %08x  %s" % (labels[name], name))

    print("собрано %d байт в %s" % (len(blob), args[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
