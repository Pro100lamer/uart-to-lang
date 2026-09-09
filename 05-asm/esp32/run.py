# -*- coding: utf-8 -*-
"""Прошить образ в ESP32 и снять то, что плата скажет в ответ.

Ничего не гадает: сбрасывает плату сам, слушает порт заданное время и
печатает всё, что пришло. Порт можно задать переменной ESP_PORT.

    python run.py hello.bin
    ESP_PORT=COM7 python run.py nowait.bin 4
"""

import os
import subprocess
import sys
import time

import serial


def flash(port, image):
    # --after no-reset: сбрасывать будем сами, иначе первые байты
    # программы уйдут раньше, чем мы успеем открыть порт.
    cmd = [sys.executable, "-m", "esptool", "--port", port, "--baud", "460800",
           "--after", "no-reset", "write-flash", "0x1000", image]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        sys.stdout.write(out)
        raise SystemExit("прошивка не удалась")
    for line in out.splitlines():
        if "Hash of data" in line or "Wrote " in line:
            print("  " + line.strip())


def listen(port, seconds):
    sp = serial.Serial(port, 115200, timeout=0.1)
    # dtr=False держит IO0 высоко: обычный запуск, а не загрузчик.
    # rts=True роняет EN, то есть держит кристалл в сбросе.
    sp.dtr = False
    sp.rts = True
    time.sleep(0.15)
    sp.reset_input_buffer()
    sp.rts = False
    end = time.time() + seconds
    data = b""
    while time.time() < end:
        data += sp.read(4096)
    sp.close()
    return data.decode("utf-8", "replace")


def main():
    # Рваный вывод из nowait содержит что угодно, и консоль Windows на
    # cp1251 на нём падает. Заставляем поток не спотыкаться.
    rc = getattr(sys.stdout, "reconfigure", None)
    if rc is not None:
        rc(encoding="utf-8", errors="replace")

    image = sys.argv[1] if len(sys.argv) > 1 else "hello.bin"
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    port = os.environ.get("ESP_PORT", "COM4")

    print("прошиваю %s по адресу 0x1000, порт %s" % (image, port))
    flash(port, image)
    print("слушаю %g с" % seconds)
    print("-" * 60)
    sys.stdout.write(listen(port, seconds))
    print()
    print("-" * 60)


if __name__ == "__main__":
    main()
