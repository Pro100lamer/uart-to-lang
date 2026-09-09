// Опыт: можно ли читать память КОМАНД по одному байту.
// Строка лежит не в памяти данных, а прямо в коде, следом за ним.
// Ожидаемый ответ кристалла: Fatal exception (3): LoadStoreError,
// причём excvaddr укажет ровно на адрес строки.
        .set    FIFO, 0x60000000
        .section .text
        .global _start
_start:
        movi    a4, FIFO
        movi    a5, 91              // '['
        s32i    a5, a4, 0
        movi    a3, message
        l8ui    a5, a3, 0           // байт из памяти КОМАНД
        s32i    a5, a4, 0
        movi    a5, 93              // ']'
        s32i    a5, a4, 0
done:   j       done

        .align  4
message:
        .asciz "Privet"
