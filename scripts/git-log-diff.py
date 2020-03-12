#!/usr/bin/env python3
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

# Compare git logs for 2 branches.
#
# # print the lines in one branch that are not in the other branch.
#
#
import os
import sys
import argparse
import subprocess

def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("-la", "--linesa", default=30, help="number of lines to grab from branch A")
    parser.add_argument("-lb", "--linesb", default=30, help="number of lines to grab from branch B")    
    parser.add_argument("-p", "--pick", default=False, action='store_true', help="number of lines to grab")
    parser.add_argument("abr", help="A branch")
    parser.add_argument("bbr", help="B branch")
    args = parser.parse_args()
    return args

def parse_file(brname,nlines=30):
     n = []
     cmd = "git log -{} --oneline {}".format(nlines, brname)
     lines = subprocess.check_output(cmd.split(), universal_newlines=True)
     lines = lines.split('\n')
     for line in lines:
         line = line.strip()
         a = line.split(' ',1)
         if len(a)==2:
             n.append(a)
     return n
         
def compare(args, abr, bbr, alines, blines):
    first = True
    picks = []
    for a in alines:
        found = False
        for b in blines:
            if b[1] == a[1]:
                found = True
            
        if found == False:
            if first:
                print("Present in {}, missing from {}:\n".format(abr,bbr))
                first = False
            keep = True
            if '(I)' in a[1]:
                keep = False
            print("{}  {}".format("    " if keep else "DROP", " ".join(a)))
            if keep:
                picks.append((a[0],a[1]))
    print()
    
    if args.pick:
        picks.reverse()
        for commitid, descr in picks:
            print("  git cherry-pick -x  {}  # {}".format(commitid, descr))
        print()

def main():
    args = setup()
    alines = parse_file(args.abr, args.linesa)
    blines = parse_file(args.bbr, args.linesb)
    compare(args,args.abr, args.bbr, alines, blines)
    compare(args,args.bbr, args.abr, blines, alines)
    return 0

if __name__ == "__main__":
    r = main()
    sys.exit(r)
