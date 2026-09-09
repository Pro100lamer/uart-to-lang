# -*- coding: utf-8 -*-
"""Попытка опрокинуть спину шестой статьи.

Возражение, которое придёт первым: «почини срезание комментариев, чтобы
оно уважало кавычки, и делу конец, никакой лексер не нужен».

Здесь эта починка не описывается, а пишется, и не одна, а две подряд:
сперва учим стриппер двойным кавычкам, потом ещё и одиночным. После
каждой смотрим, что осталось сломанным.

Ожидаемые строки не выдуманы: каждая проверена настоящим `as`, см.
колонку «as» в выводе `silent.py` и разбор в README.

    python refute.py
"""

import ast
import inspect
import sys
import textwrap

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")


def body_lines(fn):
    """Сколько строк кода в теле функции, без сигнатуры и без описания.

    Считается разбором дерева, а не вычитанием на глаз: в прошлой статье
    я написал «таблица заняла сорок строк» по ощущению, и их было 43.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    body = tree.body
    if (isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]          # описание в кавычках это не код
    ends = [n.end_lineno for n in ast.walk(tree)
            if getattr(n, "end_lineno", None) is not None]
    return max(ends) - body[0].lineno + 1


def strip_naive(line):
    """Как сейчас в asm.py: режем и не смотрим ни на что."""
    return line.split("//")[0].split("#")[0].strip()


def strip_patch1(line):
    """Заплатка 1: то же самое, но помним, что мы внутри двойных кавычек."""
    out, q, i = [], False, 0
    while i < len(line):
        c = line[i]
        if c == '"':
            q = not q
        if not q and (line.startswith("//", i) or c == "#"):
            break
        out.append(c)
        i += 1
    return "".join(out).strip()


def strip_patch2(line):
    """Заплатка 2: выучили и одиночные кавычки тоже.

    Два отдельных выключателя, каждый сам по себе. Именно так эту
    заплатку и напишешь, если чинить по одному случаю за раз: про
    двойные кавычки уже знаем, добавим такой же признак для одиночных.
    """
    out, dq, sq, i = [], False, False, 0
    while i < len(line):
        c = line[i]
        if c == '"':
            dq = not dq
        if c == "'":
            sq = not sq
        if not dq and not sq and (line.startswith("//", i) or c == "#"):
            break
        out.append(c)
        i += 1
    return "".join(out).strip()


def strip_state(line):
    """Не заплатка, а состояние: помним, КАКАЯ кавычка сейчас главная.

    Это уже не «ещё одно исключение», а другое устройство: у строки одно
    состояние на все случаи. Ровно то, что делает lexer.py.
    """
    out, mode, i = [], None, 0
    while i < len(line):
        c = line[i]
        if mode is None:
            if c in '"\'':
                mode = c
            elif line.startswith("//", i) or c == "#":
                break
        elif c == "\\":
            out.append(c)
            i += 1
            if i < len(line):
                out.append(line[i])
                i += 1
            continue
        elif c == mode:
            mode = None
        out.append(c)
        i += 1
    return "".join(out).strip()


# строка исходника, чем она должна кончиться после срезания комментария
CASES = [
    ('.string "http://x"',         '.string "http://x"'),
    ('.string "a#b"',              '.string "a#b"'),
    ('addi sp, sp, -16 // размер', 'addi sp, sp, -16'),
    ('addi sp, sp, -16 # размер',  'addi sp, sp, -16'),
    ('.string "a\\"b"',            '.string "a\\"b"'),
    (".byte '#'",                  ".byte '#'"),
    (".byte '/'",                  ".byte '/'"),
    ('.string "a" // и "б"',       '.string "a"'),
    # Две строки, до которых я сам не додумался, пока не написал вторую
    # заплатку. Обе настоящий `as` собирает верно, проверено прогоном:
    # `.string "a'b" # хвост` даёт b"a'b\0", `.byte '"' # хвост` даёт b'"'.
    ('.string "a\'b" # хвост',     '.string "a\'b"'),
    ('.byte \'"\' # хвост',        '.byte \'"\''),
]

WAYS = [
    ("наивно", strip_naive),
    ("заплатка 1", strip_patch1),
    ("заплатка 2", strip_patch2),
    ("состояние", strip_state),
]


def main():
    print("Срезание комментария: одна наивная версия, две заплатки подряд")
    print("и то, что заплаткой уже не является.")
    print()
    head = "%-28s" % "строка"
    for name, _ in WAYS:
        head += " %-12s" % name
    print(head)
    print("-" * len(head))

    bad = {name: [] for name, _ in WAYS}
    for src, want in CASES:
        row = "%-28s" % src
        for name, fn in WAYS:
            ok = fn(src) == want
            if not ok:
                bad[name].append(src)
            row += " %-12s" % ("верно" if ok else "*** НЕТ")
        print(row)

    print("-" * len(head))
    for name, _ in WAYS:
        print("%-12s неверно %d из %d" % (name, len(bad[name]), len(CASES)))

    print()
    print("=== ЧТО ИЗ ЭТОГО СЛЕДУЕТ ===")
    print()
    p1, p2 = set(bad["заплатка 1"]), set(bad["заплатка 2"])
    fixed = p1 - p2
    broke = p2 - p1
    if fixed:
        print("Заплатка 2 починила:")
        for s in sorted(fixed):
            print("   %s" % s)
    if broke:
        print("Заплатка 2 СЛОМАЛА то, что заплатка 1 собирала верно:")
        for s in sorted(broke):
            print("   %s" % s)
        print()
        print("Вот это и есть ответ заплаточнику. Дело не в том, что")
        print("исключения не кончаются. Дело в том, что вторая заплатка")
        print("не знает про первую: два выключателя, и ни один не знает,")
        print("кто из них сейчас главный.")
    elif p2:
        print("Заплатка 2 не спасает, осталось сломанным:")
        for s in sorted(p2):
            print("   %s" % s)
    else:
        print("Заплатка 2 чинит всё. Спина статьи неверна, переписывать.")

    print()
    if not bad["состояние"]:
        n = body_lines(strip_state)
        print("Версия с состоянием берёт все %d. Она отличается от заплаток"
              % len(CASES))
        print("не количеством выученных случаев, а тем, что помнит РОВНО")
        print("ОДНУ вещь: какая кавычка сейчас главная. Это и есть лексер,")
        print("только пока в %d строк." % n)
    else:
        print("Версия с состоянием тоже не всё берёт, осталось:")
        for s in bad["состояние"]:
            print("   %s" % s)


if __name__ == "__main__":
    main()
