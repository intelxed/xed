#BEGIN_LEGAL
#
#Copyright (c) 2020 Intel Corporation
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
'''run CI checks on gitlab'''
import os
import sys
import platform
import subprocess
sys.path = ['scripts'] + sys.path
import send_sms

def success():
    '''send success SMS'''
    sys.stdout.write("FINAL STATUS: Success\n")
    #send_sms.send("Success", recipients=['mjc'])
    sys.exit(0)

def fail(s):
    '''send failing SMS'''
    sys.stderr.write('FINAL STATUS: {}\n'.format(s))
    #send_sms.send(s, recipients=['mjc'])
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

errors = 0

def run(cmd, required=False):
    '''run subprocess, and record errors'''
    global errors
    #subprocess.check_call(cmd, shell=True)
    status, output = run_subprocess(cmd)
    for line in output:
        sys.stdout.write(line)
    if status != 0:
        if required:
            fail("Required task failed")
        errors += 1

def get_python_cmds():
    '''find python verions. return tuples of (name, command)'''
    if platform.system() == 'Windows':
        return [(x, 'C:/python{}/python'.format(x)) for x in ['37']]
    if platform.system() in ['Darwin', 'Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [('3.x', 'python3')]
    return [('dfltpython', 'python')]

for pyver, pycmd in get_python_cmds():
    mbuild_git = 'https://gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devtools.intel.com/xed-group/mbuild.git'
    cmd = 'git clone {} mbuild'.format(mbuild_git)
    print(cmd)
    run(cmd, required=True)

    xedext_git = 'https://gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devtools.intel.com/xed-group/xedext.git'
    cmd = 'git clone {} xedext'.format(xedext_git)
    print(cmd)
    run(cmd, required=True)

    cmd = '{} -m pip install --user ./mbuild'.format(pycmd)
    print(cmd)
    run(cmd, required=True)

    # {32b,64b} x {shared,dynamic} link
    for size in ['ia32', 'x86-64']:
        for linkkind, link in [('dfltlink', ''), ('dynamic', '--shared')]:
            build_dir = 'obj-general-{}-{}-{}'.format(pyver, size, linkkind)
            cmd = '{} mfile.py --build-dir={} host_cpu={} {} test'.format(pycmd,
                                                                          build_dir,
                                                                          size,
                                                                          link)
            print(cmd)
            run(cmd)


    size = 'x86-64'
    linkkind = 'dfltlink'
    build_dir = 'obj-conf-{}-{}-{}'.format(pyver, size, linkkind)
    cwd = os.path.abspath(os.curdir)
    cmd = '{} xedext/xed_build.py --xed-dir {} --kind internal-conf --build-dir={} host_cpu={} {} test'.format(
        pycmd, cwd, build_dir, size, link)
    print(cmd)
    run(cmd)

    # FIXME: add other required knobs
    size = 'x86-64'
    linkkind = 'dfltlink'
    build_dir = 'obj-archval-{}-{}-{}'.format(pyver, size, linkkind)
    cwd = os.path.abspath(os.curdir)
    cmd = '{} xedext/xed_build.py --xed-dir {} --kind architectural-val --build-dir=build-{} host_cpu={} {} test'.format(
        pycmd, cwd, build_dir, size, link)
    print(cmd)
    run(cmd)

    if 0:
        size = 'x86-64'
        linkkind = 'dfltlink'
        build_dir = 'obj-knc-{}-{}-{}'.format(pyver, size, linkkind)
        cmd = '{} mfile.py --knc --build-dir={} host_cpu={} {} test'.format(pycmd, build_dir, size, link)
        print(cmd)
        run(cmd)

    if errors == 0:
        success()
    fail("There were {} errors".format(errors))
