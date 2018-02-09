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
    undoc = []
    for inst in xeddb.recs:
        if inst.isa_set in chipdb[chip]:
            if inst.undocumented:
                undoc.append(inst)
            else:
                all.append(inst)
    return (all, undoc)



def work(args):  # main function
    msgb("READING XED DB")
    (chips, chip_db) = chipmodel.read_database(args.chip_filename)

    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename)

    
    (insts,undoc) = check(args.chip, xeddb, chip_db)
    ilist = list(set( [ x.iclass for x in insts ] ))
    ilist.sort()
    ulist = list(set( [x.iclass for x in  undoc] ))
    ulist.sort()
    if args.otherchip:
        (insts2,undoc2) = check(args.otherchip, xeddb, chip_db)
        ilist2 = list(set( [ x.iclass for x in insts2] ))
        ulist2 = list(set( [ x.iclass for x in  undoc2] ))
        s1 = set(ilist + ulist)
        s2 = set(ilist2 + ulist2)
        d12 = list(s1-s2)
        d21 = list(s2-s1)
        d12.sort()
        d21.sort()
        both = list(s1&s2)
        both.sort()

        for i in d12:
            print("{:20s} IN: {}   NOT IN: {}".format(i, args.chip, args.otherchip))
        for i in d21:
            print("{:20s} IN: {}   NOT IN: {}".format(i, args.otherchip, args.chip))
        for i in both:
            print("{:20s} BOTH IN: {}   IN: {}".format(i, args.chip, args.otherchip))
        
    else:
        for i in ilist:
            print(i)
        for i in ulist:
            print(i, "UNDOC")
    return 0


def setup():
    parser = argparse.ArgumentParser(
        description='Generate instruction counts per chip')
    parser.add_argument('chip', 
                        help='Chip name')
    parser.add_argument('state_bits_filename', 
                        help='Input state bits file')
    parser.add_argument('instructions_filename', 
                        help='Input instructions file')
    parser.add_argument('chip_filename', 
                        help='Input chip file')
    parser.add_argument('widths_filename', 
                        help='Input chip file')
    parser.add_argument('element_types_filename', 
                        help='Input chip file')
    parser.add_argument('--otherchip',
                        help='Other chip name, for computing differences')

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

