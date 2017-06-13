import os
import platform
import subprocess

def get_python_cmds():
    if platform.system() == 'Linux':
        for pyver in ['2.7','3.5.2']:
            pycmd = '/opt/python/{}/bin/python'.format(pyver)
            lst.append(pycmd)
        return lst
    
    return ['python']
        
    
for pycmd in get_python_cmds():
    for size in ['ia32','x86-64']:
        for link in ['','--shared']:
            cmd = '{} mfile.py --build-dir=build host_cpu={} {} test'.format(pycmd,size,link)
            print(cmd)
            subprocess.check_call(cmd, shell=True)
