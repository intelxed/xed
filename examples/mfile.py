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

import sys
import os

def _find_dir(d):
    dir = os.getcwd()
    last = ''
    while dir != last:
        target_dir = os.path.join(dir,d)
        if os.path.exists(target_dir):
            return target_dir
        last = dir
        (dir,tail) = os.path.split(dir)
    return None

def _fatal(m):
    sys.stderr.write("\n\nXED build error: %s\n\n" % (m) )
    sys.exit(1)

def _try_mbuild_import():
    try:
        import mbuild
        return True
    except:
        return False
    
def _find_add_import(d):
    p = _find_dir(d)
    if p and os.path.exists(p):
        sys.path = [p] + sys.path
        return
    _fatal("Could not find {} directory".format(d))
    
def _find_mbuild_import():
    if _try_mbuild_import():
        return
    _find_add_import('mbuild')
    
    
def _find_common():
    p = os.path.dirname(_find_dir('xed_build_common.py'))
    if p and os.path.exists(p):
        sys.path = [p] + sys.path
        return
    _fatal("Could not find xed_build_common.py")

def setup():
    if sys.version_info[0] == 3 and sys.version_info[1] < 4:        
        _fatal("Need python version 3.4 or later.")
    elif sys.version_info[0] == 2 and sys.version_info[1] < 7:        
        _fatal("Need python version 2.7 or later.")
    _find_mbuild_import()
    # when building in the source tree the xed_build_common.py file is
    # in the parent directory of the examples. When building in the
    # kit that file is in the example source directory.
    _find_common() 

    
def work():
    import xed_build_common
    import xed_examples_mbuild
    try:
        retval = xed_examples_mbuild.execute()
    except Exception as e:
        xed_build_common.handle_exception_and_die(e)
    return retval
    
if __name__ == "__main__":
    setup()
    retval = work()
    sys.exit(retval)
 
