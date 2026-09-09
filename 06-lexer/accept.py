# -*- coding: utf-8 -*-
"""Приёмка лексера. Три вопроса, на все отвечает прогон.

1. Не сломали ли старое: первая программа серии обязана собраться
   БАЙТ В БАЙТ так же, как собиралась без лексера.
2. Починилось ли то, ради чего всё затевалось: `.string "http://x"`
   и `.byte '#'`.
3. Что теперь с выражениями: лексер их РЕЖЕТ верно, но не СЧИТАЕТ.
   Считать будет разбор, это следующая работа.

Подмена ровно одна строка:  asm.read_lines = lexer.read_lines

    python accept.py
"""

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "05-asm"))
sys.path.insert(0, HERE)

import asm      # noqa: E402
import lexer    # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")

OLD_READ_LINES = asm.read_lines
FIRST = os.path.join(HERE, "..", "01-hello", "boot.s")

FRAME = ('        .section .text\n'
         '        .globl _start\n'
         '_start:\n'
         'msg:\n'
         '        %s\n')

# Конструкции, которые старый ассемблер точно умеет. Лексер обязан не
# изменить в них ни байта.
REGRESS = [
    "addi sp, sp, -16",
    "addi sp, sp, 16",
    "lw t0, -8(sp)",
    "lw t0, 8(sp)",
    "sw ra, 12(sp)",
    "li t0, -1",
    "li t0, 0x10000000",
    "mv t1, t0",
    "beqz t2, _start",
    "bnez t2, _start",
    "j _start",
    "ret",
    "nop",
    "add t0, t1, t2",
    ".byte 1, 2, 3",
    '.string "Привет"',
]

FIXED = [
    ('.string "http://x"', b"http://x\x00"),
    ('.string "a#b"',      b"a#b\x00"),
    ('.string "a;b"',      b"a;b\x00"),
    (".byte 'A'",          b"A"),
    (".byte '#'",          b"#"),
    ('.string "a /* b */ c"', b"a /* b */ c\x00"),
]


# Девять строк из обещания пятой статьи про выражение в операнде.
# Старый ассемблер собирал из них 1, ту, где выражения по сути нет.
EXPR = [
    "addi sp, sp, -16*2",
    "addi sp, sp, 8+8",
    "addi t0, t0, 1<<4",
    "addi sp, sp, -(16)",
    "addi t0, t0, 0x10|0x01",
    "lw t0, (4*2)(sp)",
    "addi t0, zero, 'A'",
    "addi sp, sp, 8 + 8",
    "addi sp, sp, -16",
]


def build(path, use_lexer):
    asm.read_lines = lexer.read_lines if use_lexer else OLD_READ_LINES
    try:
        blob, _, _ = asm.assemble(path, 0x80000000)
        return blob, None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    finally:
        asm.read_lines = OLD_READ_LINES


def regress_without_gluing():
    """Та же построчная сверка, но переходник не склеивает минус с числом.

    Показывает цену одной строчки в `_render`. Лексер при этом не трогаем:
    он и должен отдавать `-` и `16` порознь.
    """
    import re
    import types
    src = io.open(os.path.join(HERE, "lexer.py"), encoding="utf-8").read()
    m = re.search(r"^(\s*)UNARY_AFTER\s*=.*?\)\s*$", src, re.M | re.S)
    if not m:
        return -1
    code = src[:m.start()] + m.group(1) + "UNARY_AFTER = ()" + src[m.end():]
    mod = types.ModuleType("lexer_no_glue")
    exec(compile(code, "lexer_no_glue.py", "exec"), mod.__dict__)

    tmp = os.path.join(HERE, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    ok = 0
    for line in REGRESS:
        q = os.path.join(tmp, "g.s")
        io.open(q, "w", encoding="utf-8").write(FRAME % line)
        was, _ = build(q, False)
        asm.read_lines = mod.read_lines
        try:
            now, _, _ = asm.assemble(q, 0x80000000)
        except Exception:
            now = None
        finally:
            asm.read_lines = OLD_READ_LINES
        if was is not None and was == now:
            ok += 1
    return ok


def main():
    tmp = os.path.join(HERE, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    bad = 0

    print("=== 1. Не сломали ли старое ===")
    # Сверяем ПОСТРОЧНО, а не программами. Наш ассемблер умеет ровно
    # одну программу серии: на второй он спотыкается о `.equ`, которую
    # никогда не знал. Значит сверка целыми файлами почти ничего не
    # проверяет, и первая версия приёмки молчала о том, что
    # лексер сломал `addi sp, sp, -16`.
    same = 0
    for line in REGRESS:
        p = os.path.join(tmp, "r.s")
        io.open(p, "w", encoding="utf-8").write(FRAME % line)
        was, e1 = build(p, False)
        now, e2 = build(p, True)
        if was is None:
            print("   %-26s старый сам не смог, случай негодный" % line)
            continue
        if now is None:
            print("   %-26s *** СЛОМАЛИ: %s" % (line, str(e2)[:40]))
            bad += 1
        elif was == now:
            same += 1
        else:
            print("   %-26s *** РАЗОШЛОСЬ: %s против %s"
                  % (line, was.hex(), now.hex()))
            bad += 1
    print("   строк сверено %d, байт в байт совпало %d" % (len(REGRESS), same))

    # Сколько из этих 16 держится на склейке минуса в переходнике.
    # Статья называет число, значит оно должно проверяться, а не браться
    # на слово: собираем лексер с пустым UNARY_AFTER и гоняем то же самое.
    print("   без склейки минуса в переходнике: %d из %d"
          % (regress_without_gluing(), len(REGRESS)))

    was, _ = build(FIRST, False)
    now, _ = build(FIRST, True)
    if was is not None and was == now:
        print("   первая программа серии целиком: %d байт, совпало" % len(was))
    else:
        print("   первая программа серии: РАЗОШЛОСЬ")
        bad += 1

    print()
    print("=== 2. Починилось ли сломанное ===")
    print("   %-22s %-13s %-13s %-13s" % ("строка", "надо", "было", "стало"))
    for line, want in FIXED:
        p = os.path.join(tmp, "a.s")
        io.open(p, "w", encoding="utf-8").write(FRAME % line)
        old, eo = build(p, False)
        new, en = build(p, True)
        so = repr(old) if old is not None else "ошибка"
        sn = repr(new) if new is not None else "ошибка"
        ok = new == want
        if not ok:
            bad += 1
        print("   %-22s %-13r %-13s %-13s %s" %
              (line, want, so, sn, "" if ok else "*** НЕ ПОЧИНИЛОСЬ ***"))

    print()
    print("=== 3. Что разбор на слова дал выражениям ===")
    # Второе обещание пятой статьи было про выражение в операнде. Резка
    # на слова это не вычисление, но часть работы она закрывает сама.
    # Сколько именно, надо померить, а не прикинуть.
    print("   %-26s %-9s %-9s" % ("строка", "старый", "с лексером"))
    # Считаем ОДНО И ТО ЖЕ от одного основания: сколько из 9 строк
    # собирается. Раньше печаталось «не собирал 8 из 9, закрыл 1», то
    # есть две разные базы в одной строке, и это никто не понимал.
    was_ok = now_ok = 0
    for line in EXPR:
        q = os.path.join(tmp, "e.s")
        io.open(q, "w", encoding="utf-8").write(FRAME % line)
        was, _ = build(q, False)
        now, _ = build(q, True)
        if was is not None:
            was_ok += 1
        if now is not None:
            now_ok += 1
        print("   %-26s %-9s %-9s"
              % (line, "упал" if was is None else "собрал",
                 "упал" if now is None else "собрал"))
    print("   собиралось %d из %d, стало %d из %d"
          % (was_ok, len(EXPR), now_ok, len(EXPR)))
    print("   остальным нужна арифметика, а это уже не резка")

    toks = lexer.tokens("addi sp, sp, -16*2" + chr(10))
    print()
    print("   строка:  addi sp, sp, -16*2")
    print("   слова:   %s" % " ".join(t.text for t in toks if t.kind != lexer.EOL))
    q = os.path.join(tmp, "b.s")
    io.open(q, "w", encoding="utf-8").write(FRAME % "addi sp, sp, -16*2")
    now, en = build(q, True)
    if now is None:
        print("   сборка:  не собирается. Слова нарезаны, считать их некому.")
    else:
        print("   сборка:  СОБРАЛОСЬ, значит выражение кто-то посчитал")
        print("            это неожиданно, разобраться до того, как писать текст")

    print()
    print("итого неудач: %d" % bad)


if __name__ == "__main__":
    main()
