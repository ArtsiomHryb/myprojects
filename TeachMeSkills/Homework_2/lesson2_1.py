import math

cat_a = float(input("Введите длину первого катета: "))
cat_b = float(input("Введите длину второго катета: "))

area = 0.5 * cat_a * cat_b

hypotenuse = math.sqrt(cat_a**2 + cat_b**2)

print(f"\nПлощадь треугольника: {area:.2f}")
print(f"Гипотенуза: {hypotenuse:.2f}")