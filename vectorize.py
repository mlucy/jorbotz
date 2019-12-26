import json
import csv
import numpy as np

with open('data/cleaned/cards.json', 'r') as f:
    CARDS = json.load(f)
for x in CARDS:
    for y in CARDS[x]:
        CARDS[x][y] += [z+'+1' for z in CARDS[x][y]]

with open('data/code_relic_names.csv') as f:
    ALL_RELICS = [x[0] for x in csv.reader(f)]
ALL_RELICS.sort()
RELIC_INDEX_MAP = {}
for i, rname in zip(range(len(ALL_RELICS)), ALL_RELICS):
    RELIC_INDEX_MAP[rname] = i

ALL_CARDS = set()
for x in CARDS:
    for y in CARDS[x]:
        for z in CARDS[x][y]:
            ALL_CARDS.add(z)
ALL_CARDS = list(ALL_CARDS)
ALL_CARDS.sort()
CARD_INDEX_MAP = {}
for i, cname in zip(range(len(ALL_CARDS)), ALL_CARDS):
    CARD_INDEX_MAP[cname] = i

print(len(ALL_CARDS))
print(len(ALL_RELICS))

def deck_to_vector(deck):
    out_vec = np.zeros(len(ALL_CARDS))
    for cname in deck:
        if cname[-2:] == '+1':
            out_vec[CARD_INDEX_MAP[cname]] += deck[cname]
        else:
            out_vec[CARD_INDEX_MAP[cname]] += deck[cname]
            out_vec[CARD_INDEX_MAP[cname+'+1']] += deck[cname]
    return out_vec

def relics_to_vector(relics):
    out_vec = np.zeros(len(ALL_RELICS)):
    for relic in relics:
        out_vec[CARD_INDEX_MAP[relic]] += 1
    return out_vec

NUMERIC_FEATURES = ['gold', 'hp', 'max_hp', 'floor']
CHOICE_FEATURES = {
    'class': ['IRONCLAD', 'THE_SILENT', 'DEFECT'],
    'boss': ['Slime Boss'] + ['foo']*15,
}
CHOICE_INDEX_MAPS = {}
for k in CHOICE_FEATURES:
    CHOICE_INDEX_MAPS[k] = {}
    for i, choice in zip(range(len(CHOICE_FEATURES[k])), CHOICE_FEATURES[k]):
        CHOICE_INDEX_MAPS[k][choice] = i

def numeric_vector(num):
    return np.array([float(num)])

def choice_vector(field, choice):
    out_vec = np.zeros(len(CHOICE_FEATURES[field]))
    if choice in CHOICE_INDEX_MAP[field]:
        out_vec[CHOICE_INDEX_MAP[field][choice]] += 1
    return out_vec

def obj_to_vector(obj):
    all_vecs = []
    all_vecs.append(deck_to_vector(obj['deck']))
    all_vecs.append(relics_to_vector(obj['relics']))
    for feature in NUMERIC_FEATURES:
        all_vecs.append(numeric_vector(obj.get(feature, 0)))
    for feature in CHOICE_FEATURES:
        all_vecs.append(choice_vector(obj.get(feature, None)))
    return np.concatenate(all_vecs)
