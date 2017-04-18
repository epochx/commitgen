#!/usr/bin/env python
# -*-coding: utf8 -*-

import json
import numpy as np
import argparse
from os import path, environ, makedirs

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm


def get_code(num):
    return vocab["num_to_code"][str(num)]

def get_prediction_nl(prediction):
    return prediction.strip().split("\t")[1].split()

def get_attentions(attention):
    return json.loads(attention)


work_dir = environ["WORK_DIR"]

parser = argparse.ArgumentParser(description="")

parser.add_argument("dataset",
                    help="Name of the pickle dataset file (without .pickle) in " + work_dir)

parser.add_argument('language',
                    help="Language")

parser.add_argument('predictions',
                    help="Path to predictions file")

parser.add_argument('attentions',
                    help="Path to attentions file")

parser.add_argument('save_path',
                    help="Path to save images")

args = parser.parse_args()

dataset = args.dataset
language = args.language
predictions_file_path = args.predictions
attentions_file_path = args.attentions
to_save_path= args.save_path

dataset_lang = dataset + "." + language

vocab_file_name = path.join(*[work_dir, "preprocessing", dataset_lang + ".vocab.json"])
print vocab_file_name
with open(vocab_file_name, "r") as f:
    vocab = json.load(f)

test_file_name = path.join(*[work_dir, "preprocessing", dataset_lang + ".test.json"])
print test_file_name
with open(test_file_name, "r") as f:
    test_data = json.load(f)

# read Predictions in
with open(predictions_file_path, "r") as f:
    predictions = f.readlines()


# read Attentions file
with open(attentions_file_path, "r") as f:
    attentions = f.readlines()


alignments_dir = path.join(to_save_path, dataset_lang + ".alignments")

if not path.isdir(alignments_dir):
  makedirs(alignments_dir)

for test, prediction, attention in zip(test_data, predictions, attentions):
    name = path.join(alignments_dir, str(test["id"]) + ".png")
    code_tokens = map(get_code, test["code_num"])
    pred_nl_tokens = get_prediction_nl(prediction)
    alphas = get_attentions(attention)
    aspect = 1.0 * len(pred_nl_tokens) / len(code_tokens)
    print code_tokens
    print pred_nl_tokens
    # values after are zeroes due to padding
    #print alphas[:len(code_tokens)]
    try:
        fig = plt.figure(figsize=(5, 5))
        ax = fig.add_subplot(111)
        ax.matshow(alphas[:len(code_tokens)], interpolation='nearest',
                    aspect="auto", cmap=cm.gray)
        plt.xticks(np.arange(len(pred_nl_tokens)), pred_nl_tokens, rotation=45)
        plt.yticks(np.arange(len(code_tokens)), code_tokens)
        plt.tight_layout()
        plt.savefig(name)
    except Exception as e:
        print e
