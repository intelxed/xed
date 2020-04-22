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

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))



def work(args):  # main function
    msgb("READING XED DB")

    xeddb = gen_setup.read_db(args)
    chips, chipdb = gen_setup.read_chips(args)
    
    xeddb.recs.sort(key=lambda x:x.iclass)
    for chip in chips:
        cpuids = set()
        for r in xeddb.recs:
            if r.isa_set in chipdb[chip]:
                for cpuid in r.cpuid:
                    if cpuid != 'N/A':
                        cpuids.add(cpuid)
        print("CHIP {}".format(chip))
        print("\t{}".format(" ".join(cpuids)))
    return 0


if __name__ == "__main__":
    args = gen_setup.setup('Generate cpuid info')
    r = work(args)
    sys.exit(r)

