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
import os
import sys
import subprocess
import find_dir
try:
    import mbuild
except:
    sys.path.append(find_dir.find_dir('mbuild'))
    import mbuild

def _warn(s):
    sys.stderr.write("ERROR:" + s + "\n")
def _die(s):
    _warn(s)
    sys.exit(1)

def _run_cmd(cmd, die_on_errors=True):
    try:
        sub = subprocess.Popen(cmd, 
                               shell=True, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)
        lines = sub.stdout.readlines()
        sub.wait()
        return (sub.returncode, lines)
    except OSError as e:
        msg = "Execution failed for:" + str( cmd) + ".\nResult is " + str(e)
        if die_on_errors:
            _die(msg)
        else:
            return (1,[msg])


def _run_readelf_sections(fn,die_on_errors):
    cmd = 'readelf -S ' + fn
    (retval, output) = _run_cmd(cmd, die_on_errors)
    if retval:
        for line in output:
            line = line.strip()
            _warn(line)
        return None
    return output

def _find_key(line):
    key = None
    if line.find('.text') != -1:
        key='text'
    if line.find('.rodata') != -1:
        key='rodata'
    if line.find('.data') != -1:
        key='data'
    if line.find('.bss') != -1:
        key='bss'
    return key

def _read32(fn,die_on_errors):
    output = _run_readelf_sections(fn,die_on_errors)
    if not output:
        return None 
    key = None
    data = {}
    for line in output:
        line = line.strip()
        key = _find_key(line)
        if key:
            chunks = line.split()
            # unexpected input happens
            try:
                x = int(chunks[5],16)
            except:
                x = 0 # just don't die for now
            data[key] = x
    return data


def _read64(fn,die_on_errors):
    output = _run_readelf_sections(fn,die_on_errors)
    if not output:
        return None 
    # in 64b the size is on the next line after the key is located.
    key = None
    data = {}
    for line in output:
        line = line.strip()
        if key:
            chunks = line.split()
            # unexpected input happens
            try:
                x = int(chunks[0],16)
            except:
                x = 0 # just don't die for now
            data[key] = x
        key = _find_key(line)

    return data

def print_table(data):
    python27 = mbuild.check_python_version(2,7)
    fmt_str27 =  "{0:10s} {1:10,d} Bytes  {2:5.2f} MB {3:10.2f}%"
    fmt_str   =  "%10s %10d Bytes  %5.2f MB %10.2f%%"
    keys = list(data.keys())
    keys.sort()

    total = 0
    for k in keys:
        total = total +  data[k]

    for k in keys:
        try: # avoid div/0
            pct = 100.0 * data[k] / total
        except:
            pct = 0
        mb = data[k]/1024.0/1024.0
        if python27: 
            print(fmt_str27.format(k,data[k],mb,pct))
        else:
            print(fmt_str % (k,data[k],mb,pct))

    mb = total/1024.0/1024.0
    if python27: 
        print(fmt_str27.format('total', total, mb, 100))
    else:
        print(fmt_str % ('total', total, mb, 100))
    

def _find_mode(fn,die_on_errors):
    cmd = 'readelf -h ' + fn
    (retval, header) = _run_cmd(cmd, die_on_errors)
    mode = 0
    if retval == 0:
        for line in header:
            if 'Class:' in line:
                if 'ELF32' in line:
                    mode=32
                    break
                elif 'ELF64' in line:
                    mode=64
                    break
    return mode

def work(fn,die_on_errors=True):
    mode = _find_mode(fn,die_on_errors)
    if mode == 64:
        return _read64(fn,die_on_errors)
    elif mode == 32:
        return _read32(fn,die_on_errors)
    return None

if __name__ == '__main__':
    if len(sys.argv) != 2:
        _die("Need one arg")
    fn = sys.argv[1]
    d = work(fn)
    if d:
        print_table(d)
