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
import sys
import read_xed_db
import gen_setup

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))
def msge(b,s=''):
    sys.stderr.write("[{0}] {1}\n".format(b,s))



def work(args):  # main function
    msge("READING XED DB")

    xeddb = gen_setup.read_db(args)

    xeddb.recs.sort(key=lambda x:x.iclass)
    for r in xeddb.recs:
        for fld in sorted(r.__dict__.keys()):
            print("{}: {}".format(fld,getattr(r,fld)))
        print("EOSZ_LIST: {}".format(r.get_eosz_list()))
        print("\n\n")
    return 0

if __name__ == "__main__":
    args = gen_setup.setup("Dump all instructions and fields")
    r = work(args)
    sys.exit(r)

