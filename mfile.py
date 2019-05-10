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


import sys
import os

# Assume mbuild is next to the current source directory
# put mbuild on the import path
# from "path-to-xed/xed2/mfile.py" obtain: "path-to-xed/xed2".

def find_dir(d):
    dir = os.getcwd()
    last = ''
    while dir != last:
        target_dir = os.path.join(dir,d)
        if os.path.exists(target_dir):
            return target_dir
        last = dir
        (dir,tail) = os.path.split(dir)
    return None

def fatal(m):
    sys.stderr.write("\n\nXED build error: %s\n\n" % (m) )
    sys.exit(1)

def try_mbuild_import():
    try:
        import mbuild
        return True
    except:
        return False
    
def find_mbuild_import():
    if try_mbuild_import():
        # mbuild is already findable by PYTHONPATH. Nothing required from
        # this function.
        return

    script_name = sys.argv[0]
    mbuild_install_path_derived = \
                   os.path.join(os.path.dirname(script_name), '..', 'mbuild')

    mbuild_install_path_relative = find_dir('mbuild')
    mbuild_install_path = mbuild_install_path_derived
    if not os.path.exists(mbuild_install_path):
        if not mbuild_install_path_relative:
            # If find_dir() fails, it returns None. That messes
            # up os.path.exists() so we fix it with ''
            mbuild_install_path_relative=''
        mbuild_install_path = mbuild_install_path_relative
        if not os.path.exists(mbuild_install_path):
            s = "mfile.py cannot find the mbuild directory: [%s] or [%s]"
            fatal(s % (mbuild_install_path_derived, 
                       mbuild_install_path_relative))

    # modify the environment python path so that the imported modules
    # (enumer,codegen) can find mbuild.
    
    if 'PYTHONPATH' in os.environ:
        sep = ':'
        os.environ['PYTHONPATH'] =  mbuild_install_path + sep +  \
                                    os.environ['PYTHONPATH']
    else:
        os.environ['PYTHONPATH'] =  mbuild_install_path 

    sys.path.insert(0,mbuild_install_path)
    
def work():
    if sys.version_info[0] == 3:
        if sys.version_info[1] < 4:        
            fatal("Need python version 3.4 or later.")
    else:
        fatal("Need python version 3.4 or later.")
        
    try:
        find_mbuild_import()
    except:
        fatal("mbuild import failed")
    import xed_mbuild
    import xed_build_common
    if 0:
        retval = xed_mbuild.execute()
    else:
        try:
            retval = xed_mbuild.execute()
        except Exception as e:
            xed_build_common.handle_exception_and_die(e)
    return retval
    
if __name__ == "__main__":
    retval = work()
    sys.exit(retval)
 
