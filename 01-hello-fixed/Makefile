# Сборка и запуск первой программы.
# Перед запуском: source ../../scripts/env.sh

CC     = riscv-none-elf-gcc
QEMU   = qemu-system-riscv32
TARGET = hello.elf

# rv32i    — только базовые целочисленные инструкции, никаких расширений
# ilp32    — соглашение о вызовах для 32 бит
# nostdlib — стандартной библиотеки нет и не будет
# nostartfiles — стартовый код тоже наш, точка входа _start в boot.s
CFLAGS = -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles

# virt      — машина, которую эмулируем
# nographic — весь ввод-вывод в терминал
# bios none — без прошивки OpenSBI, иначе управление получит она, а не мы
QEMUFLAGS = -machine virt -nographic -bios none

all: $(TARGET)

$(TARGET): boot.s link.ld
	$(CC) $(CFLAGS) -T link.ld -o $@ boot.s

# Выход из QEMU: Ctrl-A, затем X
run: $(TARGET)
	$(QEMU) $(QEMUFLAGS) -kernel $(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: all run clean
