"""Портит в готовом ELF ровно одно поле: точку входа.

Программа не пересобирается, байты кода и данных не двигаются, меняются
4 байта заголовка. Это самый прямой способ проверить, читает ли машина
это поле вообще.

Смещение 24 это e_entry в 32-битном ELF: 16 байт e_ident, потом e_type (2),
e_machine (2), e_version (4), и дальше e_entry.

Использование:  python break-entry.py assert.elf broken-entry.elf
"""

import io
import struct
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "assert.elf"
dst = sys.argv[2] if len(sys.argv) > 2 else "broken-entry.elf"

b = bytearray(io.open(src, "rb").read())
was = struct.unpack_from("<I", b, 24)[0]
struct.pack_into("<I", b, 24, 0xDEADBEEF)
io.open(dst, "wb").write(bytes(b))

print("%s: e_entry было 0x%08x, стало 0xdeadbeef" % (dst, was))
print("всё остальное в файле не тронуто")
