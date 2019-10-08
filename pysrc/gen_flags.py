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
    sys.stderr.write("[{0}] {1}\n".format(b,s))
def msg(b):
    sys.stdout.write("{0}\n".format(b))



def work(args):  # main function
    msgb("READING XED DB")

    xeddb = gen_setup.read_db(args)

    d = {}
    for r in xeddb.recs:
        if hasattr(r,'flags'):
            if hasattr(r,'isa_set'):
                isa_set = r.isa_set
            else:
                isa_set = r.extension
                
            s= "{:<20} {:<20} {}".format(r.iclass, isa_set, r.flags)
            d[s]=True
    k = d.keys()
    k.sort()
    for a in k:
        msg(a)
    
    return 0



if __name__ == "__main__":
    args = gen_setup.setup('Generate EFLAGS report')
    r = work(args)
    sys.exit(r)

