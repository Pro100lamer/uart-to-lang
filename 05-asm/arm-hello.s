@ Тот же скелет, что в первой программе серии, на ARM (32-битный, A32).
@ Программа не запускается и не должна: сравниваем МНЕМОНИКИ.
@
@ Интересных мест два, оба видны в дизассемблере:
@   ldr r1, =message  превращается в ldr r1,[pc,#N] ПЛЮС слово данных,
@                     которое ассемблер дописывает в конец кода. И адрес
@                     в это слово подставляет уже компоновщик;
@   nop               собирается как mov r0, r0.

    .section .text
    .globl _start
_start:
    ldr     r1, =message
    mov     r0, #1
next_char:
    ldrb    r2, [r1]
    cmp     r2, #0
    beq     done
    add     r1, r1, #1
    b       next_char
done:
    nop
    bx      lr

    .section .rodata
message:
    .asciz "Privet"
