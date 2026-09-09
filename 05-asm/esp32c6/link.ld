/* ESP32-C6, RISC-V. Карта памяти HP-ядра:
 *   HP SRAM: 0x40800000..0x40880000 (512 КБ, код и данные на одной шине).
 *
 * В отличие от ESP32 (Xtensa), здесь побайтовое чтение из памяти
 * команд разрешено: шина единая.
 */

MEMORY
{
    ram (rwx) : ORIGIN = 0x40800000, LENGTH = 0x20000
}

ENTRY(_start)

SECTIONS
{
    .text :
    {
        *(.text .text.*)
    } > ram

    .rodata :
    {
        *(.rodata .rodata.*)
    } > ram

    .data :
    {
        *(.data .data.*)
    } > ram
}
