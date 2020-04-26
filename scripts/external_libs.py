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
import re
import os
import sys
import mbuild
import copy

def _grab_ldd_libraries(lines):
    files = []
    okay = True
    for line in lines:
        t=line.strip().split()
        pieces = len(t)
        if pieces == 0:
            continue
        if pieces == 2:
            files.append(t[-2])
        elif pieces == 4:
            if re.search('not found',line):
                print("\n\nWARNING: SKIPPING MISSING LIBRARY: [{}]\n\n".format(t[0]))
            else:
                files.append(t[-2])
        elif pieces == 3 and t[-2] == '=>':
            # missing library
            print ("\n\nWARNING: SKIPPING MISSING LIBRARY: [{}]\n\n".format(line.strip()))
        else:
            print("Unrecognized ldd line: [{}]".format(line.strip()))
            okay = False
    files = [os.path.abspath(x) for x in files]
    return (okay, files)

def _file_to_avoid(env,x):
    avoid_libraries = [ 'ld-linux', 'linux-vdso', 'linux-gate']
    if 'copy_libc' in env:
        if env['copy_libc']==False:
            avoid_libraries.append('libc')
    for av in avoid_libraries:
        if re.search(av, x):
            return True
    return False

def _add_to_ld_library_path(env,paths):
    new_pth=':'.join(paths)
    if 'LD_LIBRARY_PATH' in os.environ:
        new_pth =  new_pth + ":" + os.environ['LD_LIBRARY_PATH']
    mbuild.msgb("SET LD_LIBRARY_PATH", new_pth)
    os.environ['LD_LIBRARY_PATH'] = new_pth

def copy_system_libraries(env, kitdir, files, extra_ld_library_paths=[]):
   """copy system libraries to kit on Linux systems. Return True on success."""

   # Make a temporary environment for running ldd that includes any required
   # LD_LIBRARY_PATH additions.
   osenv = None
   if extra_ld_library_paths:
        osenv = copy.deepcopy(os.environ)
        s = None
        if 'LD_LIBRARY_PATH' in osenv:
            s = osenv['LD_LIBRARY_PATH']
        osenv['LD_LIBRARY_PATH'] = ":".join(extra_ld_library_paths)
        if s:
            osenv['LD_LIBRARY_PATH'] += ":" + s
   
   okay = True
   if env.on_linux() or env.on_freebsd() or env.on_netbsd():
      system_libraries = set()
      for binary_executable in files:
          if os.path.exists(binary_executable):
              (retval, lines, stderr) = mbuild.run_command(
                                              "ldd {}".format( binary_executable),
                                              osenv=osenv) 
              if retval != 0: # error handling
                  for line in lines:
                      line = line.rstrip()
                      print("\t{}".format(line))
                  if len(lines) >= 1:
                      if lines[0].find("not a dynamic executable") != -1:
                          continue
                      elif lines[0].find("not a dynamic ELF executable") != -1:
                          continue
                  mbuild.warn("Could not run ldd on [%s]" % binary_executable)
                  return False
              if env.on_freebsd() or env.on_netbsd():
                  lines = lines[1:]
              ldd_okay, files = _grab_ldd_libraries(lines)
              if not ldd_okay:
                  okay = False
              for lib in files:
                  if not _file_to_avoid(env,lib):
                      system_libraries.add(lib)
                      
      for slib in system_libraries:
          mbuild.msgb("TO COPY", slib)
      for slib in system_libraries:
          mbuild.copy_file(src=slib, tgt=kitdir)
   return okay
