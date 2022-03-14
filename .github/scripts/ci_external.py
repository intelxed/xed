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
    sys.stdout.write(str(status))
    sys.stdout.write(f'[ELAPSED TIME] {datetime.now() - status.start_time}\n')
    sys.stdout.write("[FINAL STATUS] PASS\n")
    sys.stdout.flush()
    sys.exit(0)


def fail(status):
    sys.stdout.write(str(status))
    sys.stdout.write(f'[ELAPSED TIME] {datetime.now() - status.start_time}\n')
    sys.stdout.write("[FINAL STATUS] FAIL\n")
    sys.stdout.flush()
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


def main():
    status = JobStatus()

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

        if status.fails == 0:
            success(status)
        fail(status)


if __name__ == "__main__":
    main()
    sys.exit(0)
