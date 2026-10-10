#Переменные

'''
    В качестве наименования переменной можно использовать любые слова,
    которые могут начинаться с алфавитного символа или со знака подчеркивания 
    и может содержать алфавитно-цифровые символы и знак подчеркивания.
    Кроме того, название переменной не должно совпадать с названием 
    ключевых слов языка Python, ключевых слов не так много:

    False      await      else       import     pass
    None       break      except     in         raise
    True       class      finally    is         return
    and        continue   for        lambda     try
    as         def        from       nonlocal   while
    assert     del        global     not        with
    async      elif       if         or         yield
    '''

userName = "Grand" #Camel case - каждое новое подслово в наименовании переменной начинается с большой буквы.
user_name = "Artsiom" #Underscore notation - подслова в наименовании переменной разделяются знаком подчеркивания.
#не зависимо от их наименования (name, Name), они будут разными и с разными значениями

print (userName) #вывод переменной userName
print (user_name) #вывод переменной user_name


name = "Artsiom" # первичное значение
print(name)
name = "Grand" # последующее значение
print(name)

'''
    bool - представление двух значений (True - верно либо истина; False - неверно, ложь)
    int - числа (1 - 99999999) 
    float - числа с плавающей точкой (1.68)
    str - строка (последователь символов, заключенных в одинарные либо двойные кавычки "Hello", "Artsiom" и т.д.)
'''

isArtsiom = False
print(isArtsiom) # False
 
isArtsiom = True
print(isArtsiom) # True


age = 29
print ("Возраст: ", age) # возраст = 29

count = 20
print ("Количество: ", count) # количество = 20 


height = 1.68
print(height)   # 1.68

pi = 3.14
print(pi)       # 3.14

weight = 68.
print(weight)   # 68.0

#Число с плавающей точкой можно определять в экспоненциальной записи:

'''
    Экспоненциальная запись (также называемая научной нотацией) 
    — это способ записи чисел, при котором число представляется 
    в виде произведения двух множителей:
'''
#пример:
x = 3.9e3
print(x)  # 3900.0
 
x = 3.9e-3
print(x)  # 0.0039

#пример двойной, текстовой переменной:
text = ("Hi, Artem!"
        "So, how are you finding the learning process?")
youText = input()
print(text, youText)

#пример многострочного текста, представленный текстом:
text = '''Laudate omnes gentes laudate
Magnificat in secula
Et anima mea laudate
Magnificat in secula 
'''
print(text)

'''
    Строка может содержать ряд специальных 
    символов - управляющих последовательностей.
    Некоторые из них:
    \\: позволяет добавить внутрь строки слеш
    \': позволяет добавить внутрь строки одинарную кавычку
    \": позволяет добавить внутрь строки двойную кавычку
    \n: осуществляет переход на новую строку
    \t: добавляет табуляцию (4 отступа)
'''

textGrand = "Message: \"Hello World\""
textgrand = "\n\"Hello World\""
textgRand = "\nMessage\\: \"Hello World\""
textgrAnd = "Message: \"Hello World\""
print (textGrand, textgrand, textgRand)

'''
    Python позволяет встравивать в строку значения других переменных. 
    Для этого внутри строки переменные размещаются в фигурных скобках 
    {}, а перед всей строкой ставится символ f:
'''

userName = "Artsiom"
userAge = 29
user = f"name: {userName}  age: {userAge}"
print(user)   # name: Artsiom  age: 29

userId = "abc"      # тип str
print(type(userId)) # <class 'str'>
 
userId = 234        # тип int
print(type(userId)) # <class 'int'>