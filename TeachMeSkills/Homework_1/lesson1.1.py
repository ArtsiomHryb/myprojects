print("Привет")                    # просто текст
print("Имя:", name)                # через запятую (Python добавит пробел)
print(f"Имя: {name}")              # f-строка — самый удобный способ
print("Имя: " + name)              # конкатенация (все части — строки)
print("Без переноса", end="")      # без \n в конце
print("A", "B", sep="-")           # A-B (свой разделитель)

name = input("Как тебя зовут? ")   # всегда возвращает строку
age = int(input("Возраст? "))      # преобразуем в число
price = float(input("Цена? "))     # в число с точкой

name = "Grand"        # str
age = 39              # int
height = 1.78         # float
is_active = True      # bool
nothing = None        # None

str(39)       # "39"
int("39")     # 39
float("3.14") # 3.14

s = "Hello123"

len(s)              # 8 — длина
s.lower()           # "hello123"
s.upper()           # "HELLO123"
s.isdigit()         # False — все ли символы цифры
s.isupper()         # False — все ли заглавные
s.islower()         # False — все ли строчные
s.isalpha()         # False — только буквы
s.isalnum()         # True — буквы и цифры

"5".isdigit()       # True
"H".isupper()       # True
"h".isupper()       # False

'''
TypeError — не тот тип данных
NameError — переменная не определена (опечатка?)
IndentationError — проблема с отступами
SyntaxError — опечатка в синтаксисе (if без :, незакрытая скобка)
ValueError — преобразование не удалось (int("abc"))
'''

