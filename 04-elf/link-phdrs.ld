OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

/* Сегменты объявляем сами: имя, тип и права. 4 это R, 2 это W, 1 это X. */
PHDRS
{
    text   PT_LOAD FLAGS(5);    /* R + X */
    rodata PT_LOAD FLAGS(4);    /* R     */
    data   PT_LOAD FLAGS(6);    /* R + W */
}

SECTIONS
{
    .text   : { *(.text) *(.text.*) }     > RAM :text
    .rodata : { *(.rodata) *(.rodata.*) } > RAM :rodata
    .bss    : { *(.bss) *(.bss.*) }       > RAM :data

    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . += 1024;
        . = ALIGN(16);
        _stack_top = .;
    } > RAM :data
}
