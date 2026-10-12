# lesson1.py — первая программа на Python
# Дата: 2026-10-12

name = "Artsiom"
age = 29
city = "Moscow"
height = 1.78

print ("Способ 1 (через запятую):")
print ("Меня зовут", name, "мне", age, "лет, я живу в", city)

print("\nСпособ 2 (f-строка):")
print(f"Меня зовут {name}, мне {age} лет, я живу в {city}")

print("\nСпособ 3 (конкатенация):")
print("Меня зовут " + name + ", мне " + str(age) + " лет, я живу в " + city)

current_year = 2026
birth_year = current_year - age