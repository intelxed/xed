#!/usr/bin/env python
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

import genutil
import read_xed_db
import gen_setup

gpr_nt_widths_dict = {}
# list indexed by OSZ (o16,o32,o64)
gpr_nt_widths_dict['GPRv_SB'] = [16,32,64]
gpr_nt_widths_dict['GPRv_R'] = [16,32,64]
gpr_nt_widths_dict['GPRv_B'] = [16,32,64]
gpr_nt_widths_dict['GPRz_R'] = [16,32,32]
gpr_nt_widths_dict['GPRz_B'] = [16,32,32]
gpr_nt_widths_dict['GPRy_R'] = [32,32,64]
gpr_nt_widths_dict['GPRy_B'] = [32,32,64]

gpr_nt_widths_dict['GPR8_R'] = [8,8,8]
gpr_nt_widths_dict['GPR8_B'] = [8,8,8]
gpr_nt_widths_dict['GPR8_SB'] = [8,8,8]

gpr_nt_widths_dict['GPR16_R'] = [16,16,16]
gpr_nt_widths_dict['GPR16_B'] = [16,16,16]


gpr_nt_widths_dict['GPR32_B'] = [32,32,32]
gpr_nt_widths_dict['GPR32_R'] = [32,32,32]
gpr_nt_widths_dict['GPR64_B'] = [64,64,64]
gpr_nt_widths_dict['GPR64_R'] = [64,64,64]
gpr_nt_widths_dict['VGPR32_B'] = [32,32,32]
gpr_nt_widths_dict['VGPR32_R'] = [32,32,32]
gpr_nt_widths_dict['VGPR32_N'] = [32,32,32]
gpr_nt_widths_dict['VGPRy_N'] = [32,32,64]
gpr_nt_widths_dict['VGPR64_B'] = [64,64,64]
gpr_nt_widths_dict['VGPR64_R'] = [64,64,64]
gpr_nt_widths_dict['VGPR64_N'] = [64,64,64]

gpr_nt_widths_dict['A_GPR_R' ] = 'ASZ-SIZED-GPR' # SPECIAL
gpr_nt_widths_dict['A_GPR_B' ] = 'ASZ-SIZED-GPR' 

# everything else is not typically used in scalable way. look at other
# operand.
oc2_widths_dict = {}
oc2_widths_dict['v'] = [16,32,64]
oc2_widths_dict['y'] = [32,32,64]
oc2_widths_dict['z'] = [16,32,32]
oc2_widths_dict['b'] = [8,8,8]
oc2_widths_dict['w'] = [16,16,16]
oc2_widths_dict['d'] = [32,32,32]
oc2_widths_dict['q'] = [64,64,64]

var_base = 'base'
arg_base = 'xed_reg_enum_t ' + var_base
var_index = 'index'
arg_index = 'xed_reg_enum_t ' + var_index
var_scale = 'scale'
arg_index = 'xed_uint_t ' + var_scale

var_disp8 = 'disp8'
arg_disp8 = 'xed_int8_t ' + var_disp8

var_disp16 = 'disp16'
arg_disp16 = 'xed_int16_t ' + var_disp16

var_disp32 = 'disp32'
arg_disp32 = 'xed_int32_t ' + var_disp32

var_reg0 = 'reg0'
arg_reg0 = 'xed_reg_enum_t ' + var_reg0
var_reg1 = 'reg1'
arg_reg1 = 'xed_reg_enum_t ' + var_reg1
var_reg2 = 'reg2'
arg_reg2 = 'xed_reg_enum_t ' + var_reg2
var_reg3 = 'reg3'
arg_reg3 = 'xed_reg_enum_t ' + var_reg3
var_reg4 = 'reg4'
arg_reg4 = 'xed_reg_enum_t ' + var_reg4

var_rcsae = 'rcsae'
arg_rcase = 'xed_uint_t ' + var_rcsae

var_imm8 = 'imm8'
arg_imm8 = 'xed_uint8_t ' + var_imm8
var_imm8_2 = 'imm8_2'
arg_imm8_2 = 'xed_uint8_t ' + var_imm8_2
var_imm16 = 'imm16'
arg_imm16 = 'xed_uint16_t ' + var_imm16


def _dump_fields(x):
    for fld in sorted(x.__dict__.keys()):
        print("{}: {}".format(fld,getattr(x,fld)))
    print("\n\n")



def _create_enc_fn(agi, ii):
    s = [ii.iclass.lower()]
    s.append(ii.space)
    s.append(hex(ii.opcode_base10))
    s.append(str(ii.map))
    #print('XA: {}'.format(" ".join(s)))
    # _dump_fields(ii)

    modes = ['m16','m32','m64']
    if ii.mode_restriction == 'unspecified':
        mode = 'mall'
    elif ii.mode_restriction == 'not64':
        mode = 'mnot64'
    else:
        mode = modes[ii.mode_restriction]
    s.append(mode)

    s.append(ii.easz)
    s.append(ii.eosz)

    ii.write_masking = False
    ii.write_masking_notk0 = False
    ii.write_masking_merging = False # if true, no zeroing allowed
    
    for op in ii.parsed_operands:
        if op.lookupfn_name == 'MASK1':
            ii.write_masking = True
        elif op.lookupfn_name == 'MASKNOT0':
            ii.write_masking = True
            ii.write_masking_notk0 = True
    
    if ii.write_masking:
        if 'ZEROING=0' in ii.pattern:
            ii.write_masking_merging = True
            
        s.append('masking')
        if ii.write_masking_merging:
            s.append('nz')
        if ii.write_masking_notk0:
            s.append('!k0')


    for op in ii.parsed_operands:
        # handled write masking above
        if op.lookupfn_name == 'MASK1' or op.lookupfn_name == 'MASKNOT0':
            continue

        if op.visibility != 'SUPPRESSED':
            s.append(op.name)
            if op.oc2:
                s[-1] = s[-1] + '-' + op.oc2
            #if op.xtype:
            #    s[-1] = s[-1] + '-X:' + op.xtype

            if op.lookupfn_name:
                s.append('({})'.format(op.lookupfn_name))
            elif op.bits and op.bits != '1':
                s.append('[{}]'.format(op.bits))
            if op.name == 'MEM0':
                #if op.oc2:
                #    s[-1] = s[-1] + '-' + op.oc2
                #if op.xtype:
                #    s[-1] = s[-1] + '-X:' + op.xtype
                if 'UISA_VMODRM_XMM()' in ii.pattern:
                    s[-1] = s[-1] + '-uvx'
                elif 'UISA_VMODRM_YMM()' in ii.pattern:
                    s[-1] = s[-1] + '-uvy'
                elif 'UISA_VMODRM_ZMM()' in ii.pattern:
                    s[-1] = s[-1] + '-uvz'
                elif 'VMODRM_XMM()' in ii.pattern:
                    s[-1] = s[-1] + '-vx'
                elif 'VMODRM_YMM()' in ii.pattern:
                    s[-1] = s[-1] + '-nvy'
                
    print("XX {}".format(" ".join(s)))

# used for making file paths for xed db reader
class dummy_t(object):
    def __init__(self):
        pass

def work(agi):

    args = dummy_t()
    args.prefix = os.path.join(agi.common.options.gendir,'dgen')
    gen_setup.make_paths(args)
    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename,
                                     args.cpuid_filename)

    for ii in xeddb.recs:
        _create_enc_fn(agi,ii)
            
