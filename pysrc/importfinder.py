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

# Returns a list of imported modules but it is unacceptably slow.  For
# the execution of "pysrc/importfinder.py generator pysrc" it takes 23
# seconds.
from __future__ import print_function
import os
import sys
import modulefinder

def _get_modules(fn):
    finder = modulefinder.ModuleFinder()
    finder.run_script(fn)
    all = []
    for m in finder.modules.values():
        if not isinstance(m, modulefinder.Module):
            continue
        if not m.__file__:
            continue
        # skip shared object files
        if m.__file__.endswith('.so'):
            continue
        # skip mac system stuff...
        # FIXME: would need to augment with  other OS's system stuff
        if m.__file__.startswith('/Library/Frameworks'):
            continue
        all.append(m)
    return all

def find(root_module):
    worklist = []  
    d = {} # remember what we've seen
    all = [] # output: list of path-prefixed modules

    mods =  _get_modules(root_module)
    worklist.extend(mods)
    while worklist:
        x = worklist.pop(0)
        for m in _get_modules(x.__file__):
            if m.__name__ not in d:
                worklist.append(m)
                all.append(m.__file__)
                d[m.__name__]=True
    all.sort()
    return all


if __name__ == "__main__":
    sys.path =  [sys.argv[2]] + sys.path
    print(find(os.path.join(sys.argv[2],sys.argv[1]+'.py')))
