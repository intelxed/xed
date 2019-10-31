#!/usr/bin/env python
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
from __future__ import print_function
import sys
import optparse
import collections

def read_keys(env):
    kys_lst = []
    for line in file(env.fn):
        line = line.strip()
        line = map(int,line.split())
        kys_lst.append(line)
    return kys_lst
        
def sequential_nonzero_base(kys):
    ln = len(kys)
    minimum = kys[0]
    lst = kys[-1]
    if (ln-1) == (lst-minimum):
        return True
    return False

def mildly_sparse(kys):
    ln = len(kys)
    minimum = kys[0]
    lst = kys[-1]
    nrange =   kys[-1] - minimum
    # tolerate 10% sparsity
    if nrange <= ln * 1.20:
        return True
    return False
def sparse_and_small(kys):
    ln = len(kys)
    minimum = kys[0]
    lst = kys[-1]
    nrange =   kys[-1] - minimum
    limit = 32
    if nrange <= limit and ln <= limit:
        return True
    return False

def two_values(kys):
    if len(kys) == 2:
        return True
    return False

def three_values(kys):
    if len(kys) == 3:
        return True
    return False

    

def classify(kys,env):
    ln = len(kys)

    env.lengths[ln] += 1
    env.unique_sequences[str(kys)] += 1

    if (ln-1) == kys[-1]:
        env.sequential_zero_base += 1
    elif  sequential_nonzero_base(kys):
        env.sequential_nonzero_base += 1
    elif two_values(kys):
        env.twofer  += 1
    elif three_values(kys):
        env.threefer  += 1
    elif mildly_sparse(kys):
        env.mildly_sparse  += 1
    elif sparse_and_small(kys):
        env.sparse_and_small  += 1
    else:
        env.funky.append(kys)
    
def dump_classifications(env):
    for k in env.lengths.keys():
        v = env.lengths[k]
        print("LENGTH {} COUNT {}".format(k,v))

    for lst in env.funky:
        print(str(lst))

    u = len(list(env.unique_sequences.keys()))
    print("TOTAL KEY SEQUENCES {}".format(env.all_keys))
    print("UNIQUE KEY SEQUENCES {}".format(u))
    print("")
    print("SEQUENTIAL (Zero Based) {}".format(env.sequential_zero_base))
    print("SEQUENTIAL (NonZero Based) {}".format(env.sequential_nonzero_base))
    print("MILDLY SPARSE 20% {}".format(env.mildly_sparse))
    print("SPARSE and SMALL (<=32 values and values <= 32) {}".format(env.sparse_and_small))
    print("TWO VALUES {}".format(env.twofer))
    print("THREE VALUES {}".format(env.threefer))
    r = (u - env.sequential_nonzero_base - env.sequential_zero_base  - 
         env.mildly_sparse - env.twofer - env.threefer - env.sparse_and_small)
    print("OTHER {}".format(r))


def main(env):
    env.funky = []
    env.mildly_sparse = 0
    env.sparse_and_small = 0
    env.twofer = 0
    env.threefer = 0
    env.sequential_zero_base = 0
    env.sequential_nonzero_base = 0
    env.lengths = collections.defaultdict(int)
    env.unique_sequences = collections.defaultdict(int)

    kys_lst =  read_keys(env)
    env.all_keys = len(kys_lst)
    u = {}
    for k in kys_lst:
        u[str(k)]=k
    unique_keys = list(u.values())

    for k in unique_keys:
        classify(k,env)
    dump_classifications(env)
    return 0

class obj_t(object):
    def __init__(self):
        pass

def setup():
    env = obj_t()

    parser = optparse.OptionParser()
    parser.add_option('-i', 
                      action='store',
                      dest='input', 
                      default='keys.dec',
                      help='Input file name')

    (options,args) = parser.parse_args()
    env.fn = options.input
    return env

if __name__ == "__main__":
    env = setup()
    r = main(env)
    sys.exit(r)
