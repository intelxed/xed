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
'''Run CI checks on github'''
import os
import platform
import subprocess


def github_actions():
    return 'GITHUB_ACTIONS' in os.environ and os.environ['GITHUB_ACTIONS'] == 'true'
    
def size_variants():
    if platform.system() == 'Darwin' and github_actions():
        # 32 bit deprecated in latest macos
        return ['x86-64']
    else:
        return ['ia32', 'x86-64']

def get_python_cmds():
    '''find python verions. return tuples of (name, command)'''
    if github_actions():
        return [('3.x', 'python')]
    if platform.system() == 'Windows':
        return [(x, 'C:/python{}/python'.format(x)) for x in ['37']]
    if platform.system() in ['Darwin', 'Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [('3.x', 'python3')]
    return [('dfltpython', 'python')]

for pyver, pycmd in get_python_cmds():
    cmd = '{} -m pip install --user https://github.com/intelxed/mbuild/zipball/main'.format(pycmd)
    print(cmd)
    subprocess.check_call(cmd, shell=True)
    for size in size_variants():
        for linkkind, link in [('dfltlink', ''), ('dynamic', '--shared')]:
            build_dir = '{}-{}-{}'.format(pyver, size, linkkind)
            cmd = '{} mfile.py --build-dir=build-{} host_cpu={} {} test'.format(
                pycmd, build_dir, size, link)
            print(cmd)
            subprocess.check_call(cmd, shell=True)
