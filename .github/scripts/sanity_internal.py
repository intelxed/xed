# BEGIN_LEGAL
#
# Copyright (c) 2022 Intel Corporation
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
# END_LEGAL
""" run CI checks """
import os
import platform
import sys
from typing import Dict
import utils


def all_instr(pyver, pycmd, status, kind):
    """Generate build command that tests decode-encode path of all the kind's available instructions"""
    size = 'x86-64'
    linkkind = 'static'
    build_dir = f'obj-{kind}-{pyver}-{size}-{linkkind}'
    flags = f'--kind {kind} --enc2-test-checked'
    cmd = f'{pycmd} ../xedext/xed_build.py {flags}  --build-dir={build_dir} host_cpu={size}'
    ok = utils.run(status, cmd)

    if ok:
        cmd = f'{build_dir}/enc2-m64-a64/enc2tester-enc2-m64-a64 --reps 1 --main --gnuasm > a.c'
        ok = utils.run(status, cmd)

        if 1:  # FIXME: ignore error code for now.
            cmd = 'gcc a.c'
            utils.run(status, cmd)

            if ok:
                cmd = f'{build_dir}/wkit/bin/xed -i a.out > all.dis'
                utils.run(status, cmd)


def archval(pyver, pycmd, status):
    """Build and test the architectural-val kind"""
    size = 'x86-64'
    linkkind = 'static'
    build_dir = f'obj-archval-{pyver}-{size}-{linkkind}'
    flags = f"--kind architectural-val {os.getenv('ARCHVAL_OPTIONS')}"
    cmd = f'{pycmd} ../xedext/xed_build.py {flags} --build-dir={build_dir} host_cpu={size}'
    utils.run(status, cmd)


def get_branches_from_file() -> Dict[str, str]:
    """retrieves the branches from a specific file and returns a mapping from repository to respective branch"""
    f = open("../../misc/ci-branches.txt", "r")
    lines = f.readlines()
    f.close()
    d = {}
    for x in lines:
        x = x.strip()
        a = x.split()
        repo = a[0]
        branch = a[1]
        print(f"READING REPO: {repo}  TO BRANCH: {branch}")
        d[repo] = branch
    return d


def checkout_branches(status, branches):
    """checkout to given branches in respective repositories"""
    for repo, branch in branches.items():
        print(f"CHANGING REPO: {repo}  TO BRANCH: {branch}")
        utils.run(status, f"git checkout {branch}", cwd=repo)


def main():
    status = utils.JobStatus()

    # IPLDT scan XED and MBUILD
    if 0:  # disabled until get  right branch
        # obtain IPLDT scanner tool
        bintools_git = git_base + 'binary-tools.git'
        cmd = f'git clone --depth 1 {bintools_git} binary-tools'
        run(status, cmd, required=True)

        # clone another copy of xed sources just for IPLDT scanning
        # FIXME: need to get the branch we are testing!
        xed_git = git_base + 'xed.git'
        cmd = f'git clone --depth 1 {xed_git} xed'
        run(status, cmd, required=True)

        cmd = 'binary-tools/lin/ipldt3 -i xed -r ipldt-results-xed'
        run(status, cmd, required=False)
        cmd = 'cat ipldt-results-xed/ipldt_results.txt'
        run(status, cmd, required=True)

        cmd = 'binary-tools/lin/ipldt3 -i mbuild -r ipldt-results-mbuild'
        run(status, cmd, required=False)
        cmd = 'cat ipldt-results-mbuild/ipldt_resuplts.txt'
        run(status, cmd, required=True)

    for pyver, pycmd in utils.get_python_cmds():
        
        python_pip = 'python3'
        if platform.system() in ['Darwin', 'Linux']:
            # use python version with pip (No in system PATH)
            python_pip = f'/opt/python3/37/bin/{python_pip}'
        cmd = f'{python_pip} -m pip install --user ../mbuild'
        utils.run(status, cmd)

        # {32b,64b} x {shared,dynamic} link
        for size in ['ia32', 'x86-64']:
            for linkkind, link in [('static', ''), ('dynamic', '--shared')]:
                build_dir = f'obj-general-{pyver}-{size}-{linkkind}'
                cmd = f'{pycmd} mfile.py --build-dir={build_dir} host_cpu={size} {link} test'
                utils.run(status, cmd)

        # do a build with asserts enabled
        build_dir = f'obj-assert-{pyver}-x86-64'
        cmd = f'{pycmd} mfile.py --asserts --build-dir={build_dir} host_cpu=x86-64 test'
        utils.run(status, cmd)

        # all instr tests
        all_instr(pyver, pycmd, status, 'internal-conf')
        all_instr(pyver, pycmd, status, 'external')

        # arch val test
        archval(pyver, pycmd, status)

        # knc test
        size = 'x86-64'
        linkkind = 'static'
        build_dir = f'obj-knc-{pyver}-{size}-{linkkind}'
        cmd = f'{pycmd} mfile.py --knc --build-dir={build_dir} host_cpu={size} test'
        utils.run(status, cmd)

        status.report_and_exit()


if __name__ == "__main__":
    main()
    sys.exit(0)
