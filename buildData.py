#!/usr/bin/env python
# -*-coding: utf8 -*-

from os import path
import json
import pickle
import os
import argparse
from commitgen.data import build_data, split_list, build_vocab

desc = "Help for buildData"
work_dir = os.environ['WORK_DIR']

parser = argparse.ArgumentParser(description=desc)

parser.add_argument("dataset",
                    help="Name or comma-separated names of the pickle dataset file/s (without .pickle) in " + work_dir)

parser.add_argument('--language', "-l",
                    help="Language")

parser.add_argument('--code_max_length', "-cml",
                    type=int,
                    default=100,
                    help="maximum code length")

parser.add_argument('--nl_max_length', "-nml",
                    type=int,
                    default=100,
                    help="maximum nl length")

parser.add_argument('--code_unk_threshold', "-cut",
                    type=int,
                    default=2,
                    help="code unk threshold")

parser.add_argument('--nl_unk_threshold', "-nut",
                    type=int,
                    default=2,
                    help="nl unk threshold")

parser.add_argument("--test", "-t",
                    action='store_true',
                    help="To generate a test set (otherwise valid=test)")

parser.add_argument("--ratio", "-r",
                    type=float,
                    default=0.8,
                    help="Train/Test split ratio")

args = parser.parse_args()

work_dir = os.path.join(work_dir, "preprocessing")
if not os.path.isdir(work_dir):
    os.mkdir(work_dir)

if "," in args.dataset:
    datasets = args.dataset.split(",")
else:
    datasets = [args.dataset]

per_dataset_parsed_commits = []
all_parsed_commits = []

for dataset in datasets:
  filepath = os.path.join(work_dir, dataset + ".pickle")
  if os.path.isfile(filepath):
      with open(filepath, "rb") as f:
          parsed_commits = pickle.load(f)
      per_dataset_parsed_commits.append(parsed_commits)
      all_parsed_commits += parsed_commits
  else:
    raise IOError("Pickle file does not exist")

vocab = build_vocab(all_parsed_commits, args.code_unk_threshold, args.nl_unk_threshold)

dataset_name = "_".join(datasets)

# storing vocab
vocab_file_name = ".".join([dataset_name, args.language, 'vocab.json'])
with open(path.join(work_dir, vocab_file_name), 'w') as f:
    json.dump(vocab, f)

all_train = []
all_valid = []
all_test = []

for parsed_commits in per_dataset_parsed_commits:
    # splitting dataset
    train, valid, test = split_list(parsed_commits, generate_test=args.test, ratio=args.ratio)
    all_train += train
    all_valid += valid
    all_test += test

print len(all_train), len(all_valid), len(all_test)
# generating data and saving files
train_data = build_data(all_train, vocab,
                        max_code_length=args.code_max_length,
                        max_nl_length=args.nl_max_length)

train_name = ".".join([dataset_name, args.language, "train.json"])
with open(os.path.join(work_dir, train_name), 'w') as f:
    json.dump(train_data, f)


valid_data = build_data(all_valid, vocab,
                        max_code_length=args.code_max_length,
                        max_nl_length=args.nl_max_length)

valid_name = ".".join([dataset_name, args.language, "valid.json"])
with open(os.path.join(work_dir, valid_name), 'w') as f:
    json.dump(valid_data, f)


# we don't set a maximum length ONLY for test data
test_data, ref_data = build_data(all_test, vocab, ref=True)
test_name = ".".join([dataset_name, args.language, "test.json"])
with open(os.path.join(work_dir, test_name), 'w') as f:
    json.dump(test_data, f)

ref_name = ".".join([dataset_name, args.language, "ref.txt"])
with open(os.path.join(work_dir, ref_name), 'w') as f:
    for sha, nl in ref_data:
        try:
            f.write(str(sha )+ "\t" + nl.decode('utf-8').encode('ascii', 'ignore') + "\n")
        except:
            pass
