# Собирает два варианта вывода в UART с настройкой скорости линии.
# naive  — пишет в THR не спрашивая;
# polled — ждёт THRE перед каждым байтом.
#
# Обе версии в конце гасят QEMU через тестовое устройство SiFive
# по адресу 0x100000 (запись 0x5555 = штатное завершение), иначе
# программа висит в бесконечном цикле и время замерить нечем.

import io
import sys

DIV = int(sys.argv[1])
DLL = DIV & 0xFF
DLM = (DIV >> 8) & 0xFF

MSG = ("0123456789 " * 20).strip() + " КОНЕЦ\\n"

TEMPLATE = """    .section .text
    .globl _start

_start:
    li      t0, 0x10000000

    /* Настройка скорости линии, как на железе.
       LCR бит 7 (DLAB) открывает доступ к делителю, делитель лежит
       по смещениям 0 и 1, затем DLAB снимаем и задаём формат 8N1.
       Делитель {div}: чем больше, тем медленнее линия. */
    li      t4, 0x80
    sb      t4, 3(t0)
    li      t4, {dll}
    sb      t4, 0(t0)
    li      t4, {dlm}
    sb      t4, 1(t0)
    li      t4, 0x03
    sb      t4, 3(t0)

    la      t1, message

next_char:
    lbu     t2, 0(t1)
    beqz    t2, done
{send}
    addi    t1, t1, 1
    j       next_char

done:
    /* Пауза перед выходом. Без неё QEMU гаснет раньше, чем backend
       успевает сбросить буфер на диск, и последние байты пропадают.
       Это артефакт замера, а не поведение UART: путать их нельзя. */
    li      t5, 30000000
wait_flush:
    addi    t5, t5, -1
    bnez    t5, wait_flush

    /* Гасим QEMU: тестовое устройство машины virt. */
    li      t0, 0x100000
    li      t1, 0x5555
    sw      t1, 0(t0)
1:  wfi
    j       1b

    .section .rodata
message:
    .string "{msg}"
"""

NAIVE_SEND = "    sb      t2, 0(t0)"

POLLED_SEND = """wait_thre:
    lbu     t3, 5(t0)           /* LSR */
    andi    t3, t3, 0x20        /* THRE: передатчик свободен */
    beqz    t3, wait_thre
    sb      t2, 0(t0)"""

for name, send in (("naive", NAIVE_SEND), ("polled", POLLED_SEND)):
    src = TEMPLATE.format(div=DIV, dll=DLL, dlm=DLM, send=send, msg=MSG)
    io.open(f"{name}.s", "w", encoding="utf-8", newline="\n").write(src)
