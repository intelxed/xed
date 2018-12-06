#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2018 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL
from __future__ import print_function
import os
import sys
import argparse
import re
import collections

import read_xed_db
import chipmodel

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))


def check(chip, xeddb, chipdb):
    all = []
    for inst in xeddb.recs:
        if inst.isa_set in chipdb[chip]:
            all.append(inst)
    return all


def chip_list(chip, xeddb, chip_db):
    insts = check(chip, xeddb, chip_db)
    return insts

def work(args):  # main function
    msgb("READING XED DB")
    (chips, chip_db) = chipmodel.read_database(args.chip_filename)

    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename)

    # base chip instr
    bi = chip_list(args.basechip, xeddb, chip_db)
    # newer chip instr
    ni = chip_list(args.newchip, xeddb, chip_db)
    
    missing_new = []
    for b in bi:
        found = False
        for n in ni:
            if b.iclass == n.iclass:
                found = True
                break
        if not found:
            missing_new.append(b)

    missing_old = []
    for n in ni:
        found = False
        for b in bi:
            if n.iclass == b.iclass:
                found = True
                break
        if not found:
            missing_old.append(n)
            
    missing_old.sort(key=lambda x: x.iclass)
    missing_new.sort(key=lambda x: x.iclass)
    
    for i in missing_old:
        print("+{}   {}    {} {}".format(i.iclass, i.isa_set, i.space, i.vl))
    for i in missing_new:
        print("-{}   {}    {} {}".format(i.iclass, i.isa_set, i.space, i.vl))
    return 0


def setup():
    parser = argparse.ArgumentParser(
        description='Generate instruction differences between two chips')
    parser.add_argument('basechip', 
                        help='First chip name')
    parser.add_argument('newchip', 
                        help='Second chip name')
    parser.add_argument('state_bits_filename', 
                        help='Input state bits file')
    parser.add_argument('instructions_filename', 
                        help='Input instructions file')
    parser.add_argument('chip_filename', 
                        help='Input chip file')
    parser.add_argument('widths_filename', 
                        help='Input widths file')
    parser.add_argument('element_types_filename', 
                        help='Input element type file ')

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

