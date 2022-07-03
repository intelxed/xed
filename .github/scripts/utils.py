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

import platform
import subprocess
from job_status import *


def ensure_string(x):
    """handle non unicode output"""
    if isinstance(x, bytes):
        try:
            return x.decode('utf-8')
        except:
            return ''
    return x


def run_subprocess(cmd, **kwargs):
    """front end to running subprocess"""
    sub = subprocess.Popen(cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           **kwargs)
    lines = sub.stdout.readlines()
    lines = [ensure_string(x) for x in lines]
    sub.wait()
    return sub.returncode, lines


def get_python_cmds():
    """find python verions. return tuples of (name, command)"""
    if platform.system() == 'Windows':
        for x in ['37']:
            p_path = f'C:/python{x}/python'
            if os.path.exists(p_path):
                return [(x, p_path)]
    if platform.system() in ['Darwin', 'Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [('3.x', 'python3')]
    return [('dfltpython', 'python')]


def run(status: JobStatus, cmd, required=False, cwd=None):
    """run a command in subprocess and return status and stdout"""
    sys.stdout.write(f'{cmd}\n')
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
            status.report_and_exit()
    return retval == 0
