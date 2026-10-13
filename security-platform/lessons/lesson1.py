# lesson1.py — первая программа на Python
# Дата: 2026-10-12

name = "Grand"
age = 39
city = "Moscow"
height = 1.78

print("Способ 1 (через запятую):")
print("Меня зовут", name, "мне", age, "лет, я живу в", city)

print("\nСпособ 2 (f-строка):")
print(f"Меня зовут {name}, мне {age} лет, я живу в {city}")

print("\nСпособ 3 (конкатенация):")
print("Меня зовут " + name + ", мне " + str(age) + " лет, я живу в " + city)

current_year = 2026
birth_year = current_year - age
print(f"\nЯ родился в {birth_year} году")

print(f"\nТип переменной age: {type(age)}")
print(f"Тип переменной height: {type(height)}")

name = input("Как тебя зовут? ")
age = int(input("Сколько тебе лет? "))
print(f"Привет, {name}! Тебе {age}")
print(f"Ты прожил примерно {age * 365}")
print(f"Ты родился в {current_year - age} году.")