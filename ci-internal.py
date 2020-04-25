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

class jobs_status_t:
    '''record job status (success, failure and (retval,job) list'''
    def __init__(self):
        self.jobs = 0
        self.fails = 0
        self.successes = 0
        self.commands = [] # list of  tuples of (retval, command)
        
    def __str__(self):
        s = []
        s.append("JOBS: {}, SUCCESSES: {}, FAILS: {}".format(
            self.jobs, self.successes, self.fails))
        i = 0
        for r, c in self.commands:
            s.append("{}: status: {} cmd: {}".format(i, r, c))
            i = i+1
        return "\n".join(s) + '\n'
    
    def addjob(self, retval, cmd):
        self.jobs += 1
        self.commands.append((retval, cmd))
        
    def fail(self, retval, cmd):
        self.fails += 1
        self.addjob(retval, cmd)
        
    def success(self, retval, cmd):
        self.successes += 1
        self.addjob(retval, cmd)



def success(status):
    '''send success SMS'''
    sys.stdout.write("FINAL STATUS: PASS\n")
    sys.stdout.write(str(status))
    sys.stdout.flush()
    #send_sms.send("Success", recipients=['mjc'])
    sys.exit(0)

def fail(status):
    '''send failing SMS'''
    sys.stdout.write("FINAL STATUS: FAIL\n")
    sys.stdout.write(str(status))
    sys.stdout.flush()
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


def run(status, cmd, required=False):
    '''run subprocess, and record fails'''
    print(cmd)
    retval, output = run_subprocess(cmd)
    for line in output:
        sys.stdout.write(line)
    if retval == 0:
        print("[SUCCESS]")
        status.success(retval, cmd)
    else:
        print("[FAIL] retval = {}".format(retval))
        status.fail(retval, cmd)
        if required:
            fail("Required task failed")
    return retval == 0 # 1=ok!

def get_python_cmds():
    '''find python verions. return tuples of (name, command)'''
    if platform.system() == 'Windows':
        return [(x, 'C:/python{}/python'.format(x)) for x in ['37']]
    if platform.system() in ['Darwin', 'Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [('3.x', 'python3')]
    return [('dfltpython', 'python')]

def main():
    status = jobs_status_t()
    # FIXME: add knob for local use
    # git_base = 'ssh://git@gitlab.devtools.intel.com/xed-group/'
    git_base = 'https://gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devtools.intel.com/xed-group/'
    for pyver, pycmd in get_python_cmds():
        mbuild_git = git_base + 'mbuild.git'
        cmd = 'git clone {} mbuild'.format(mbuild_git)
        run(status, cmd, required=True)

        xedext_git = git_base + 'xedext.git'
        cmd = 'git clone {} xedext'.format(xedext_git)
        run(status, cmd, required=True)

        cmd = '{} -m pip install --user ./mbuild'.format(pycmd)
        run(status, cmd, required=True)

        # {32b,64b} x {shared,dynamic} link
        for size in ['ia32', 'x86-64']:
            for linkkind, link in [('static', ''), ('dynamic', '--shared')]:
                build_dir = 'obj-general-{}-{}-{}'.format(pyver, size, linkkind)
                cmd = '{} mfile.py --build-dir={} host_cpu={} {} test'.format(pycmd,
                                                                              build_dir,
                                                                              size,
                                                                              link)
                run(status, cmd)

        # all instr test with internal-conf
        size = 'x86-64'
        linkkind = 'static'
        build_dir = 'obj-conf-{}-{}-{}'.format(pyver, size, linkkind)
        cwd = os.path.abspath(os.curdir)
        flags = '--kind internal-conf --enc2-test-checked'
        cmd = '{} xedext/xed_build.py --xed-dir {} {}  --build-dir={} host_cpu={}'.format(
            pycmd, cwd, flags, build_dir, size)
        ok = run(status, cmd)

        if ok:
            cmd = '{}/enc2-m64-a64/enc2tester-enc2-m64-a64 --reps 1 --main --gnuasm > a.c'.format(
                build_dir)
            ok = run(status, cmd)

            if 1: # FIXME: ignore error code for now.
                cmd = 'gcc a.c'
                run(status, cmd)

                if ok:
                    cmd = '{}/wkit/bin/xed -i a.out > all.dis'.format(build_dir)
                    run(status, cmd)

        # arch val test
        # FIXME: add other required knobs
        size = 'x86-64'
        linkkind = 'static'
        build_dir = 'obj-archval-{}-{}-{}'.format(pyver, size, linkkind)
        cwd = os.path.abspath(os.curdir)
        flags = '--kind architectural-val'
        cmd = '{} xedext/xed_build.py --xed-dir {} {} --build-dir={} host_cpu={}'.format(
            pycmd, cwd, flags, build_dir, size)
        run(status, cmd)

        # knc test
        if 0:
            size = 'x86-64'
            linkkind = 'static'
            build_dir = 'obj-knc-{}-{}-{}'.format(pyver, size, linkkind)
            cmd = '{} mfile.py --knc --build-dir={} host_cpu={} test'.format(
                pycmd, build_dir, size)
            run(status, cmd)

        if status.fails == 0:
            success(status)
        fail(status)

def test():
    status = jobs_status_t()
    status.success(1,'foo')
    status.success(1,'bar')
    fail(status)
if __name__ == "__main__":
    #test()
    main()
    sys.exit(0)
