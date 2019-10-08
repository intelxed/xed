#!/usr/bin/env python
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
from __future__ import print_function
import sys
import read_xed_db
import gen_setup
import chipmodel

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stderr.write("[{0}] {1}\n".format(b,s))


def check(chip, xeddb, chipdb):
    all_inst = []
    undoc = []
    for inst in xeddb.recs:
        if inst.isa_set in chipdb[chip]:
            if inst.undocumented:
                undoc.append(inst)
            else:
                all_inst.append(inst)
    return (all_inst, undoc)

def prefixes_summary(v):
    s = []
    if v.f2_required:
        s.append('f2')
    if v.f3_required:
        s.append('f3')
    if v.osz_required:
        s.append('66')
    if v.no_prefixes_allowed:
        s.append('NP')
    if len(s) == 0:
        s.append('*')
    return ",".join(s)

def wbit_summary(v):
    if v.rexw_prefix == 'unspecified':
        return '*'
    return v.rexw_prefix
def mode_summary(v):
    if v.mode_restriction == 'unspecified':
        return '*'
    if v.mode_restriction == 0:
        return '16b'
    if v.mode_restriction == 1:
        return '32b'
    if v.mode_restriction == 2:
        return '64b'
    return  v.mode_restriction
def print_header():
    print("iclass, explicit-operands, implicit-operands, memop, public/undoc, isa_set, vl, space, prefix, " +
          "map, opcode, modrm.mod, modrm.reg, modrm.rm, wbit, mode")
def print_rec(v,extra='N/A'):
    s = " ".join(['{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, ',
                  '{}, ',
                  '{}, ',
                  '{}, ',
                  '{}, ',
                  '{}'])
    print(s.format(v.iclass,
                   "-".join(v.explicit_operands),
                   "-".join(v.implicit_operands),
                   v.memop_rw,
                   extra,
                   v.isa_set,
                   v.vl if v.space in ['vex','evex'] else 'N/A',
                   v.space,
                   prefixes_summary(v),
                   v.map,
                   v.opcode,
                   '*' if v.mod_required == 'unspecified' else v.mod_required,
                   '*' if v.reg_required == 'unspecified' else v.reg_required,
                   '*' if v.rm_required == 'unspecified' else v.rm_required,
                   wbit_summary(v),
                   mode_summary(v)))



def work(args):  # main function
    msgb("READING XED DB")
    (chips, chip_db) = chipmodel.read_database(args.chip_filename)

    xeddb = gen_setup.read_db(args)
    
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
        insts.sort(key=lambda x:(x.space,x.iclass,x.isa_set,x.vl))
        undoc.sort(key=lambda x:(x.space,x.iclass,x.isa_set,x.vl))
        print_header()
        for i in insts:
            public = 'PUBLIC'
            if hasattr(i,'real_opcode') and i.real_opcode == 'N':
                public = 'PRIVATE'
            print_rec(i, public)
        for i in undoc:
            print_rec(i, "UNDOC")
    return 0


def setup():
    parser = gen_setup.create('Generate instruction counts per chip')
    
    parser.add_argument('--chip',
                        default='FUTURE',
                        help='Chip name')
    parser.add_argument('--otherchip',
                        help='Other chip name, for computing differences')

    args = gen_setup.parse(parser)
    return args

if __name__ == "__main__":
    args = setup()
    r = work(args)
    sys.exit(r)

