import os
import platform
import subprocess

def get_python_cmds():
    if platform.system() == 'Linux':
        for pyver in ['2.7','3.5.2']:
            pycmd = '/opt/python/{}/bin/python'.format(pyver)
            lst.append((pyver,pycmd))
        return lst
    
    return [('dfltpython','python')]
        
    
for pyver,pycmd in get_python_cmds():
    for size in ['ia32','x86-64']:
        for linkkind,link in [('dfltlink',''),('dynamic','--shared')]:
            build_dir = '{}-{}-{}'.format(pyver, size, linkkind)
            cmd = '{} mfile.py --build-dir=build-{} host_cpu={} {} test'.format(pycmd,build_dir,size,link)
            print(cmd)
            subprocess.check_call(cmd, shell=True)
