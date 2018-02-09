#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2018 Intel Corporation
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
