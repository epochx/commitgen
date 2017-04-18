#!/usr/bin/python
# -*- coding: utf-8 -*-

import Levenshtein
import argparse


def read_file(filepath):
    with open(filepath, "r") as f:
         lines = f.readlines()
    r = {}
    for line in lines:
        a, b = line.strip().split("\t")
        r[a] = b
    return r


parser = argparse.ArgumentParser(description="")

parser.add_argument('gen',
                    help="Generated file")

parser.add_argument('ref',
                    help="Reference file")

parser.add_argument('--limit', "-l",
                    type=int,
                    default=50,
                    help="Limit")

args = parser.parse_args()


gen = read_file(args.gen)
ref = read_file(args.ref)

sims = []
for idx, gen_nl in gen.items():
    try:
        ref_nl = ref[idx]
        sims.append((idx,Levenshtein.ratio(gen_nl, ref_nl)))
    except KeyError:
        pass

sims = sorted(sims, key=lambda x: x[1], reverse=True)


for idx, sim in sims[:args.limit]:
    print "REF:\t" + ref[idx]
    print "GEN:\t" + gen[idx]
    print "SIM:\t" + str(sim)
    print '======================='
    

