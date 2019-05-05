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
    
    fo = codegen.function_object_t(fname, return_type='void')
    return fo


def _add_test_function(ii,fo):
    ii.enc_test_functions.append(fo)
    dbg("TEST FUNCTION:")
    dbg(fo.emit())



def  get_gpr64(env, ii):
    return 'XED_REG_RBX'
def  get_gpr32(env, ii):
    return 'XED_REG_ECX'
def  get_gpr16(env, ii):
    return 'XED_REG_DX'

def  get_gpr8(env, ii):
    return 'XED_REG_BL'

def  get_xmm(env, ii):
    return 'XED_REG_XMM0'

def  get_ymm(env, ii):
    return 'XED_REG_YMM1'

def  get_zmm(env, ii):
    return 'XED_REG_ZMM3'

def  get_kreg(env, ii):
    return 'XED_REG_K1'
def  get_kreg_not0(env, ii):
    return 'XED_REG_K2'

def  get_x87(env, ii):
    return 'XED_REG_ST1'

def  get_mmx(env, ii):
    return 'XED_REG_MM0'

def  get_imm8(env, ii):
    return '0xFF'

def  get_imm16(env, ii):
    return '0xFEED'

def  get_imm32(env, ii):
    return '0xAABBCCDD'
def  get_imm64(env, ii):
    return '0xAABBCCDDEEFF1122'

def  get_disp8(env, ii):
    return '0x15'

def  get_disp16(env, ii):
    return '0x1234'

def  get_disp32(env, ii):
    return '0x12345678'

def  get_disp64(env, ii):
    return '0x1122334455667788'

def  get_cr(env, ii):
    return 'XED_REG_CR4'

def  get_dr(env, ii):
    return 'XED_REG_DR0'

def  get_seg(env, ii):
    return 'XED_REG_FS'

def  get_zeroing(env, ii):
    return '1'

def  get_rcsae(env, ii):
    return '0x2'

def  get_scale(env, ii):
    return '2'

def  get_ax(env, ii):
    return 'XED_REG_AX'

def  get_eax(env, ii):
    return 'XED_REG_EAX'

def  get_rax(env, ii):
    return 'XED_REG_RAX'
    


arginfo2value_creator = {
     'gpr64': get_gpr64,
     'gpr32': get_gpr32,
     'gpr16': get_gpr16,
     'gpr8': get_gpr8,
     'xmm': get_xmm,
     'ymm': get_ymm,
     'zmm': get_zmm,
     'kreg': get_kreg,
     'kreg!0': get_kreg_not0,
     'x87': get_x87,
     'mmx': get_mmx,
    
     'imm8': get_imm8,
     'imm16': get_imm16,
     'imm32': get_imm32,
     'imm64': get_imm64,
    
     'int8': get_imm8,  # using imm8...
     'int16': get_imm16,
     'int32': get_imm32,
     'int64': get_imm64,
    
     'disp8': get_disp8,
     'disp16': get_disp16,
     'disp32': get_disp32,
     'disp64': get_disp64,
     'cr': get_cr,
     'dr': get_dr,
     'seg': get_seg,
     'zeroing': get_zeroing,
     'rcsae': get_rcsae,
     'scale': get_scale,
     'ax': get_ax,
     'eax': get_eax,
     'rax': get_rax
 }


    
    
def _create_enc_test_functions(env, ii, encfn):
    global arginfo2value_creator
 
    testfn = _make_test_function_object(env,encfn)

    # gather args
    args = []
    for arg,arginfo in encfn.get_args():
        arg_chunks = arg.split(' ')
        argtype = " ".join(arg_chunks[:-1])
        argname = arg_chunks[-1]
        args.append((argtype,argname,arginfo))

    request_arg = None
    for argtype,argname,arginfo in args:
        if arginfo == 'req':
            request_arg = argname
    if not request_arg:
        die("NO REQUEST ARG FOUND")

    # arg var decls
    for i,(argtype,argname,arginfo) in enumerate(args):
        testfn.add_code_eol('{} {}'.format(argtype, argname))

    # common configuration
    testfn.add_code_eol('xed_enc2_req_t request')
    testfn.add_code_eol('xed_uint8_t output_buffer[XED_MAX_INSTRUCTION_BYTES]')
    
    
    # set vars to test values  - FIXME
    for argtype,argname,arginfo in args:
        if arginfo == 'req':
            # set up the request structure and output buffer
            testfn.add_code_eol('xed_enc2_req_t_init(&request, output_buffer)')
            testfn.add_code_eol('{} = &request'.format(request_arg) )
        else:
            if not arginfo:
                die("NO ARGINFO FOR {} {} in {}".format(argtype, argname, ii.iclass))
            vfn = arginfo2value_creator[arginfo]
            v = vfn(env,ii)
            testfn.add_code_eol('{} = {}'.format(argname, v))            
    
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

    # FIXME: call XED decode to test the encoder output!
    
    _add_test_function(ii, testfn)
    
    
def create_test_fn_main(env, ii):
    env.test_function_names = collections.defaultdict(int)
    ii.enc_test_functions = []

    for encfn in ii.encoder_functions:
        _create_enc_test_functions(env, ii, encfn)

    
