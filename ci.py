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
import os
import platform
import subprocess

def get_python_cmds():
    if platform.system() == 'Windows':
        return [ (x,'C:/python{}/python'.format(x)) for x in ['37'] ]
    elif platform.system() in ['Darwin','Linux']:
        # The file .travis.yml installs python3 on linux. Already present on mac
        return [ ('3.x','python3')]
    return [('dfltpython','python')]
        
    
for pyver,pycmd in get_python_cmds():
    cmd = '{} -m pip install --user https://github.com/intelxed/mbuild/zipball/master'.format(pycmd)
    print(cmd)
    subprocess.check_call(cmd, shell=True)
    for size in ['ia32','x86-64']:
        for linkkind,link in [('dfltlink',''),('dynamic','--shared')]:
            build_dir = '{}-{}-{}'.format(pyver, size, linkkind)
            cmd = '{} mfile.py --build-dir=build-{} host_cpu={} {} test'.format(pycmd,build_dir,size,link)
            print(cmd)
            subprocess.check_call(cmd, shell=True)
