#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2024 Intel Corporation
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

from pathlib import Path
import sys
import os

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

# import apply_legal_header from mbuild or xed
XED_ROOT = find_dir('xed')
assert XED_ROOT, 'Couldn\'t locate XED root directory'
sys.path.append(str( os.path.join(XED_ROOT, 'scripts')))
import apply_legal_header

def get_interesting_files():
    """returns a list of staged files that should get their legal header checked/changed"""
    files = set([]) # make the list unique
    cmd = 'git diff-index --cached --name-only --diff-filter=AMRC HEAD'
    (_, output) = apply_legal_header.run_shell_command(cmd)
    for line in output:
        line = line.rstrip()
        chunks = line.split()
        if len(chunks) == 0:
            print('should not happen')
        fn = str(Path(chunks[0]).resolve(strict=True))
        files.add(fn)
    return list(files)

def stage_modified_files(files):
    """stages the files that got their legal header changed"""
    # ignore deleted files (d)
    _,out = apply_legal_header.run_shell_command("git diff-index --name-status --diff-filter=d HEAD")
    for line in out:
        fname = line.split()[1]
        rel_fname = str(Path(fname).resolve(strict=True))
        if rel_fname in files: # stage only the files that got their legal header changed
            apply_legal_header.run_shell_command(f"git add {fname}")


if __name__ == "__main__":
    modified_files = get_interesting_files()
    template_path = Path(os.getcwd(), 'misc','legal-header.txt')
    apply_legal_header.replace_headers(modified_files)
    stage_modified_files(modified_files)
    print("Checked and replaced legal headers.")

