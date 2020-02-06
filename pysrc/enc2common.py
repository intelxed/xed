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
from __future__ import print_function
import sys
import genutil

def die(s):
    genutil.die(s)

PY3 = sys.version_info > (3,)
def is_python3():
    global PY3
    return PY3
if is_python3() == False:
    die("This script requires python3\n")
    
dbg_output = sys.stdout
def set_dbg_output(x):
    global dbg_output
    dbg_output = x

def dbg(s):
    global dbg_output
    print(s, file=dbg_output)

def msge(s):
    print(s, file=sys.stderr, flush=True)
def warn(s):
    print("\t"+s, file=sys.stderr, flush=True)
    #genutil.warn(s)
    
def dump_fields(x):
    for fld in sorted(x.__dict__.keys()):
        msge("{}: {}".format(fld,getattr(x,fld)))
    msge("\n\n")
