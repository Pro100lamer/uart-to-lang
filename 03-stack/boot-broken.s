/* Так делать нельзя, и это тут показано специально.

   Приём из второй статьи: адрес возврата кладём в свободный регистр,
   стека нет. Для цепочки вызовов он работал. Попробуем ту же рекурсию.

   fib вызывает саму себя. Первый же вложенный вызов кладёт в тот же
   регистр свой адрес возврата и затирает адрес возврата внешнего
   вызова. Вернуться туда, откуда пришли, больше некуда.

   Собирается и запускается. Смотрите, что выведет. */

    .equ UART_BASE,  0x10000000
    .equ UART_THR,   0
    .equ UART_LCR,   3
    .equ UART_LSR,   5
    .equ LCR_8N1,    0x03
    .equ LSR_THRE,   0x20

    .section .text
    .globl _start

_start:
    li      s0, UART_BASE
    li      t0, LCR_8N1
    sb      t0, UART_LCR(s0)

    la      a0, msg
    jal     t4, print_str

    li      a0, 5               /* fib(5) должно быть 5 */
    jal     t5, fib_broken

    /* Печатаем результат как одну цифру: если досюда дойдём, конечно. */
    addi    a1, a0, '0'
    jal     t6, putc

    la      a0, msg_nl
    jal     t4, print_str

done:
    wfi
    j       done


/* fib_broken: возврат через t5, как во второй статье.
   Именно здесь всё и ломается. */
fib_broken:
    li      t0, 2
    blt     a0, t0, fb_ret      /* fib(0)=0, fib(1)=1 */

    mv      t1, a0              /* n во временный регистр */

    addi    a0, t1, -1
    jal     t5, fib_broken      /* ЗДЕСЬ t5 затирается адресом возврата
                                   вложенного вызова, и адрес, по которому
                                   надо было вернуться наружу, потерян */
    mv      t2, a0

    addi    a0, t1, -2
    jal     t5, fib_broken

    add     a0, a0, t2

fb_ret:
    jr      t5


putc:
1:  lbu     t0, UART_LSR(s0)
    andi    t0, t0, LSR_THRE
    beqz    t0, 1b
    sb      a1, UART_THR(s0)
    jr      t6


print_str:
1:  lbu     a1, 0(a0)
    beqz    a1, 2f
    jal     t6, putc
    addi    a0, a0, 1
    j       1b
2:  jr      t4


    .section .rodata
msg:
    .string "fib(5) без стека = "
msg_nl:
    .string "\n"
