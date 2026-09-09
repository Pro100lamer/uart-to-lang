# Стенд на живом ESP32. Нужны:
#   - плата ESP32 на USB (у нас ESP32-D0WD rev 1.1, переходник CH340);
#   - тулчейн Xtensa: скачивается из релизов espressif/crosstool-NG,
#     распаковывается в tools/xtensa-esp-elf;
#   - esptool: pip install esptool.
#
# Порт задаётся переменной ESP_PORT, по умолчанию COM4.
#
# ВНИМАНИЕ: цели run, nowait и iram-byte ПИШУТ ВО ФЛЕШ платы по адресу
# 0x1000, поверх её загрузчика. Сначала снимите образ: make backup.

AS      = xtensa-esp32-elf-as
LD      = xtensa-esp32-elf-ld
OBJDUMP = xtensa-esp32-elf-objdump
PORT   ?= $(if $(ESP_PORT),$(ESP_PORT),COM4)

# Режим флеша ОБЯЗАТЕЛЬНО dio. По умолчанию esptool ставит qio, и на
# этой плате ПЗУ читает первый сегмент, а на втором получает мусор:
# в журнале видно mode:QIO и load: с нелепым адресом.
IMGFLAGS = --flash-mode dio --flash-freq 40m --flash-size 4MB

all: hello.bin

%.o: %.s
	$(AS) -o $@ $<

%.elf: %.o link.ld
	$(LD) -T link.ld -o $@ $<

%.bin: %.elf
	python -m esptool --chip esp32 elf2image $(IMGFLAGS) --output $@ $<

# Снять образ флеша ЦЕЛИКОМ, прежде чем что-то в него писать.
backup:
	python -m esptool --port $(PORT) --baud 460800 read-flash 0 ALL esp32-flash-backup.bin

# Вернуть плату к тому, что на ней было.
restore:
	python -m esptool --port $(PORT) --baud 460800 write-flash 0 esp32-flash-backup.bin

# Что написано и что кристалл на самом деле исполняет.
listing: hello.elf
	@echo "-- что я написал:"
	@grep -oE '^[[:space:]]+[a-z][a-z0-9._]*' hello.s | tr -d ' ' | paste -sd' ' -
	@echo ""
	@echo "-- что вышло:"
	@$(OBJDUMP) -d hello.elf | sed -n '/Disassembly/,$$p'
	@echo "-- слова данных, адреса в них вписал компоновщик:"
	@$(OBJDUMP) -s -j .text hello.elf | sed -n '3,5p'

# Рабочая программа: печатает строку и останавливается.
run: hello.bin
	python run.py hello.bin 2

# Тот же цикл без ожидания передатчика. Вывод рвётся.
nowait: nowait.bin
	python run.py nowait.bin 2

# Побайтовое чтение памяти команд. Кристалл отвечает исключением.
iram-byte: iram-byte.bin
	python run.py iram-byte.bin 2

clean:
	rm -f *.o *.elf *.bin

.PHONY: all backup restore listing run nowait iram-byte clean
