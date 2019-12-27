from sklearn.linear_model import LogisticRegression

import pickle
import vectorize

import sys
import json
import copy

from pprint import pprint
with open('logistic.model', 'rb') as f:
    pca, model = pickle.load(f)

print(model)

def load_test_cases_from_filename(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
        for state in data:
            # Not vectorized
            choices = state['choices']

            # TODO handle singing bowl
            poss_states = [("SKIP", copy.deepcopy(state))]
            for choice in choices:
                poss_state = copy.deepcopy(state)

                if choice == "SKIP":
                    continue
                if choice not in poss_state['deck']:
                    poss_state['deck'][choice] = 0
                poss_state['deck'][choice] += 1
                poss_states.append((choice, poss_state))

            print("\nchoice","win rate")
            print(state)
            best_chance = -1
            best_card = None
            for poss_state in poss_states:
                vectorized = vectorize.obj_to_vector(poss_state[1])
                inp = pca.transform([vectorized])
                predicted_win = model.predict_proba(inp)[0]
                print(poss_state[0], predicted_win[1])
                if predicted_win[1] > best_chance:
                    best_card = poss_state[0]
                    best_chance = predicted_win[1]

            print('Us:    ', best_card)
            print('Jorbs: ', state['picked'])

for i in range(1, len(sys.argv)):
    load_test_cases_from_filename(sys.argv[i])

