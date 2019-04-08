#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2019 Intel Corporation
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

# for each instruction, dump all the fields provided by the reader.

from __future__ import print_function
import os
import sys
import argparse
import re
import collections

import read_xed_db

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))



def work(args):  # main function
    msgb("READING XED DB")


    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename,
                                     args.cpuid_filename)

    xeddb.recs.sort(key=lambda x:x.iclass)
    for r in xeddb.recs:
        for fld in sorted(r.__dict__.keys()):
            print("{}: {}".format(fld,getattr(r,fld)))
        print("\n\n")


    return 0

def setup():
    parser = argparse.ArgumentParser(
        description='Dump instruction fields')
    parser.add_argument('prefix', 
                        help='Path to obj/dgen directory')
    args = parser.parse_args()

    args.state_bits_filename    = args.prefix + '/all-state.txt'
    args.cpuid_filename         = args.prefix + '/all-cpuid.txt'
    args.instructions_filename  = args.prefix + '/all-dec-instructions.txt'
    args.chip_filename          = args.prefix + '/all-chip-models.txt'
    args.widths_filename        = args.prefix + '/all-widths.txt'
    args.element_types_filename = args.prefix + '/all-element-types.txt'
    return args


if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

