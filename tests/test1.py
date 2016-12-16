#!/usr/bin/env python
# -*- python -*-
import sys, optparse, stat, os, re, shutil, copy, time, glob

def find_dir(d):
    dir = os.getcwd()
    last = ''
    while dir != last:
        target_dir = os.path.join(dir,d)
        if os.path.exists(target_dir):
            return target_dir
        last = dir
        (dir,tail) = os.path.split(dir)
    return None
sys.path = [find_dir('mbuild')] + sys.path

def dirname_n(s,n):
    t = s
    for i in range(0,n):
        t = os.path.dirname(t)
    return t

import mbuild
start_time=mbuild.get_time()

env = mbuild.env_t()
env.parse_args()
work_queue = mbuild.work_queue_t(env['jobs'])


cmds= ['obj/xed -64 -i /bin/ls > ls.out',
       'obj/xed -n 10m -v 0 -64 -i /usr/X11R6/bin/Xvnc ' ]
for cmd in cmds:
    c = mbuild.command_t(cmd)
    work_queue.add(c)

phase = "XED2-TESTS"
okay = work_queue.build()
if not okay:
    mbuild.die("[%s]  failed" % (phase))
mbuild.msgb(phase, "succeeded")

end_time=mbuild.get_time()
mbuild.msgb("ELAPSED TIME", mbuild.get_elapsed_time(start_time,end_time))
