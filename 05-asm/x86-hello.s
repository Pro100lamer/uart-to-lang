# Тот же скелет, что в первой программе серии на RISC-V, только на x86-64:
# загрузить адрес строки, взять байт, сравнить с нулём, сдвинуться,
# прыгнуть назад.
#
# Программа не запускается и не должна: она нужна, чтобы сравнить МНЕМОНИКИ.
# Вопрос один: сколько строк из написанных процессор выполняет как есть.
# На RISC-V из девяти строк настоящих было четыре.

    .section .text
    .globl _start
_start:
    lea     message(%rip), %rsi
    mov     $1, %rdi
next_char:
    movzbl  (%rsi), %eax
    test    %al, %al
    je      done
    mov     %al, %dl
    inc     %rsi
    jmp     next_char
done:
    ret
    nop

    .section .rodata
message:
    .string "Privet\n"
