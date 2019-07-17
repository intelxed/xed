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
import codegen
from enc2common import *

def _make_arg_check_function_object(env, enc_fn):
    encoder_fn = enc_fn.get_function_name()
    fname = '{}_chk'.format(encoder_fn)
    fo = codegen.function_object_t(fname, return_type='void', dll_export=True)
    return fo


def _add_arg_check_function(ii,fo):
    ii.enc_arg_check_functions.append(fo)
    dbg("ARG CHECK FUNCTION:")
    dbg(fo.emit())

    
def _fixup_arg_type(ii,s):
    if ii.space == 'vex':
        if s in ['xmm','ymm']:
            return "{}_avx".format(s)
    if s == 'kreg!0':
        return 'kreg_not0'
    return s
    
    
def _create_enc_arg_check_function(env, ii, encfn):
    chk_fn = _make_arg_check_function_object(env,encfn)
    
    # gather args
    args = []
    for arg,arginfo in encfn.get_args():
        arg_chunks = arg.split(' ')
        argtype = " ".join(arg_chunks[:-1])
        argname = arg_chunks[-1]
        args.append((argtype,argname,arginfo))

    for argtype,argname,arginfo in args:
        chk_fn.add_arg('{} {}'.format(argtype, argname), arginfo)


    args_to_check = False
    for argtype,argname,arginfo in args:
        if not arginfo:
            die("NO ARGINFO FOR {} {} in {}".format(argtype, argname, ii.iclass))
        elif arginfo == 'req':
            continue # don't check the request structure
        elif 'int' in arginfo:
            continue # don't check the integer arguments
        elif 'imm' in arginfo:
            continue # don't check the integer arguments
        else:
            args_to_check = True
            break

    if args_to_check:
        chk_fn.add_code('if (xed_enc2_check_args) {')
        chk_fn.add_code_eol('   const char* pfn = "{}"'.format(  chk_fn.get_function_name() ))
        for argtype,argname,arginfo in args:
            if arginfo == 'req':
                continue # don't check the request structure
            elif 'int' in arginfo:
                continue # don't check the integer arguments
            elif 'imm' in arginfo:
                continue # don't check the integer arguments
            else:
                chk_fn.add_code_eol('   xed_enc2_invalid_{}({}, {},"{}",pfn)'.format(
                    _fixup_arg_type(ii,arginfo),
                    env.mode,
                    argname,
                    argname))
        chk_fn.add_code('}') # end of "if (xed_enc2_check_args) ..." clause
            
    # call encoder function call
    s = []
    s.append(  encfn.get_function_name() )
    s.append( '(' )
    for i,(argtype,argname,arginfo) in enumerate(args):
        if i>0:
            s.append(',')
        s.append("{} /*{}*/".format(argname,arginfo))
    s.append( ')' )
    chk_fn.add_code_eol(''.join(s))

    

    _add_arg_check_function(ii, chk_fn)
    
    
def create_arg_check_fn_main(env, ii):
    ii.enc_arg_check_functions = []
    for encfn in ii.encoder_functions:
        _create_enc_arg_check_function(env, ii, encfn)

    
