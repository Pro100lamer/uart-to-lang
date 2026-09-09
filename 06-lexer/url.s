/* Программа, которая печатает адрес репозитория.
 *
 * Ничего особенного в ней нет: тот же скелет, что и в первой части серии.
 * Вся разница в одной строке данных, где внутри кавычек стоит `//`.
 *
 * Собранная СТАРЫМ разбором, она молчит. Собранная с лексером, печатает
 * адрес. Байты при этом отличаются не на пару штук: 40 против 84.
 *
 * Прогон: make url
 */

        .section .text
        .globl _start
_start:
        li   t0, 0x10000000     /* приёмник UART на machine virt */
        la   t1, message

next_char:
        lbu  t2, 0(t1)
        beqz t2, done
        sb   t2, 0(t0)
        addi t1, t1, 1
        j    next_char

done:
        wfi
        j    done

        .section .rodata
message:
        .string "https://github.com/Pro100lamer/uart-to-lang"
