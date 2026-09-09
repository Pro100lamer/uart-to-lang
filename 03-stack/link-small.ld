/* То же самое, что link.ld, но под стек отведено 128 байт вместо 1024.

   Это опыт из статьи. Пику fib(20) нужно 320 байт, так что 128 заведомо
   мало. Интересно тут не то, что программа сломается, а то, что про стек
   не скажет никто: ни компоновщик при сборке, ни процессор при работе.
   Предупреждение про RWX у сегмента вылезет, но оно про другое и точно
   так же вылезает на исправной сборке.

   Собрать и посмотреть:

     riscv-none-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles \
         -T link-small.ld -o small.elf boot.s
     qemu-system-riscv32 -machine virt -nographic -bios none -kernel small.elf

   Первые десять чисел напечатаются верно, дальше в поток полезет мусор,
   и программа зависнет. Что именно затёрлось, видно по адресам:

     riscv-none-elf-nm -n small.elf

   Кадры уезжают ниже _stack_bottom прямо на numbuf и на строки в .rodata. */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

SECTIONS
{
    .text : {
        *(.text)
        *(.text.*)
    } > RAM

    .rodata : {
        *(.rodata)
        *(.rodata.*)
    } > RAM

    .bss : {
        *(.bss)
        *(.bss.*)
    } > RAM

    /* Вот и вся разница с link.ld: 128 вместо 1024. */
    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . += 128;
        . = ALIGN(16);
        _stack_top = .;
    } > RAM
}
