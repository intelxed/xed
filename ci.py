import os
import platform
import subprocess

def get_python_cmds():
    if platform.system() == 'Windows':
        lst = []
        pyvers = ['27','35']
        #pyvers = ['27']
        for pyver in pyvers:
            pycmd = 'C:/python{}/python'.format(pyver)
            lst.append((pyver,pycmd))
        return lst
    elif platform.system() == 'Linux':
        # The file .travis.yml installs python2 and python3
        return [('2.7','python'),
                ('3.x','python3')]
    elif platform.system() == 'Darwin':
        # The file .travis.yml installs python2 and python3
        return [('2.7','/usr/local/bin/python2'),
                ('3.x','/usr/local/bin/python3')]
    
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
