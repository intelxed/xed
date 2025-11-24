#!/usr/bin/env python3
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

try:
    import mbuild 
except:
    # mbuild is not in the path, so try to add it
    mbuild_path = _find_dir('mbuild')
    if mbuild_path:
        sys.path.append(str(mbuild_path))
        import mbuild
    else:
        # mbuild is not in the path and we could not find it
        sys.stderr.write("\n\nXED build error: Could not find mbuild directory\n\n")
        sys.exit(1)

def _fatal(m):
    sys.stderr.write("\n\nXED build error: %s\n\n" % (m) )
    sys.exit(1)
    
def _find_common():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_path = os.path.join(script_dir, 'xed_build_common.py')
    if os.path.exists(common_path):
        sys.path = [script_dir] + sys.path
        return
    
    common_dir = _find_dir('xed_build_common.py')
    if common_dir:
        p = os.path.dirname(common_dir)
        if p and os.path.exists(p):
            sys.path = [p] + sys.path
            return
        
    _fatal("Could not find xed_build_common.py")


def setup():
    mbuild.check_python_version(3,9)
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
 
