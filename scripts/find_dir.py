#! /usr/bin/env python 
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
import os
import sys

def find_dir(d,required=True):
    idir = os.getcwd()    
    last_idir = ''    
    while idir != last_idir:
        mfile = os.path.join(idir,d)
        if os.path.exists(mfile):
            break
        last_idir = idir
        idir = os.path.dirname(idir)
    if not os.path.exists(mfile):
        if required:
            print("Could not find {} file, looking upwards".format(mfile))
            sys.exit(1)
        return None
    return mfile
