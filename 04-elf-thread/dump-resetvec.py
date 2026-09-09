"""Сравнивает ПЕРЕХОДНИК по адресу 0x1000 при разных способах запуска.

Вопрос, ради которого написано: адрес, по которому машина стартует после
сброса, это свойство МАШИНЫ или свойство ФАЙЛА? На настоящем кристалле это
свойство машины и поменять его нельзя. Проверяем, для каких ключей QEMU это
так, а для каких он переписывает переходник под наш файл.

Дамп снимается через монитор работающей машины, программа не меняется.

Использование:  python dump-resetvec.py
"""

import socket
import subprocess
import sys
import time

PORT = 45460
QEMU = "qemu-system-riscv32"

# (подпись, аргументы запуска)
CASES = [
    ("-bios none -kernel hello.elf",       ["-bios", "none", "-kernel", "hello.elf"]),
    ("-bios none -kernel high.elf",        ["-bios", "none", "-kernel", "high.elf"]),
    ("-bios hello.elf",                    ["-bios", "hello.elf"]),
    ("-bios high.elf",                     ["-bios", "high.elf"]),
]


def dump(args, addr, count, port):
    """Возвращает count байт по адресу addr из работающей машины."""
    p = subprocess.Popen(
        [QEMU, "-machine", "virt", "-nographic"] + args +
        ["-serial", "null", "-monitor", f"tcp:127.0.0.1:{port},server,nowait"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        # Монитор поднимается не мгновенно, и на Windows заметно медленнее.
        # Стучимся, пока не откроется, вместо одной паузы наугад.
        s = None
        for _ in range(40):
            if p.poll() is not None:
                err = p.stderr.read().decode("utf-8", "replace").strip() if p.stderr else ""
                raise RuntimeError("QEMU не запустился: %s" % (err or "без вывода"))
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.25)
        if s is None:
            raise RuntimeError("монитор так и не открылся на порту %d" % port)
        s.settimeout(2)
        time.sleep(0.3)
        try:
            s.recv(65536)
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
        s.close()
        return out.decode("utf-8", "replace")
    finally:
        p.kill()
        p.wait()


def words(text):
    """Из вывода монитора достаёт байты и складывает в 32-битные слова."""
    bs = []
    for line in text.split("\n"):
        if ":" not in line:
            continue
        for tok in line.split(":", 1)[1].split():
            if tok.startswith("0x") and len(tok) == 4:
                bs.append(int(tok, 16))
    return [int.from_bytes(bytes(bs[i:i + 4]), "little")
            for i in range(0, len(bs) - 3, 4)]


def main():
    print("Переходник по 0x1000. Ключевое слово лежит по 0x1018:")
    print("именно его читает `lw t0, 24(t0)` перед прыжком.\n")
    port = PORT
    for label, args in CASES:
        text = dump(args, 0x1000, 48, port)
        port += 1
        w = words(text)
        if len(w) < 7:
            print("%-32s дамп не снялся" % label)
            continue
        print("%-32s слово по 0x1018 = 0x%08x" % (label, w[6]))
    print("\nЕсли число меняется вслед за файлом, значит запуск переписывает")
    print("переходник машины. На кристалле этот адрес зашит и не меняется.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
