# Стенд пятой статьи: собственный ассемблер.
#
# Перед запуском: source ../../scripts/env.sh
#
# Программы не завершаются сами, поэтому запуски обёрнуты в timeout.

CC    = riscv-none-elf-gcc
AS    = riscv-none-elf-as
OBJC  = riscv-none-elf-objcopy
OBJD  = riscv-none-elf-objdump
QEMU  = qemu-system-riscv32

CFLAGS    = -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles
QEMUFLAGS = -machine virt -nographic -bios none
T         = 5

SRC  = ../01-hello/boot.s
LD   = ../01-hello/link.ld

all: compare

# ГЛАВНАЯ ЦЕЛЬ ПРИЁМКИ. Собираем первую программу серии двумя способами и
# сравниваем байты. Не «похоже», а cmp: либо совпало, либо нет.
compare: mine.bin ref.bin
	@echo "наш ассемблер: $$(wc -c < mine.bin) байт"
	@echo "настоящий:     $$(wc -c < ref.bin) байт"
	@cmp mine.bin ref.bin && echo "БАЙТ В БАЙТ СОВПАДАЕТ" \
	  || echo "РАСХОЖДЕНИЕ, смотри make diff"

mine.bin: asm.py $(SRC)
	python asm.py $(SRC) $@

ref.bin: $(SRC) $(LD)
	$(CC) $(CFLAGS) -T $(LD) -o ref.elf $(SRC)
	$(OBJC) -O binary ref.elf $@

# ВТОРАЯ ЦЕЛЬ ПРИЁМКИ. Правильные байты на бумаге ничего не стоят, пока они
# не запустились. Грузим ОБРАЗ НАШЕЙ СБОРКИ прямо по 0x80000000.
run: mine.bin
	@echo "запускаем то, что собрал наш ассемблер:"
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=mine.bin,addr=0x80000000
	@echo ""

# То же самое настоящей сборкой, для сравнения на глаз.
run-ref: ref.bin
	-@timeout $(T) $(QEMU) $(QEMUFLAGS) -device loader,file=ref.bin,addr=0x80000000
	@echo ""

# Что и во что превратилось, строка за строкой.
listing: asm.py $(SRC)
	python asm.py $(SRC) mine.bin --listing

# Побайтовое расхождение, если вдруг оно появится.
diff: mine.bin ref.bin
	od -A d -t x1 mine.bin > .mine.txt
	od -A d -t x1 ref.bin  > .ref.txt
	-diff .mine.txt .ref.txt
	@rm -f .mine.txt .ref.txt

# Доля псевдоинструкций по всем программам репозитория. Это опыт на
# опровержение спины статьи: считаем не по одной удобной программе, а по всем.
pseudo:
	python count-pseudo.py

# Обещанное в конце четвёртой статьи: как из строки получаются байты.
promise:
	@echo '    addi    sp, sp, -16' > .p.s
	@$(AS) -march=rv32i -mabi=ilp32 -o .p.o .p.s
	@echo "настоящий ассемблер:"
	@$(OBJD) -d .p.o | tail -1
	@$(OBJC) -O binary .p.o .p.bin
	@echo -n "  байты в файле: "; od -A n -t x1 .p.bin
	@echo "наш ассемблер:"
	@printf '    .section .text\n    addi sp, sp, -16\n' > .q.s
	@python asm.py .q.s .q.bin > /dev/null
	@echo -n "  байты в файле: "; od -A n -t x1 .q.bin
	@cmp .p.bin .q.bin && echo "  совпало" || echo "  РАСХОЖДЕНИЕ"
	@rm -f .p.s .p.o .p.bin .q.s .q.bin

# ОПЫТ С ОДНИМ ИЗМЕНЯЕМЫМ ПАРАМЕТРОМ.
#
# Утверждение: ассемблер, выдающий объектный файл, не может дописать `la` до
# конца, потому что не знает, где окажется метка.
#
# Слабое доказательство: показать .o и слинкованный файл рядом. Там меняются
# сразу две вещи (и стадия сборки, и адреса), и придраться есть к чему.
#
# Сильное: собрать объектный файл ОДИН РАЗ и слинковать его ДВАЖДЫ, разными
# скриптами. Объектный файл при этом байт в байт тот же, его сумма печатается.
# Меняется ровно одно: куда велено положить .rodata. Если байты `la` после
# этого разные, ассемблер их знать не мог.
where: obj.o
	@echo "объектный файл собран один раз, его сумма:"
	@md5sum obj.o
	@$(CC) $(CFLAGS) -T $(LD) -nostdlib -o w-near.elf obj.o
	@$(CC) $(CFLAGS) -T link-shift.ld -nostdlib -o w-far.elf obj.o
	@echo ""
	@echo "-- .rodata сразу за кодом (link.ld):"
	@$(OBJD) -d w-near.elf | grep -E "auipc|addi.*t1,t1" | head -2
	@echo "-- .rodata по 0x80001000 (link-shift.ld):"
	@$(OBJD) -d w-far.elf  | grep -E "auipc|addi.*t1,t1" | head -2
	@echo ""
	@echo "-- а что стояло в самом объектном файле:"
	@$(OBJD) -d -M no-aliases,numeric obj.o | grep -E "auipc|addi.*x6,x6" | head -2
	@echo ""
	@echo "объектный файл не пересобирался, сумма прежняя:"
	@md5sum obj.o

obj.o: $(SRC)
	$(AS) -march=rv32i -mabi=ilp32 -o $@ $(SRC)

# СРАВНЕНИЕ С x86: чьё это свойство, 44 процента выдумки.
#
# Тот же скелет на x86-64. Считаем не инструкции, а МНЕМОНИКИ: сколько строк
# из написанных процессор выполняет как есть, без развёртки. На RISC-V из
# девяти строк первой программы серии настоящих было четыре.
#
# Нужен родной x86-ассемблер. Он есть в mingw и в любом Linux; если его нет,
# цель честно скажет об этом и ничего не сделает.
x86: x86-hello.s
	@command -v as >/dev/null 2>&1 || { echo "нет родного as для x86, прогоняйте на Linux или в WSL"; exit 0; }
	@as --64 -o x86-hello.o x86-hello.s
	@grep -oE '^[[:space:]]+[a-z][a-z0-9]*' x86-hello.s | tr -d ' ' > .src.txt
	@objdump -d x86-hello.o | awk -F'\t' 'NF>2 {split($$3,w," "); print w[1]}' > .got.txt
	@echo ""
	@echo "-- мнемоники, которые я написал:  $$(tr '\n' ' ' < .src.txt)"
	@echo "-- мнемоники, которые вышли:      $$(tr '\n' ' ' < .got.txt)"
	@echo ""
	@head -n $$(wc -l < .src.txt) .got.txt > .head.txt
	@if diff -q .src.txt .head.txt >/dev/null; then \
	   echo "СОВПАЛИ ВСЕ $$(wc -l < .src.txt): каждая написанная мнемоника осталась собой,"; \
	   echo "ни одна не развернулась в две. Псевдоинструкций тут нет."; \
	 else \
	   echo "РАСХОЖДЕНИЕ, ассемблер что-то развернул:"; diff .src.txt .head.txt; \
	 fi
	@extra=$$(( $$(wc -l < .got.txt) - $$(wc -l < .src.txt) )); \
	 if [ $$extra -gt 0 ]; then \
	   echo ""; \
	   echo "Плюс $$extra лишних в хвосте. Это НЕ развёртка, а выравнивание секции:"; \
	   echo "ассемблер добил .text пустыми командами до границы. Проверить так:"; \
	   echo "    objdump -h x86-hello.o | grep -A1 .text"; \
	 fi
	@rm -f .src.txt .got.txt .head.txt

# ТО ЖЕ НА ARM. Третья точка между x86 и RISC-V, и самая интересная.
#
# Нужен кросс-ассемблер: apt install binutils-arm-linux-gnueabihf.
# На Windows его нет, гоняйте в WSL или на Linux.
ARMAS   = arm-linux-gnueabihf-as
ARMOBJD = arm-linux-gnueabihf-objdump

arm: arm-hello.s
	@if command -v $(ARMAS) >/dev/null 2>&1; then $(MAKE) --no-print-directory arm-run; else echo "нет $(ARMAS): apt install binutils-arm-linux-gnueabihf"; fi

arm-run:
	@$(ARMAS) -o arm-hello.o arm-hello.s
	@echo ""
	@echo "-- что я написал:"
	@grep -oE '^[[:space:]]+[a-z][a-z0-9.]*' arm-hello.s | tr -d ' ' | paste -sd' ' -
	@echo ""
	@echo "-- что вышло:"
	@$(ARMOBJD) -d arm-hello.o | grep -E '^ +[0-9a-f]+:'
	@echo ""
	@echo "-- куда смотреть:"
	@echo "   ldr r1,=message стало ldr r1,[pc,#N] ПЛЮС слово данных в хвосте кода."
	@echo "   nop собрался как mov r0, r0, objdump подписывает это сам."
	@echo ""
	@echo "-- а слово данных пустое, адрес в него впишет компоновщик:"
	@$(ARMOBJD) -r arm-hello.o | grep R_ARM || true
	@rm -f arm-hello.o

clean:
	rm -f *.bin *.elf *.o .p.* .q.* .mine.txt .ref.txt

.PHONY: all compare run run-ref listing diff pseudo promise where x86 arm arm-run clean
