#!/usr/bin/env python
# -*-coding: utf8 -*-

from os import path, listdir
import json
from unidiff import PatchSet, PatchedFile
import warnings
import collections
import random


PAD = 1
UNK = 2
START = 3
END = 4
NEW_FILE = 5

class RawDataset(object):

    def __init__(self, data_path):
        json_path = path.join(data_path, "json")
        diffs_path = path.join(data_path, "diff")
        diff_files = listdir(diffs_path)
        json_files = listdir(json_path)

        shas_diff = [f.replace('.diff', '') for f in diff_files]
        shas_json = [f.replace('.json', '') for f in json_files]

        if not set(shas_diff) == set(shas_json):
            warnings.warn("There were missing files")
            self.shas = list(set(shas_diff) & set(shas_json))
        else:
          self.shas = shas_json
        
        self.diff = {}
        self.metadata = {}

        for sha in self.shas:
            diff_filepath = path.join(diffs_path, sha + '.diff')
            try:
                with open(diff_filepath, 'r') as diff_file:
                    diff = diff_file.read().decode('utf-8')
                    diff_data = PatchSet(diff.splitlines())

                json_filepath = path.join(json_path, sha + '.json')
                with open(json_filepath, 'r') as json_file:
                    json_data = json.load(json_file)

                self.diff[sha] = diff_data
                self.metadata[sha] = json_data
            except Exception as e:
                warnings.warn("Problem in sha " + sha)


Commit = collections.namedtuple('Commit', ['sha', 'metadata', 'diff_file'], verbose=False)
ParsedCommit = collections.namedtuple('ParsedCommit', ['id', 'code', 'nl_tokens', 'code_tokens'], verbose=False)


def extract_commits(raw_dataset, code_lines_extractor, filters=()):
    """

    :param raw_dataset: RawDataset object containing commit metadata and dif files
    :param get_code_lines_fn: function to extract code lines from the diff file
    :param filters: list of filter functions to a commit
    :return:
    """
    commits = []
    for sha in raw_dataset.shas:
        try:
            diff_file = raw_dataset.diff[sha]
            metadata = raw_dataset.metadata[sha]
            commit = Commit(sha, metadata, diff_file)
            if all([func(commit) for func in filters]):
                message = commit.metadata['commit']['message']
                code_lines = code_lines_extractor.get_lines(commit.diff_file)
                commits.append((sha, message, code_lines))
        except KeyError:
            pass
    return commits


def parse_commits(commits, nl_tokenizer, code_tokenizer, ignore_types=None, filters=(), marker=None):
    """
    Parses a list of extracted commits (sha, message, code_lines) tuples.

    :param commits_data: (sha, message, code_lines)
    :param language: (str) the language of the code in the commits
    :return: list of tuples of the form (sha, code, parsed_nl, parsed_code)
    """
    parsed_commits = []
    for i, (sha, message, code_lines) in enumerate(commits):
        parsed_nl = nl_tokenizer.tokenize(message)
        if marker:
            parsed_code = []
            code_lines_chunk = []
            for code_line in code_lines:
                if code_line != marker:
                    code_lines_chunk.append(code_line)
                else:
                    parsed_code.append("NEW_FILE")
                    parsed_code += code_tokenizer.tokenize(code_lines_chunk, ignore_types=ignore_types)
                    code_lines_chunk = []
            if code_lines_chunk:
                parsed_code += code_tokenizer.tokenize(code_lines_chunk, ignore_types=ignore_types)
        else:
            parsed_code = code_tokenizer.tokenize(code_lines, ignore_types=ignore_types)
        parsed_commit = ParsedCommit(i, '\n'.join(code_lines), parsed_nl, parsed_code)
        if all([func(parsed_commit) for func in filters]):
            parsed_commits.append(parsed_commit)
    return parsed_commits


def build_vocab(parsed_commits, code_unk_threshold, nl_unk_threshold):
    """
    Generates the vocabularies and index_to_token mappings for both code an nl

    :param parsed_commits: list of tuples (sha, parsed_nl, parsed_code)
    :param code_unk_threshold: minimum freq. to consider a code token as UNKNOWN
    :param nl_unk_threshold: minimum freq. to consider a nl token as UNKNOWN
    :param language: (str) language
    :return: vocab
    """

    words = collections.Counter()
    tokens = collections.Counter()

    for sha, code, nl_tokens, code_tokens in parsed_commits:
        words.update(nl_tokens)
        tokens.update(code_tokens)

    if "NEW_FILE" in  tokens:
        vocab = {"nl_to_num": {"UNK": UNK, "CODE_START": START, "CODE_END": END},
                 "code_to_num": {"UNK": UNK, "CODE_START": START, "CODE_END": END, "NEW_FILE": NEW_FILE},
                 "num_to_nl": {PAD: "UNK", UNK: "UNK", START: "CODE_START", END: "CODE_END"},
                 "num_to_code": {UNK: "UNK", START: "CODE_START", END: "CODE_END", NEW_FILE: "NEW_FILE"}}

        token_count = NEW_FILE + 1
        nl_count = END + 1

    else:
        vocab = {"nl_to_num": {"UNK": UNK, "CODE_START": START, "CODE_END": END},
                 "code_to_num": {"UNK": UNK, "CODE_START": START, "CODE_END": END},
                 "num_to_nl": {PAD: "UNK", UNK: "UNK", START: "CODE_START", END: "CODE_END"},
                 "num_to_code": {UNK: "UNK", START: "CODE_START", END: "CODE_END"}}

        token_count = END + 1
        nl_count = END + 1

    # Do unigram tokens, skip NEW_FILE
    for tok in tokens:
        if tok != "NEW_FILE":
            if tokens[tok] > code_unk_threshold:
                vocab["code_to_num"][tok] = token_count
                vocab["num_to_code"][token_count] = tok
                token_count += 1
            else:
                vocab["code_to_num"][tok] = UNK

    for word in words:
        if words[word] > nl_unk_threshold:
            vocab["nl_to_num"][word] = nl_count
            vocab["num_to_nl"][nl_count] = word
            nl_count += 1
        else:
            vocab["nl_to_num"][word] = UNK

    vocab["max_code"] = token_count - 1
    vocab["max_nl"] = nl_count - 1

    return vocab


def build_data(parsed_commits, vocab, ref=False, max_code_length=None, max_nl_length=None):
    """
    Build the training dataset

    :param parsed_commits:
    :param vocab: vocabulary as generated by build_vocab
    :param ref: if True, return reference list
    :param max_code_length:
    :param max_nl_length:
    :return: dataset
    """

    dataset = []
    skipped = 0

    if ref:
        ref_cont = []

    for sha, code, nl_tokens, code_tokens in parsed_commits:
        nlToks = nl_tokens
        codeToks = code_tokens

        datasetEntry = {"id": sha,
                        "code": code,
                        "code_sizes": len(codeToks),
                        "code_num": [],
                        "nl_num": []}

        for tok in codeToks:
            if tok not in vocab["code_to_num"]:
                vocab["code_to_num"][tok] = UNK
            datasetEntry["code_num"].append(vocab["code_to_num"][tok])

        datasetEntry["nl_num"].append(vocab["nl_to_num"]["CODE_START"])
        for word in nlToks:
            if word not in vocab["nl_to_num"]:
                vocab["nl_to_num"][word] = UNK
            datasetEntry["nl_num"].append(vocab["nl_to_num"][word])

        datasetEntry["nl_num"].append(vocab["nl_to_num"]["CODE_END"])

        if max_code_length or max_nl_length:
            code_ok, nl_ok = True, True
            if max_code_length and len(datasetEntry["code_num"]) >= max_code_length:
                code_ok = False
            if max_nl_length and len(datasetEntry["nl_num"]) >= max_nl_length:
                nl_ok = False
            if code_ok and nl_ok:
                dataset.append(datasetEntry)
                if ref:
                    ref_cont.append((sha, " ".join(nl_tokens)))
            else:
                skipped += 1
        else:
            dataset.append(datasetEntry)
            if ref:
                ref_cont.append((sha, " ".join(nl_tokens)))

    print 'Total size = ' + str(len(dataset))
    print 'Total skipped = ' + str(skipped)

    if ref:
        return dataset, ref_cont
    return dataset


def split_list(dataset, ratio=0.8, generate_test=False):
    """

    :param dataset: dataset
    :param ratio: to split train/test
    :param generate_test: (otherwise valid=test)
    :return:
    """

    train, valid, test = [], [], []
    dev_size = int(len(dataset) * ratio)

    if generate_test:
        # fixed 90/10 ratio for development set
        train_size = int(dev_size * 0.9)
        for datasetEntry in dataset:
            r = random.random()
            if r <= ratio and len(train) + len(valid) < dev_size:
                rr = random.random()
                if rr < 0.9 and len(train) < train_size:
                    train.append(datasetEntry)
                else:
                    valid.append(datasetEntry)
            else:
                test.append(datasetEntry)

        return train, valid, test

    else:
        train_size = dev_size
        for datasetEntry in dataset:
            r = random.random()
            if r <= ratio and len(train) < train_size:
                train.append(datasetEntry)
            else:
                valid.append(datasetEntry)

        return train, valid, valid
