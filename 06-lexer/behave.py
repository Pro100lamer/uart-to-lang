# -*- coding: utf-8 -*-
"""Та же поломка, но показанная поведением, а не сравнением байтов.

Остальные цели стенда сличают наш вывод с выводом настоящего `as`. Это
числа, и по ним не видно, чем потеря оборачивается. Здесь программа
просто запускается, и разницу видно без всяких таблиц: одна сборка
печатает адрес, другая молчит.

Программа одна и та же, `url.s`. Меняется РОВНО ОДНО: чем разрезан
исходник на строки.

Нужен qemu-system-riscv32 из tools/qemu/bin, см. scripts/env.sh.

    python behave.py
"""

import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "05-asm"))
sys.path.insert(0, HERE)

import asm      # noqa: E402
import lexer    # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")

OLD_READ_LINES = asm.read_lines
SRC = os.path.join(HERE, "url.s")
BASE = 0x80000000
QEMU = "qemu-system-riscv32"


def build(use_lexer, out):
    asm.read_lines = lexer.read_lines if use_lexer else OLD_READ_LINES
    try:
        blob, _, syms = asm.assemble(SRC, BASE)
        io.open(out, "wb").write(blob)
        return blob, syms
    finally:
        asm.read_lines = OLD_READ_LINES


def run(path):
    """Запускает образ и возвращает то, что программа напечатала."""
    try:
        r = subprocess.run(
            [QEMU, "-machine", "virt", "-nographic", "-bios", "none",
             "-device", "loader,file=%s,addr=0x%x" % (path, BASE)],
            capture_output=True, timeout=5)
        return r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        # Программа не завершается сама, это ожидаемо: она кончается wfi
        # в вечном цикле. Забираем то, что успело напечататься.
        return (e.stdout or b"").decode("utf-8", "replace")


def main():
    if shutil.which(QEMU) is None:
        print("Нет %s в PATH. Выполните: source ../../scripts/env.sh" % QEMU)
        return

    tmp = os.path.join(HERE, ".tmp")
    os.makedirs(tmp, exist_ok=True)

    print("Одна программа, два разбора исходника на строки.")
    print("Строка данных: .string \"https://github.com/...\"")
    print()

    rows = []
    for tag, use_lexer in (("старый разбор", False), ("лексер", True)):
        path = os.path.join(tmp, "url-%s.bin" % ("new" if use_lexer else "old"))
        blob, syms = build(use_lexer, path)
        out = run(path)
        ghost = [k for k in syms if '"' in k]
        rows.append((tag, len(blob), out, ghost))

    print("%-16s %-8s %s" % ("сборка", "байт", "что напечатала программа"))
    print("-" * 76)
    for tag, n, out, ghost in rows:
        shown = out.strip() if out.strip() else "(ничего)"
        print("%-16s %-8d %s" % (tag, n, shown))
    print("-" * 76)
    print()

    for tag, n, out, ghost in rows:
        if ghost:
            print("В таблице меток у сборки «%s» завелось вот это:" % tag)
            for g in ghost:
                print("     %r" % g)
            print("  Это половина строки данных, принятая за имя метки.")
            print()

    silent = [t for t, n, o, g in rows if not o.strip()]
    talking = [t for t, n, o, g in rows if o.strip()]
    if silent and talking:
        print("ГЛАВНОЕ ТУТ НЕ РАЗМЕР ОБРАЗА, А ПОВЕДЕНИЕ.")
        print("Сборка «%s» не падает, не ругается и возвращает код успеха."
              % silent[0])
        print("Она просто ничего не печатает. Если бы это была прошивка в")
        print("плате, вы бы полезли проверять провода и скорость порта.")
    elif not silent:
        print("Обе сборки печатают. Опыт ничего не показывает, разобраться.")
    else:
        print("Обе сборки молчат. Проверьте, работает ли сам запуск.")


if __name__ == "__main__":
    main()
