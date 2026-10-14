has_digit = False       # начальное значение — «не найдено»

for char in password:
    if char.isdigit():
        has_digit = True
        break

# После цикла has_digit = True/False
if has_digit:
    print("Есть цифра")