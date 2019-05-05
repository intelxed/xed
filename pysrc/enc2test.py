#!/usr/bin/env python3
# -*- python -*-
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
import copy
import types
import glob
import re
import argparse
import itertools
import collections

import find_dir # finds mbuild and adds it to sys.path
import mbuild

import genutil
import codegen
import read_xed_db
import gen_setup
from enc2common import *

def _make_test_function_object(env, enc_fn):
    encoder_fn = enc_fn.get_function_name()
    versions = env.test_function_names[encoder_fn]
    fname = 'test_{}_{}'.format(versions, encoder_fn)
    env.test_function_names[encoder_fn] += 1
    
    fo = codegen.function_object_t(fname, return_value='void')
    return fo


def _add_test_function(ii,fo):
    ii.enc_test_functions.append(fo)
    dbg("TEST FUNCTION:")
    dbg(fo.emit())

    
def _create_enc_test_functions(env, ii, encfn):
    testfn = _make_test_function_object(env,encfn)

    # gather args
    args = []
    for arg,arginfo in encfn.get_args():
        @arg_chunks = arg.split(' ')
        argtype = " ".join(arg_chunks[:-1])
        argname = arg_chunks[-1]
        args.append((argtype,argname,arginfo))

    # arg var decls
    for i,(argtype,argname,arginfo) in enumerate(args):
        testfn.add_code_eol('{} {}'.format(argtype, argname))

    # set vars to test values  - FIXME
        
    # test function call
    s = []
    s.append(  encfn.get_function_name() )
    s.append( '(' )
    for i,(argtype,argname,arginfo) in enumerate(args):
        if i>0:
            s.append(',')
        s.append("{} /*{}*/".format(argname,arginfo))
    s.append( ')' )
    testfn.add_code_eol(''.join(s))
    
    _add_test_function(ii, testfn)
    
    
def create_test_fn_main(env, ii):
    env.test_function_names = collections.defaultdict(int)
    ii.enc_test_functions = []

    for encfn in ii.encoder_functions:
        _create_enc_test_functions(env, ii, encfn)

    
