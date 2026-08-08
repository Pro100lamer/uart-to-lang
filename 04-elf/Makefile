# Стенд четвёртой статьи: ELF и компоновщик.
# Перед запуском: source ../../scripts/env.sh
#
# Программа та же, что в третьей статье, и это нарочно: меняется не код,
# а только то, как его раскладывают по файлу.

CC    = riscv-none-elf-gcc
QEMU  = qemu-system-riscv32

CFLAGS    = -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles
QEMUFLAGS = -machine virt -nographic -bios none

all: hello.elf phdrs.elf assert.elf

# Как было в третьей статье: один сегмент на всё, отсюда и RWX.
hello.elf: boot.s link.ld
	$(CC) $(CFLAGS) -T link.ld -o $@ boot.s

# Сегменты объявлены руками, права раздельные, предупреждение уходит.
phdrs.elf: boot.s link-phdrs.ld
	$(CC) $(CFLAGS) -T link-phdrs.ld -o $@ boot.s

# То же плюс ASSERT: компоновщик сам сверяет размер стека.
assert.elf: boot.s link-assert.ld
	$(CC) $(CFLAGS) -T link-assert.ld -o $@ boot.s

run: assert.elf
	$(QEMU) $(QEMUFLAGS) -kernel assert.elf

# --- опыты, которые должны сломаться ---

# Ловушка лежит в .text первой, _start уезжает ниже. Печатает X.
decoy: decoy.elf
	$(QEMU) $(QEMUFLAGS) -kernel decoy.elf
decoy.elf: boot-decoy.s link.ld
	$(CC) $(CFLAGS) -T link.ld -o $@ boot-decoy.s

# Программа по 0x80100000. Вывода не будет вовсе.
high: high.elf
	$(QEMU) $(QEMUFLAGS) -kernel high.elf
high.elf: boot.s link-high.ld
	$(CC) $(CFLAGS) -T link-high.ld -o $@ boot.s

# Стек 128 байт при ASSERT на 736. Сборка обязана упасть.
small:
	-$(CC) $(CFLAGS) -T link-assert-small.ld -o small.elf boot.s

# Тот же исходник с ловушкой, но _start вынесен в .text.entry, и скрипт
# кладёт эту секцию первой. Порядок в файле перестаёт что-либо решать.
entry: entry.elf
	$(QEMU) $(QEMUFLAGS) -kernel entry.elf
entry.elf: boot-entry.s link-entry.ld
	$(CC) $(CFLAGS) -T link-entry.ld -o $@ boot-entry.s

# Портим в готовом ELF только точку входа и запускаем. Программа считает
# как ни в чём не бывало: поля для машины не существует.
broken-entry: broken-entry.elf
	riscv-none-elf-readelf -h broken-entry.elf | grep -i "entry point"
	$(QEMU) $(QEMUFLAGS) -kernel broken-entry.elf
broken-entry.elf: assert.elf break-entry.py
	python break-entry.py assert.elf $@

# --- заглянуть внутрь ---

elf: assert.elf
	riscv-none-elf-readelf -h assert.elf
	riscv-none-elf-readelf -S assert.elf
	riscv-none-elf-readelf -l assert.elf

# Переходник, который QEMU кладёт по 0x1000 у работающей машины.
resetvec: assert.elf
	python dump-mem.py assert.elf 0x1000 32

clean:
	rm -f *.elf *.txt resetvec.bin

.PHONY: all run decoy high small entry broken-entry elf resetvec clean
