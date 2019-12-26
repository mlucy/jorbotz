import copy
import csv
import json
import re
import sys

from pprint import pprint, pformat

SILLY_POTION_NAMES = [
    'EssenceOfSteel',
    'GamblersBrew',
    'EntropicBrew',
    'LiquidBronze',
    'GhostInAJar',
    'Fruit Juice',
    'SmokeBomb'
]

def note_card_raw(state, cname, diff):
    if cname not in state['deck']:
        state['deck'][cname] = 0
    state['deck'][cname] += diff
    if state['deck'][cname] == 0:
        del state['deck'][cname]

def note_card(state, cname, diff):
    if 'Omamori' in state['relics'] and is_type(cname, 'Curse') and diff > 0:
        uses = state['scratch'].get('omamori_uses', 0)
        if uses < 2:
            state['scratch']['omamori_uses'] = uses + 1
            return False
    note_card_raw(state, cname, diff)
    return True

def update_from_floor(states, floor, required_diffs, diffs, cb=None):
    for cname in diffs:
        required_diffs[cname] -= diffs[cname]
        if required_diffs[cname] == 0:
            del required_diffs[cname]
    for state in states[floor:]:
        for cname in diffs:
            note_card_raw(state, cname, diffs[cname])
        if cb:
            cb(state)

# Assume that we only pass in the upgraded ones
def patch_card_upgrade_relics(date, states, required_diffs):
    last_state = states[-1]
    for cname in required_diffs:
        floor = None
        scratch_name = None
        if cname[-2:] == '+1' and required_diffs[cname] > 0:
            old_cname = cname[:-2]
            if required_diffs.get(old_cname, 0) < 0:
                if is_type(cname, 'Skill'):
                    scratch_name = 'war_paint'
                elif is_type(cname, 'Attack'):
                    scratch_name='whetstone'
                else:
                    continue
                upgrades = last_state['scratch'].get(scratch_name+'_upgrades', 0)
                if upgrades > 0:
                    floor = last_state['scratch'][scratch_name+'_floor']
                    if old_cname not in states[floor]['deck']:
                        continue
                    def f(state):
                        state['scratch'][scratch_name+'_upgrades'] -= 1
                    print('Upgrade %s from %s on floor %s.' % (old_cname, scratch_name, floor))
                    update_from_floor(states, floor,
                                      required_diffs, {old_cname: -1, cname: 1}, cb=f)
                    return True
    return False

def patch_card_neow_cost_raw(data, states, required_diffs):
    cost = data['neow_cost']
    if cost == 'CURSE':
        for cname in required_diffs:
            if is_type(cname, 'Curse') and required_diffs[cname] > 0:
                print('Neow curse %s on floor 0.' % cname)
                update_from_floor(states, 0, required_diffs, {cname: 1})
                return True
    return False

def patch_card_neow_bonus_raw(data, states, required_diffs):
    bonus = data['neow_bonus']
    if bonus in ['ONE_RANDOM_RARE_CARD']:#, 'THREE_RARE_CARDS', 'THREE_CARDS']:
        for cname in required_diffs:
            if required_diffs[cname] > 0:
                print('Neow card %s on floor 0.' % cname)
                update_from_floor(states, 0, required_diffs, {cname: 1})
                return True
    if bonus == 'UPGRADE_CARD':
        for cname in required_diffs:
            if cname[-2:] == '+1' and required_diffs[cname] > 0:
                old_cname = cname[:-2]
                if old_cname in states[0]['deck']:
                    if required_diffs.get(old_cname, 0) < 0:
                        print('Neow upgrade %s on floor 0.' % old_cname)
                        update_from_floor(states, 0, required_diffs, {old_cname: -1, cname: 1})
                        return True
    if bonus == 'REMOVE_CARD':
        for cname in required_diffs:
            if cname in states[0]['deck'] and required_diffs[cname] < 0:
                update_from_floor(states, 0, required_diffs, {cname: -1})
                return True
    if bonus == 'REMOVE_TWO':
        removal_candidates = []
        for cname in required_diffs:
            if cname in states[0]['deck']:
                if required_diffs[cname] < -1:
                    print('Neow remove 2x %s on floor 0.' % cname)
                    update_from_floor(states, 0, required_diffs, {cname: -2})
                    return True
                elif required_diffs[cname] < 0:
                    removal_candidates.append(cname)
                    if len(removal_candidates) == 2:
                        print('Neow remove %s on floor 0.' % removal_candidates)
                        update_from_floor(states, 0, required_diffs, {
                            removal_candidates[0]: -1,
                            removal_candidates[1]: -1,
                        })
                        return True
    return False

def patch_astrolabe(data, states, required_diffs):
    astrolabe_floor = states[-1]['scratch'].get('astrolabe_floor', None)
    if astrolabe_floor is None:
        return False

    upgrade_candidates = []
    removal_candidates = []


    for cname in required_diffs:
        if (cname[-2:] == '+1' and
            required_diffs[cname] > 0):
            upgrade_candidates += [cname] * required_diffs[cname]

        elif (cname in states[astrolabe_floor]['deck'] and
              required_diffs[cname] < 0):
            removal_candidates += [cname] * (-1 * required_diffs[cname])

    deduped_upgrade_candidates = list(set(upgrade_candidates))
    if len(deduped_upgrade_candidates) >= 3:
        upgrade_candidates = deduped_upgrade_candidates
    upgrade_candidates = upgrade_candidates[:3]
    removal_candidates = removal_candidates[:3]
    if len(upgrade_candidates) == 3 and len(removal_candidates) == 3:
        update_diffs = {}
        for u in upgrade_candidates:
            if u not in update_diffs:
                update_diffs[u] = 0
            update_diffs[u] += 1
        for r in removal_candidates:
            if r not in update_diffs:
                update_diffs[r] = 0
            update_diffs[r] -= 1

        print('Astrolabe %s on floor %s' % (update_diffs, astrolabe_floor))
        def f(state):
            state['scratch']['astrolabe_floor'] = None
        update_from_floor(states, astrolabe_floor, required_diffs, update_diffs, cb=f)

        return True

    return False

def patch_card_neow(data, states, required_diffs):
    if states[-1]['scratch'].get('neow_bonus_available', True):
        if patch_card_neow_bonus_raw(data, states, required_diffs):
            states[-1]['scratch']['neow_bonus_available'] = False
            return True
    if states[-1]['scratch'].get('neow_cost_available', True):
        if patch_card_neow_cost_raw(data, states, required_diffs):
            states[-1]['scratch']['neow_cost_available'] = False
            return True
    return False

def patch_card_neow_liberal_raw(data, states, required_diffs):
    bonus = data['neow_bonus']
    lost_card = None
    gained_card = None
    if bonus == 'TRANSFORM_CARD':
        for cname in required_diffs:
            if required_diffs[cname] < 0:
                if cname in states[0]['deck']:
                    if lost_card is None:
                        lost_card = cname
            elif required_diffs[cname] > 0:
                if gained_card is None:
                    gained_card = cname
            if lost_card and gained_card:
                print('Neow transform %s -> %s.' % (lost_card, gained_card))
                update_from_floor(states, 0, required_diffs, {lost_card: -1, gained_card: 1})
                return True
    return False

# TRANSFORM_CARD is so easy to satisfy that we put it separately in
# the precedence.
def patch_card_neow_liberal(data, states, required_diffs):
    if states[-1]['scratch'].get('neow_bonus_available', True):
        if patch_card_neow_liberal_raw(data, states, required_diffs):
            states[-1]['scratch']['neow_bonus_available'] = False
            return True
    return False

# TODO: check that card counts never go negative during run.

def patch_empty_cage(data, states, required_diffs):
    for cname in required_diffs:
        if required_diffs[cname] < 0:
            removes = states[-1]['scratch'].get('empty_cage_removes', 0)
            if removes > 0:
                floor = states[-1]['scratch']['empty_cage_floor']
                if cname not in states[floor]['deck']:
                    continue
                def f(state):
                    state['scratch']['empty_cage_removes'] -= 1
                print('Empty cage remove %s.' % cname)
                update_from_floor(states, floor, required_diffs, {cname: -1}, cb=f)
                return True
    return False

def patch_vampires(data, states, required_diffs):
    vampire_floor = states[-1]['scratch']['vampire_floor']
    if vampire_floor is not None:
        missing_strikes = required_diffs.get('Strike', 0)
        if missing_strikes < 0:
            update_from_floor(states, vampire_floor, required_diffs, {'Strike': missing_strikes})
        missing_strikes_plus = required_diffs.get('Strike+1', 0)
        if missing_strikes_plus < 0:
            update_from_floor(states, vampire_floor, required_diffs, {'Strike+1': missing_strikes_plus})
        if missing_strikes < 0 or missing_strikes_plus < 0:
            return True
    return False

def patch_unupgraded_cards(data, states, required_diffs):
    for card, floor in zip(states[-1]['scratch']['unupgraded_name_cards'],
                           states[-1]['scratch']['unupgraded_name_floors']):
        if card is not None:
            if card[-2:] != '+1':
                if required_diffs.get(card, 0) > 0:
                    if required_diffs.get(card+'+1', 0) < 0:
                        print('Patching unupgraded cards %s on floor %s.' % (card, floor))
                        update_from_floor(states, floor, required_diffs,
                                          {card: +1, card+'+1': -1})
                        return True
                elif required_diffs.get(card, 0) < 0:
                    if required_diffs.get(card+'+1', 0) > 0:
                        print('Patching upgraded cards %s on floor %s.' % (card, floor))
                        update_from_floor(states, floor, required_diffs,
                                          {card: -1, card+'+1': +1})
                        return True
    return False

# TODO: cursed key

def patch_mirror(data, states, required_diffs):
    mirror_floor = states[-1]['scratch'].get('mirror_floor', None)
    if mirror_floor is not None:
        for cname in required_diffs:
            if (required_diffs[cname] > 0 and
                cname in states[mirror_floor]['deck'] and
                not is_type(cname, 'Curse')):
                def f(state):
                    state['scratch']['mirror_floor'] = None
                print('Dollys Mirror adding %s on floor %s' % (cname, mirror_floor))
                update_from_floor(states, mirror_floor, required_diffs, {cname: 1}, cb=f)

                return True
    return False

def patch_tiny_house(data, states, required_diffs):
    house_floor = states[-1]['scratch'].get('tiny_house_floor', None)
    if house_floor is not None:
        for cname in required_diffs:
            if (cname[-2:] == "+1" and
                required_diffs[cname] > 0 and
                cname[:-2] in states[house_floor]['deck'] and
                required_diffs.get(cname[:-2], 0) < 0 ):
                print('Tiny House upgrading %s on floor %s' % (cname[:-2], house_floor))
                def f(state):
                    state['scratch']['tiny_house_floor'] = None
                update_from_floor(states, house_floor, required_diffs,
                                  {cname[:-2]:-1, cname:1}, cb=f)
                return True
    return False

def patch_curse_ignorer(data, states, required_diffs):
    for cname in required_diffs:
        if is_type(cname, 'Curse') and required_diffs[cname] > 0:
            print('Ignoring curse %s.' % cname)
            update_from_floor(states, len(states)-1, required_diffs, {cname: 1})
            return True
    return False

# TODO: necronomicurse

def patch_card_history(data, states, required_diffs):
    # TODO only run patches that are required, and in order
    precedence = [
        patch_card_upgrade_relics,
        patch_unupgraded_cards,
        patch_card_neow,
        patch_vampires,
        patch_empty_cage,
        patch_card_neow_liberal,
        patch_tiny_house,
        patch_astrolabe,
        patch_mirror,
        patch_curse_ignorer,
    ]
    found = True
    while found:
        found = False
        for f in precedence:
            if f(data, states, required_diffs):
                found = True
                break

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

    for i in range(0, data['floor_reached']+1):
        card_change_map[i] = []
        relic_change_map[i] = []
    for c in data['card_choices']:
        if c['picked'] not in ['SKIP', 'Singing Bowl']:
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
            if not (re.match('(?i).*potion$', purchase) or
                    purchase in SILLY_POTION_NAMES):
                print(ALL_RELICS)
                print(purchase)
                assert(False)

    # Despite the name this does not include cards purged at campfires with toke.
    for floor, purge in zip(data['items_purged_floors'], data['items_purged']):
        add_card_change(floor, purge, -1)

    nloth_lost_relic = None
    vampire_floor = None
    unupgraded_name_cards = []
    unupgraded_name_floors = []
    for e in data['event_choices']:
        if e['player_choice'] == 'Became a vampire':
            vampire_floor = e['floor']
        if (e['event_name'] in ['Falling', 'Bonfire Elementals', 'Purifier'] or
            e['player_choice'] in ['Forget', 'Upgrade and Remove']):
            unupgraded_name_cards.append(tr(e['cards_removed'][0]))
            unupgraded_name_floors.append(e['floor'])
        if e['player_choice'] in ['Became Test Subject', 'Transformed Cards']:
            for cname in e['cards_transformed']:
                unupgraded_name_cards.append(tr(cname))
                unupgraded_name_floors.append(e['floor'])
        if e['player_choice'] in ['Copied']:
            for cname in e['cards_obtained']:
                unupgraded_name_cards.append(tr(cname))
                unupgraded_name_floors.append(e['floor'])
        if e['event_name'] == "N'loth" and e['player_choice']=='Traded Relic':
            nloth_lost_relic = e['relics_lost'][0]
        for cname in e.get('cards_removed', []) + e.get('cards_transformed', []):
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

    floor_state = []
    new_state = {
        'deck': STARTING_DECKS[data['character_chosen']],
        'relics': STARTING_RELICS[data['character_chosen']],
        'scratch': {
            'vampire_floor': vampire_floor,
            'unupgraded_name_cards': unupgraded_name_cards,
            'unupgraded_name_floors': unupgraded_name_floors,
        },
    }

    if data['neow_bonus'] in ['ONE_RARE_RELIC', 'RANDOM_COMMON_RELIC', 'THREE_ENEMY_KILL']:
        # Bullshit case where we never aquired a relic, but it's traded to N'loth
        if nloth_lost_relic is None:
            new_state['relics'].add(data['relics'][1])
        else:
            found_nloth_lost_relic = False
            for floor in relic_change_map:
                # print (nloth_lost_relic, relic_change_map[floor])
                if (nloth_lost_relic, 1) in relic_change_map[floor]:
                    new_state['relics'].add(data['relics'][1])
                    found_nloth_lost_relic = True
                    break
            if not found_nloth_lost_relic:
                new_state['relics'].add(nloth_lost_relic)

    elif data['neow_bonus'] in ['BOSS_RELIC']:
        new_state['relics'] = set([data['relics'][0]])

    for floor in range(0, data['floor_reached']+1):
        if floor_state != []:
            new_state = copy.deepcopy(floor_state[-1])

        for rname, diff in relic_change_map[floor]:
            if diff == 1:
                # print(rname, new_state['relics'])
                assert(rname not in new_state['relics'])
                new_state['relics'].add(rname)
                if rname == 'War Paint':
                    new_state['scratch']['war_paint_upgrades'] = 2
                    new_state['scratch']['war_paint_floor'] = floor
                elif rname == 'Whetstone':
                    new_state['scratch']['whetstone_upgrades'] = 2
                    new_state['scratch']['whetstone_floor'] = floor
                elif rname == 'Empty Cage':
                    new_state['scratch']['empty_cage_removes'] = 2
                    new_state['scratch']['empty_cage_floor'] = floor
                elif rname == 'Tiny House':
                    new_state['scratch']['tiny_house_floor'] = floor
                elif rname == 'Astrolabe':
                    new_state['scratch']['astrolabe_floor'] = floor
                elif rname == 'DollysMirror':
                    new_state['scratch']['mirror_floor'] = floor
                elif rname == 'FrozenCore':
                    new_state['relics'].remove('Cracked Core')
                elif rname == 'Black Blood':
                    new_state['relics'].remove('Burning Blood')
                elif rname == 'Ring of the Serpent':
                    new_state['relics'].remove('Ring of the Snake')
            elif diff == -1:
                assert(rname in new_state['relics'])
                new_state['relics'].remove(rname)
            else:
                assert(False)

        for cname, diff in card_change_map[floor]:
            if diff > 0:
                if (('Frozen Egg 2' in new_state['relics'] and is_type(cname, 'Power')) or
                    ('Toxic Egg 2' in new_state['relics'] and is_type(cname, 'Skill')) or
                    ('Molten Egg 2' in new_state['relics'] and is_type(cname, 'Attack'))):
                    if cname[-2:] != '+1':
                        cname += '+1'
            note_card(new_state, cname, diff)

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
    all_card_names = list(set(master_deck.keys()).union(set(calculated_deck.keys())))
    required_diffs = {}
    for cname in all_card_names:
        req = master_deck.get(cname, 0) - calculated_deck.get(cname, 0)
        if req != 0:
            required_diffs[cname] = req
    patch_card_history(data, floor_state, required_diffs)
    for cname in required_diffs:
        if required_diffs[cname] != 0:
            print('Failed to resolve diffs.')
            pprint(master_deck)
            pprint(calculated_deck)
            pprint(required_diffs)
            break
    assert(master_deck == calculated_deck)

    # pprint(set(data['relics']))
    # pprint(floor_state[-1]['relics'])
    # TODO: if we found out that we got Omamori from the Neow bonus
    # then we need to go through and remove curses.  (In fact, I think
    # this means we need to do the relic calculation before the
    # per-floor card calculation.)
    master_relics = set(data['relics'])
    calculated_relics = set(floor_state[-1]['relics'])

    # print(master_relics);print(calculated_relics)
    assert(master_relics == calculated_relics)

    # pprint(list(zip(range(100), floor_state)))
    return floor_state

def formatted_output(data, state, floor, extra={}):
    boss = None

    for fight in data['damage_taken']:
        if fight['floor'] == 16 and floor <= 16:
            boss = fight['enemies']
        if fight['floor'] == 33 and floor > 16 and floor <= 33:
            boss = fight['enemies']
        if fight['floor'] == 50 and floor > 33 and floor <= 50:
            boss = fight['enemies']

    formatted_output = {
        'class': data['character_chosen'],
        'floor': floor,
        'deck': state['deck'],
        'relics': state['relics'],
        'gold': data['gold_per_floor'][floor],
        'hp': data['current_hp_per_floor'][floor],
        'max_hp': data['max_hp_per_floor'][floor],
        'boss': boss,
    }
    return {**formatted_output, **extra}

def reformat(data, filename):
    floor_state = calc_state_by_floor(data)
    # pprint(list(zip(range(100), floor_state)))
    card_choices = data['card_choices']
    won = data['current_hp_per_floor'][-1] != 0

    with open('processed/winrate/'+filename, 'w') as o:
        output_array = []
        for i, state in zip(range(min(len(floor_state)-1, 56)), floor_state):
            output_array.append(
                formatted_output(
                    data,
                    state,
                    i,
                    {
                        'won': won,
                    },
                )
            )
        json.dump(output_array, o)

    with open('processed/cardchoice/'+filename, 'w') as o:
        output_array = []
        for card_choice in card_choices:
            floor = card_choice['floor']
            state = floor_state[floor]
            not_picked = [tr(name) for name in card_choice['not_picked']]
            picked = tr(card_choice['picked'])
            choices = [picked] + not_picked
            choices.sort()

            output_array.append(
                formatted_output(
                    data,
                    floor_state[floor],
                    floor,
                    {
                        'choices': choices,
                        'picked': picked,
                    }
                )
            )
        json.dump(output_array, o)

    # pprint(card_choices)

for i in range(1, len(sys.argv)):
    with open(sys.argv[i], 'r') as f:
        data = json.load(f)
        filename = sys.argv[i].split('/')[-1]
        reformat(data, filename)
