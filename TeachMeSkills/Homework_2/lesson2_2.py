test_strings = [
    'Hello world',
    'a b c',
    'test',
    'test1 test2 test3 test4 test5'
]

def count_words(text):
    
    words = text.split()
    return len(words)

for s in test_strings:
    word_count = count_words(s)
    print(f"Строка: '{s}' -> Количество слов: {word_count}")