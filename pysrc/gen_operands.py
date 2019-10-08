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
import re
import collections

import read_xed_db
import gen_setup

def work(args):  # main function
    gen_setup.msge("READING XED DB")

    xeddb = gen_setup.read_db(args)

    histo = collections.defaultdict(int)
    for r in xeddb.recs:
        if hasattr(r,'operands'):
            s = re.sub(r'[ ]+',' ',r.operands)
            if 0:
                histo[s] = histo[s] + 1
            if 1:
                for t in s.split():
                    if t.startswith('REG'):
                        t = 'REG' + t[4:]
                    if t.startswith('MEM'):
                        t = 'MEM' + t[4:]
                    histo[t] = histo[t] + 1
        


    for k,v in sorted( list(histo.items()), key=lambda t: t[1] ):
        print("{0:4d} {1}".format(v,k))
    print("TOTAL: ", len(histo))

    return 0


if __name__ == "__main__":
    args = gen_setup.setup('Generate operand lists')
    r = work(args)
    sys.exit(r)

