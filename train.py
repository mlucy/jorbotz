import json
import csv
import numpy as np
import sys
from os import path
from sklearn import model_selection

xs = []
ys = []
def load_test_cases_from_filename(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
        for case in data:
            xs.append(case[0])
            ys.append(case[1])

for i in range(1, len(sys.argv)):
    load_test_cases_from_filename(sys.argv[i])

xs = np.array(xs)
ys = np.array(ys)

x_train, x_test, y_train, y_test = model_selection.train_test_split(
    xs, ys, test_size=0.2)

print(len(x_train))

