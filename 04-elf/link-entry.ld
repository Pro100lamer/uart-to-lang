/* Итоговый скрипт компоновщика: всё, что разобрано в четвёртой статье.
 *
 * Что здесь есть сверх обычного примера из интернета:
 *
 *   PHDRS         сегменты объявлены руками, права раздельные. Без этого
 *                 весь файл попадает в один LOAD с правами RWE, и
 *                 компоновщик ругается на RWX.
 *   .text.entry   точка входа кладётся первой явно, а не по везению.
 *                 Машина прыгает на фиксированный адрес и точку входа из
 *                 заголовка ELF не читает, так что важно, что там лежит.
 *   ASSERT        компоновщик сам сверяет размер стека при каждой сборке.
 *                 Не влезло: сборка падает, ELF не создаётся.
 *
 * Что менять под себя:
 *   ORIGIN и LENGTH   карта памяти вашей машины;
 *   . += 1024         нужный размер стека;
 *   736 в ASSERT      ваш посчитанный худший случай.
 *
 * И в исходнике объявить точку входа так:
 *     .section .text.entry
 *     .globl _start
 *   _start:
 */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

/* Имя, тип и права. 4 это R, 2 это W, 1 это X. */
PHDRS
{
    text   PT_LOAD FLAGS(5);    /* R + X */
    rodata PT_LOAD FLAGS(4);    /* R     */
    data   PT_LOAD FLAGS(6);    /* R + W */
}

SECTIONS
{
    .text   : { *(.text.entry) *(.text) *(.text.*) } > RAM :text
    .rodata : { *(.rodata) *(.rodata.*) }            > RAM :rodata
    .bss    : { *(.bss) *(.bss.*) }                  > RAM :data

    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . += 1024;
        . = ALIGN(16);
        _stack_top = .;
    } > RAM :data

    /* Худший случай нашей рекурсии: fib(46) это 46 кадров по 16 байт. */
    ASSERT(_stack_top - _stack_bottom >= 736, "stack too small for fib(46)")
}
