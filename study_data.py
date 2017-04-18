#!/usr/bin/env python
# -*-coding: utf8 -*-

import os
import argparse
from pygments.token import Comment, String, Whitespace, Text

from commitgen.data import RawDataset, extract_commits, parse_commits
from commitgen.diff import PerFileExtractor, get_added_lines, get_removed_lines
from commitgen.code import CodeLinesTokenizer
from commitgen.nlp import TreebankTokenizer

def is_only_removed(c):
    return len(get_added_lines(c.diff_file)) == 0

def is_only_added(c):
    return len(get_removed_lines(c.diff_file)) == 0

def is_atomic(c):
    return len(c.diff_file.modified_files) + \
           len(c.diff_file.added_files) +  \
           len(c.diff_file.removed_files) == 1

def get_len_filter(max_code_len, max_nl_len):
    return lambda pc: 1 <= len(pc.code_tokens) <= max_code_len \
                      and 1 <= len(pc.nl_tokens) <= max_nl_len

desc = "Help for buildData"
work_dir = os.environ['WORK_DIR']

parser = argparse.ArgumentParser()

parser.add_argument("dataset",
                    help="Name of the pickle dataset file (without .pickle) in " + work_dir)

parser.add_argument('language',
                    help="Language")

parser.add_argument('--only_added', "-oa",
                    action='store_true',
                    help="Only added")


parser.add_argument('--only_removed', "-or",
                    action='store_true',
                    help="Only removed")

args = parser.parse_args()

if args.only_added and args.only_removed:
    raise Exception("Choose only added or only removed")

marker = "NEW_FILE"
ignore_list = [Comment, String, Whitespace, Text]
code_lines_tokenizer = CodeLinesTokenizer(language=args.language)
per_file_code_extractor = PerFileExtractor(marker=marker)
treebank_tokenizer = TreebankTokenizer()

data_path = os.path.join(work_dir, args.dataset + "_commits")

raw_dataset = RawDataset(data_path)

all_filters = []
atomic_filters = [is_atomic]
if args.only_added:
    print "Using commits with only added lines"
    all_filters.append(is_only_added)
    atomic_filters.append(is_only_added)
elif args.only_removed:
    print "Using commits with only removed lines"
    all_filters.append(is_only_removed)
    atomic_filters.append(is_only_removed)


commits = extract_commits(raw_dataset, per_file_code_extractor,
                          filters=all_filters)

atomic_commits = extract_commits(raw_dataset, per_file_code_extractor,
                                 filters=atomic_filters)

parsed_commits = parse_commits(commits, treebank_tokenizer,
                               code_lines_tokenizer,
                               ignore_types=ignore_list,
                               marker=marker)

parsed_atomic_commits = parse_commits(atomic_commits, treebank_tokenizer,
                                      code_lines_tokenizer,
                                      ignore_types=ignore_list,
                                      marker=marker)

print "Parsed Commits " + str(len(parsed_commits))
print "Atomic Parsed Commits " + str(len(parsed_atomic_commits))

ln_code_len_filter = get_len_filter(100, 100)

filtered_parsed_atomic_commits = filter(ln_code_len_filter, parsed_atomic_commits)
filtered_parsed_commits = filter(ln_code_len_filter, parsed_commits)

print "Filtered Parsed Commits " + str(len(filtered_parsed_commits))
print "Atomic Filtered Parsed Commits " + str(len(filtered_parsed_atomic_commits))
print "Increased size: " + str(1.0*len(filtered_parsed_commits)/ len(filtered_parsed_atomic_commits))

