#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#Copyright (c) 2004-2015, Intel Corporation. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
    if sys.version_info[0] >= 3:
        _fatal("Python version 3.x not supported.")
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:        
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
 
