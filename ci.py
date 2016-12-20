import os
import platform
import subprocess

for size in ['ia32','x86-64']:
    for link in ['','--shared']:
        cmd = 'python mfile.py --build-dir=build host_cpu=%s %s test' % (size,link)
        print(cmd)
        subprocess.check_call(cmd, shell=True)
