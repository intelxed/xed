#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2023 Intel Corporation
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
from typing import Set
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
    for r in xeddb.recs:
        if not r.cpuid_groups:
            continue
        cpuids: Set[str] = set()
        for grp in r.cpuid_groups:
            cpuids.update([str(rec) for rec in grp.get_records()])
        if r.space in ['vex','evex']:
            print("{}: {}/{}: {}".format(r.iclass, r.space, r.vl, ", ".join(cpuids)))
        else:
            print("{}: {}: {}".format(r.iclass, r.space, ", ".join(cpuids)))


if __name__ == "__main__":
    args = gen_setup.setup('Generate cpuid info')
    work(args)
    sys.exit(0)

