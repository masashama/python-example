import Levenshtein

costs = [
    'Хостинг большой и дорогой vps',
    'Налоги никому не платим',
    'Зарплаты платим всем',
    'Подарки только себе',
    'Премии если трудился на славу во имя императора',
    'Удаленщики обойдутся',
    'Левый хостинг',
    'Правый средний зеленый хостинг сервер',
    'Сфеерический хостинг в вакуме',
    'В вакуме где то что то',
    'Вакумный конь',
    "В вакуме",
]

inrow = "в вакме кнь"

result = dict()

for key, row in enumerate(costs):
    res = []
    index = []
    for word in row.lower().split(" "):
        for inword in inrow.lower().split(" "):
            if len(inword) > 2:
                index.append(Levenshtein.distance(inword, word))
                res.append(index)
        result[key] = res

res = dict()


def check_word(sequence, word):
    indexes = []
    for sequence_word in sequence:
        indexes.append(Levenshtein.distance(word, sequence_word))
    return indexes


for key, row in enumerate(costs):
    res[row] = []
    for inword in inrow.lower().split(' '):
        if len(inword) > 2:
            res[row].append(check_word(row.lower().split(' '), inword))


array = []

for key in res:
    for i, indexes in enumerate(res[key]):
        res[key][i] = min(indexes)
    array.append((key, res[key]))



array.sort(key=lambda item: min(item[1]))

for item in array:
    print(item)
