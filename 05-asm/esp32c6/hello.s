# Первая программа серии на живом ESP32-C6 (RISC-V).
#
# Тот же цикл, что в work/01-hello/boot.s: взять байт, положить
# в UART, сдвинуться, повторить. Набор команд тот же: RV32I.
#
# Вывод через UART0 (GPIO16 TX, GPIO17 RX), слушаем на CH340 (COM4).
# ПЗУ настраивает UART0 на 115200 перед загрузкой, мы только пишем.
#
# Сторожевой таймер (TG0 WDT) отключаем первым делом.

        .equ    UART0_FIFO,   0x60000000
        .equ    UART0_STATUS, 0x6000001C   # txfifo_cnt в битах 16..23

        .equ    TG0_WDTCONFIG0,  0x60008048
        .equ    TG0_WDTWPROTECT, 0x60008064
        .equ    WDT_UNLOCK_KEY,  0x50D83AA1

        .section .text
        .global _start
_start:
        # --- отключаем сторожевой таймер TG0 ---
        lui     a5, %hi(TG0_WDTWPROTECT)
        addi    a5, a5, %lo(TG0_WDTWPROTECT)
        lui     a6, %hi(WDT_UNLOCK_KEY)
        addi    a6, a6, %lo(WDT_UNLOCK_KEY)
        sw      a6, 0(a5)
        lui     a5, %hi(TG0_WDTCONFIG0)
        addi    a5, a5, %lo(TG0_WDTCONFIG0)
        sw      zero, 0(a5)

        la      a0, message
        lui     a1, 0x60000         # a1 = 0x60000000, база UART0

next_char:
        lbu     a3, 0(a0)
        beqz    a3, done

wait_tx:
        lw      a4, 0x1C(a1)        # UART_STATUS_REG
        srli    a4, a4, 16          # txfifo_cnt в битах 16..23
        andi    a4, a4, 0xFF
        bnez    a4, wait_tx

        sw      a3, 0(a1)           # UART0_FIFO
        addi    a0, a0, 1
        j       next_char

done:
        j       done

        .section .rodata
message:
        .ascii  "\xd0\x9f\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82"
        .ascii  " \xd1\x81 "
        .ascii  "\xd0\xb6\xd0\xb5\xd0\xbb\xd0\xb5\xd0\xb7\xd0\xb0!"
        .byte   13, 10, 0
