# Опыты, родившиеся в комментариях к четвёртой статье.
#
# Отдельный каталог, а не правка соседнего, нарочно. Тег article-04 это
# снимок того, что описано в статье. Всё, что появилось после выхода,
# лежит здесь и в тег не попадает.
#
# Исходники и скрипты компоновщика берутся из ../04-elf: копий не держим,
# иначе они разойдутся.
#
# Перед запуском: source ../../scripts/env.sh

CC    = riscv-none-elf-gcc
QEMU  = qemu-system-riscv32

SRC   = ../04-elf
CFLAGS    = -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles
QEMUFLAGS = -machine virt -nographic -bios none

# Программы не завершаются сами, поэтому каждый запуск обёрнут в timeout.
# Без него цель висит до Ctrl-A X, и так по четыре раза подряд.
T = 3

all: loader

# Ловушка печатает X по 0x80000000, точка входа в заголовке 0x8000001c.
decoy.elf: $(SRC)/boot-decoy.s $(SRC)/link.ld
	$(CC) $(CFLAGS) -T $(SRC)/link.ld -o $@ $(SRC)/boot-decoy.s

# Та же программа, собранная по 0x80100000.
high.elf: $(SRC)/boot.s $(SRC)/link-high.ld
	$(CC) $(CFLAGS) -T $(SRC)/link-high.ld -o $@ $(SRC)/boot.s

hello.elf: $(SRC)/boot.s $(SRC)/link.ld
	$(CC) $(CFLAGS) -T $(SRC)/link.ld -o $@ $(SRC)/boot.s

# ЧЕТЫРЕ СПОСОБА ЗАПУСКА НА ОДНОМ ФАЙЛЕ.
#
# ВНИМАНИЕ на -bios none в первых трёх строках. Без него QEMU подставит
# свой OpenSBI, и на экране будет его баннер, а не наш вывод. Я на этом
# один раз споткнулся и чуть не опубликовал бессмысленную таблицу.
loader: decoy.elf
	@echo "--- -kernel: ждём X, машина идёт по адресу из ПЗУ"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -kernel decoy.elf
	@echo ""
	@echo "--- -device loader без cpu-num: тоже X, счётчик команд не тронут"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=decoy.elf
	@echo ""
	@echo "--- -device loader с cpu-num=0: числа, взята точка входа"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=decoy.elf,cpu-num=0
	@echo ""
	@echo "--- -bios: числа. Подсказал maquefel в треде"
	-@timeout $(T) $(QEMU) -machine virt -nographic -bios decoy.elf
	@echo ""

# Третья форма loader: addr без file принудительно задаёт reset-vector.
# Подсказал maquefel, проверено.
force: decoy.elf
	@echo "--- только загрузка: ждём X"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=decoy.elf
	@echo ""
	@echo "--- плюс принудительный reset-vector на _start: ждём числа"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=decoy.elf \
	    -device loader,addr=0x8000001c,cpu-num=0
	@echo ""

# Слово по 0x1018, которое переходник машины читает перед прыжком.
# Показывает, что под -kernel адрес старта от файла не зависит вовсе,
# а -bios переписывает его адресом из заголовка.
resetvec: hello.elf high.elf
	python dump-resetvec.py

clean:
	rm -f *.elf *.txt

.PHONY: all loader force resetvec clean
