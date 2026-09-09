# -*- coding: utf-8 -*-
"""Разбор текста на слова: один проход, который всё время знает, где он.

Прежний разбор в asm.py резал строку правилами по очереди: сперва убрать
комментарий, потом отделить метку, потом поделить операнды запятыми.
Каждое правило по отдельности верно, а вместе они теряют данные, потому
что ни одно не знает про строковые литералы.

Здесь один проход слева направо. У прохода есть состояние: он в обычном
тексте, внутри двойных кавычек, внутри одиночных или внутри блочного
комментария. Символ значит разное в зависимости от состояния, и в этом
вся разница.

Наружу торчат две вещи:

    tokens(text)      поток слов с номерами строк
    read_lines(path)  замена read_lines из asm.py, той же формы
"""

import io

# Виды слов. Строкой, а не числом: в отладке читается глазами.
WORD = "word"        # мнемоника, имя регистра, метка, директива
NUMBER = "number"    # 16, 0x10, -16 разбирается как знак и число
STRING = "string"    # "текст", уже без кавычек и с раскрытыми escape
CHAR = "char"        # 'A', уже как число
PUNCT = "punct"      # , ( ) + - * / < > | & : и прочее
EOL = "eol"          # конец логической строки

ESCAPES = {"n": 10, "t": 9, "r": 13, "0": 0, "\\": 92, '"': 34, "'": 39}

# Двухсимвольные знаки надо узнавать целиком, иначе << прочитается как < <
DOUBLES = ("<<", ">>", "//")


class LexError(Exception):
    pass


class Token(object):
    __slots__ = ("kind", "text", "value", "line")

    def __init__(self, kind, text, value, line):
        self.kind = kind
        self.text = text
        self.value = value
        self.line = line

    def __repr__(self):
        return "%s(%r)" % (self.kind, self.value if self.kind in
                           (NUMBER, CHAR) else self.text)


def _read_escape(s, i, line):
    """Разбирает \\n и подобное, возвращает (код, сколько съели)."""
    if i + 1 >= len(s):
        raise LexError("строка %d: обратная косая в конце" % line)
    c = s[i + 1]
    if c in ESCAPES:
        return ESCAPES[c], 2
    # Неизвестное экранирование оставляем как есть, как делает GNU as.
    # Проверено прогоном: `\q` и у него, и у нас даёт букву q.
    # ИЗВЕСТНАЯ ДЫРА: восьмеричного тут нет. `\015` настоящий as
    # собирает в возврат каретки, а мы отдаём ноль и дальше буквы 1 и 5.
    # Чинится отдельно, вместе с арифметикой в операндах.
    return ord(c), 2


def tokens(text):
    """Один проход по всему тексту. Возвращает список Token.

    Блочный комментарий умеет переходить со строки на строку, поэтому
    проход идёт по тексту целиком, а не построчно.
    """
    out = []
    i, line, n = 0, 1, len(text)
    while i < n:
        c = text[i]

        # --- перевод строки ---
        if c == "\n":
            out.append(Token(EOL, "\n", None, line))
            line += 1
            i += 1
            continue

        # --- пробелы ---
        if c in " \t\r":
            i += 1
            continue

        # --- блочный комментарий ---
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise LexError("строка %d: блочный комментарий не закрыт" % line)
            line += text.count("\n", i, end)
            i = end + 2
            continue

        # --- строчный комментарий: до конца строки, но НЕ дальше ---
        if text.startswith("//", i) or c == "#" or c == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue

        # --- строковый литерал ---
        if c == '"':
            j, buf = i + 1, bytearray()
            while True:
                if j >= n or text[j] == "\n":
                    raise LexError("строка %d: кавычка не закрыта" % line)
                if text[j] == "\\":
                    code, eaten = _read_escape(text, j, line)
                    buf.append(code)
                    j += eaten
                    continue
                if text[j] == '"':
                    break
                buf.extend(text[j].encode("utf-8"))
                j += 1
            out.append(Token(STRING, text[i:j + 1], bytes(buf), line))
            i = j + 1
            continue

        # --- символьный литерал ---
        if c == "'":
            if i + 1 >= n:
                raise LexError("строка %d: одиночная кавычка в конце" % line)
            if text[i + 1] == "\\":
                code, eaten = _read_escape(text, i + 1, line)
                j = i + 1 + eaten
            else:
                code = ord(text[i + 1])
                j = i + 2
            # Закрывающая кавычка не обязательна: GNU as принимает и 'A
            if j < n and text[j] == "'":
                j += 1
            out.append(Token(CHAR, text[i:j], code, line))
            i = j
            continue

        # --- число ---
        if c.isdigit():
            j = i
            if text.startswith("0x", i) or text.startswith("0X", i):
                j = i + 2
                while j < n and text[j] in "0123456789abcdefABCDEF_":
                    j += 1
            else:
                while j < n and (text[j].isdigit() or text[j] == "_"):
                    j += 1
            raw = text[i:j].replace("_", "")
            out.append(Token(NUMBER, text[i:j], int(raw, 0), line))
            i = j
            continue

        # --- слово: имя, метка, директива ---
        if c.isalpha() or c in "._$":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "._$"):
                j += 1
            out.append(Token(WORD, text[i:j], text[i:j], line))
            i = j
            continue

        # --- знаки ---
        two = text[i:i + 2]
        if two in DOUBLES:
            out.append(Token(PUNCT, two, two, line))
            i += 2
            continue
        out.append(Token(PUNCT, c, c, line))
        i += 1

    out.append(Token(EOL, "", None, line))
    return out


def read_lines(path):
    """Замена read_lines из asm.py. Та же форма: список (номер, текст).

    Метки отделяются, комментарии срезаны, но всё это сделано ПОСЛЕ
    того, как текст разобран на слова, а не до.
    """
    text = io.open(path, encoding="utf-8").read()
    out, cur, cur_line = [], [], None

    def flush():
        if not cur:
            return
        # Метки в начале логической строки отдаём отдельными записями
        k = 0
        while k + 1 < len(cur) and cur[k].kind == WORD and \
                cur[k + 1].kind == PUNCT and cur[k + 1].value == ":":
            out.append((cur_line, cur[k].text + ":"))
            k += 2
        rest = cur[k:]
        if rest:
            out.append((cur_line, _render(rest)))
        del cur[:]

    for t in tokens(text):
        if t.kind == EOL:
            flush()
            cur_line = None
            continue
        if cur_line is None:
            cur_line = t.line
        cur.append(t)
    flush()
    return out


def _render(toks):
    """Собирает слова обратно в строку для СТАРОГО разбора asm.py.

    Это мост, а не часть лексера. Лексер отдаёт `-` и `16` двумя
    словами, потому что решать, унарный это минус или вычитание, дело
    разбора, а не резки. Но старый asm.py разбора не имеет и ждёт
    готовое `-16`, поэтому мост склеивает их обратно.

    Первая версия моста этого не делала, и `addi sp, sp, -16` перестала
    собираться. Поймано приёмкой не сразу: сборка первой программы шла
    байт в байт, потому что отрицательных чисел в ней просто нет.

    Символьный литерал отдаётся числом: лексер его уже разобрал, а
    старый `parse_int` про кавычки ничего не знает.
    """
    # Минус унарный, если перед ним ничего нет или стоит знак, после
    # которого число начинается заново.
    UNARY_AFTER = (None, ",", "(", "+", "-", "*", "/", "|", "&", "<<", ">>")

    parts, prev = [], None
    i = 0
    while i < len(toks):
        t = toks[i]

        if t.kind == PUNCT and t.value == "-" and prev in UNARY_AFTER \
                and i + 1 < len(toks) and toks[i + 1].kind == NUMBER:
            parts.append("-" + toks[i + 1].text)
            prev = NUMBER
            i += 2
            continue

        if t.kind == STRING:
            parts.append(t.text)
        elif t.kind == CHAR:
            parts.append(str(t.value))
        elif t.kind == PUNCT and t.value in ",)":
            if parts:
                parts[-1] = parts[-1] + t.text
            else:
                parts.append(t.text)
        else:
            parts.append(t.text)

        prev = t.value if t.kind == PUNCT else t.kind
        i += 1

    return " ".join(parts).replace("( ", "(")
