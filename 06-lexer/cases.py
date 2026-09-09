# -*- coding: utf-8 -*-
"""Где наш разборщик ломается на выражениях в операндах.

Пятая статья кончилась обещанием: «на первом же выражении в операнде это
развалится». Здесь это обещание проверяется, а не пересказывается.

Каждый случай это одна строка, которую настоящий `as` собирает. Прогоняем
обоими ассемблерами и печатаем, что вышло у каждого.

    python cases.py            таблица
    python cases.py -v         плюс сообщение об ошибке целиком
"""

import io
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OURS = os.path.join(HERE, "..", "05-asm", "asm.py")
GAS = "riscv-none-elf-as"
OBJDUMP = "riscv-none-elf-objdump"

# Каркас, который наш ассемблер точно понимает: проверяем ОДНУ строку,
# а не заодно и всё остальное. Без этого первый же прогон соврал:
# он спотыкался на «.text» и до выражения не доходил.
FRAME = """        .section .text
        .globl _start
_start:
%s
msg:
        .string "x"
msg_end:
"""

CASES = [
    ("умножение",            "        addi    sp, sp, -16*2"),
    ("сложение",             "        addi    sp, sp, 8+8"),
    ("сдвиг",                "        addi    t0, t0, 1<<4"),
    ("скобки",               "        addi    sp, sp, -(16)"),
    ("побитовое или",        "        addi    t0, t0, 0x10|0x01"),
    ("разность меток",       "        addi    t1, t1, msg_end-msg"),
    ("выражение в скобке",   "        lw      t0, (4*2)(sp)"),
    ("символ в кавычках",    "        addi    t0, zero, 'A'"),
    ("пробелы вокруг знака", "        addi    sp, sp, 8 + 8"),
    ("простое число",        "        addi    sp, sp, -16"),
]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def gas(src, tmp):
    """Настоящий ассемблер: собрать и вынуть закодированное слово."""
    io.open(os.path.join(tmp, "c.s"), "w", encoding="utf-8").write(src)
    rc, out = run([GAS, "-march=rv32i", "-mabi=ilp32", "-o", "c.o", "c.s"], tmp)
    if rc != 0:
        return None, out
    rc, out = run([OBJDUMP, "-d", "c.o"], tmp)
    for line in out.split("\n"):
        m = re.match(r"\s+0:\s+([0-9a-f]+)\s+\t(.*)", line)
        if m:
            return m.group(1), m.group(2).strip()
    return None, "инструкция не найдена в дизассемблере"


def ours(src, tmp):
    io.open(os.path.join(tmp, "c.s"), "w", encoding="utf-8").write(src)
    rc, out = run([sys.executable, OURS, "c.s", "c.bin"], tmp)
    if rc != 0:
        return None, out
    data = open(os.path.join(tmp, "c.bin"), "rb").read()[:4]
    return "".join("%02x" % b for b in reversed(data)), ""


def main():
    verbose = "-v" in sys.argv
    tmp = os.path.join(HERE, ".tmp")
    os.makedirs(tmp, exist_ok=True)

    print("%-22s %-30s %-10s %-10s %s" %
          ("случай", "строка", "настоящий", "наш", "итог"))
    print("-" * 104)
    broke = 0
    for name, line in CASES:
        src = FRAME % line
        g_word, _ = gas(src, tmp)
        o_word, o_err = ours(src, tmp)

        if g_word is None:
            verdict = "настоящий сам не смог, случай негодный"
        elif o_word is None:
            verdict = "НАШ УПАЛ"
            broke += 1
        elif g_word == o_word:
            verdict = "совпало"
        else:
            verdict = "РАЗОШЛИСЬ БАЙТЫ"
            broke += 1

        print("%-22s %-30s %-10s %-10s %s" %
              (name, line.strip(), g_word or "ошибка", o_word or "ошибка",
               verdict))
        if verbose and o_err:
            print("      наш сказал: %s" % o_err.replace("\n", " ")[:150])

    print("-" * 104)
    print("случаев %d, наш не осилил %d" % (len(CASES), broke))


if __name__ == "__main__":
    main()
