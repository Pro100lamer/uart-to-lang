/* Стек, вызовы функций и соглашение о вызовах.

   Во второй статье подпрограммы возвращались каждая через свой регистр,
   потому что сохранять адрес возврата было некуда. Приём работал ровно
   до тех пор, пока вызовы не начали вкладываться друг в друга по-
   настоящему.

   Здесь считаем числа Фибоначчи рекурсивно. Взяты они не случайно:
   fib(n) = fib(n-1) + fib(n-2), то есть два вызова из одной функции,
   и между ними надо не потерять промежуточный результат. Без стека это
   не работает никак.

   Умножения в RV32I нет, как не было деления, поэтому Фибоначчи ещё и
   удобны: там одно сложение.
*/

    .equ UART_BASE,  0x10000000
    .equ UART_THR,   0
    .equ UART_DLM,   1
    .equ UART_LCR,   3
    .equ UART_LSR,   5

    .equ LCR_DLAB,   0x80
    .equ LCR_8N1,    0x03
    .equ LSR_THRE,   0x20
    .equ DIVISOR,    1

    .section .text
    .globl _start

/* ЛОВУШКА. Лежит в .text первой, то есть попадает по 0x80000000.
   Печатает X и встаёт. Если процессор придёт сюда, мы это увидим. */
decoy:
    li      t0, 0x10000000
    li      t1, 'X'
    sb      t1, 0(t0)
    li      t1, 10
    sb      t1, 0(t0)
1:  wfi
    j       1b

_start:
    /* Первым делом стек. До этой строки вызывать ничего нельзя:
       sp содержит мусор, и любой пролог функции запишет кадр по
       случайному адресу. */
    la      sp, _stack_top

    li      s0, UART_BASE

    li      t0, LCR_DLAB
    sb      t0, UART_LCR(s0)
    li      t0, DIVISOR
    sb      t0, UART_THR(s0)
    li      t0, 0
    sb      t0, UART_DLM(s0)
    li      t0, LCR_8N1
    sb      t0, UART_LCR(s0)

    /* Первые десять чисел, чтобы было видно последовательность. */
    la      a0, msg_row
    jal     ra, print_str

    li      s1, 1               /* счётчик n */
    li      s2, 11              /* до скольки считаем */
row_loop:
    mv      a0, s1
    jal     ra, fib
    jal     ra, print_dec
    la      a0, msg_space
    jal     ra, print_str
    addi    s1, s1, 1
    blt     s1, s2, row_loop

    la      a0, msg_nl
    jal     ra, print_str

    /* Одно число побольше: тут рекурсия развернётся в тысячи вызовов. */
    la      a0, msg_fib20
    jal     ra, print_str
    li      a0, 20
    jal     ra, fib
    jal     ra, print_dec
    la      a0, msg_nl
    jal     ra, print_str

done:
    wfi
    j       done


/* fib: принимает n в a0, возвращает fib(n) в a0.

   Соглашение о вызовах RISC-V, всё как у взрослых:
     a0..a7  аргументы и возвращаемое значение,
     ra      адрес возврата,
     t0..t6  временные, вызванная функция может их портить,
     s0..s11 сохраняемые, вызванная функция обязана вернуть как было.

   Имена эти живут не в наборе команд, а в psABI: процессор знает только
   x0..x31. Оттуда же и правило держать sp кратным 16, и направление
   роста стека вниз.

   Нам нужно пережить два вложенных вызова, поэтому кадр хранит три
   вещи: адрес возврата, наш n и результат первого вызова. */
fib:
    addi    sp, sp, -16         /* выделяем кадр, стек растёт вниз */
    sw      ra, 12(sp)          /* адрес возврата: его затрёт первый же jal */
    sw      s3, 8(sp)           /* s3 сохраняемый, вернём как было */
    sw      s4, 4(sp)

    li      t0, 2
    blt     a0, t0, fib_base    /* fib(0) = 0, fib(1) = 1, возвращаем как есть */

    mv      s3, a0              /* запомнили n */

    addi    a0, s3, -1
    jal     ra, fib             /* fib(n-1) */
    mv      s4, a0              /* результат надо пережить второй вызов */

    addi    a0, s3, -2
    jal     ra, fib             /* fib(n-2) */

    add     a0, a0, s4          /* складываем */

fib_return:
    lw      ra, 12(sp)          /* восстанавливаем всё, что обещали */
    lw      s3, 8(sp)
    lw      s4, 4(sp)
    addi    sp, sp, 16          /* и отдаём кадр обратно */
    ret

fib_base:
    j       fib_return          /* a0 уже содержит ответ */


/* putc: печатает байт из a1. Теперь обычная функция с ra и стеком. */
putc:
1:  lbu     t0, UART_LSR(s0)
    andi    t0, t0, LSR_THRE
    beqz    t0, 1b
    sb      a1, UART_THR(s0)
    ret


/* print_str: печатает строку, адрес в a0. */
print_str:
    addi    sp, sp, -16
    sw      ra, 12(sp)
    sw      s5, 8(sp)
    mv      s5, a0
1:  lbu     a1, 0(s5)
    beqz    a1, 2f
    jal     ra, putc
    addi    s5, s5, 1
    j       1b
2:  lw      ra, 12(sp)
    lw      s5, 8(sp)
    addi    sp, sp, 16
    ret


/* print_dec: печатает беззнаковое число из a0.
   Деления в RV32I нет, поэтому делим вычитанием, как во второй статье. */
print_dec:
    addi    sp, sp, -16
    sw      ra, 12(sp)
    sw      s6, 8(sp)

    la      s6, numbuf
    addi    s6, s6, 15
    sb      zero, 0(s6)

    bnez    a0, 1f
    addi    s6, s6, -1
    li      t0, '0'
    sb      t0, 0(s6)
    j       3f

1:  beqz    a0, 3f
    li      t1, 10
    li      t2, 0               /* частное */
2:  blt     a0, t1, 2f
    sub     a0, a0, t1
    addi    t2, t2, 1
    j       2b
2:  addi    a0, a0, '0'         /* остаток превращаем в цифру */
    addi    s6, s6, -1
    sb      a0, 0(s6)
    mv      a0, t2
    j       1b

3:  mv      a0, s6
    lw      ra, 12(sp)
    lw      s6, 8(sp)
    addi    sp, sp, 16
    j       print_str           /* хвостовой вызов: печатаем собранное */


    .section .rodata
msg_row:
    .string "fib(1..10): "
msg_fib20:
    .string "fib(20) = "
msg_space:
    .string " "
msg_nl:
    .string "\n"

    .section .bss
    .align 2
numbuf:
    .space 16
