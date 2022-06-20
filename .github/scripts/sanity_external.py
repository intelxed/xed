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
import sys
import utils


def main():
    status = utils.JobStatus()

    for pyver, pycmd in utils.get_python_cmds():
        cmd = f'{pycmd} -m pip install --user ./mbuild'
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

        # check enc-dec for all instructions
        build_dir = f'obj-enc2-{pyver}-x86-64-static'
        cmd = f'{pycmd} mfile.py --enc2-test-checked --build-dir={build_dir} host_cpu=x86-64 test'
        ok = utils.run(status, cmd)
        if ok:
            cmd = f'{build_dir}/enc2-m64-a64/enc2tester-enc2-m64-a64 --reps 1 --main --gnuasm > a.c'
            ok = utils.run(status, cmd)
            if ok:
                cmd = 'gcc a.c'
                utils.run(status, cmd)
                if ok:
                    cmd = f'{build_dir}/wkit/bin/xed -i a.out > all.dis'
                    utils.run(status, cmd)

        # knc test
        build_dir = f'obj-knc-{pyver}-x86-64-static'
        cmd = f'{pycmd} mfile.py --knc --build-dir={build_dir} host_cpu={size} test'
        utils.run(status, cmd)

        status.report_and_exit()


if __name__ == "__main__":
    main()
    sys.exit(0)
