from os import path
from sklearn import metrics
from sklearn import model_selection
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import csv
import json
import matplotlib.pyplot as plt
import numpy as np
import pickle
import random
import sys

random.seed(2)
np.random.seed(2)

def load_test_cases_from_filename(filename, xs, ys):
    with open(filename, 'r') as f:
        data = json.load(f)
        for case in data:
            xs.append(case[0])
            ys.append(case[1])

filenames = sys.argv[1:]
train_filenames = []
test_filenames = []
for filename in filenames:
    if random.random() < 0.2:
        test_filenames.append(filename)
    else:
        train_filenames.append(filename)

x_train = []
x_test = []
y_train = []
y_test = []

for fn in train_filenames:
    load_test_cases_from_filename(fn, x_train, y_train)
for fn in test_filenames:
    load_test_cases_from_filename(fn, x_test, y_test)

# scaler = StandardScaler(with_std=False)
# scaler.fit(x_train + x_test)
# x_train = scaler.transform(x_train)
# x_test = scaler.transform(x_test)

pca = PCA(whiten=True, n_components=200)
pca.fit(np.concatenate((x_train,x_test)))
x_train = pca.transform(x_train)
x_test = pca.transform(x_test)

# good_x = []
# good_y = []
# for x, y in zip(list(x_test), list(y_test)):
#     if x[-13] > 40:
#         good_x.append(x)
#         good_y.append(y)

# print(len(good_x))

logistic = LogisticRegression()

logistic.fit(x_train, y_train)

# predictions = logistic.predict(good_x)
# confusion = metrics.confusion_matrix(good_y, predictions)
print('train', logistic.score(x_train, y_train))
print('test', logistic.score(x_test, y_test))
predictions = logistic.predict(x_test)
confusion = metrics.confusion_matrix(y_test, predictions)
print(confusion)

with open('logistic.model', 'wb') as f:
    pickle.dump((pca, logistic), f)

