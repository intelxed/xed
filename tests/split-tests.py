#!/usr/bin/env python
# -*- python -*-

import os,sys,re,glob

def work():
    files = glob.glob("*.txt")
    for fn in files:
        lines = file(fn).readlines()
        lines = map(lambda x: x.strip(), lines)
        ofn = fn + ".new"
        of = open(ofn,'w')
        for line in lines:
            if line:
                incodes, cmd = line.split(';') # incodes are tossed
                cmd = cmd.strip()
                codes = []
                if ' -de ' in cmd:
                    codes.append('DEC')
                    codes.append('ENC')
                elif ' -e ' in cmd:
                    codes.append('ENC')
                elif ' -d ' in cmd:
                    codes.append('DEC')
                elif 'ild' in cmd:
                    codes.append('DEC')
                elif 'ex1' in cmd:
                    codes.append('DEC')
                elif 'ex3' in cmd:
                    codes.append('ENC')
                elif 'ex4' in cmd:
                    codes.append('DEC')
                elif 'ex6' in cmd:
                    codes.append('DEC')
                    codes.append('ENC')
                else:
                    codes.append('OTHER')
                
                if 'C4' in cmd or 'C5' in cmd or 'c4' in cmd or 'c5' in cmd:
                    codes.append('AVX')
                if '  8f' in cmd: # total hack: FIXME, miss some xop stuff in c4 space
                    codes.append('XOP')
                if ' v' in cmd or ' V' in cmd:
                    codes.append('AVX')

                cs = " ".join(codes)
                of.write("{0:20s} ; {1}\n".format(cs, cmd))

        of.close()


if __name__ == "__main__":
    work()
