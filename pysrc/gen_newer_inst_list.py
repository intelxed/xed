#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
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
"""
Instruction set comparison utility between two chip models.

This script generates a list of instruction differences between two chips, specifically
focusing on instructions that are present in one chip but not the other.

Usage: python gen_newer_inst_list.py --basechip <chip1> --newchip <chip2> <path_to_obj/dgen>

Example:
    python gen_newer_inst_list.py --basechip ALDER_LAKE --newchip FUTURE ../obj/dgen

Functionality:
- Reads the XED database and chip database.
- Generates a list of instructions for two specified chips (base chip and new chip).
- Compares the instruction sets of the two chips and identifies instructions that are missing in the new chip compared to the base chip, and vice versa.
- Prints the differences in instruction sets between the two chips.

Output:
- Prints instructions that are present in the base chip but missing in the new chip.
- Prints instructions that are present in the new chip but missing in the base chip.
"""
from __future__ import print_function
import sys
import read_xed_db
import gen_setup
import chipmodel


def check(chip, xeddb, chipdb):
    all_inst = []
    for inst in xeddb.recs:
        if inst.isa_set in chipdb[chip]:
            all_inst.append(inst)
    return all_inst


def chip_list(chip, xeddb, chip_db):
    insts = check(chip, xeddb, chip_db)
    return insts

def work(args):  # main function
    gen_setup.msge("READING XED DB")
    (chips, chip_db) = chipmodel.read_database(args.chip_filename)

    xeddb = gen_setup.read_db(args)

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
    parser = gen_setup.create('Generate instruction differences between two chips')
    
    parser.add_argument('--basechip', 
                        help='First chip name')
    parser.add_argument('--newchip', 
                        help='Second chip name')

    args = gen_setup.parse(parser)
    return args

if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

