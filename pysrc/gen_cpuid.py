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
CPUID feature list generator.

This utility script generates a list of CPUID features for each instruction
from the XED database. Shows which CPUID feature bits are required to execute
each instruction, organized by instruction class, encoding space, and vector length.

Usage: python gen_cpuid.py <path_to_obj/dgen>
Example: python gen_cpuid.py ../obj/dgen
"""
from __future__ import print_function

from collections import defaultdict
import sys
import gen_setup

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))



def work(args):  # main function
    msgb("READING XED DB")

    xeddb = gen_setup.read_db(args)

    xeddb.recs.sort(key=lambda x:x.iclass)
    records = defaultdict(list)
    for r in xeddb.recs:
        if not r.cpuid_groups:
            continue
        cpuid_str = ""
        for grp in r.cpuid_groups:
            cpuid_str += repr(grp) + " "
        rec_key = (r.iclass, r.space, r.vl)
        if rec_key in records and cpuid_str in records[rec_key]:
            continue
        records[rec_key].append(cpuid_str)
        # print
        if r.space in ['vex','evex']:
            print("{}: {}/{}: {}".format(r.iclass, r.space, r.vl, cpuid_str))
        else:
            print("{}: {}: {}".format(r.iclass, r.space, cpuid_str))


if __name__ == "__main__":
    args = gen_setup.setup('Generate cpuid info')
    work(args)
    sys.exit(0)

