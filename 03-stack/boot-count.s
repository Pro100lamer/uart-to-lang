/* То же самое, что boot.s, но программа заодно считает саму себя.

   В статье приведены два числа: 21891 вызов на fib(20) и 320 байт пика
   стека. Выдумывать их не хочется, поэтому вот версия, которая их меряет
   и печатает. Считает она себя сама, во время работы:

     calls   увеличивается в прологе fib, по одному на вызов;
     min_sp  запоминает самое нижнее значение sp, какое видел пролог.

   Пик считается как _stack_top минус min_sp. Меряется только рекурсия:
   кадры печати живут отдельно от неё и глубже одного не вкладываются,
   так что на пик не влияют.

   Второй, независимый способ: перед стартом весь стек заливается одним и тем же
   байтом 0xaa, а после работы ищется самый нижний байт, который остался
   нетронутым. Он даёт на четыре байта меньше, и это не ошибка: пролог не
   пишет в нижние четыре байта кадра, они добиты для выравнивания. Заливка
   там уцелела, хотя место занято.

   У заливки есть и настоящая слабость: она показывает не «докуда дошёл
   стек», а «что перестало быть 0xaa». Затереть эти байты мог кто угодно, а
   байт, случайно совпавший с 0xaa, засчитается свободным.

   Учёт стоит восемь строк в прологе (десять инструкций после разворота
   псевдокоманд la) и на результат не влияет. В основной стенд он не
   вынесен: там нужен чистый пример, а не пример с обвязкой.

   Собрать и запустить:  make count && make run-count
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

_start:
    /* Заливаем весь стек байтом 0xaa. Делать это можно только до того,
       как в sp что-то положено: своих кадров у нас ещё нет, портить
       нечего. Байт выбран так, чтобы узнаваться в дампе глазом. */
    la      t0, _stack_bottom
    la      t1, _stack_top
    li      t2, 0xaa
1:  sb      t2, 0(t0)
    addi    t0, t0, 1
    bltu    t0, t1, 1b

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

    /* Счётчики: вызовов ноль, самая нижняя точка пока что вершина. */
    la      t0, calls
    sw      zero, 0(t0)
    la      t0, min_sp
    la      t1, _stack_top
    sw      t1, 0(t0)

    la      a0, msg_fib20
    jal     ra, print_str
    li      a0, 20
    jal     ra, fib
    mv      s7, a0              /* результат придержим: сначала замер */

    /* Второй способ измерить пик, независимый от счётчика в прологе.
       Ищем снизу вверх первый байт, который перестал быть 0xaa. */
    la      t0, _stack_bottom
    la      t1, _stack_top
    li      t2, 0xaa
1:  lbu     t3, 0(t0)
    bne     t3, t2, 2f
    addi    t0, t0, 1
    bltu    t0, t1, 1b
2:  sub     s8, t1, t0          /* сколько байт заливки съедено */

    mv      a0, s7
    jal     ra, print_dec
    la      a0, msg_nl
    jal     ra, print_str

    /* Сколько вызовов получилось. */
    la      a0, msg_calls
    jal     ra, print_str
    la      t0, calls
    lw      a0, 0(t0)
    jal     ra, print_dec
    la      a0, msg_nl
    jal     ra, print_str

    /* Насколько глубоко ушёл стек. */
    la      a0, msg_peak
    jal     ra, print_str
    la      t0, min_sp
    lw      t1, 0(t0)
    la      t2, _stack_top
    sub     a0, t2, t1
    jal     ra, print_dec
    la      a0, msg_bytes
    jal     ra, print_str

    /* И то же самое, измеренное заливкой. */
    la      a0, msg_paint
    jal     ra, print_str
    mv      a0, s8
    jal     ra, print_dec
    la      a0, msg_bytes
    jal     ra, print_str

done:
    wfi
    j       done


/* fib с учётом. Всё, кроме восьми строк после пролога, как в boot.s. */
fib:
    addi    sp, sp, -16
    sw      ra, 12(sp)
    sw      s3, 8(sp)
    sw      s4, 4(sp)

    /* Учёт. t0..t2 временные, портить их можно свободно. */
    la      t0, calls
    lw      t1, 0(t0)
    addi    t1, t1, 1
    sw      t1, 0(t0)
    la      t0, min_sp
    lw      t1, 0(t0)
    bgeu    sp, t1, 1f          /* адреса сравниваем беззнаково */
    sw      sp, 0(t0)
1:

    li      t0, 2
    blt     a0, t0, fib_base

    mv      s3, a0

    addi    a0, s3, -1
    jal     ra, fib
    mv      s4, a0

    addi    a0, s3, -2
    jal     ra, fib

    add     a0, a0, s4

fib_return:
    lw      ra, 12(sp)
    lw      s3, 8(sp)
    lw      s4, 4(sp)
    addi    sp, sp, 16
    ret

fib_base:
    j       fib_return


putc:
1:  lbu     t0, UART_LSR(s0)
    andi    t0, t0, LSR_THRE
    beqz    t0, 1b
    sb      a1, UART_THR(s0)
    ret


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
    li      t2, 0
2:  blt     a0, t1, 2f
    sub     a0, a0, t1
    addi    t2, t2, 1
    j       2b
2:  addi    a0, a0, '0'
    addi    s6, s6, -1
    sb      a0, 0(s6)
    mv      a0, t2
    j       1b

3:  mv      a0, s6
    lw      ra, 12(sp)
    lw      s6, 8(sp)
    addi    sp, sp, 16
    j       print_str


    .section .rodata
msg_fib20:
    .string "fib(20) = "
msg_calls:
    .string "вызовов: "
msg_peak:
    .string "пик по счётчику: "
msg_paint:
    .string "пик по заливке: "
msg_bytes:
    .string " байт\n"
msg_nl:
    .string "\n"

    .section .bss
    .align 2
numbuf:
    .space 16
calls:
    .space 4
min_sp:
    .space 4
