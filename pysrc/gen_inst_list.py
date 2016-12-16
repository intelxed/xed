#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2016 Intel Corporation
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
                                     args.instructions_filename)

    
    (insts,undoc) = check(args.chip, xeddb, chip_db)
    ilist = list(set(map(lambda x: x.iclass, insts)))
    ilist.sort()
    ulist = list(set(map(lambda x: x.iclass, undoc)))
    ulist.sort()
    for i in ilist:
        print i
    for i in ulist:
        print i, "UNDOC"
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
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

