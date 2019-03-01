#!/usr/bin/env python
#-*- python -*-
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

# The tests XED by running a bunch of cmd files from a bunch of directories.
# It tests for correctness by looking at the return code, the stdout and stderr.
#
# FIXME: The version number changes need to be ignored.
#
# This can also create a bunch of test directories from a bulk command
# line file. It substitutes BUILDDIR for the path to the xed examples,
# typically ../obj and that value comes from the env['build_dir']

from __future__ import print_function
import sys
import os
import re
import time
import difflib

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

import mbuild

def write_file(fn,lines):
    print("[EMIT] %s" % (fn))
    # write the file in binary mode to prevent LF -> CR LF expansion on Windows
    f = open(fn,"wb")
    if lines:
        for line in lines:
            f.write(line.replace('\r', '')) # gobble CR symbols if any
    f.close()


def create_reference(env, test_dir, codes_and_cmd, make_new=True):
    mbuild.cmkdir(test_dir)

    if make_new:
        codes, cmd = codes_and_cmd.split(';')
        cmd_fn = os.path.join(test_dir,"cmd")
        write_file(cmd_fn,cmd + '\n')
        codes_fn = os.path.join(test_dir,"codes")
        write_file(codes_fn,codes + '\n')
    else:
        cmd = codes_and_cmd

    # abspath required for windoze
    build_dir = mbuild.posix_slashes(os.path.abspath(env['build_dir']))
    cmd2 = re.sub('BUILDDIR',build_dir,cmd)
    print(cmd2)

    (retcode, stdout,stderr) = mbuild.run_command(cmd2,separate_stderr=True)
    print("Retcode %s" % (str(retcode)))
    if stdout:
        for line in stdout:
            print("[STDOUT] %s" % (line))
    if stderr:
        for line in stderr:
            print("[STDERR] %s" % (line))

    write_file(os.path.join(test_dir,"retcode.reference"), [ str(retcode) + "\n" ])
    write_file(os.path.join(test_dir,"stdout.reference"), stdout)
    write_file(os.path.join(test_dir,"stderr.reference"), stderr)

def make_bulk_tests(env):
    i = 0
    for bulk_test_file in  env['bulk_tests']:
        print("[READING BULK TESTS] %s" % (bulk_test_file))
        tests = open(bulk_test_file,'r').readlines()
        tests = [ re.sub(r"#.*",'',x) for x in tests] # remove comments
        tests = [ x.strip() for x in tests]  # remove leading/trailing whitespace, newlines
        for test in tests:
            if test:
                si = mbuild.join(env['otests'],"test-%05d" % (i))
                create_reference(env, si, test, make_new=True)
                i = i + 1

def compare_file(reference, this_test):
    ref_lines = open(reference,'r').readlines()
    ref_lines = [ x.rstrip() for x in ref_lines]
    this_test = [ x.rstrip() for x in  this_test]
    for line in difflib.unified_diff(ref_lines, this_test,
                                     fromfile=reference, tofile="current"):
        sys.stdout.write(line.rstrip()+'\n')
    if len(ref_lines) != len(this_test):
        mbuild.msgb("DIFFERENT NUMBER OF LINES", "ref %d test %d" % (len(ref_lines),len(this_test)))
        for ref in ref_lines:
            mbuild.msgb("EXPECTED",'%s' % (ref.strip()))
        return False
    for (ref,test) in zip(ref_lines,this_test):
        if ref.strip() != test.strip():
            if ref.find("XED version") != -1:  # skip the version lines
                continue
            mbuild.msgb("DIFFERENT", "\n\tref  [%s]\n\ttest [%s]" % (ref, test))
            return False
    return True

def all_codes_present(specified_codes, test_codes):
    """The test codes must be a subset of the specified codes. 
    If no codes are specified, we do everything.
    """
    if specified_codes:
        print("comparing restriction: {} and  test: {}".format(str(specified_codes), str(test_codes)))
        s = set(specified_codes)
        t = set(test_codes)
        u = s.union(t)
        if u-s:
            # there are codes in t that are not in s, so we reject this test
            return False
    return True 

def _prep_stream(strm,name):
    if len(strm) == 1:
        strm= strm[0].split("\n")
    if len(strm) == 1 and strm[0] == '':
        strm = []
    if len(strm) > 0 and len(strm[-1]) == 0:
        strm.pop()
    for line in strm:
        print("[{}] {} {}".format(name,len(line),line))
    return strm

def one_test(env,test_dir):

    cmd_fn = os.path.join(test_dir,"cmd")
    cmd = open(cmd_fn,'r').readlines()[0]

    # abspath required for windoze
    build_dir = mbuild.posix_slashes(os.path.abspath(env['build_dir']))
    cmd2 = re.sub('BUILDDIR',build_dir,cmd)
    cmd2 = cmd2.strip()
    print(cmd2)

    (retcode, stdout,stderr) = mbuild.run_command(cmd2,separate_stderr=True)
    print("Retcode %s" % (str(retcode)))
    if stdout:
        stdout = _prep_stream(stdout,"STDOUT")
    if stderr:
        stderr = _prep_stream(stderr,"STDERR")

    ret_match = compare_file(os.path.join(test_dir,"retcode.reference"), [ str(retcode) ])
    stdout_match = compare_file(os.path.join(test_dir,"stdout.reference"), stdout)
    stderr_match = compare_file(os.path.join(test_dir,"stderr.reference"), stderr)
    
    okay = True
    if not ret_match:
        mbuild.msgb("RETCODE MISMATCH")
        okay = False
    if not stdout_match:
        mbuild.msgb("STDOUT MISMATCH")
        okay = False
    if not stderr_match:
        mbuild.msgb("STDERR MISMATCH")
        okay = False
    print("-"*40 + "\n\n\n")
    return okay

def find_tests(env):
    test_dirs = []
    for d in env['tests']:
        test_dirs.extend(mbuild.glob(mbuild.join(d,"test-[0-9][0-9]*")))
    return  test_dirs

def rebase_tests(env):
    test_dirs = find_tests(env)
    for test_dir in test_dirs:
        cmd_fn = os.path.join(test_dir,"cmd")
        test_cmd = open(cmd_fn,'r').readlines()[0]
        create_reference(env, test_dir, test_cmd, make_new=False)
    
def run_tests(env):
    failing_tests = []
    test_dirs = find_tests(env)
    errors = 0
    skipped = 0
    for tdir in test_dirs:
        #if env.on_windows():
        #    time.sleep(1) # try to avoid a bug on windows running commands to quickly
        print('-'*40) 
        mbuild.msgb("TESTING" , tdir)

        codes_fn = os.path.join(tdir,"codes")
        codes = open(codes_fn,'r').readlines()[0].strip().split()

        if all_codes_present(env['codes'],codes):
            okay = one_test(env,tdir)
            if not okay:
                failing_tests.append(tdir)
                errors += 1
        else:
            mbuild.msgb("SKIPPING DUE TO TEST SUBSET RESTRICTION")
            print('-'*40 + "\n\n\n")
            skipped += 1

    ntests = len(test_dirs)
    tested = ntests-skipped
    mbuild.msgb("TESTS",   str(ntests))
    mbuild.msgb("SKIPPED", str(skipped))
    mbuild.msgb("TESTED",  str(tested))
    mbuild.msgb("ERRORS",  str(errors))
    if tested:
        mbuild.msgb("PASS_PCT", "%2.4f%%" % (100.0 * (tested-errors)/tested))
    else:
        mbuild.msgb("PASS_PCT", '0%')
    failing_tests.sort()
    for t in failing_tests:
        mbuild.msgb("FAIL", t)
    return errors

#############################################3
    
def work():
    env = mbuild.env_t()
    env.parser.add_option(
        "--bulk-make-tests", "-b",
        dest="bulk_tests", action="append",
        default=[], 
        help="List of bulk tests from which to create test references. Repeatable")
    env.parser.add_option("--rebase-tests", 
                          dest="rebase_tests", 
                          action="store_true",
                          default=False, 
                          help="Update the reference output files. Do not compare.")
    env.parser.add_option("--tests", 
                          dest="tests", 
                          action="append",
                          default=[], 
                          help="Directory where tests live.")
    env.parser.add_option("--otests", 
                          dest="otests", 
                          action="store",
                          default='tests-base', 
                          help="Directory where tests live.")
    env.parser.add_option("-c", "--code", 
                          dest="codes", 
                          action="append",
                          default=[], 
                          help="Codes for test subsetting (DEC, ENC, AVX, " 
                             + "AVX512X, AVX512PF, XOP, VIA, KNC)." 
                             + " Only used for running tests, not creating them.")
    env.parse_args()

    if not env['tests']:
        env['tests'] = ['tests-base']

    xed = mbuild.join(env['build_dir'],'xed')
    #xedexe = xed + ".exe" 
    #if not os.path.exists(xed) and not os.path.exists(xedexe):
    #    mbuild.die("Need the xed command line tool: %s or %s\n\n" % (xed,xedexe))

    if len(env['bulk_tests']) != 0:
        mbuild.msgb("MAKE BULK TESTS")
        make_bulk_tests(env)
        sys.exit(0)

    if env['rebase_tests']:
        rebase_tests(env)
        sys.exit(0)


    errors=run_tests(env)
    sys.exit(errors)


if __name__ == "__main__":
    work()
