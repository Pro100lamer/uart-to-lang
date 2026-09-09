"""Считает, какая доля строк в наших ассемблерных программах это
псевдоинструкции, то есть то, чего в процессоре нет.

Зачем: спина пятой статьи держится на утверждении «больше половины строк
реальной программы это выдумка ассемблера». Очевидное возражение к нему:
«вы посчитали по одной удобной программе». Скрипт считает по всем, какие
есть в репозитории, и печатает разброс. Если доля где-то мала, это должно
быть видно, а не спрятано.

Классификация по мнемонике. Настоящие взяты из базового набора RV32I плюс
то немногое из привилегированной части, что встречается на наших стендах.
Всё остальное, что похоже на инструкцию, считается псевдо.

Использование:
    python count-pseudo.py ../01-hello/boot.s ../03-stack/boot.s
    python count-pseudo.py            # все .s репозитория
"""

import io
import os
import re
import sys

# Базовый RV32I. Список закрытый и короткий нарочно: если мнемоники тут нет,
# скрипт скажет об этом отдельной строкой, а не молча запишет её в псевдо.
RV32I = set("""
lui auipc jal jalr
beq bne blt bge bltu bgeu
lb lh lw lbu lhu
sb sh sw
addi slti sltiu xori ori andi slli srli srai
add sub sll slt sltu xor srl sra or and
fence ecall ebreak
""".split())

# Привилегированные и Zicsr, встречаются на наших стендах.
EXTRA_REAL = set("wfi mret sret csrrw csrrs csrrc csrrwi csrrsi csrrci".split())

REAL = RV32I | EXTRA_REAL

# Псевдоинструкции, которые мы действительно используем или можем встретить.
# Список нужен не для классификации (всё не из REAL и так псевдо), а чтобы
# отличить known-псевдо от опечатки или незнакомой мнемоники.
PSEUDO = set("""
li la mv not neg seqz snez sltz sgtz
beqz bnez blez bgez bltz bgtz bgt ble bgtu bleu
j jr ret call tail nop
csrr csrw csrs csrc
""".split())

DIRECTIVE = re.compile(r"^\s*\.")
LABEL_ONLY = re.compile(r"^\s*[.\w$]+:\s*(/\*.*)?$")
MNEMONIC = re.compile(r"^\s+([a-z][a-z0-9._]*)\b")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//.*", " ", text)
    return text


def scan(path):
    """Возвращает (список настоящих, список псевдо, список незнакомых)."""
    text = strip_comments(io.open(path, encoding="utf-8", errors="replace").read())
    real, pseudo, unknown = [], [], []
    for line in text.split("\n"):
        if not line.strip():
            continue
        if DIRECTIVE.match(line):
            continue
        # Метка и инструкция на одной строке: отрезаем метку.
        m = re.match(r"^\s*[.\w$]+:\s*(.+)$", line)
        if m and not LABEL_ONLY.match(line):
            line = "    " + m.group(1)
        elif LABEL_ONLY.match(line):
            continue
        m = MNEMONIC.match(line)
        if not m:
            continue
        mn = m.group(1)
        if mn in REAL:
            real.append(mn)
        elif mn in PSEUDO:
            pseudo.append(mn)
        else:
            unknown.append(mn)
    return real, pseudo, unknown


def main():
    args = sys.argv[1:]
    if not args:
        # normpath обязателен: без него корень выглядит как
        # ".../05-asm/..", и любая проверка на скрытые каталоги по
        # подстроке os.sep + "." отсеивает вообще всё.
        root = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        args = []
        for d, _, files in os.walk(root):
            if os.sep + "." in d:
                continue
            for f in sorted(files):
                # Считаем только RISC-V. Каталоги esp32, esp32c6, nanopi
                # содержат код для других архитектур (Xtensa, ARM),
                # а *-hello.s это скелеты для сравнения наборов.
                skip_dirs = {"esp32", "esp32c6", "nanopi"}
                if f.endswith(".s") and not f.endswith("-hello.s"):
                    if not any(s in d for s in skip_dirs):
                        args.append(os.path.join(d, f))
        args.sort()

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")

    print("%-38s %6s %6s %7s  %s" % ("файл", "всего", "псевдо", "доля", "какие"))
    print("-" * 100)
    tot_r = tot_p = 0
    all_unknown = {}
    for path in args:
        if not os.path.isfile(path):
            print("нет файла: %s" % path)
            continue
        real, pseudo, unknown = scan(path)
        n = len(real) + len(pseudo)
        if n == 0:
            continue
        tot_r += len(real)
        tot_p += len(pseudo)
        for u in unknown:
            all_unknown[u] = all_unknown.get(u, 0) + 1
        short = os.path.relpath(path).replace("\\", "/")
        if len(short) > 38:
            short = "..." + short[-35:]
        kinds = ", ".join(sorted(set(pseudo)))
        print("%-38s %6d %6d %6.0f%%  %s"
              % (short, n, len(pseudo), 100.0 * len(pseudo) / n, kinds))

    total = tot_r + tot_p
    print("-" * 100)
    if total:
        print("ИТОГО: инструкций %d, из них псевдо %d, это %.0f%%"
              % (total, tot_p, 100.0 * tot_p / total))
    if all_unknown:
        print()
        print("НЕЗНАКОМЫЕ МНЕМОНИКИ (в счёт не пошли, разобрать вручную):")
        for u in sorted(all_unknown):
            print("   %s  x%d" % (u, all_unknown[u]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
