# -*- coding: utf-8 -*-
"""Где наш разборщик молчит и ошибается. Это страшнее, чем падение.

Падение видно сразу. А тут ассемблер возвращает ноль, печатает
«собрано N байт» и отдаёт не то, что написано.

Причина одна на все случаи: строка режется правилами по очереди, и ни
одно правило не знает, что оно сейчас внутри строкового литерала.

Ожидаемые байты заданы В ТАБЛИЦЕ, а не взяты из дампа настоящего
ассемблера. Первый заход я сделал через objcopy и получил ложное
срабатывание: gas добивает секцию до выравнивания, лишние байты
попадали в сравнение, и исправный случай выглядел поломанным.

    python silent.py
"""

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OURS = os.path.join(HERE, "..", "05-asm", "asm.py")

FRAME = ('        .section .text\n'
         '        .globl _start\n'
         '_start:\n'
         'msg:\n'
         '        %s\n')

# строка исходника, что обязано получиться
CASES = [
    ("две косые в строке", '.string "http://x"', b"http://x\x00"),
    ("решётка в строке",   '.string "a#b"',      b"a#b\x00"),
    ("запятая в строке",   '.string "a,b"',      b"a,b\x00"),
    ("точка с запятой",    '.string "a;b"',      b"a;b\x00"),
    ("двоеточие в конце",  '.string "time:"',    b"time:\x00"),
    ("звёздочка и косая",  '.string "a/*b"',     b"a/*b\x00"),
    # Блочный комментарий ЦЕЛИКОМ внутри строки. Правило /* */ работает
    # по всему файлу разом, до разрезания на строки, и про кавычки не
    # знает вовсе. Ожидаемые байты сверены с настоящим as.
    ("блочный в строке",   '.string "a /* b */ c"', b"a /* b */ c\x00"),
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")

    tmp = os.path.join(HERE, ".tmp")
    os.makedirs(tmp, exist_ok=True)

    print("%-20s %-22s %-13s %-13s %s" %
          ("случай", "строка", "надо", "получили", "итог"))
    print("-" * 92)
    silent = loud = 0
    for name, line, want in CASES:
        io.open(os.path.join(tmp, "s.s"), "w", encoding="utf-8").write(FRAME % line)
        p = subprocess.run([sys.executable, OURS, "s.s", "s.bin"], cwd=tmp,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            verdict, got = "упал с ошибкой, она видна", b"-"
            loud += 1
        else:
            got = open(os.path.join(tmp, "s.bin"), "rb").read()
            if got == want:
                verdict = "верно"
            else:
                verdict = "*** МОЛЧА НЕВЕРНО ***"
                silent += 1
        print("%-20s %-22s %-13r %-13r %s" % (name, line, want, got, verdict))

    print("-" * 92)
    print("случаев %d, молча неверных %d, упавших с ошибкой %d"
          % (len(CASES), silent, loud))
    print()
    print("Разбор самого тихого, `.string \"http://x\"`. Строка проходит два")
    print("правила подряд, и каждое по отдельности разумно:")
    print("  1. всё после // это комментарий   ->  остаётся  .string \"http:")
    print("  2. строка, кончающаяся двоеточием, это метка")
    print("Второе срабатывает, потому что от URL остался хвост с двоеточием.")
    print("Данные исчезают, а в таблице меток заводится вот такое имя:")
    print("     '.string \"http'")
    print("Ни одно правило не знало, что оно внутри строкового литерала.")


if __name__ == "__main__":
    main()
