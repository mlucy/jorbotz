import json
import csv

CARDS = {
    'IRONCLAD': {},
    'SILENT': {},
    'DEFECT': {},
    'COLORLESS': {},
}

SEEN = set()

with open('name_translation.json', 'r') as f:
    TRANSLATION = json.load(f)

def translate(name):
    name = ''.join([x[0].upper() + x[1:] for x in name.split()])
    return TRANSLATION.get(name, name)

with open('code_card_names.csv', 'r') as f:
    CODE_CARDS = set([translate(x[0]) for x in csv.reader(f)])

with open('cards.csv', 'r') as f:
    for line in csv.reader(f):
        if line[0] == 'Name':
            pass
        elif line[0] == 'Ironclad Cards':
            CURRENT_CLASS = 'IRONCLAD'
        elif line[0] == 'Silent Cards':
            CURRENT_CLASS = 'SILENT'
        elif line[0] == 'Defect Cards':
            CURRENT_CLASS = 'DEFECT'
        elif line[0] == 'Colorless Cards':
            CURRENT_CLASS = 'COLORLESS'
        elif line[0] == 'Status Cards':
            CURRENT_CLASS = 'COLORLESS'
        elif line[0] == 'Curse Cards':
            CURRENT_CLASS = 'COLORLESS'
        else:
            name = translate(line[0])
            typ = line[1]
            assert(name in CODE_CARDS)
            if name in SEEN:
                print('Duplicate %s' % name)
            SEEN.add(name)
            if typ not in CARDS[CURRENT_CLASS]:
                CARDS[CURRENT_CLASS][typ] = []
            CARDS[CURRENT_CLASS][typ].append(name)

assert(CODE_CARDS == SEEN)
for x in CARDS:
    for y in CARDS[x]:
        CARDS[x][y].sort()

print(CARDS)

with open('cleaned/cards.json', 'w') as f:
    json.dump(CARDS, f)
