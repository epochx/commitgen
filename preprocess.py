#!/usr/bin/env python
# -*-coding: utf8 -*-

import pickle
import numpy as np
import argparse
import os

from commitgen.data import RawDataset, extract_commits, parse_commits
from commitgen.diff import AddRemExtractor, PerFileExtractor, get_added_lines, get_removed_lines
from commitgen.code import CodeChunkTokenizer, CodeLinesTokenizer
from commitgen.nlp import TreebankTokenizer
from pygments.token import Comment, String, Whitespace, Text


def is_only_removed(c):
    return len(get_added_lines(c.diff_file)) == 0

def is_only_added(c):
    return len(get_removed_lines(c.diff_file)) == 0

def is_atomic(c):
    return len(c.diff_file.modified_files) + \
           len(c.diff_file.added_files) +  \
           len(c.diff_file.removed_files) == 1



desc = "Help for preprocess"

try:
    work_dir = os.environ['WORK_DIR']
except Exception:
    print "Please set env. variable WORK_DIR, for example use: env WORK_DIR=. python preprocess.py"

parser = argparse.ArgumentParser(description=desc)

parser.add_argument("commits_path",
                    help="Name of the commits folder in " + work_dir)

languages = ["python", "cpp", "javascript", "java"]
parser.add_argument('--language', "-l",
                    choices = languages,
                    default=None,
                    help="Language, choose from " + ', '.join(languages),
                    metavar="")

code_extractors = ["add_rem", "per_file"]
parser.add_argument('--code_extractor', "-c",
                    default="add_rem",
                    choices = code_extractors,
                    help="Strategy to extract code lines from diffiles. Default='addrem'. Allowed values are " + ', '.join(code_extractors),
                    metavar='')


lexers = ["lines", "chunks"]
parser.add_argument('--lexer', "-lx",
                    default="lines",
                    choices = lexers,
                    help="Code lexer to use to pre-process code. Default='lines'. Allowed values are " + ', '.join(lexers),
                    metavar='')


parser.add_argument('--code_max_length', "-cml",
                    type=int,
                    default=100,
                    help="Maximum code length. Default=100")

parser.add_argument('--nl_max_length', "-nml",
                    type=int,
                    default=100,
                    help="Maximum nl length. Default=100")

parser.add_argument('--atomic', "-a",
                    action='store_true',
                    help="Atomic changes")

parser.add_argument('--only_added', "-oa",
                    action='store_true',
                    help="Chose commits only with added lines")

parser.add_argument('--only_removed', "-or",
                    action='store_true',
                    help="Choose commits only with removed lines")

parser.add_argument('--no_len_filters', "-nf",
                    action='store_true',
                    help="Atomic changes")

args = parser.parse_args()

if args.language is None:
    print "Please choose a language"
    exit()

if args.only_added and args.only_removed:
    print "Choose only_added or only_removed"
    exit()

if args.lexer == "chunks":
    lexer = CodeChunkTokenizer(language=args.language)
else:
    lexer = CodeLinesTokenizer(language=args.language)


tokenizer = TreebankTokenizer()

extract_filters = []

if args.atomic:
    extract_filters.append(is_atomic)
    marker = None
else:
    marker = "NEW_FILE"

if args.only_added:
    extract_filters.append(is_only_added)
if args.only_removed:
    extract_filters.append(is_only_removed)


if args.code_extractor == "add_rem":
    code_extractor = AddRemExtractor(marker=marker)
if args.code_extractor == "per_file":
    code_extractor = PerFileExtractor(marker=marker)


if args.no_len_filters:
    parse_filters = []
else:
    # filtered parsed commits by code len and nl len
    parse_filters = [lambda pc: 1 <= len(pc.code_tokens) <= args.code_max_length,
                     lambda pc: 1 <= len(pc.nl_tokens) <= args.nl_max_length]


ignore_list = [Comment, String, Whitespace, Text]

commits_path = os.path.join(work_dir, args.commits_path)
if not os.path.isdir(commits_path):
    print commits_path + " does not exist"
    exit()

raw_dataset = RawDataset(commits_path)

commits = extract_commits(raw_dataset, code_extractor, filters=extract_filters)
print "Extracted " + str(len(commits)) + " commits"


parsed_commits = parse_commits(commits, tokenizer, lexer,
                               filters=parse_filters,
                               ignore_types=ignore_list,
                               marker=marker)

print "Parsed " + str(len(parsed_commits)) + " commits"


from collections import Counter
words = Counter()
code_tokens = Counter()
for parsed_commit in parsed_commits:
    words.update(parsed_commit.nl_tokens)
    code_tokens.update(parsed_commit.code_tokens)

print "Average NL length = " + str(np.mean([len(pc.nl_tokens) for pc in parsed_commits]))
print "average Source Code length = " + str(np.mean([len(pc.code_tokens) for pc in parsed_commits]))

project_name = args.commits_path.split("_")[0]
pickle_file_name = project_name
if args.atomic:
    pickle_file_name += "_atomic"
if args.only_added:
    pickle_file_name += "_added"
if args.only_removed:
    pickle_file_name += "_removed"
pickle_file_name += ".pickle"

pickle_store_path = os.path.join(work_dir, "preprocessing")
if not os.path.isdir(pickle_store_path):
    os.mkdir(pickle_store_path )

with open(os.path.join(pickle_store_path, pickle_file_name), "wb") as f:
    pickle.dump(parsed_commits, f)
    print "Dumped processed commits in " + os.path.join(pickle_store_path, pickle_file_name)
