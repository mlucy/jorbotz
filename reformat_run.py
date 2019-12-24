import json
import sys
import copy
from pprint import pprint

# TODO: add support for relics so that we can handle frozen egg properly.

CARDS = {
    'IRONCLAD': {
        'POWERS': ['Inflame'],
        'ATTACKS': [],
        'SKILLS': [],
        'OTHER': [],
    },
}
for cls in CARDS:
    for typ in CARDS[cls]:
        CARDS[cls][typ] += [x+'+1' for x in CARDS[cls][typ]]

STARTING_DECKS = {
    'IRONCLAD': {'Strike_R': 5, 'Defend_R': 4, 'Bash': 1},
}

def calc_state_by_floor(data):
    card_change_map = {}
    for i in range(1, data['floor_reached']):
        card_change_map[i] = []
    for c in data['card_choices']:
        if c['picked'] != 'SKIP':
            card_change_map[c['floor']].append((c['picked'], 1))

    for c in data['campfire_choices']:
        cname = c.get('data', '')
        if c['key'] == 'SMITH':
            card_change_map[c['floor']].append((cname, -1))
            card_change_map[c['floor']].append((cname+'+1', 1))
        elif c['key'] == 'PURGE':
            card_change_map[c['floor']].append((cname, -1))
        # TODO: DIG, LIFT, RECALL

    for floor, purchase in zip(data['item_purchase_floors'], data['items_purchased']):
        if purchase not in data['relics']:
            card_change_map[floor].append((purchase, 1))
        else:
            # TODO: relics
            pass

    # Despite the name this does not include cards purged at campfires with toke.
    for floor, purge in zip(data['items_purged_floors'], data['items_purged']):
        card_change_map[floor].append((purge, -1))

    for e in data['event_choices']:
        # TODO: relics
        for cname in e.get('cards_removed', []):
            card_change_map[e['floor']].append((cname, -1))
        for cname in e.get('cards_upgraded', []):
            card_change_map[e['floor']].append((cname, -1))
            card_change_map[e['floor']].append((cname+'+1', 1))
        for cname in e.get('cards_obtained', []):
            card_change_map[e['floor']].append((cname, 1))

    floor_state = [{
        'deck': STARTING_DECKS[data['character_chosen']],
    }]
    for floor in range(1, data['floor_reached']):
        new_state = copy.deepcopy(floor_state[-1])
        for cname, diff in card_change_map[floor]:
            if cname not in new_state['deck']:
                new_state['deck'][cname] = 0
            new_state['deck'][cname] += diff
            assert(new_state['deck'][cname] >= 0)
            if new_state['deck'][cname] == 0:
                del new_state['deck'][cname]

        # TODO: relics
        # TODO: events
        floor_state.append(new_state)

    master_deck = {}
    for cname in data['master_deck']:
        if cname == 'AscendersBane':
            continue
        if cname not in master_deck:
            master_deck[cname] = 0
        master_deck[cname] += 1
    pprint(master_deck)
    pprint(floor_state[-1]['deck'])
    assert(master_deck == floor_state[-1]['deck'])

    pprint(list(zip(range(100), floor_state)))
    exit(1)

def reformat(data):
    state_by_floor = calc_state_by_floor(data)
    card_choices = data['card_choices']
    pprint(card_choices)

for i in range(1, len(sys.argv)):
    with open(sys.argv[i], 'r') as f:
        data = json.load(f)
        if data['character_chosen'] != 'IRONCLAD':
            print('Only IRONCLAD supported (got %s).' % data['character_chosen'])
            exit(1)
        reformat(data)
