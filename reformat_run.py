import copy
import csv
import json
import re
import sys

from pprint import pprint

# TODO: add support for relics so that we can handle frozen egg properly.

with open('data/cleaned/cards.json', 'r') as f:
    CARDS = json.load(f)
for x in CARDS:
    for y in CARDS[x]:
        CARDS[x][y] += [z+'+1' for z in CARDS[x][y]]
STARTING_DECKS = {
    'IRONCLAD': {'Strike': 5, 'Defend': 4, 'Bash': 1},
}
STARTING_RELICS = {
    'IRONCLAD': set(['Burning Blood']),
}
ALL_CARDS = set()
for x in CARDS:
    for y in CARDS[x]:
        for z in CARDS[x][y]:
            ALL_CARDS.add(z)

def is_type(card, typ):
    for x in CARDS:
        if card in CARDS[x][typ]:
            return True

with open('data/code_relic_names.csv') as f:
    ALL_RELICS = [x[0] for x in csv.reader(f)]

with open('data/name_translation.json', 'r') as f:
    TRANSLATION = json.load(f)
def tr(name):
    name = ''.join([x[0].upper() + x[1:] for x in name.split()])
    return TRANSLATION.get(name, name)

def calc_state_by_floor(data):
    card_change_map = {}
    relic_change_map = {}

    def add_card_change(floor, cname, diff):
        card_change_map[floor].append((tr(cname), diff))

    for i in range(1, data['floor_reached']):
        card_change_map[i] = []
        relic_change_map[i] = []
    for c in data['card_choices']:
        if c['picked'] != 'SKIP':
            add_card_change(c['floor'], c['picked'], 1)

    for r in data['relics_obtained']:
        relic_change_map[r['floor']].append((r['key'], 1))
    for floor, r in zip([16, 33], data['boss_relics']):
        relic_change_map[floor].append((r['picked'], 1))

    for c in data['campfire_choices']:
        cname = c.get('data', '')
        if c['key'] == 'SMITH':
            add_card_change(c['floor'], cname, -1)
            add_card_change(c['floor'], cname+'+1', 1)
        elif c['key'] == 'PURGE':
            add_card_change(c['floor'], cname, -1)
        # DIG is in relics_obtained
        # TODO: LIFT, RECALL

    for floor, purchase in zip(data['item_purchase_floors'], data['items_purchased']):
        if tr(purchase) in ALL_CARDS:
            add_card_change(floor, purchase, 1)
        elif purchase in ALL_RELICS:
            relic_change_map[floor].append((purchase, 1))
        else:
            # TODO: potions
            if not re.match('(?i).*potion$', purchase):
                print(ALL_RELICS)
                print(purchase)
                assert(False)

    # Despite the name this does not include cards purged at campfires with toke.
    for floor, purge in zip(data['items_purged_floors'], data['items_purged']):
        add_card_change(floor, purge, -1)

    for e in data['event_choices']:
        for cname in e.get('cards_removed', []):
            add_card_change(e['floor'], cname, -1)
        for cname in e.get('cards_upgraded', []):
            add_card_change(e['floor'], cname, -1)
            add_card_change(e['floor'], cname+'+1', 1)
        for cname in e.get('cards_obtained', []):
            add_card_change(e['floor'], cname, 1)

        for rname in e.get('relics_obtained', []):
            relic_change_map[e['floor']].append((rname, 1))
        for rname in e.get('relics_lost', []):
            relic_change_map[e['floor']].append((rname, -1))

    floor_state = [{
        'deck': STARTING_DECKS[data['character_chosen']],
        'relics': STARTING_RELICS[data['character_chosen']],
    }]
    for floor in range(1, data['floor_reached']):
        new_state = copy.deepcopy(floor_state[-1])

        for rname, diff in relic_change_map[floor]:
            if diff == 1:
                assert(rname not in new_state['relics'])
                new_state['relics'].add(rname)
            elif diff == -1:
                assert(rname in new_state['relics'])
                new_state['relics'].remove(rname)
            else:
                assert(False)

        for cname, diff in card_change_map[floor]:
            if (('Frozen Egg 2' in new_state['relics'] and is_type(cname, 'Power')) or
                ('Toxic Egg 2' in new_state['relics'] and is_type(cname, 'Skill')) or
                ('Molten Egg 2' in new_state['relics'] and is_type(cname, 'Attack'))): 
                if cname[-2:] != '+1':
                    cname += '+1'
            if cname not in new_state['deck']:
                new_state['deck'][cname] = 0
            new_state['deck'][cname] += diff
            assert(new_state['deck'][cname] >= 0)
            if new_state['deck'][cname] == 0:
                del new_state['deck'][cname]

        floor_state.append(new_state)

    master_deck = {}
    for cname in data['master_deck']:
        cname = tr(cname)
        if cname == 'AscendersBane':
            continue
        if cname not in master_deck:
            master_deck[cname] = 0
        master_deck[cname] += 1
    # pprint(master_deck)
    # pprint(floor_state[-1]['deck'])
    assert(master_deck == floor_state[-1]['deck'])

    # pprint(set(data['relics']))
    # pprint(floor_state[-1]['relics'])
    assert(set(data['relics']) == floor_state[-1]['relics'])

    # pprint(list(zip(range(100), floor_state)))
    exit(1)

def reformat(data):
    state_by_floor = calc_state_by_floor(data)
    card_choices = data['card_choices']
    # pprint(card_choices)

for i in range(1, len(sys.argv)):
    with open(sys.argv[i], 'r') as f:
        data = json.load(f)
        if data['character_chosen'] != 'IRONCLAD':
            print('Only IRONCLAD supported (got %s).' % data['character_chosen'])
            exit(1)
        reformat(data)
