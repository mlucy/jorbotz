import copy
import csv
import json
import re
import sys

from pprint import pprint

# TODO: add support for relics so that we can handle frozen egg properly.

CARD_GRANTING_NEOW_BONUSES = [
    'ONE_RANDOM_RARE_CARD', 'THREE_RARE_CARDS', 'THREE_CARDS', 'TRANSFORM_CARD', 'UPGRADE_CARD',
]

CARD_REMOVING_NEOW_BONUSES = [
    'REMOVE_CARD', 'REMOVE_TWO', 'TRANSFORM_CARD', 'UPGRADE_CARD',
]

RELIC_GRANTING_NEOW_BONUSES = [
    'BOSS_RELIC', 'ONE_RARE_RELIC', 'RANDOM_COMMON_RELIC',
]

RELIC_REMOVING_NEOW_BONUSES = [
    'BOSS_RELIC'
]

def valid_neow_add(data, cname):
    return ((data['neow_bonus'] in CARD_GRANTING_NEOW_BONUSES) or
            (data['neow_cost'] == 'CURSE' and is_type(cname, 'Curse')))

def valid_neow_del(data, cname):
    return data['neow_bonus'] in CARD_REMOVING_NEOW_BONUSES

def valid_neow_relic_add(data):
    return data['neow_bonus'] in RELIC_GRANTING_NEOW_BONUSES

def valid_neow_relic_del(data, rname):
    return ((data['neow_bonus'] in RELIC_REMOVING_NEOW_BONUSES) and
            (rname in STARTING_RELICS[data['character_chosen']]))

def valid_relic_upgrade(data, states, cname):
    floor = old_cname = None
    if cname[-2:] == '+1':
        old_cname = cname[:-2]
        if is_type(cname, 'Skill'):
            upgrades = states[-1]['scratch'].get('war_paint_upgrades', 0)
            if upgrades > 0:
                floor = states[-1]['scratch']['war_paint_floor']
                states[-1]['scratch']['war_paint_upgrades'] = upgrades-1
        if is_type(cname, 'Attack'):
            upgrades = states[-1]['scratch'].get('whetstone_upgrades', 0)
            if upgrades > 0:
                states[-1]['scratch']['whetstone_upgrades'] = upgrades-1
                floor = states[-1]['scratch']['whetstone_floor']
    if states[floor]['deck'].get(old_cname, 0) == 0:
        floor = old_cname = None
    return floor, old_cname

def note_card(state, cname, diff):
    if 'Omamori' in state['relics'] and is_type(cname, 'Curse'):
        uses = state['scratch'].get('omamori_uses', 0)
        if uses < 2:
            state['scratch']['omamori_uses'] = uses + 1
            return False
    if cname not in state['deck']:
        state['deck'][cname] = 0
    state['deck'][cname] += diff
    return True

with open('data/cleaned/cards.json', 'r') as f:
    CARDS = json.load(f)
for x in CARDS:
    for y in CARDS[x]:
        CARDS[x][y] += [z+'+1' for z in CARDS[x][y]]
STARTING_DECKS = {
    'IRONCLAD': {'Strike': 5, 'Defend': 4, 'Bash': 1},
    'THE_SILENT': {'Strike': 5, 'Defend': 5, 'Survivor': 1, 'Neutralize': 1},
    'DEFECT': {'Strike': 4, 'Defend': 4, 'Zap': 1, 'Dualcast': 1},
}
STARTING_RELICS = {
    'IRONCLAD': set(['Burning Blood']),
    'THE_SILENT': set(['Ring of the Snake']),
    'DEFECT': set(['Cracked Core']),
}
ALL_CARDS = set()
for x in CARDS:
    for y in CARDS[x]:
        for z in CARDS[x][y]:
            ALL_CARDS.add(z)

def is_type(card, typ):
    for x in CARDS:
        if card in CARDS[x].get(typ, []):
            return True

with open('data/code_relic_names.csv') as f:
    ALL_RELICS = [x[0] for x in csv.reader(f)]

with open('data/name_translation.json', 'r') as f:
    TRANSLATION = json.load(f)
for k in list(TRANSLATION):
    TRANSLATION[k+'+1'] = TRANSLATION[k]+'+1'

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
        'scratch': {},
    }]
    for floor in range(1, data['floor_reached']):
        new_state = copy.deepcopy(floor_state[-1])

        for rname, diff in relic_change_map[floor]:
            if diff == 1:
                assert(rname not in new_state['relics'])
                new_state['relics'].add(rname)
                if rname == 'War Paint':
                    new_state['scratch']['war_paint_upgrades'] = 2
                    new_state['scratch']['war_paint_floor'] = floor
                elif rname == 'Whetstone':
                    new_state['scratch']['whetstone_upgrades'] = 2
                    new_state['scratch']['whetstone_floor'] = floor
            elif diff == -1:
                # We might be removing a relic we got from the Neow bonus.
                if rname not in new_state['relics']:
                    assert(valid_neow_relic_add(data))
                    for state in floor_state + [new_state]:
                        state['relics'].add(rname)
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
            if note_card(new_state, cname, diff):
                # We might have been given a card during our neow bonus.
                if new_state['deck'][cname] < 0:
                    # TODO: this might be incorrect if the neow bonus is also in play.
                    upgrade_floor, old_cname = valid_relic_upgrade(
                        data, floor_state + [new_state], cname)
                    if upgrade_floor is not None:
                        for state in floor_state[upgrade_floor:] + [new_state]:
                            note_card(state, old_cname, -1)
                            note_card(state, cname, 1)
                    else:
                        assert(valid_neow_add(data, cname))
                        for state in floor_state + [new_state]:
                            note_card(state, cname, 1)
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
    calculated_deck = floor_state[-1]['deck']
    # pprint(master_deck)
    # pprint(calculated_deck)
    if master_deck != calculated_deck:
        all_card_names = list(set(master_deck.keys()).union(set(calculated_deck.keys())))
        all_card_names.sort(reverse=True)
        for cname in all_card_names:
            # print(cname)
            master_count = master_deck.get(cname, 0)
            calculated_count = calculated_deck.get(cname, 0)
            if master_count != calculated_count:
                print(cname, master_deck, calculated_deck, data['neow_bonus'], data['neow_cost'])
                if master_count > calculated_count:
                    if cname[-2:] == '+1':
                        if ((master_deck.get(cname, 0) - calculated_deck.get(cname, 0)) ==
                            (calculated_deck.get(cname[:-2], 0) - master_deck.get(cname[:-2], 0))):
                            upgrade_floor, old_cname = valid_relic_upgrade(data, floor_state, cname)
                            if upgrade_floor is not None:
                                for state in floor_state[upgrade_floor:]:
                                    diff = master_count - calculated_count
                                    note_card(state, old_cname, -1*diff)
                                    note_card(state, cname, diff)
                                continue
                    assert(valid_neow_add(data, cname))
                else:
                    assert(valid_neow_del(data, cname))
                print('NEOW_BONUS %s: %s %s' % (
                    data['neow_bonus'], cname, (master_count - calculated_count)))
                for state in floor_state:
                    note_card(state, cname, (master_count - calculated_count))
                    assert(state['deck'][cname] >= 0)
                    if state['deck'][cname] == 0:
                        del state['deck'][cname]

    assert(master_deck == calculated_deck)

    # pprint(set(data['relics']))
    # pprint(floor_state[-1]['relics'])
    # TODO: if we found out that we got Omamori from the Neow bonus
    # then we need to go through and remove curses.  (In fact, I think
    # this means we need to do the relic calculation before the
    # per-floor card calculation.)
    master_relics = set(data['relics'])
    calculated_relics = floor_state[-1]['relics']
    if master_relics != calculated_relics:
        for rname in list(master_relics):
            if rname not in calculated_relics:
                assert(valid_neow_relic_add(data))
                print('NEOW_BONUS RELIC ADD %s: %s' % (data['neow_bonus'], rname))
                for state in floor_state:
                    state['relics'].add(rname)
        for rname in list(calculated_relics):
            if rname not in master_relics:
                assert(valid_neow_relic_del(data, rname))
                print('NEOW_BONUS RELIC DEL %s: %s' % (data['neow_bonus'], rname))
                for state in floor_state:
                    state['relics'].remove(rname)
    assert(master_relics == calculated_relics)

    # pprint(list(zip(range(100), floor_state)))
    return floor_state

def reformat(data):
    floor_state = calc_state_by_floor(data)
    pprint(list(zip(range(100), floor_state)))
    card_choices = data['card_choices']
    # pprint(card_choices)

for i in range(1, len(sys.argv)):
    with open(sys.argv[i], 'r') as f:
        data = json.load(f)
        reformat(data)
