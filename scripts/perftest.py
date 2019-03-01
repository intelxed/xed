#!/usr/bin/env python
#-*- python -*-
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
import os
import sys
import argparse
import textwrap
import find_dir
import math

try:
    import mbuild
except:    
    sys.path.append(find_dir.find_dir('mbuild'))
    import mbuild

def graph_it(lst):
    import numpy as np
    import matplotlib.pyplot as plt

    plt.plot(lst)
    plt.show()

def variance(cpd):
    cpd_avg = sum(cpd)/len(cpd)
    s = 0.0
    for x in cpd:
        d =  (x-cpd_avg)
        s += d*d
    return s/(len(cpd)-1)
def standard_deviation(cpd):
    return math.sqrt(variance(cpd))


def work(args):
    print("Testing performance...")

    if not os.path.exists(args.input):
        mbuild.warn("Performance test input binary not found: {}".format(args.input))
        return 2
    if not os.path.exists(args.xed):
        mbuild.warn("Performance test executable binary not found: {}".format(args.xed))
        return 2

    s = args.xed + ' -v 0 -i ' + args.input
    cpd = []
    
    print("Skipping {} samples...".format(args.skip))
    for sample in range(0,args.skip):
        (status, stdout, stderr) =  mbuild.run_command(s)

    print("Running  {} tests...".format(args.samples))
    for sample in range(0,args.samples):
        (status, stdout, stderr) =  mbuild.run_command(s)
        found=False
        if status == 0 and stdout:
            for line in stdout:
                if '#Total cycles/instruction DECODE' in line:
                    chunks = line.strip().split()
                    cpd_one = float(chunks[-1])
                    found = True
        if status and stdout:
            print("Error messages from sample {0:d}:".format(sample))
            for line in stdout:
                print("   ",line, end=' ')
        if found:
            cpd.append(cpd_one)
    
    if len(cpd) == args.samples:

        expected = 450.0  # cycles / decode 

        cpd_min = min(cpd)
        cpd_max = max(cpd)
        cpd_avg = sum(cpd)/len(cpd)
        print(textwrap.fill("Samples: " +  
                            ", ".join(["{0:6.2f}".format(x) for x in cpd]),
                            subsequent_indent = "         "))

        print("Minimum: {0:6.2f}".format(cpd_min))
        print("Average: {0:6.2f}".format(cpd_avg))
        print("Maximum: {0:6.2f}".format(cpd_max))
        print("Range  : {0:6.2f}".format(cpd_max-cpd_min))
        print("Stddev : {0:6.2f}".format(standard_deviation(cpd)))


        if cpd_avg > expected:
            s =  ["PERFORMANCE DEGREDATION: "]
            s.append("Observed {0:.2f} vs Expected {1:.2f}".format(
                    cpd_avg, expected))
            print("".join(s))
            return 1 # error
        print("Success. Average less than {0:.2f}".format(expected))
        
        if args.graph:
            graph_it(cpd)
        return 0 # success
    print("MISSING SAMPLES")
    return 2

def setup(defaults):
    parser = argparse.ArgumentParser(description='XED Performance testing.')
    parser.add_argument("--xed", help='input XED executable',
                        default=defaults.xed)
    parser.add_argument("--input", help='input test file name',
                        default=defaults.input)
    parser.add_argument("--graph", help='graph the samples',
                        action="store_true",
                        default=defaults.graph)
    parser.add_argument("--samples", help='number of samples',
                        type=int, default=defaults.samples)
    parser.add_argument("--skip", help='number of samples to skip',
                        type=int, default=defaults.skip)
    args = parser.parse_args()
    return args

class args_t:
    pass

def mkargs():
    args = args_t()
    args.xed = 'obj/examples/xed'
    args.input = '/usr/bin/emacs24-x'
    args.graph = False
    args.samples=10
    args.skip=12
    return args

if __name__ == "__main__":
    defaults = mkargs()
    args = setup(defaults)
    r = work(args)
    sys.exit(r)
    
