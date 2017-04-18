#!/usr/bin/env python
# -*-coding: utf8 -*-


import json
import os
import argparse


def write_txt_files(dataset_lang_part):
    code = []
    nl = []
    global work_dir
    json_file_name = os.path.join(work_dir, dataset_lang_part + ".json")
    with open(json_file_name, 'r') as f:
        data = json.load(f)

    for entry in data:
        code_tokens = map(get_code_token,entry["code_num"])
        nl_tokens = map(get_nl_token, entry["nl_num"])
        joint_code = " ".join(code_tokens)
        joint_code = joint_code.replace("\n", " ")
        code.append(joint_code)
        # got NL skip CODE_START and CODE_END
        nl.append(" ".join(nl_tokens[1:-1]))

    code_txt_file_name = os.path.join(work_dir, dataset_lang_part + ".code")
    with open(code_txt_file_name, "w") as f:
        f.write("\n".join(code).encode("ascii", errors="replace"))

    nl_txt_file_name = os.path.join(work_dir, dataset_lang_part + ".nl")
    with open(nl_txt_file_name, "w") as f:
        f.write("\n".join(nl).encode("ascii", errors="replace"))

def get_code_token(num):
    global vocab
    return vocab["num_to_code"][str(num)]

def get_nl_token(num):
    global vocab
    return vocab["num_to_nl"][str(num)]

desc = "Help for buildMosesData"

work_dir = os.environ['WORK_DIR']
work_dir = os.path.join(work_dir, "preprocessing")

parser = argparse.ArgumentParser(description=desc)

parser.add_argument("dataset",
                    help="Name of the pre_processed dataset " + work_dir)

parser.add_argument('language',
                    help="Language")

args = parser.parse_args()

dataset_lang = args.dataset + "." + args.language

vocab_file_name = os.path.join(work_dir, dataset_lang + ".vocab.json")
with open(vocab_file_name, 'r') as f:
    vocab = json.load(f)

train_file_name = dataset_lang + ".train"
write_txt_files(train_file_name)

valid_file_name = dataset_lang + ".valid"
write_txt_files(valid_file_name)

test_file_name = dataset_lang + ".test"
write_txt_files(test_file_name)