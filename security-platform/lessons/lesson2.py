password = input("Введите пароль?")

has_digit = False #есть ли цифра в пароле
has_upper = False #есть ли заглавная буква

for char in password:
    if char.isdigit():
        has_digit = True
        break

for char in password:
    if char.isupper():
        has_upper = True
        break

score = 0
if len(password) >= 8:
    score += 1
if has_digit:
    score += 1
if has_upper:
    score += 1

mark = "✅" if len(password) >= 8 else "❌"
print(f"{mark} Длина ≥ 8: {'да' if len(password) >= 8 else 'нет'}")

mark = "✅" if has_digit else "❌"
print(f"{mark} Есть цифры: {'да' if has_digit else 'нет'}")

mark = "✅" if has_upper else "❌"
print(f"{mark} Есть заглавная буква: {'да' if has_upper else 'нет'}")

if score == 3:
    print("Надёжный пароль")
elif score == 2:
    print("Средний пароль")
else:
    print("Слабый пароль")



    