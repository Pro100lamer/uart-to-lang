# Сборка и запуск стенда третьей статьи.
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

# Та же рекурсия без стека, возврат через регистр. Зависает навсегда.
broken: broken.elf
broken.elf: boot-broken.s link.ld
	$(CC) $(CFLAGS) -T link.ld -o $@ boot-broken.s

# Тот же код, но под стек 128 байт вместо 1024. Портит вывод и зависает.
small: small.elf
small.elf: boot.s link-small.ld
	$(CC) $(CFLAGS) -T link-small.ld -o $@ boot.s

# Считает вызовы и пик стека сам и печатает их. Откуда взялись 21891 и 320.
count: count.elf
count.elf: boot-count.s link.ld
	$(CC) $(CFLAGS) -T link.ld -o $@ boot-count.s

run-count: count.elf
	$(QEMU) $(QEMUFLAGS) -kernel count.elf

clean:
	rm -f $(TARGET) broken.elf small.elf count.elf

.PHONY: all run broken small count run-count clean
