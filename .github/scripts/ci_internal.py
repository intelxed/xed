# BEGIN_LEGAL
#
# Copyright (c) 2021 Intel Corporation
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
import subprocess
import sys
from datetime import datetime
from typing import Dict

sys.path = ['scripts'] + sys.path


class JobStatus:
    """record job status (success, failure and (retval,job) list"""

    def __init__(self):
        self.jobs = 0
        self.fails = 0
        self.successes = 0
        self.start_time = datetime.now()
        self.commands = []  # list of  tuples of (retval, command)

    def __str__(self):
        s = [f"JOBS: {self.jobs}, SUCCESSES: {self.successes}, FAILS: {self.fails}"]

        for index, (r, c) in enumerate(self.commands):
            s.append(f"{index}: status: {r} cmd: {c}")
        return os.linesep.join(s) + os.linesep

    def addjob(self, retval, cmd):
        self.jobs += 1
        self.commands.append((retval, cmd))

    def fail(self, retval, cmd):
        self.fails += 1
        self.addjob(retval, cmd)

    def success(self, retval, cmd):
        self.successes += 1
        self.addjob(retval, cmd)

    def merge(self, status):
        """merge status object"""
        self.jobs += status.jobs
        self.fails += status.fails
        self.successes += status.successes
        self.commands.extend(status.commands)

    def pass_rate_fraction(self):
        return f'{self.successes}/{self.jobs}'


def success(status):
    '''send success SMS'''
    sys.stdout.write(str(status))
    sys.stdout.write(f'[ELAPSED TIME] {datetime.now() - status.start_time}\n')
    sys.stdout.write("[FINAL STATUS] PASS\n")
    sys.stdout.flush()
    # send_sms.send("XED CI: Passed ({} passing)".format(
    #    status.pass_rate_fraction()))
    sys.exit(0)


def fail(status):
    '''send failing SMS'''
    sys.stdout.write(str(status))
    sys.stdout.write(f'[ELAPSED TIME] {datetime.now() - status.start_time}\n')
    sys.stdout.write("[FINAL STATUS] FAIL\n")
    sys.stdout.flush()
    # send_sms.send("XED CI: Failed ({} passing)".format(
    #    status.pass_rate_fraction()))
    sys.exit(1)


def ensure_string(x):
    '''handle non unicode output'''
    if isinstance(x, bytes):
        return x.decode('utf-8')
    return x


def run_subprocess(cmd, **kwargs):
    '''front end to running subprocess'''
    sub = subprocess.Popen(cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           **kwargs)
    lines = sub.stdout.readlines()
    lines = [ensure_string(x) for x in lines]
    sub.wait()
    return sub.returncode, lines


def run(status:JobStatus, cmd, required=False, cwd=None):
    """run subprocess, and record fails"""
    print(cmd, flush=True)
    retval, output = run_subprocess(cmd, cwd=cwd)
    for line in output:
        sys.stdout.write(line)
    if retval == 0:
        print("[SUCCESS]")
        status.success(retval, cmd)
    else:
        print(f"[FAIL] retval = {retval}")
        status.fail(retval, cmd)
        if required:
            fail(status)
    return retval == 0  # 1=ok!


def get_python_cmds():
    '''find python verions. return tuples of (name, command)'''
    if platform.system() == 'Windows':
        for x in ['37']:
            p_path = f'C:/python{x}/python'
            if os.path.exists(p_path):
                return [(x, p_path)]
    if platform.system() in ['Darwin', 'Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [('3.x', 'python3')]
    return [('dfltpython', 'python')]


def all_instr(pyver, pycmd, status, kind):
    size = 'x86-64'
    linkkind = 'static'
    build_dir = f'obj-{kind}-{pyver}-{size}-{linkkind}'
    cwd = os.path.abspath(os.curdir)
    flags = f'--kind {kind} --enc2-test-checked'
    cmd = f'{pycmd} xedext/xed_build.py --xed-dir {cwd} {flags}  --build-dir={build_dir} host_cpu={size}'
    ok = run(status, cmd)

    if ok:
        cmd = f'{build_dir}/enc2-m64-a64/enc2tester-enc2-m64-a64 --reps 1 --main --gnuasm > a.c'
        ok = run(status, cmd)

        if 1:  # FIXME: ignore error code for now.
            cmd = 'gcc a.c'
            run(status, cmd)

            if ok:
                cmd = f'{build_dir}/wkit/bin/xed -i a.out > all.dis'
                run(status, cmd)


def archval(pyver, pycmd, status):
    size = 'x86-64'
    linkkind = 'static'
    build_dir = f'obj-archval-{pyver}-{size}-{linkkind}'
    cwd = os.path.abspath(os.curdir)
    flags = f"--kind architectural-val {os.getenv('ARCHVAL_OPTIONS')}"
    cmd = f'{pycmd} xedext/xed_build.py --xed-dir {cwd} {flags} --build-dir={build_dir} host_cpu={size}'
    run(status, cmd)


def get_branches_from_file() -> Dict[str, str]:
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
    for repo, branch in branches.items():
        print(f"CHANGING REPO: {repo}  TO BRANCH: {branch}")
        run(status, f"git checkout {branch}", cwd=repo)


def main():
    status = JobStatus()

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
    if 'CI' not in os.environ:
        git_base = 'https://gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devtools.intel.com/xed-group/'

        mbuild_git = git_base + 'mbuild.git'
        cmd = f'git clone {mbuild_git} mbuild'
        run(status, cmd, required=True)

        branches = get_branches_from_file()
        checkout_branches(status, branches)

    archval_repo = os.getenv('ARCHVAL_REPO')
    if archval_repo:
        archval_git = git_base + archval_repo
        short_name = os.path.splitext(archval_repo)[0]
        cmd = f'git clone {archval_git} {short_name}'
        run(status, cmd, required=True)

    for pyver, pycmd in get_python_cmds():

        cmd = f'{pycmd} -m pip install --user ./mbuild'
        run(status, cmd, required=True)

        # {32b,64b} x {shared,dynamic} link
        for size in ['ia32', 'x86-64']:
            for linkkind, link in [('static', ''), ('dynamic', '--shared')]:
                build_dir = f'obj-general-{pyver}-{size}-{linkkind}'
                cmd = f'{pycmd} mfile.py --build-dir={build_dir} host_cpu={size} {link} test'
                run(status, cmd)

        # do a build with asserts enabled
        build_dir = f'obj-assert-{pyver}-{"x86-64"}'
        cmd = f'{pycmd} mfile.py --asserts --build-dir={build_dir} host_cpu={"x86-64"} test'
        run(status, cmd)

        # all instr tests
        all_instr(pyver, pycmd, status, 'internal-conf')
        all_instr(pyver, pycmd, status, 'external')

        # arch val test
        archval(pyver, pycmd, status)

        # knc test
        if 0:
            size = 'x86-64'
            linkkind = 'static'
            build_dir = f'obj-knc-{pyver}-{size}-{linkkind}'
            cmd = f'{pycmd} mfile.py --knc --build-dir={build_dir} host_cpu={size} test'
            run(status, cmd)

        if status.fails == 0:
            success(status)
        fail(status)


def test():
    status = JobStatus()
    status.success(1, 'foo')
    status.success(1, 'bar')
    fail(status)


if __name__ == "__main__":
    # test()
    main()
    sys.exit(0)
