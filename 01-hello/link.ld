/* Карта памяти для машины virt в QEMU.
   ОЗУ у неё начинается с 0x80000000 — туда и кладём всё, что у нас есть. */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

SECTIONS
{
    /* .text идёт первой, поэтому _start окажется ровно по 0x80000000 —
       по адресу, куда QEMU передаст управление. */
    .text : {
        *(.text)
        *(.text.*)
    } > RAM

    .rodata : {
        *(.rodata)
        *(.rodata.*)
    } > RAM
}
