# Стенд шестой статьи: где ломается разбор текста на слова.
#
# Пятая кончилась обещанием «на первом же выражении в операнде это
# развалится». Здесь обещание проверяется прогоном, а не пересказом.
#
# Нужен тулчейн RISC-V из tools/riscv-gcc/bin в PATH, а цели url
# ещё и qemu-system-riscv32. Всё это даёт scripts/env.sh.

PY = python

all: cases silent refute accept url

# Выражения в операндах: что умеет настоящий as и что умеем мы.
cases:
	@$(PY) cases.py

# То же с сообщениями об ошибках целиком.
cases-v:
	@$(PY) cases.py -v

# Молчаливая порча: ассемблер возвращает ноль и отдаёт не то.
silent:
	@$(PY) silent.py

# Попытка опрокинуть спину: чиним срезание комментариев и ищем
# следующий случай, который всё равно ломается.
refute:
	@$(PY) refute.py

# Приёмка лексера: не сломали ли старое, починилось ли сломанное.
accept:
	@$(PY) accept.py

# Та же поломка, но показанная поведением: одна программа, два разбора,
# одна печатает адрес, другая молчит. Нужен qemu-system-riscv32.
url:
	@$(PY) behave.py

# Показать, на какие слова лексер режет файл. Кавычки через оболочку
# не передать, они теряются, поэтому читаем из файла:
#     make show F=пример.s
show:
	@$(PY) -c "import lexer,sys; [print('%-8s %r' % (t.kind, t.text)) for t in lexer.tokens(open(sys.argv[1],encoding='utf-8').read()) if t.kind!='eol']" $(F)

clean:
	rm -rf .tmp

.PHONY: all cases cases-v silent refute accept url show clean
