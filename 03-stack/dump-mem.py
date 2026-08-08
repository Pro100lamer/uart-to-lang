"""Снимает дамп памяти работающей машины через монитор QEMU.

Программа не меняется, значит и адреса не съезжают: дамп берётся ровно с
той сборки, о которой идёт речь в статье.

Использование:  python dump-mem.py <elf> <адрес> [сколько байт]
"""

import socket
import subprocess
import sys
import time

elf = sys.argv[1]
addr = int(sys.argv[2], 0)
count = int(sys.argv[3]) if len(sys.argv) > 3 else 16
port = 45454

qemu = subprocess.Popen(
    ["qemu-system-riscv32", "-machine", "virt", "-nographic", "-bios", "none",
     "-kernel", elf, "-serial", "null",
     "-monitor", f"tcp:127.0.0.1:{port},server,nowait"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    time.sleep(2.5)          # даём программе досчитать и повиснуть
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.settimeout(2)
    time.sleep(0.3)
    try:
        s.recv(65536)        # приветствие монитора
    except socket.timeout:
        pass
    s.sendall(f"xp/{count}xb 0x{addr:08x}\n".encode())
    time.sleep(0.6)
    out = b""
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except socket.timeout:
        pass
    s.sendall(b"quit\n")
    s.close()
    print(out.decode(errors="replace"))
finally:
    qemu.kill()
    qemu.wait()
