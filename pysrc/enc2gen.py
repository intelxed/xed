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

# This is the "fast" encoder generator known as "enc2".

from __future__ import print_function
import os
import sys
import copy
import re
import argparse
import itertools
import collections
import traceback

import find_dir # finds mbuild and adds it to sys.path
import mbuild

import codegen
import read_xed_db
import gen_setup
import enc2test
import enc2argcheck

from enc2common import *

def get_fname(depth=1): # default is current caller
    #return sys._getframe(depth).f_code.co_name
    return traceback.extract_stack(None, depth+1)[0][2]


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

enc_fn_prefix = "xed_enc"

arg_reg_type = 'xed_reg_enum_t '

var_base = 'base'
arg_base = 'xed_reg_enum_t ' + var_base
var_index = 'index'
arg_index = 'xed_reg_enum_t ' + var_index

var_indexx = 'index_xmm'
arg_indexx = 'xed_reg_enum_t ' + var_indexx
var_indexy = 'index_ymm'
arg_indexy = 'xed_reg_enum_t ' + var_indexy
var_indexz = 'index_zmm'
arg_indexz = 'xed_reg_enum_t ' + var_indexz
var_vsib_index_dct = { 'xmm': var_indexx,
                       'ymm': var_indexy,
                       'zmm': var_indexz }


var_scale = 'scale'
arg_scale = 'xed_uint_t ' + var_scale

var_disp8 = 'disp8'
arg_disp8 = 'xed_int8_t ' + var_disp8

var_disp16 = 'disp16'
arg_disp16 = 'xed_int16_t ' + var_disp16

var_disp32 = 'disp32'
arg_disp32 = 'xed_int32_t ' + var_disp32

var_disp64 = 'disp64'
arg_disp64 = 'xed_int64_t ' + var_disp64

var_request = 'r'
arg_request = 'xed_enc2_req_t* ' + var_request

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

var_kmask = 'kmask'
arg_kmask = 'xed_reg_enum_t ' + var_kmask
var_kreg0 = 'kreg0'
arg_kreg0 = 'xed_reg_enum_t ' + var_kreg0
var_kreg1 = 'kreg1'
arg_kreg1 = 'xed_reg_enum_t ' + var_kreg1
var_kreg2 = 'kreg2'
arg_kreg2 = 'xed_reg_enum_t ' + var_kreg2

var_rcsae = 'rcsae'
arg_rcsae = 'xed_uint_t ' + var_rcsae
var_zeroing = 'zeroing'
arg_zeroing = 'xed_bool_t ' + var_zeroing

var_imm8 = 'imm8'
arg_imm8 = 'xed_uint8_t ' + var_imm8
var_imm8_2 = 'imm8_2'
arg_imm8_2 = 'xed_uint8_t ' + var_imm8_2
var_imm16 = 'imm16'
arg_imm16 = 'xed_uint16_t ' + var_imm16
var_imm16_2 = 'imm16_2'
arg_imm16_2 = 'xed_uint16_t ' + var_imm16_2


var_imm32 = 'imm32'
arg_imm32 = 'xed_uint32_t ' + var_imm32
var_imm64 = 'imm64'
arg_imm64 = 'xed_uint64_t ' + var_imm64

def special_index_cases(ii):
    if ii.avx512_vsib or ii.avx_vsib or ii.sibmem:
        return True
    return False

# if I wanted to prune the number of memory variants, I could set
# index_vals to just [True]. 
index_vals = [False,True]
def get_index_vals(ii):
    global index_vals
    if special_index_cases(ii):
        return [True]
    return index_vals

gprv_index_names = { 16:'gpr16_index', 32:'gpr32_index', 64:'gpr64_index'}
gprv_names = { 8:'gpr8', 16:'gpr16', 32:'gpr32', 64:'gpr64'} # added gpr8 for convenience
gpry_names = { 16:'gpr32', 32:'gpr32', 64:'gpr64'}
gprz_names = { 16:'gpr16', 32:'gpr32', 64:'gpr32'}

vl2names = { '128':'xmm', '256':'ymm', '512':'zmm',
             'LIG':'xmm', 'LLIG':'xmm' }
vl2func_names = { '128':'128', '256':'256', '512':'512',
                  'LIG':'', 'LLIG':'' }

bits_to_widths = {8:'b', 16:'w', 32:'d', 64:'q' }

arg_immz_dct = { 0: '', 8: arg_imm8, 16: arg_imm16, 32: arg_imm32, 64: arg_imm32 }
var_immz_dct = { 0: '', 8: var_imm8, 16: var_imm16, 32: var_imm32, 64: var_imm32 }
arg_immz_meta = { 0: '', 8:'int8', 16: 'int16', 32: 'int32', 64: 'int32' }

arg_immv_dct = { 0: '', 8: arg_imm8, 16: arg_imm16, 32: arg_imm32, 64: arg_imm64 }
var_immv_dct = { 0: '', 8: var_imm8, 16: var_imm16, 32: var_imm32, 64: var_imm64 }
arg_immv_meta = { 0: '', 8:'int8', 16: 'int16', 32: 'int32', 64: 'int64' }

arg_dispv = { 8: arg_disp8, 16: arg_disp16, 32: arg_disp32, 64: arg_disp64 }  # index by dispsz
var_dispv = { 8: arg_disp8, 16:var_disp16, 32:var_disp32, 64:var_disp64 }
arg_dispz = { 16: arg_disp16, 32: arg_disp32, 64: arg_disp32 }  # index by dispsz
tag_dispz = { 16: 'int16', 32: 'int32', 64: 'int32' }  # index by dispsz
var_dispz = { 16:var_disp16, 32:var_disp32, 64:var_disp32 }
arg_dispv_meta = { 8:'int8', 16:'int16', 32:'int32', 64:'int64' }

widths_to_bits = {'b':8, 'w':16, 'd':32, 'q':64 }
widths_to_bits_y = {'w':32, 'd':32, 'q':64 }
widths_to_bits_z = {'w':16, 'd':32, 'q':32 }

# if I cut the number of displacements by removing 0, I would have to
# add some sort of gizmo to omit the displacent if the value of the
# displacement is 0, but then that creates a problem for people who
# what zero displacements for patching.  I could also consider merging
# disp8 and disp16/32 and then chose the smallest displacement that
# fits, but that also takes away control from the user.
def get_dispsz_list(env):
    return  [0,8,16] if env.asz == 16 else [0,8,32]
def get_osz_list(env):
    return  [16,32,64] if env.mode == 64 else [16,32]

_modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
def get_modval(dispsz):
    global _modvals
    return _modvals[dispsz]


def _gen_opnds(ii): # generator
    # filter out write-mask operands and suppressed operands
    for op in ii.parsed_operands:
        if op.lookupfn_name in [ 'MASK1', 'MASKNOT0']:
            continue
        if op.visibility == 'SUPPRESSED':
            continue
        if op.name == 'BCAST':
            continue
        yield op

        
def _gen_opnds_nomem(ii): # generator
    # filter out write-mask operands and suppressed operands and memops
    for op in ii.parsed_operands:
        if op.name.startswith('MEM'):
            continue
        if op.lookupfn_name == 'MASK1':
            continue
        if op.lookupfn_name == 'MASKNOT0':
            continue
        if op.visibility == 'SUPPRESSED':
            continue
        if op.name == 'BCAST':
            continue
        yield op
def first_opnd(ii):
    op = next(_gen_opnds(ii))
    return op
def first_opnd_nonmem(ii):
    op = next(_gen_opnds_nomem(ii))
    return op

#def second_opnd(ii):
#    for i,op in enumerate(_gen_opnds(ii)):
#        if i==1:
#            return op

def op_mask_reg(op):
    return op_luf_start(op,'MASK')
def op_masknot0(op):
    return op_luf_start(op,'MASKNOT0')
    
        
def op_scalable_v(op):
    if op_luf_start(op,'GPRv'):
        return True
    if op.oc2 == 'v':
        return True
    return False
def op_gpr8(op):
    if op_luf_start(op,'GPR8'):
        return True
    if op_reg(op) and op.oc2 == 'b':
        return True
    return False
def op_gpr16(op):
    if op_luf_start(op,'GPR16'):
        return True
    if op_reg(op) and op.oc2 == 'w':
        return True
    return False

def op_seg(op):
    return op_luf_start(op,'SEG')
def op_cr(op):
    return op_luf_start(op,'CR')
def op_dr(op):
    return op_luf_start(op,'DR')
def op_gprz(op):
    return op_luf_start(op,'GPRz')
def op_gprv(op):
    return op_luf_start(op,'GPRv')
def op_gpry(op):
    return op_luf_start(op,'GPRy')
def op_vgpr32(op):
    return op_luf_start(op,'VGPR32')
def op_vgpr64(op):
    return op_luf_start(op,'VGPR64')
def op_gpr32(op):
    return op_luf_start(op,'GPR32')
def op_gpr64(op):
    return op_luf_start(op,'GPR64')

def op_ptr(op):
    if 'PTR' in op.name:
        return True
    return False
def op_reg(op):
    if 'REG' in op.name:
        return True
    return False
def op_mem(op):
    if 'MEM' in op.name:
        return True
    return False

def op_agen(op): # LEA
    if 'AGEN' in op.name:
        return True
    return False
def op_tmm(op):
    if op.lookupfn_name:
        if 'TMM' in op.lookupfn_name:
            return True
    return False
def op_xmm(op):
    if op.lookupfn_name:
        if 'XMM' in op.lookupfn_name:
            return True
    return False
def op_ymm(op):
    if op.lookupfn_name:
        if 'YMM' in op.lookupfn_name:
            return True
    return False
def op_zmm(op):
    if op.lookupfn_name:
        if 'ZMM' in op.lookupfn_name:
            return True
    return False
def op_mmx(op):
    if op.lookupfn_name:
        if 'MMX' in op.lookupfn_name:
            return True
    return False
def op_x87(op):
    if op.lookupfn_name:
        if 'X87' in op.lookupfn_name:
            return True
    elif (op.name.startswith('REG') and
          op.lookupfn_name == None and
          re.match(r'XED_REG_ST[0-7]',op.bits) ):
        return True
    return False

def one_scalable_gpr_and_one_mem(ii): # allows optional imm8,immz, one implicit specific reg
    implicit,n,r,i = 0,0,0,0
    for op in _gen_opnds(ii):
        if op_mem(op):
            n += 1
        elif op_reg(op) and op_implicit_specific_reg(op):
            implicit += 1
        elif op_gprv(op): #or op_gpry(op):
            r += 1
        elif op_imm8(op) or op_immz(op):
            i += 1
        else:
            return False
    return n==1 and r==1 and i<=1 and implicit <= 1

    
def one_gpr_reg_one_mem_scalable(ii):
    n,r = 0,0
    for op in _gen_opnds(ii):
        if op_agen(op) or (op_mem(op) and op.oc2 in ['v']):
            n += 1
        elif op_gprv(op):
            r += 1
        else:
            return False
    return n==1 and r==1
def one_gpr_reg_one_mem_zp(ii):
    n,r = 0,0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['p','z']:
            n += 1
        elif op_gprz(op):
            r += 1
        else:
            return False
    return n==1 and r==1

def one_gpr_reg_one_mem_fixed(ii):
    n,r = 0,0
    for op in _gen_opnds(ii):
        # FIXME: sloppy could bemixing b and d operands, for example
        if op_mem(op) and op.oc2 in ['b', 'w', 'd', 'q','dq']:
            n += 1
        elif op_gpr8(op) or op_gpr16(op) or op_gpr32(op) or op_gpr64(op):
            r += 1
        else:
            return False
    return n==1 and r==1

simd_widths = ['b','w','xud', 'qq', 'dq', 'q', 'ps','pd', 'ss', 'sd', 'd', 'm384', 'm512', 'xuq', 'zd']

def one_xmm_reg_one_mem_fixed_opti8(ii): # allows gpr32, gpr64, mmx too
    global simd_widths
    i,r,n=0,0,0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in simd_widths:
            n = n + 1
        elif (op_xmm(op) or op_mmx(op) or op_gpr32(op) or op_gpr64(op)) and op.oc2 in simd_widths:
            r = r + 1
        elif op_imm8(op):
            i = i + 1
        else:
            return False
    return n==1 and r==1 and i<=1

def one_mem_common(ii): # b,w,d,q,dq, v, y, etc.
    n = 0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b','w','d','q','dq','v', 'y', 's',
                                     'mem14','mem28','mem94','mem108',
                                     'mxsave', 'mprefetch', 
                                     'mem16', 's64', 'mfpxenv',
                                     'm384', 'm512' ]:
            n = n + 1
        else:
            return False
    return n==1

def is_gather_prefetch(ii):
    if 'GATHER' in ii.attributes:
        if 'PREFETCH' in ii.attributes:
            return True
    return False

def is_far_xfer_mem(ii):
    if 'FAR_XFER' in ii.attributes:
        for op in _gen_opnds(ii):
            if op_mem(op) and op.oc2 in ['p','p2']:
                return True
    return False
def is_far_xfer_nonmem(ii):
    p,i=0,0
    if 'FAR_XFER' in ii.attributes:
        for op in _gen_opnds(ii):
            if op_ptr(op):
                p =+ 1
            elif op_imm16(op):
                i += 1
            else:
                return False
        return True
    return i==1 and p==1
            

def op_reg_invalid(op):
    if op.bits and op.bits != '1':
        if op.bits == 'XED_REG_INVALID':
            return True
    return False

def one_mem_common_one_implicit_gpr(ii): 
    '''memop can be b,w,d,q,dq, v, y, etc.  with
       GPR8 or GPRv'''
    n,g = 0,0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b','w','d','q','dq','v', 'y',
                                     'mem14','mem28','mem94','mem108',
                                     'mxsave', 'mprefetch' ]:
            n += 1
        elif op_reg(op) and op_implicit(op) and not op_reg_invalid(op):
            # FIXME: could improve the accuracy by enforcing GPR. but
            #        not sure if that is strictly necessary. Encoding works...
            g += 1
        else:
            return False
    return n==1 and g==1



def one_mem_fixed_imm8(ii): # b,w,d,q,dq, etc.
    n = 0
    i = 0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b','w','d','q','dq', 'v', 'y',
                                     'mem14','mem28','mem94','mem108']:
            n = n + 1
        elif op_imm8(op):
            i = i + 1
        else:
            return False
    return n==1 and i==1

def one_mem_fixed_immz(ii): # b,w,d,q,dq, etc.
    n = 0
    i = 0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b','w','d','q','dq', 'v', 'y',
                                     'mem14','mem28','mem94','mem108']:
            n = n + 1
        elif op_immz(op):
            i = i + 1
        else:
            return False
    return n==1 and i==1
    
def two_gpr_one_scalable_one_fixed(ii):
    f,v = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_scalable_v(op):
            v += 1
        elif op_reg(op) and (op_gpr8(op) or op_gpr16(op) or op_gpr32(op)):
            f += 1
        else:
            return False
    return v==1 and f==1
    
def two_scalable_regs(ii): # allow optional imm8, immz, allow one implicit GPR
    n,i,implicit = 0,0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_scalable_v(op):
            n += 1
        elif op_reg(op) and op_implicit_specific_reg(op):
            implicit += 1
        elif op_imm8(op) or op_immz(op):
            i += 1
        else:
            return False
    return n==2 and i <= 1 and implicit <= 1
def op_implicit(op):
    return op.visibility == 'IMPLICIT'
def op_implicit_or_suppressed(op):
    return op.visibility in ['IMPLICIT','SUPPRESSED']
    
def one_x87_reg(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_x87(op) and not op_implicit(op):
            n = n + 1
        else:
            return False
    return n==1

def two_x87_reg(ii): # one implicit
    n = 0
    implicit = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_x87(op):
            n = n + 1
            if op_implicit(op):
                implicit = implicit + 1
        else:
            return False
        
    return n==2 and implicit == 1

def one_x87_implicit_reg_one_memop(ii): 
    mem,implicit_reg = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_x87(op):
            if op_implicit(op):
                implicit_reg = implicit_reg + 1
            else:
                return False
        elif op_mem(op):
            mem = mem + 1
        else:
            return False
        
    return mem==1 and implicit_reg==1


def zero_operands(ii):# allow all implicit regs
    n = 0
    for op in _gen_opnds(ii):
        if op_implicit(op):
            continue
        n = n + 1
    return n == 0

def one_implicit_gpr_imm8(ii):
    '''this allows implicit operands'''
    n = 0
    for op in _gen_opnds(ii):
        if op_imm8(op):
            n = n + 1
        elif op_implicit(op):
            continue
        else:
            return False
    return n == 1

def op_implicit_specific_reg(op):
    if op.name.startswith('REG'):
        if op.bits and op.bits.startswith('XED_REG_'):
            return True
    return False


def one_gprv_one_implicit(ii):  
    n,implicit = 0,0
    for op in _gen_opnds(ii):
        if op_gprv(op):
            n += 1
        elif op_implicit_specific_reg(op):
            implicit += 1
        else:
            return False
    return n == 1 and implicit == 1

def one_gpr8_one_implicit(ii):  
    n,implicit = 0,0
    for op in _gen_opnds(ii):
        if op_gpr8(op):
            n += 1
        elif op_implicit_specific_reg(op):
            implicit += 1
        else:
            return False
    return n == 1 and implicit == 1


def one_nonmem_operand(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_mem(op):
            return False
        if op_implicit_or_suppressed(op): # for RCL/ROR etc with implicit imm8
            continue
        n = n + 1
    return n == 1

    
def two_gpr8_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_gpr8(op):
            n = n + 1
        else:
            return False
    return n==2


def op_immz(op):
    if op.name == 'IMM0':
        if op.oc2 == 'z':
            return True
    return False
def op_immv(op):
    if op.name == 'IMM0':
        if op.oc2 == 'v':
            return True
    return False
def op_imm8(op):
    if op.name == 'IMM0':
        if op.oc2 == 'b':
            if op_implicit_or_suppressed(op):
                return False
            return True
    return False

def op_imm16(op):
    if op.name == 'IMM0':
        if op.oc2 == 'w':
            return True
    return False
def op_imm8_2(op):
    if op.name == 'IMM1':
        if op.oc2 == 'b':
            return True
    return False

def one_mmx_reg_imm8(ii):
    n = 0
    for i,op in enumerate(_gen_opnds(ii)):
        if op_reg(op) and op_mmx(op):
            n = n + 1
        elif i == 1 and op_imm8(op):
            continue
        else:
            return False
    return n==1
def one_xmm_reg_imm8(ii): # also allows SSE4 2-imm8 instr
    i,j,n=0,0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            n += 1
        elif op_imm8(op):
            i += 1
        elif op_imm8_2(op):
            j += 1
        else:
            return False
    return n==1 and i==1 and j<=1
    
def two_xmm_regs_imm8(ii):
    n = 0
    for i,op in enumerate(_gen_opnds(ii)):
        if op_reg(op) and op_xmm(op):
            n = n + 1
        elif i == 2 and op_imm8(op):
            continue
        else:
            return False
    return n==2

    
def gen_osz_list(mode, osz_list):
    """skip osz 64 outside of 64b mode"""
    for osz in osz_list:
        if mode != 64 and osz == 64:
            continue
        yield osz
        
def modrm_reg_first_operand(ii):
    op = first_opnd(ii)
    if op.lookupfn_name:
        if op.lookupfn_name.endswith('_R'):
            return True
        if op.lookupfn_name.startswith('SEG'):
            return True
    return False

def emit_required_legacy_prefixes(ii,fo):
    if ii.iclass.endswith('_LOCK'):
        fo.add_code_eol('emit(r,0xF0)')
    if ii.f2_required:
        fo.add_code_eol('emit(r,0xF2)', 'required by instr')
    if ii.f3_required:
        fo.add_code_eol('emit(r,0xF3)', 'required by instr')
    if ii.osz_required:
        fo.add_code_eol('emit(r,0x66)', 'required by instr')
        
def emit_67_prefix(fo):
    fo.add_code_eol('emit(r,0x67)', 'change EASZ')
        
def emit_required_legacy_map_escapes(ii,fo):
    if ii.map == 1:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 1')
    elif ii.map == 2:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 2')
        fo.add_code_eol('emit(r,0x38)', 'escape map 2')
    elif ii.map == 3:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 3')
        fo.add_code_eol('emit(r,0x3A)', 'escape map 3')
    elif ii.amd_3dnow_opcode:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 3dNOW')
        fo.add_code_eol('emit(r,0x0F)', 'escape map 3dNOW')

        
def get_implicit_operand_name(op):
    if op_implicit(op):
        if op.name.startswith('REG'):
            if op.bits and op.bits.startswith('XED_REG_'):
                reg_name = re.sub('XED_REG_','',op.bits).lower()
                return reg_name
            elif op.lookupfn_name:
                ntluf = op.lookupfn_name
                return ntluf
        elif op.name == 'IMM0' and op.type == 'imm_const' and op.bits == '1':
            return 'one'
        die("Unhandled implicit operand {}".format(op))
    return None
        
def _gather_implicit_regs(ii):
    names = []
    for op in _gen_opnds(ii):
        nm = get_implicit_operand_name(op)
        if nm:
            names.append(nm)
    return names

def _implicit_reg_names(ii):
    extra_names = _gather_implicit_regs(ii)
    if extra_names:
        extra_names = '_' + '_'.join( extra_names )
    else:
        extra_names = ''
    return extra_names

def emit_vex_prefix(env, ii, fo, register_only=False):
    if ii.map == 1 and ii.rexw_prefix != '1':
        # if any of x,b are set, need c4, else can use c5
        
        # performance: we know statically if something is register
        #        only.  In which case, we can avoid testing rexx.
        if env.mode == 64:
            if register_only:
                fo.add_code('if  (get_rexb(r))')
            else:
                fo.add_code('if  (get_rexx(r) || get_rexb(r))')
            fo.add_code_eol('    emit_vex_c4(r)')
            fo.add_code('else')
            fo.add_code_eol('    emit_vex_c5(r)')
        else:
            fo.add_code_eol('emit_vex_c5(r)') 
    else:
        fo.add_code_eol('emit_vex_c4(r)')
    
def emit_opcode(ii,fo):
    if ii.amd_3dnow_opcode:
        return # handled later. See add_enc_func()

    opcode = "0x{:02X}".format(ii.opcode_base10)
    fo.add_code_eol('emit(r,{})'.format(opcode),
                    'opcode')
    

def create_modrm_byte(ii,fo):
    mod,reg,rm = 0,0,0
    modrm_required = False
    if ii.mod_required:
        if ii.mod_required in ['unspecified']:
            pass
        elif ii.mod_required in ['00/01/10']:
            modrm_requried = True
        else:
            mod = ii.mod_required
            modrm_required = True
    if ii.reg_required:
        if ii.reg_required in ['unspecified']:
            pass
        else:
            reg = ii.reg_required
            modrm_required = True
    if ii.rm_required:
        if ii.rm_required in ['unspecified']:
            pass
        else:
            rm = ii.rm_required
            modrm_required = True
    if modrm_required:
        modrm = (mod << 6) | (reg<<3) | rm
        fo.add_comment('MODRM = 0x{:02x}'.format(modrm))
        if mod: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))
        if reg: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(reg))
        if rm: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(rm))
    return modrm_required

numbered_function_creators = collections.defaultdict(int)
def dump_numbered_function_creators():
    global numbered_function_creators
    for k,val in sorted(numbered_function_creators.items(),
                        key=lambda x: x[1]):
        print("NUMBERED FN CREATORS: {:5d} {:30s}".format(val,k))
        
numbered_functions = 0
def make_function_object(env, ii, fname, return_value='void', asz=None):
    '''Create function object. Augment function name for conventions '''
    global numbered_functions
    global numbered_function_creators
    
    if 'AMDONLY' in ii.attributes:
        fname += '_amd'
        
    if ii.space == 'evex':
        fname += '_e'

    # Distinguish the 16/32b mode register-only functions to avoid
    # name collisions.  The stuff references memory has an
    # "_a"+env.asz suffix. The non-memory stuff can still have name
    # collisions. To avoid those collisions, I append _md16 or _md32
    # to the function names.
    if asz:
        fname += '_a{}'.format(asz)
    elif env.mode in [16,32]:
        fname += '_md{}'.format(env.mode)
        
    if fname in env.function_names:
        numbered_functions += 1
        t = env.function_names[fname] + 1
        env.function_names[fname] = t
        fname = '{}_vr{}'.format(fname,t)
        numbered_function_creators[get_fname(2)] += 1
        #msge("Numbered function name for: {} from {}".format(fname, get_fname(2)))
    else:
        env.function_names[fname] = 0

    fo = codegen.function_object_t(fname, return_value, dll_export=True)
    if ii.iform:
        fo.add_comment(ii.iform)
    return fo


def make_opnd_signature(env, ii, using_width=None, broadcasting=False, special_xchg=False):
    '''This is the heart of the naming conventions for the encode
       functions. If using_width is present, it is used for GPRv and
       GPRy operations to specify a width.    '''
    global vl2func_names, widths_to_bits, widths_to_bits_y, widths_to_bits_z

    def _translate_rax_name(w):
        rax_names = { 16: 'ax', 32:'eax', 64:'rax' }
        osz = _translate_width_int(w)
        return rax_names[osz]
    
    def _translate_eax_name(w):
        eax_names = { 16: 'ax', 32:'eax', 64:'eax' }
        osz = _translate_width_int(w)
        return eax_names[osz]
    
    def _translate_r8_name(w):
        # uppercase to try to differentiate r8 (generic 8b reg) from R8 64b reg
        r8_names = { 16: 'R8W', 32:'R8D', 64:'R8' }
        osz = _translate_width_int(w)
        return r8_names[osz]

    def _translate_width_int(w):
        if w in [8,16,32,64]:
            return w
        return widths_to_bits[w]
    
    def _translate_width(w):
        return str(_translate_width_int(w))
    
    def _translate_width_y(w):
        if w in [32,64]:
            return str(w)
        elif w == 16:
            return '32'
        return str(widths_to_bits_y[w])
    
    def _translate_width_z(w):
        if w in [16,32]:
            return str(w)
        elif w == 64:
            return '32'
        return str(widths_to_bits_z[w])

    def _convert_to_osz(w):
        if w in [16,32,64]:
            return w
        elif w in widths_to_bits:
            return widths_to_bits[w]
        else:
            die("Cannot convert {}".format(w) )
    
    s = []
    for op in _gen_opnds(ii):
        if op_implicit(op):
            nm = get_implicit_operand_name(op)
            if nm in ['OrAX'] and using_width:
                s.append( _translate_rax_name(using_width) )
            elif nm in ['OeAX'] and using_width:
                s.append( _translate_eax_name(using_width) )
            else:
                s.append(nm)
            continue
        
        # for the modrm-less MOV instr
        if op.name.startswith('BASE'):
            continue
        if op.name.startswith('INDEX'):
            continue

        if op_tmm(op):
            s.append('t')
        elif op_xmm(op):
            s.append('x')
        elif op_ymm(op):
            s.append('y')
        elif op_zmm(op):
            s.append('z')
        elif op_mask_reg(op):
            s.append('k')
        elif op_vgpr32(op):
            s.append('r32')
        elif op_vgpr64(op):
            s.append('r64') #FIXME something else
        elif op_gpr8(op):
            s.append('r8')
        elif op_gpr16(op):
            s.append('r16')
        elif op_gpr32(op):
            s.append('r32')
        elif op_gpr64(op):
            s.append('r64') #FIXME something else
        elif op_gprv(op):
            if special_xchg:
                s.append(_translate_r8_name(using_width))
            else:
                s.append('r' + _translate_width(using_width))
        elif op_gprz(op):
            s.append('r' + _translate_width_z(using_width))
        elif op_gpry(op):
            s.append('r' + _translate_width_y(using_width))
        elif op_agen(op):
            s.append('m') # somewhat of a misnomer
        elif op_mem(op):
            if op.oc2 == 'b':
                s.append('m8')
            elif op.oc2 == 'w':
                s.append('m16')
            elif op.oc2 == 'd':
                s.append('m32')
            elif op.oc2 == 'q':
                s.append('m64')
            elif op.oc2 == 'ptr': # sibmem
                s.append('mptr')
            #elif op.oc2 == 'dq': don't really want to start decorating the wider memops
            #    s.append('m128')
            elif op.oc2 == 'v' and using_width:
                s.append('m' + _translate_width(using_width))
            elif op.oc2 == 'y' and using_width:
                s.append('m' + _translate_width_y(using_width))
            elif op.oc2 == 'z' and using_width:
                s.append('m' + _translate_width_z(using_width))
            else:
                osz = _convert_to_osz(using_width) if using_width else 0
                if op.oc2 == 'tv' or op.oc2.startswith('tm'):
                    bits =  'tv'
                elif op.oc2 == 'vv':
                    # read_xed_db figures out the memop width for
                    # no-broadcast and broadcasting cases for EVEX
                    # memops. 
                    if broadcasting:
                        bits = ii.element_size
                    else:
                        bits = ii.memop_width 
                else:
                    bits = env.mem_bits(op.oc2, osz)
                    if bits == '0':
                        die("OC2FAIL: {}: oc2 {} osz {} -> {}".format(ii.iclass, op.oc2, osz, bits))
                s.append('m{}'.format(bits))
                
            # add the index reg width for sparse ops (scatter,gather)
            if ii.avx_vsib:
                s.append(ii.avx_vsib[0])
            if ii.avx512_vsib:
                s.append(ii.avx512_vsib[0])
        elif op_imm8(op):
            s.append('i8')
        elif op_immz(op):
            if using_width:
                s.append('i' + _translate_width_z(using_width))
            else:
                s.append('i')
        elif op_immv(op):
            if using_width:
                s.append('i' + _translate_width(using_width))
            else:
                s.append('i')
        elif op_imm16(op):
            s.append('i16')
        elif op_imm8_2(op):
            s.append('i') #FIXME something else?
        elif op_x87(op):
            s.append('sti') # FIXME: or 'x87'?
        elif op_mmx(op):
            s.append('mm') # FIXME: or "mmx"? "mm" is shorter.
        elif op_cr(op):
            s.append('cr')
        elif op_dr(op):
            s.append('dr')
        elif op_seg(op):
            s.append('seg')
        elif op.name in ['REG0','REG1'] and op_luf(op,'OrAX'):
            if using_width:
                s.append( _translate_rax_name(using_width) )
            else:
                s.append('r') # FIXME something else?
        else:
            die("Unhandled operand {}".format(op))
            
    if ii.space in ['evex']:
        if ii.rounding_form:
            s.append( 'rc' )
        elif ii.sae_form:
            s.append( 'sae' )
            
    if ii.space in ['evex','vex']:
        if 'KMASK' not in ii.attributes:
            vl =  vl2func_names[ii.vl]
            if vl:
                s.append(vl)
    return "_".join(s)



def create_legacy_one_scalable_gpr(env,ii,osz_values,oc2):  
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0, gprv_names
            
    for osz in osz_values:
        if env.mode != 64 and osz == 64:
            continue

        special_xchg = False
        if ii.partial_opcode: 
            if ii.rm_required != 'unspecified':
                if ii.iclass == 'XCHG':
                    if env.mode != 64:
                        continue
                    # This is a strange XCHG that takes r8w, r8d or r8
                    # depending on the EOSZ. REX.B is required & 64b  mode obviously.
                    # And no register specifier is required.
                    special_xchg = True
        
        opsig = make_opnd_signature(env, ii, osz, special_xchg=special_xchg)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                    ii.iclass.lower(),
                                    opsig)

        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_one_scalable_gpr")
        if special_xchg:
            fo.add_comment("special xchg using R8W/R8D/R8")
        fo.add_arg(arg_request,'req')
        
        if not special_xchg:
            fo.add_arg(arg_reg0, gprv_names[osz])
        emit_required_legacy_prefixes(ii,fo)
        
        rex_forced = False

        if special_xchg:
            fo.add_code_eol('set_rexb(r,1)')
            rex_forced  = True
            

        if env.mode == 64 and osz == 16:
            if ii.eosz == 'osznot16':
                warn("SKIPPING 16b version for: {} / {}".format(ii.iclass, ii.iform))
                continue # skip 16b version for this instruction
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 64 and osz == 32 and ii.default_64b == True:
            continue # not encodable
        elif env.mode == 64 and osz == 64 and ii.default_64b == False:
            if ii.eosz == 'osznot64':
                warn("SKIPPING 64b version for: {} / {}".format(ii.iclass, ii.iform))
                continue # skip 64b version for this instruction
            fo.add_code_eol('set_rexw(r)')
            rex_forced = True
        elif env.mode == 32 and osz == 16:
            if ii.eosz == 'osznot16':
                warn("SKIPPING 16b version for: {} / {}".format(ii.iclass, ii.iform))
                continue # skip 16b version for this instruction
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and osz == 32:
            fo.add_code_eol('emit(r,0x66)')

        if modrm_reg_first_operand(ii):
            f1, f2 = 'reg','rm'
        else:
            f1, f2 = 'rm','reg'
        # if f1 is rm then we handle partial opcodes farther down
        if f1 == 'reg' or not ii.partial_opcode:
            fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1, osz, var_reg0))
        
        if f2 == 'reg':
            if ii.reg_required != 'unspecified':
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
        else:
            if ii.rm_required != 'unspecified':
                fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))

        if ii.partial_opcode: 
            if ii.rm_required == 'unspecified':
                op = first_opnd(ii)
                if op_luf(op,'GPRv_SB'):
                    fo.add_code_eol('enc_srm_gpr{}(r,{})'.format(osz, var_reg0))
                else:
                    warn("NOT HANDLING SOME PARTIAL OPCODES YET: {} / {} / {}".format(ii.iclass, ii.iform, op))
                    ii.encoder_skipped = True
                    return
            else:
                # we have some XCHG opcodes encoded as partial register
                # instructions but have fixed RM fields.
                fo.add_code_eol('set_srm(r,{})'.format(ii.rm_required))

                #dump_fields(ii)
                #die("SHOULD NOT HAVE A VALUE FOR  PARTIAL OPCODES HERE {} / {}".format(ii.iclass, ii.iform))

        emit_rex(env, fo, rex_forced)
        emit_required_legacy_map_escapes(ii,fo)
                
        if ii.partial_opcode:
            emit_partial_opcode_variable_srm(ii,fo)
        else:
            emit_opcode(ii,fo)
            emit_modrm(fo)
        add_enc_func(ii,fo)
        
def add_enc_func(ii,fo):
    # hack to cover AMD 3DNOW wherever they are created...
    if ii.amd_3dnow_opcode:
        fo.add_code_eol('emit_u8(r,{})'.format(ii.amd_3dnow_opcode), 'amd 3dnow opcode')

    dbg(fo.emit())
    ii.encoder_functions.append(fo)

def create_legacy_one_imm_scalable(env,ii, osz_values): 
    '''just an imm-z (or IMM-v)'''
    global enc_fn_prefix, arg_request

    for osz in osz_values:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_m{}_{}_{}".format(enc_fn_prefix, env.mode, ii.iclass.lower(), opsig)
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_one_imm_scalable")
        fo.add_arg(arg_request,'req')
        add_arg_immv(fo,osz)

        if ii.has_modrm:
            die("NOT REACHED")

        if env.mode != 16 and osz == 16: 
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and osz == 32: 
            fo.add_code_eol('emit(r,0x66)')

        if not ii.default_64b:
            die("Only DF64 here for now")
        emit_required_legacy_prefixes(ii,fo)
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        emit_immv(fo,osz)
        add_enc_func(ii,fo)

def create_legacy_one_gpr_fixed(env,ii,width_bits):
    global enc_fn_prefix, arg_request, gprv_names
    opsig = make_opnd_signature(env,ii,width_bits)
    fname = "{}_{}_{}".format(enc_fn_prefix, ii.iclass.lower(), opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_gpr_fixed")
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0, gprv_names[width_bits])    
    if width_bits not in [8,16,32,64]:
        die("SHOULD NOT REACH HERE")
    
    fo.add_code_eol('set_mod(r,{})'.format(3))
    if modrm_reg_first_operand(ii):
        f1,f2 = 'reg', 'rm'
    else:
        f1,f2 = 'rm', 'reg'
    fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1,width_bits, var_reg0))
    if f2 == 'reg':
        if ii.reg_required != 'unspecified':
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    else:
        if ii.rm_required != 'unspecified':
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
            
    if env.mode == 64 and width_bits == 64 and ii.default_64b == False:
        fo.add_code_eol('set_rexw(r)')

    emit_required_legacy_prefixes(ii,fo)
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)


def create_legacy_relbr(env,ii):
    global enc_fn_prefix, arg_request
    op = first_opnd(ii)
    if op.oc2 == 'b':
        osz_values = [8]
    elif op.oc2 == 'd':
        osz_values = [32]
    elif op.oc2 == 'z':
        osz_values = [16,32]
    else:
        die("Unhandled relbr width for {}: {}".format(ii.iclass, op.oc2))
        
    for osz in osz_values:
        fname = "{}_{}_o{}".format(enc_fn_prefix, ii.iclass.lower(), osz)
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_relbr")
        fo.add_arg(arg_request,'req')
        add_arg_disp(fo,osz)

        #if ii.iclass in ['JCXZ','JECXZ','JRCXZ']:
        if ii.easz != 'aszall':
            if env.mode == 64 and ii.easz == 'a32':
                emit_67_prefix(fo)
            elif env.mode == 32 and ii.easz == 'a16':
                emit_67_prefix(fo)
            elif env.mode == 16 and ii.easz == 'a32':
                emit_67_prefix(fo)
        
        if op.oc2 == 'z':
            if env.mode in [32,64] and osz == 16:
                fo.add_code_eol('emit(r,0x66)')
            elif env.mode == 16 and osz == 32:
                fo.add_code_eol('emit(r,0x66)')

        modrm_required = create_modrm_byte(ii,fo)
        emit_required_legacy_prefixes(ii,fo)
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        if modrm_required:
            emit_modrm(fo)
        if osz == 8:
            fo.add_code_eol('emit_i8(r,{})'.format(var_disp8))
        elif osz == 16:
            fo.add_code_eol('emit_i16(r,{})'.format(var_disp16))
        elif osz == 32:
            fo.add_code_eol('emit_i32(r,{})'.format(var_disp32))
        add_enc_func(ii,fo)

def create_legacy_one_imm_fixed(env,ii):
    global enc_fn_prefix, arg_request

    fname = "{}_{}".format(enc_fn_prefix,
                           ii.iclass.lower())
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_imm_fixed")
    op = first_opnd(ii)

    fo.add_arg(arg_request,'req')
    if op.oc2 == 'b':
        fo.add_arg(arg_imm8,'int8')
    elif op.oc2 == 'w':
        fo.add_arg(arg_imm16,'int16')
    else:
        die("not handling imm width {}".format(op.oc2))
        
    modrm_required = create_modrm_byte(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    if modrm_required:
        emit_modrm(fo)
    if op.oc2 == 'b':
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    elif op.oc2 == 'w':
        fo.add_code_eol('emit_i16(r,{})'.format(var_imm16))

    add_enc_func(ii,fo)

def create_legacy_one_implicit_reg(env,ii,imm8=False):
    global enc_fn_prefix, arg_request, arg_imm8, var_imm8

    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_implicit_reg")

    fo.add_arg(arg_request,'req')
    if imm8:
        fo.add_arg(arg_imm8,'int8')
    modrm_required = create_modrm_byte(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    if modrm_required:
        emit_modrm(fo)
    if imm8:
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    add_enc_func(ii,fo)
    
    
def create_legacy_one_nonmem_opnd(env,ii):

    # GPRv, GPR8, GPR16, RELBR(b,z), implicit fixed reg, GPRv_SB, IMM0(w,b)
    op = first_opnd(ii)
    if op.name == 'RELBR':
        create_legacy_relbr(env,ii)
    elif op.name == 'IMM0':
        if op.oc2 in ['b','w','d','q']:
            create_legacy_one_imm_fixed(env,ii)
        elif op.oc2 == 'z':
            create_legacy_one_imm_scalable(env,ii,[16,32])
        else:
            warn("Need to handle {} in {}".format(
                op, "create_legacy_one_nonmem_opnd"))

    elif op.lookupfn_name:
        if op.lookupfn_name.startswith('GPRv'):
            create_legacy_one_scalable_gpr(env,ii,[16,32,64],'v')        
        elif op.lookupfn_name.startswith('GPRy'):
            create_legacy_one_scalable_gpr(env,ii,[32,64],'y')        
        elif op.lookupfn_name.startswith('GPR8'):
            create_legacy_one_gpr_fixed(env,ii,8)        
        elif op.lookupfn_name.startswith('GPR16'):
            create_legacy_one_gpr_fixed(env,ii,16)        
        elif op.lookupfn_name.startswith('GPR32'):
            create_legacy_one_gpr_fixed(env,ii,32)        
        elif op.lookupfn_name.startswith('GPR64'):
            create_legacy_one_gpr_fixed(env,ii,64)        
    elif op_implicit(op) and op.name.startswith('REG'):
        create_legacy_one_implicit_reg(env,ii,imm8=False)
    else:
        warn("Need to handle {} in {}".format(
            op, "create_legacy_one_nonmem_opnd"))


def scalable_implicit_operands(ii): 
    for op in _gen_opnds(ii):
        if op_luf(op,'OeAX'):
            return True
    return False

def create_legacy_zero_operands_scalable(env,ii):
    # FIXME 2020-06-06: IN and OUT are the only two instr with OeAX()
    # operands. I should write more general code for realizing that
    # only 16/32 are accessible.
    if ii.iclass in ['IN','OUT']:  
        osz_list = [16,32]
        
    for osz in osz_list:
        opsig = make_opnd_signature(env,ii,osz)
        if opsig:
            opsig += '_'
        fname = "{}_{}_{}o{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      opsig,
                                      osz) # FIXME:osz
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_zero_operands_scalable")
        fo.add_arg(arg_request,'req')
        modrm_required = create_modrm_byte(ii,fo)
        if env.mode in [32,64] and osz == 16:
            fo.add_code_eol('emit(r,0x66)')
        if env.mode == 16 and osz == 32:
            fo.add_code_eol('emit(r,0x66)')

        emit_required_legacy_prefixes(ii,fo)
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            die("NOT HANDLING  PARTIAL OPCODES YET in create_legacy_zero_operands_scalable")
        emit_opcode(ii,fo)
        if modrm_required:
            emit_modrm(fo)
        add_enc_func(ii,fo)

        

def create_legacy_zero_operands(env,ii): # allows all implicit too
    global enc_fn_prefix, arg_request
    
    if env.mode == 64 and ii.easz == 'a16':
        # cannot do 16b addressing in 64b mode...so skip these!
        ii.encoder_skipped = True
        return
    if scalable_implicit_operands(ii):
        create_legacy_zero_operands_scalable(env,ii)
        return
                
    opsig = make_opnd_signature(env,ii)
    if opsig:
        opsig = '_'  + opsig

    fname = "{}_{}{}".format(enc_fn_prefix,
                             ii.iclass.lower(),
                             opsig)
    if ii.easz in ['a16','a32','a64']:
        fname = fname + '_' + ii.easz
    if ii.eosz in ['o16','o32','o64']:
        fname = fname + '_' + ii.eosz
        
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_zero_operands")
    fo.add_arg(arg_request,'req')

    modrm_required = create_modrm_byte(ii,fo)
    
    # twiddle ASZ if specified
    if env.mode == 64 and ii.easz == 'a32':
        emit_67_prefix(fo)
    elif env.mode == 32 and ii.easz == 'a16':
        emit_67_prefix(fo)
    elif env.mode == 16 and ii.easz == 'a32':
        emit_67_prefix(fo)

    # twiddle OSZ
    rexw_forced=False
    if not ii.osz_required:
        if env.mode == 64 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 64 and ii.eosz == 'o32' and ii.default_64b == True:
            return # skip this one. cannot do 32b osz in 64b mode if default to 64b
        elif env.mode == 64 and ii.eosz == 'o64' and ii.default_64b == False:
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)')
        elif env.mode == 32 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif ii.eosz == 'oszall':  # works in any OSZ. no prefixes required
            pass
        elif env.mode == 64 and ii.eosz == 'osznot64':
            return
        elif ii.eosz == 'osznot16':
            pass


    emit_required_legacy_prefixes(ii,fo)
    if rexw_forced:
        fo.add_code_eol('emit_rex(r)')
    emit_required_legacy_map_escapes(ii,fo)
    if ii.partial_opcode: 
        if ii.rm_required != 'unspecified':
            emit_partial_opcode_fixed_srm(ii,fo)
        else:
            warn("NOT HANDLING SOME PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
            ii.encoder_skipped = True
            return
    else:
        emit_opcode(ii,fo)
        if modrm_required:
            emit_modrm(fo)
    add_enc_func(ii,fo)

    
def two_fixed_gprs(ii):
    width = None
    n = 0 # count of the number of GPR32 or GPR64 stuff we encounter
    c = 0 # operand count, avoid stray stuff
    for op in _gen_opnds(ii):
        c += 1
        for w in [16,32,64]:
            if op_luf_start(op,'GPR{}'.format(w)):
                if not width:
                    width = w
                    n += 1
                elif width != w:
                    return False
                else:
                    n += 1
    return width and n == 2 and c == 2

def get_gpr_opsz_code(op):
    if op_luf_start(op,'GPR8'):
        return 'rb'
    if op_luf_start(op,'GPR16'):
        return 'rw'
    if op_luf_start(op,'GPR32'):
        return 'rd'
    if op_luf_start(op,'GPR64'):
        return 'rq'
    if op_luf_start(op,'GPRv'):
        return 'rv'
    if op_luf_start(op,'GPRy'):
        return 'ry'
    else:
        die("Unhandled GPR width: {}".format(op))

def create_legacy_two_gpr_one_scalable_one_fixed(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1

    opsz_to_bits = { 'rb':8, 'rw':16, 'rd':32, 'rq':64 }
    osz_list = get_osz_list(env)
    opnds = []
    opsz_codes =[]
    for op in _gen_opnds(ii):
        opnds.append(op)
        opsz_codes.append( get_gpr_opsz_code(op) )
    for osz in osz_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  opsig)   #  "".join(opsz_codes), osz)
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_two_gpr_one_scalable_one_fixed")
        fo.add_arg(arg_request,'req')
        opnd_types = get_opnd_types(env,ii,osz)
        fo.add_arg(arg_reg0, opnd_types[0])
        fo.add_arg(arg_reg1, opnd_types[1])
        emit_required_legacy_prefixes(ii,fo)
        if not ii.osz_required:
            if osz == 16 and env.mode != 16:
                # add a 66 prefix outside of 16b mode, to create 16b osz
                fo.add_code_eol('emit(r,0x66)')
            if osz == 32 and env.mode == 16:
                # add a 66 prefix outside inside 16b mode to create 32b osz
                fo.add_code_eol('emit(r,0x66)')

        rexw_forced = cond_emit_rexw(env,ii,fo,osz)
        if modrm_reg_first_operand(ii):
            f1, f2 = 'reg','rm'
        else:
            f1, f2 = 'rm','reg'
            
        if opsz_codes[0] in ['rv','ry']:
            op0_bits = osz
        else:
            op0_bits = opsz_to_bits[opsz_codes[0]]
        fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1,osz,var_reg0))
            
        if opsz_codes[1] in ['rv','ry']:
            op1_bits = osz
        else:
            op1_bits = opsz_to_bits[opsz_codes[1]]
        fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f2,op1_bits,var_reg1))
            
        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
        else:
            emit_opcode(ii,fo)
            emit_modrm(fo)
        add_enc_func(ii,fo)


def create_legacy_two_fixed_gprs(env,ii):
    op = first_opnd(ii)
    if op_luf_start(op,'GPR16'):
        create_legacy_two_scalable_regs(env,ii,[16])
    elif op_luf_start(op,'GPR32'):
        create_legacy_two_scalable_regs(env,ii,[32])
    elif op_luf_start(op,'GPR64'):
        create_legacy_two_scalable_regs(env,ii,[64])
    else:
        die("NOT REACHED")

def create_legacy_two_scalable_regs(env, ii, osz_list):
    """Allows optional imm8,immz"""
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    global arg_imm8, var_imm8

    extra_names = _implicit_reg_names(ii) # for NOPs only (FIXME: not used!?)

    if modrm_reg_first_operand(ii):
        opnd_order = {0:'reg', 1:'rm'}
    else:
        opnd_order = {1:'reg', 0:'rm'}
    var_regs = [var_reg0, var_reg1]
    arg_regs = [arg_reg0, arg_reg1]
    
    # We have some funky NOPs that come through here, that have been
    # redefined for CET. They were two operand, but one operand is now
    # fixed via a MODRM.REG restriction and some become have MODRM.RM
    # restriction as well, and no real operands. For those funky NOPs,
    # we remove the corresponding operands. I *think* the REX.R and
    # REX.B bits don't matter.
    s = []
    fixed = {'reg':False, 'rm':False}
    nop_opsig = None
    if ii.iclass == 'NOP' and ii.iform in [ 'NOP_MEMv_GPRv_0F1C',
                                            'NOP_GPRv_GPRv_0F1E' ]:
        if ii.reg_required != 'unspecified':
            s.append('reg{}'.format(ii.reg_required))
            fixed['reg']=True

        if ii.rm_required != 'unspecified':
            s.append('rm{}'.format(ii.rm_required))
            fixed['rm']=True
        if s:
            nop_opsig = "".join(s)
            
    
    for osz in gen_osz_list(env.mode,osz_list):
        if nop_opsig:
            fname = "{}_{}{}_{}_o{}".format(enc_fn_prefix,
                                            ii.iclass.lower(),
                                            extra_names,
                                            nop_opsig,osz)
        else:
            opsig = make_opnd_signature(env,ii,osz)
            fname = "{}_{}_{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      opsig)
            
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_two_scalable_regs")
        fo.add_arg(arg_request,'req')
        opnd_types = get_opnd_types(env,ii,osz)

        for i in [0,1]:        
            if not fixed[opnd_order[i]]:
                fo.add_arg(arg_regs[i], opnd_types[i])
            
        if ii.has_imm8:
            fo.add_arg(arg_imm8,'int8')
        elif ii.has_immz:
            add_arg_immz(fo,osz)
                
        emit_required_legacy_prefixes(ii,fo)
        if not ii.osz_required:
            if osz == 16 and env.mode != 16:
                if ii.iclass not in ['ARPL']: # FIXME: make a generic property default16b  or something...
                    # add a 66 prefix outside of 16b mode, to create 16b osz
                    fo.add_code_eol('emit(r,0x66)')
            if osz == 32 and env.mode == 16:
                # add a 66 prefix outside inside 16b mode to create 32b osz
                fo.add_code_eol('emit(r,0x66)')

        rexw_forced = cond_emit_rexw(env,ii,fo,osz)
        
        if ii.mod_required == 3:
            fo.add_code_eol('set_mod(r,3)')
            

        for i in [0,1]:
            if not fixed[opnd_order[i]]:
                fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(opnd_order[i],osz,var_regs[i]))

        for slot in ['reg','rm']:
            if fixed[slot]:
                if slot == 'reg':
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
                else:
                    fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
                    
        
        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
        else:
            emit_opcode(ii,fo)
            emit_modrm(fo)

        cond_emit_imm8(ii,fo)
        if ii.has_immz:
            emit_immz(fo,osz)
        add_enc_func(ii,fo)


def create_legacy_two_gpr8_regs(env, ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_two_gpr8_regs")
            
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0,'gpr8')
    fo.add_arg(arg_reg1,'gpr8')
    emit_required_legacy_prefixes(ii,fo)

    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_gpr8(r,{})'.format(f1,var_reg0))
    fo.add_code_eol('enc_modrm_{}_gpr8(r,{})'.format(f2,var_reg1))
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)

    if ii.partial_opcode:
        die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
    else:
        emit_opcode(ii,fo)
        emit_modrm(fo)
    add_enc_func(ii,fo)

def add_arg_disp(fo,dispsz): 
    global arg_dispv, arg_dispv_meta
    fo.add_arg(arg_dispv[dispsz], arg_dispv_meta[dispsz])
def add_arg_immz(fo,osz): 
    global arg_immz_dct, arg_immz_meta
    fo.add_arg(arg_immz_dct[osz], arg_immz_meta[osz])
def add_arg_immv(fo,osz): 
    global arg_immv_dct, arg_immv_meta
    fo.add_arg(arg_immv_dct[osz], arg_immv_meta[osz])

vlmap = { 'xmm': 0, 'ymm': 1, 'zmm': 2 }    
def set_evexll_vl(ii,fo,vl):
    global vlmap
    if not ii.rounding_form and not ii.sae_form:
        fo.add_code_eol('set_evexll(r,{})'.format(vlmap[vl]),
                        'VL={}'.format(ii.vl))

    
def emit_immz(fo,osz):
    global var_immz_dct
    emit_width_immz = { 16:16, 32:32, 64:32 }

    fo.add_code_eol('emit_i{}(r,{})'.format(emit_width_immz[osz],
                                            var_immz_dct[osz]))
def emit_immv(fo,osz):
    global var_immv_dct
    emit_width_immv = {8:8, 16:16, 32:32, 64:64 }

    fo.add_code_eol('emit_u{}(r,{})'.format(emit_width_immv[osz],
                                            var_immv_dct[osz]))
def emit_disp(fo,dispsz):
    global var_dispv
    fo.add_code_eol('emit_i{}(r,{})'.format(dispsz,
                                            var_dispv[dispsz]))
        
def cond_emit_imm8(ii,fo):
    global var_imm8, var_imm8_2
    if ii.has_imm8:
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    if ii.has_imm8_2:
        fo.add_code_eol('emit(r,{})'.format(var_imm8_2))
def cond_add_imm_args(ii,fo):
    global arg_imm8, arg_imm8_2
    if ii.has_imm8:
        fo.add_arg(arg_imm8,'int8')
    if ii.has_imm8_2:
        fo.add_arg(arg_imm8_2,'int8')    
    

def emit_rex(env, fo, rex_forced):
    if env.mode == 64:
        if rex_forced:
            fo.add_code_eol('emit_rex(r)')
        else:
            fo.add_code_eol('emit_rex_if_needed(r)')


def get_opnd_types_short(ii):
    types= []
    for op in _gen_opnds(ii):
        if op.oc2:
            types.append(op.oc2)
        elif op_luf_start(op,'GPRv'):
            types.append('v')
        elif op_luf_start(op,'GPRz'):
            types.append('z')
        elif op_luf_start(op,'GPRy'):
            types.append('y')
        else:
            die("Unhandled op type {}".format(op))
    return types


def get_reg_type_fixed(op):
    '''return a type suitable for use in an enc_modrm function'''
    if op_gpr32(op):
        return 'gpr32'
    elif op_gpr64(op):
        return 'gpr64'
    elif op_xmm(op):
        return 'xmm'
    elif op_ymm(op):
        return 'ymm'
    elif op_mmx(op):
        return 'mmx'
    die("UNHANDLED OPERAND TYPE {}".format(op))
    
orax = { 16:'ax', 32:'eax', 64:'rax' }
oeax = { 16:'ax', 32:'eax', 64:'eax' }

def get_opnd_types(env, ii, osz=0):
    """Create meta-data about operands that can be used for generating
       testing content."""
    global orax, oeax
    s = []
    for op in _gen_opnds(ii):
        if op_luf_start(op,'GPRv'):
            if osz == 0:
                die("Need OSZ != 0")
            s.append('gpr{}'.format(osz))
        elif op_luf_start(op,'GPRy'):
            if osz == 0:
                die("Need OSZ != 0")
            s.append('gpr{}'.format(osz if osz > 16 else 32))
        elif op_luf_start(op,'GPRz'):
            if osz == 0:
                die("Need OSZ != 0")
            s.append('gpr{}'.format(osz if osz < 64 else 32))
        elif op_luf_start(op,'OrAX'):
            if osz == 0:
                die("Need OSZ != 0")
            s.append(orax[osz])
        elif op_luf_start(op,'OrAX'):
            if osz == 0:
                die("Need OSZ != 0")
            s.append(oeax[osz])
        elif op_luf_start(op,'ArAX'):
            s.append(orax[env.asz])
        elif op_immz(op):
            if osz == 0:
                die("Need OSZ != 0")
            s.append('imm{}'.format(osz if osz < 64 else 32))
        elif op_immv(op):
            if osz == 0:
                die("Need OSZ != 0")
            s.append('imm{}'.format(osz))
        elif op_luf_start(op, 'A_GPR'):
            s.append('gpr{}'.format(env.asz))
            
        elif op_implicit_specific_reg(op):
            pass # ignore
           
        elif op_tmm(op):
            s.append('tmm')
        elif op_xmm(op):
            s.append('xmm')
        elif op_ymm(op):
            s.append('ymm')
        elif op_zmm(op):
            s.append('zmm')
        elif op_vgpr32(op):
            s.append('gpr32')
        elif op_vgpr64(op):
            s.append('gpr64') 
        elif op_gpr32(op):
            s.append('gpr32')
        elif op_gpr64(op):
            s.append('gpr64') 
        elif op_gpr8(op):
            s.append('gpr8') 
        elif op_gpr16(op):
            s.append('gpr16') 
        elif op_mem(op):
            s.append('mem')
        elif op_agen(op):  # LEA
            s.append('agen')
        elif op_imm8(op):
            s.append('int8')
        elif op_imm16(op):
            s.append('int16') 
        elif op_imm8_2(op):
            s.append('int8') 
        elif op_mmx(op):
            s.append('mmx')
        elif op_cr(op):
            s.append('cr')
        elif op_dr(op):
            s.append('dr')
        elif op_seg(op):
            s.append('seg')
        elif op_masknot0(op): # must be before generic mask test below
            s.append('kreg!0')
        elif op_mask_reg(op):
            s.append('kreg')
        else:
            die("Unhandled operand {}".format(op))
    return s

    

def two_fixed_regs_opti8(ii): # also allows 2-imm8 SSE4 instr
    j,i,d,q,m,x=0,0,0,0,0,0
    for op in _gen_opnds(ii):
        if op_imm8(op):
            i += 1
        elif op_imm8_2(op):
            j += 1
        elif op_gpr32(op):
            d += 1
        elif op_gpr64(op):
            q += 1
        elif op_mmx(op):
            m += 1
        elif op_xmm(op):
            x += 1
        else:
            return False
    if i>=2 or j>=2:
        return False
    sum = d + q + m + x
    return sum == 2  # 1+1 or 2+0...either is fine

            
def create_legacy_two_fixed_regs_opti8(env,ii): 
    '''Two regs and optional imm8. Regs can be gpr32,gpr64,xmm,mmx, and
       they can be different from one another'''
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_reg1, var_reg1

    opnd_sig = make_opnd_signature(env,ii)

    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  opnd_sig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_two_fixed_regs_opti8")
        
    fo.add_arg(arg_request,'req')
    opnd_types = get_opnd_types(env,ii)
    fo.add_arg(arg_reg0, opnd_types[0])
    fo.add_arg(arg_reg1, opnd_types[1])
    cond_add_imm_args(ii,fo)
    
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        locations = ['reg', 'rm']
    else:
        locations = ['rm', 'reg']
    regs = [ var_reg0, var_reg1]

    rexw_forced = cond_emit_rexw(env,ii,fo,osz=0) # legit
    fo.add_code_eol('set_mod(r,3)')
    for i,op in enumerate(_gen_opnds(ii)):
        if op_imm8(op):
            break
        reg_type = get_reg_type_fixed(op)
        fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(locations[i], reg_type, regs[i]))
    emit_rex(env,fo,rexw_forced)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    cond_emit_imm8(ii,fo)
    
    add_enc_func(ii,fo)
    

def create_legacy_one_mmx_reg_imm8(env,ii):
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_imm8, var_imm8

    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  opsig) 
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_mmx_reg_imm8")
        
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0, 'mmx')
    cond_add_imm_args(ii,fo)
    
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_mmx(r,{})'.format(f1,var_reg0))
    fo.add_code_eol('set_mod(r,3)')
    if f2 == 'reg':
        if ii.reg_required != 'unspecified':
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    else:
        if ii.rm_required != 'unspecified':
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))

    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    cond_emit_imm8(ii,fo)
    add_enc_func(ii,fo)


def create_legacy_one_xmm_reg_imm8(env,ii):
    '''also handles 2 imm8 SSE4 instr'''
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_imm8, var_imm8

    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig) 
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_xmm_reg_imm8")
        
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0,'xmm')
    cond_add_imm_args(ii,fo)
    
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_xmm(r,{})'.format(f1,var_reg0))
    fo.add_code_eol('set_mod(r,3)')
    if f2 == 'reg':
        if ii.reg_required != 'unspecified':
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    else:
        if ii.rm_required != 'unspecified':
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))

    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    cond_emit_imm8(ii,fo)
    add_enc_func(ii,fo)

    
def create_legacy_two_x87_reg(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0
    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_two_x87_reg")    
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0,'x87')
    emit_required_legacy_prefixes(ii,fo)
    fo.add_code_eol('set_mod(r,3)')
    if ii.reg_required == 'unspecified':
        die("Need a value for MODRM.REG in x87 encoding")
    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    fo.add_code_eol('enc_modrm_rm_x87(r,{})'.format(var_reg0))
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

    
def create_legacy_one_x87_reg(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0
    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_one_x87_reg")    
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_reg0,'x87')
    emit_required_legacy_prefixes(ii,fo)
    if ii.mod_required == 3:
        fo.add_code_eol('set_mod(r,3)')
    else:
        die("FUNKY MOD on x87 op: {}".format(ii.mod_required))
    if ii.reg_required == 'unspecified':
        die("Need a value for MODRM.REG in x87 encoding")
    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    fo.add_code_eol('enc_modrm_rm_x87(r,{})'.format(var_reg0))
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

    
def gpr8_imm8(ii):
    reg,imm=0,0
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf_start(op,'GPR8'): 
                reg = reg + 1
            else:
                return False
        elif i == 1:
            if op.name == 'IMM0' and op.oc2 == 'b':
                if op_implicit_or_suppressed(op):
                    return False
                imm = imm + 1
            else:
                return False
        else:
            return False
    return reg == 1 and imm == 1
            
def gprv_imm8(ii):
    reg,imm=0,0
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and  op_luf_start(op,'GPRv'):
                reg = reg + 1
            else:
                return False
        elif i == 1:
            if op.name == 'IMM0' and op.oc2 == 'b':
                if op_implicit_or_suppressed(op):
                    return False
                imm = imm + 1
            else:
                return False
        else:
            return False
    return reg == 1 and imm == 1

def gprv_immz(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf_start(op,'GPRv'):
                continue
            else:
                return False
        elif i == 1:
            if op_immz(op):
                continue
            else:
                return False
        else:
            return False
    return True

def gprv_immv(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf_start(op,'GPRv'):
                continue
            else:
                return False
        elif i == 1:
            if op_immv(op):
                continue
            else:
                return False
        else:
            return False
    return True

def orax_immz(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf(op,'OrAX'):
                continue
            else:
                return False
        elif i == 1:
            if op_immz(op):
                continue
            else:
                return False
        else:
            return False
    return True


def op_luf(op,s):
    if op.lookupfn_name:
        if op.lookupfn_name == s:
            return True
    return False
def op_luf_start(op,s):
    if op.lookupfn_name:
        if op.lookupfn_name.startswith(s):
            return True
    return False

def gprv_implicit_orax(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf(op,'GPRv_SB'):
                continue
            else:
                return False
        elif i == 1:
            if op.name == 'REG1' and op_luf(op,'OrAX'):
                continue
            else:
                return False
        else:
            return False
    return True
    

def create_legacy_gpr_imm8(env,ii,width_list):
    '''gpr8 or gprv with imm8. nothing fancy'''
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0, arg_imm8,  var_imm8, gprv_names
    
    for osz in gen_osz_list(env.mode,width_list):
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      opsig)

        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_gpr_imm8")
        fo.add_arg(arg_request,'req')
        fo.add_arg(arg_reg0, gprv_names[osz])
        fo.add_arg(arg_imm8,'int8')
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        elif ii.default_64b and osz == 32: # never happens
            continue

        rexw_forced = cond_emit_rexw(env,ii,fo,osz)
        if ii.partial_opcode:
            fo.add_code_eol('enc_srm_gpr{}(r,{})'.format(osz, var_reg0))
        else:
            if modrm_reg_first_operand(ii):
                f1, f2 = 'reg','rm'
            else:
                f1, f2 = 'rm','reg'
            fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1,osz,var_reg0))

            if f2 == 'reg':
                if ii.reg_required != 'unspecified':
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
            
        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            emit_partial_opcode_variable_srm(ii,fo)
        else:
            emit_opcode(ii,fo)
            emit_modrm(fo)
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
        add_enc_func(ii,fo)


def create_legacy_gprv_immz(env,ii):
    global enc_fn_prefix, arg_request, gprv_names, arg_reg0,  var_reg0
    width_list = get_osz_list(env)

    for osz in width_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      opsig)
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_gprv_immz")
        fo.add_arg(arg_request,'req')
        fo.add_arg(arg_reg0, gprv_names[osz])
        add_arg_immz(fo,osz)
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        if osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        elif ii.default_64b and osz == 32: # never happens
            continue

        
        rexw_forced = cond_emit_rexw(env,ii,fo,osz)
        if modrm_reg_first_operand(ii):
            f1, f2 = 'reg','rm'
        else:
            f1, f2 = 'rm','reg'
        fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1,osz,var_reg0))
        if f2 == 'reg':
            if ii.reg_required != 'unspecified':
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
        else:
            if ii.rm_required != 'unspecified':
                fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))

        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        emit_modrm(fo)
        emit_immz(fo,osz)
        add_enc_func(ii,fo)


def create_legacy_orax_immz(env,ii): 
    """Handles OrAX+IMMz. No MODRM byte"""
    global enc_fn_prefix, arg_request
    global arg_imm16
    global arg_imm32

    width_list = get_osz_list(env)

    for osz in width_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  opsig)

        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_orax_immz")
        fo.add_arg(arg_request,'req')
        opnd_types = get_opnd_types(env,ii,osz)
        # no need to mention the implicit OrAX arg... we don't use it for anything
        #fo.add_arg(arg_reg0,opnd_types[0])
        add_arg_immz(fo,osz)

        
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        elif ii.default_64b and osz == 32: # never happens
            continue
        rexw_forced = cond_emit_rexw(env,ii,fo,osz)

        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        emit_immz(fo,osz)
        add_enc_func(ii,fo)


def create_legacy_gprv_immv(env,ii,imm=False):
    """Handles GPRv_SB-IMMv partial reg opcodes and GPRv_SB+OrAX implicit"""
    global enc_fn_prefix, arg_request, gprv_names
    global arg_reg0,  var_reg0
    global arg_imm16, var_imm16
    global arg_imm32, var_imm32
    global arg_imm64, var_imm64
    width_list = get_osz_list(env)

    
    for osz in width_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                    ii.iclass.lower(),
                                    opsig)

        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_gprv_immv")
        fo.add_arg(arg_request,'req')
        fo.add_arg(arg_reg0, gprv_names[osz])
        if imm:
            add_arg_immv(fo,osz)
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        elif ii.default_64b and osz == 32: # never happens
            continue

        rexw_forced = cond_emit_rexw(env,ii,fo,osz)

        # WE know this is a SRM partial opcode instr
        if not ii.partial_opcode:
            die("Expecting partial opcode instruction in create_legacy_gprv_immv")

        op = first_opnd(ii)
        if op_luf(op,'GPRv_SB'):
            fo.add_code_eol('enc_srm_gpr{}(r,{})'.format(osz, var_reg0))
        else:
            die("NOT REACHED")

        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        emit_partial_opcode_variable_srm(ii,fo)
        if imm:
            emit_immv(fo,osz)
        add_enc_func(ii,fo)
        

def emit_partial_opcode_variable_srm(ii,fo):
    opcode = "0x{:02X}".format(ii.opcode_base10)
    fo.add_code_eol('emit(r,{} | get_srm(r))'.format(opcode),
                    'partial opcode, variable srm')

def emit_partial_opcode_fixed_srm(ii,fo):
    fixed_opcode_srm = ii.rm_required
    opcode = "0x{:02X}".format(ii.opcode_base10)
    fo.add_code_eol('emit(r,{} | {})'.format(opcode,fixed_opcode_srm),
                    'partial opcode, fixed srm')
        

memsig_idx_16 = {  0: 'bi',
                   8: 'bid8',
                   16: 'bid16' }

memsig_idx_32or64 = {  0: 'bis',
                       8: 'bisd8',
                       32: 'bisd32' }

memsig_noidx_16 = {  0: 'b',
                     8: 'bd8',
                     16: 'bd16' }

memsig_noidx_32or64 = {  0: 'b',
                         8: 'bd8',
                         32: 'bd32' }

memsig_str_16 =  { True : memsig_idx_16,  # indexed by use_index
                   False: memsig_noidx_16 } 
memsig_str_32or64 =  { True : memsig_idx_32or64,  # indexed by use_index
                       False: memsig_noidx_32or64 }


def get_memsig(asz, using_indx, dispz):
    global memsig_str_16
    global memsig_str_32or64
    
    if asz == 16:
        return memsig_str_16[using_indx][dispz]
    return memsig_str_32or64[using_indx][dispz]


def add_memop_args(env, ii, fo, use_index, dispsz, immw=0, reg=-1, osz=0):
    """reg=-1 -> no reg opnds, 
       reg=0  -> first opnd is reg,
       reg=1  -> 2nd opnd is reg. 
    AVX or AVX512 vsib moots the use_index value"""
    
    global arg_reg0, arg_imm_dct
    global arg_base, arg_index, arg_scale
    global arg_disp8, arg_disp16, arg_disp32
    
    opnd_types = get_opnd_types(env,ii,osz)
    if reg == 0:
        fo.add_arg(arg_reg0,opnd_types[0])
        
    fo.add_arg(arg_base, gprv_names[env.asz])
    if ii.avx_vsib:
        fo.add_arg("{} {}".format(arg_reg_type, var_vsib_index_dct[ii.avx_vsib]),
                   ii.avx_vsib)
    elif ii.avx512_vsib:
        fo.add_arg("{} {}".format(arg_reg_type, var_vsib_index_dct[ii.avx512_vsib]),
                   ii.avx512_vsib)
    elif use_index:
        fo.add_arg(arg_index, gprv_index_names[env.asz])
        
    if use_index or special_index_cases(ii):
        if env.asz in [32,64]:
            fo.add_arg(arg_scale, 'scale')  # a32, a64

    if dispsz != 0:
        add_arg_disp(fo,dispsz)

    if reg == 1:
        fo.add_arg(arg_reg0, opnd_types[1])

    if immw:
        add_arg_immv(fo,immw)

def create_legacy_one_xmm_reg_one_mem_fixed(env,ii):
    '''allows xmm, mmx, gpr32, gpr64 regs optional imm8'''
    global var_reg0
    
    op = first_opnd(ii)
    width = op.oc2
    immw = 8 if ii.has_imm8 else 0
    regpos = 0 if modrm_reg_first_operand(ii) else 1    # i determines argument order
    #opsig = 'rm' if regpos==0 else 'mr'
    #if ii.has_imm8:
    #    opsig = opsig + 'i'
    opsig = make_opnd_signature(env,ii)
        
    gpr32,gpr64,xmm,mmx = False,False,False,False
    for op in _gen_opnds(ii):
        if op_mmx(op):
            mmx=True
            break
        if op_xmm(op):
            xmm=True
            break
        if op_gpr32(op):
            gpr32=True
            break
        if op_gpr64(op):
            gpr64=True
            break
        

    dispsz_list = get_dispsz_list(env)
        
    ispace = itertools.product(get_index_vals(ii), dispsz_list)
    for use_index, dispsz in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = "{}_{}_{}_{}".format(enc_fn_prefix,
                                        ii.iclass.lower(),
                                        opsig,
                                        #width, # FIXME:osz, funky
                                        memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_legacy_one_xmm_reg_one_mem_fixed")
        fo.add_arg(arg_request,'req')
        add_memop_args(env, ii, fo, use_index, dispsz, immw, reg=regpos)

        rexw_forced = False
        if ii.eosz == 'o16' and env.mode in [32,64]:
            fo.add_code_eol('emit(r,0x66)', 'xx: fixed width with 16b osz')
        elif ii.eosz == 'o32' and env.mode == 16:
            fo.add_code_eol('emit(r,0x66)')
        elif (ii.eosz == 'o64' and env.mode == 64 and ii.default_64b == False) or ii.rexw_prefix == '1':
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')

        emit_required_legacy_prefixes(ii,fo)

        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))

        # the sole reg is reg0 whether it is first or 2nd operand...
        if xmm:
            fo.add_code_eol('enc_modrm_reg_xmm(r,{})'.format(var_reg0))
        elif mmx:
            fo.add_code_eol('enc_modrm_reg_mmx(r,{})'.format(var_reg0))
        elif gpr32:
            fo.add_code_eol('enc_modrm_reg_gpr32(r,{})'.format(var_reg0))
        elif gpr64:
            fo.add_code_eol('enc_modrm_reg_gpr64(r,{})'.format(var_reg0))
        else:
            die("NOT REACHED")

        encode_mem_operand(env, ii, fo, use_index, dispsz)
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced, space='legacy')

        add_enc_func(ii,fo)


def get_reg_width(op):
    if op_gpr8(op):
        return 'b'
    elif op_gpr16(op):
        return 'w'
    elif op_gpr32(op):
        return 'd'
    elif op_gpr64(op):
        return 'q'
    die("NOT REACHED")
            
def create_legacy_one_gpr_reg_one_mem_fixed(env,ii):   
    """REGb-GPRb or GPRb-REGb also GPR32-MEMd, GPR64-MEMq or MEMdq  and MEMw+GPR16"""
    global var_reg0, widths_to_bits
    dispsz_list = get_dispsz_list(env)

    width = None
    for i,op in enumerate(_gen_opnds(ii)):
        if op_reg(op):
            regn = i
            width = get_reg_width(op)
            break
    if width == None:
        dump_fields(ii)
        die("Bad search for width")
    
    widths = [width]
    opsig = make_opnd_signature(env,ii)

    ispace = itertools.product(widths, get_index_vals(ii), dispsz_list)
    for width, use_index, dispsz in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = "{}_{}_{}_{}".format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opsig,
                                     memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_legacy_one_gpr_reg_one_mem_fixed")
        fo.add_arg(arg_request,'req')
        add_memop_args(env, ii, fo, use_index, dispsz, immw=0, reg=regn)

        emit_required_legacy_prefixes(ii,fo)

        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))

        # the sole reg is reg0 whether it is first or 2nd operand...
        fo.add_code_eol('enc_modrm_reg_gpr{}(r,{})'.format(widths_to_bits[width],
                                                           var_reg0))

        encode_mem_operand(env, ii, fo, use_index, dispsz)
        osz=64 if width=='q' else 0
        rexw_forced = cond_emit_rexw(env, ii, fo, osz)

        immw=False
        finish_memop(env, ii, fo,  dispsz, immw, rexw_forced, space='legacy')
        add_enc_func(ii,fo)


def create_legacy_one_gpr_reg_one_mem_scalable(env,ii):   
    """GPRv-MEMv, MEMv-GPRv, GPRy-MEMv, MEMv-GPRy w/optional imm8 or immz.  This
       will work with anything that has one scalable register operand
       and another fixed or scalable memory operand. """
    # The GPRy stuff is not working yet
    global arg_reg0, var_reg0, widths_to_bits, widths_to_bits_y
    dispsz_list = get_dispsz_list(env)

    op = first_opnd(ii)
    widths = ['w','d']
    if env.mode == 64:
        widths.append('q')

    gpry=False
    for op in _gen_opnds(ii):
        if op_gpry(op):
            gpry=True

    fixed_reg = False
    if ii.iclass == 'NOP' and ii.iform.startswith('NOP_MEMv_GPRv_0F1C'):
        if ii.reg_required != 'unspecified':
            fixed_reg = True
    immw = 8  if ii.has_imm8 else 0
    
    ispace = itertools.product(widths, get_index_vals(ii), dispsz_list)
    for width, use_index, dispsz in ispace:
        opsig = make_opnd_signature(env,ii, width)
        opnd_types_org = get_opnd_types(env,ii, osz_translate(width))        
        opnd_types  = copy.copy(opnd_types_org)
        if ii.has_immz:
            immw = 16 if (width == 16 or width == 'w') else 32
            
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = "{}_{}_{}_{}".format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opsig,
                                     memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_legacy_one_gpr_reg_one_mem_scalable")
        fo.add_arg(arg_request,'req')

        for i,optype in enumerate(opnd_types_org):
            if optype.startswith('gpr'):
                if not fixed_reg:
                    fo.add_arg(arg_reg0, opnd_types.pop(0))
            elif optype in ['mem', 'agen']:
                add_memop_args(env, ii, fo, use_index, dispsz, immw=0, osz=osz_translate(width))
                opnd_types.pop(0)
            elif optype.startswith('int') or optype.startswith('imm'):
                add_arg_immv(fo,immw)
                opnd_types.pop(0) # imm8 is last so we technically can skip this pop
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))


        rexw_forced = False

        if width == 'w' and env.mode != 16:
            fo.add_code_eol('emit(r,0x66)')
        elif width == 'd' and  env.mode == 16:
            fo.add_code_eol('emit(r,0x66)')
        elif width == 'q' and  ii.default_64b == False:
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')

        emit_required_legacy_prefixes(ii,fo)

        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))


        if ii.reg_required != 'unspecified':
            if ii.reg_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required),
                                'reg opcode extension')
        else:
            d=widths_to_bits_y if gpry else widths_to_bits
            fo.add_code_eol('enc_modrm_reg_gpr{}(r,{})'.format(d[width],
                                                               var_reg0))

        encode_mem_operand(env, ii, fo, use_index, dispsz)

        finish_memop(env, ii, fo,  dispsz, immw, rexw_forced=rexw_forced, space='legacy')
        add_enc_func(ii,fo)
def create_legacy_far_xfer_nonmem(env,ii):  # WRK
    '''call far and jmp far via ptr+imm. BRDISPz + IMMw'''
    global var_immz_dct, argv_immz_dct,arg_immz_meta, var_imm16_2, arg_imm16_2

    for osz in [16,32]:
        fname = '{}_{}_o{}'.format(enc_fn_prefix,
                                   ii.iclass.lower(),
                                   osz) 

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment('created by create_legacy_far_xfer_nonmem')
        fo.add_arg(arg_request,'req')
        fo.add_arg(arg_immz_dct[osz],arg_immz_meta[osz])
        fo.add_arg(arg_imm16_2,'int16')

        if osz == 16 and env.mode != 16:
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 32 and  env.mode == 16:
            fo.add_code_eol('emit(r,0x66)')
        emit_required_legacy_prefixes(ii,fo)
        emit_opcode(ii,fo)
        emit_immz(fo,osz)
        fo.add_code_eol('emit_i16(r,{})'.format(var_imm16_2))
        add_enc_func(ii,fo)

    
def create_legacy_far_xfer_mem(env,ii):
    '''call far and jmp far via memop. p has widths 4/6/6 bytes. p2 has 4/6/10 widths'''
    p_widths = {16:4, 32:6, 64:6} 
    p2_widths = {16:4, 32:6, 64:10}
    op = first_opnd(ii)
    if op.oc2 == 'p2':
        widths = p2_widths
    elif op.oc2 == 'p':
        widths = p_widths
    else:
        die("NOT REACHED")
    osz_list = get_osz_list(env)
    dispsz_list = get_dispsz_list(env)

    ispace = itertools.product(osz_list, get_index_vals(ii), dispsz_list)
    for osz, use_index, dispsz in ispace:
        membytes = widths[osz]
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = '{}_{}_m{}_{}'.format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      membytes*8,
                                      memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment('created by create_legacy_far_xfer_mem')
        fo.add_arg(arg_request,'req')
        add_memop_args(env, ii, fo, use_index, dispsz)
        rexw_forced = False
        if osz == 16 and env.mode != 16:
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 32 and  env.mode == 16:
            fo.add_code_eol('emit(r,0x66)')
        elif osz == 64 and  ii.default_64b == False:
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')
        emit_required_legacy_prefixes(ii,fo)

        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))

        if ii.reg_required != 'unspecified':
            if ii.reg_required != 0:  # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

        encode_mem_operand(env, ii, fo, use_index, dispsz)
        
        finish_memop(env, ii, fo,  dispsz,
                     immw=0,
                     rexw_forced=rexw_forced,
                     space='legacy')
        add_enc_func(ii,fo)

        
def osz_translate(width):
    if width in  ['w',16]:
        return 16
    elif width in ['d',32]:
        return 32
    elif width in ['q', 64]:
        return 64
    return 0
        

def create_legacy_one_mem_common(env,ii,imm=0):
    """Handles one memop, fixed or scalable."""
    dispsz_list = get_dispsz_list(env)
    
    op = first_opnd(ii)
    if op.oc2 == 'v':
        widths = [16,32]
        if env.mode == 64:
            widths.append(64)
    elif op.oc2 == 'y':
        widths = [32]
        if env.mode == 64:
            widths.append(64)
    elif op.oc2 == 's':
        widths = [16,32]
    else:
        widths = ['nominal'] # just something to get the loop going

    immz_dict = { 16:16, 32:32, 64:32 }
    for width in widths:
        immw = 0
        if imm == '8':
            immw = 8
        elif imm == 'z':
            immw = immz_dict[width]
            
        #fwidth = "_{}".format(width) if width not in ['b','w','d','q'] else ''
        
        ispace = itertools.product(get_index_vals(ii), dispsz_list)
        for use_index, dispsz in ispace:
            memaddrsig = get_memsig(env.asz, use_index, dispsz)
            
            if width != 'nominal':
                opsig = make_opnd_signature(env, ii, width)
            else:
                opsig = make_opnd_signature(env, ii)
                
            fname = '{}_{}_{}_{}'.format(enc_fn_prefix,
                                         ii.iclass.lower(),
                                         opsig,
                                         memaddrsig)
                                  
            fo = make_function_object(env,ii,fname, asz=env.asz)
            fo.add_comment('created by create_legacy_one_mem_common')
            fo.add_arg(arg_request,'req')
            add_memop_args(env, ii, fo, use_index, dispsz, immw, osz=osz_translate(width))

            rexw_forced = False

            if op.oc2 in [ 'y','v', 's']:                  # handle scalable ops
                if width == 16 and env.mode != 16:
                    fo.add_code_eol('emit(r,0x66)')
                elif width == 32 and  env.mode == 16:
                    fo.add_code_eol('emit(r,0x66)')
                elif width == 64 and ii.default_64b == False:
                    rexw_forced = True
                    fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')
            else:  # fixed width ops
                if ii.eosz == 'o16' and env.mode in [32,64]:
                    fo.add_code_eol('emit(r,0x66)', 'xx: fixed width with 16b osz')
                elif ii.eosz == 'o32' and env.mode == 16:
                    fo.add_code_eol('emit(r,0x66)')
                elif (ii.eosz == 'o64' and env.mode == 64 and ii.default_64b == False) or ii.rexw_prefix == '1':
                    rexw_forced = True
                    fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')

            emit_required_legacy_prefixes(ii,fo)

            mod = get_modval(dispsz)
            if mod:  # ZERO-INIT OPTIMIZATION
                fo.add_code_eol('set_mod(r,{})'.format(mod))

            if ii.reg_required != 'unspecified':
                if ii.reg_required != 0:  # ZERO INIT OPTIMIZATION
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

            encode_mem_operand(env, ii, fo, use_index, dispsz)
            finish_memop(env, ii, fo,  dispsz, immw, rexw_forced, space='legacy')
            add_enc_func(ii,fo)

            
def encode_mem_operand(env, ii, fo, use_index, dispsz): 
    global var_base, var_index, var_scale, memsig_idx_32or64, var_vsib_index_dct
    # this may overwrite modrm.mod
    memaddrsig = get_memsig(env.asz, use_index, dispsz)
    
    if ii.avx_vsib:
        memsig = memsig_idx_32or64[dispsz]
        fo.add_code_eol('enc_avx_modrm_vsib_{}_{}_a{}(r,{},{},{})'.format(
             ii.avx_vsib, memaddrsig, env.asz, var_base,
            var_vsib_index_dct[ii.avx_vsib], var_scale))

    elif ii.avx512_vsib:
        memsig = memsig_idx_32or64[dispsz]
        fo.add_code_eol('enc_avx512_modrm_vsib_{}_{}_a{}(r,{},{},{})'.format(
            ii.avx512_vsib, memaddrsig, env.asz, var_base,
            var_vsib_index_dct[ii.avx512_vsib], var_scale))

    elif use_index:
        if env.asz == 16: # no scale
            fo.add_code_eol('enc_modrm_rm_mem_{}_a{}(r,{},{})'.format(
                memaddrsig, env.asz, var_base, var_index))
        else:  
            fo.add_code_eol('enc_modrm_rm_mem_{}_a{}(r,{},{},{})'.format(
                memaddrsig, env.asz, var_base, var_index, var_scale))
    else: # no index,scale
        fo.add_code_eol('enc_modrm_rm_mem_{}_a{}(r,{})'.format(
            memaddrsig, env.asz, var_base))

            
def finish_memop(env, ii, fo, dispsz, immw, rexw_forced=False, space='legacy'):
    global var_disp8, var_disp16, var_disp32

    if space == 'legacy':
        emit_rex(env,fo,rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
    elif space =='evex':
        fo.add_code_eol('emit_evex(r)')

        
    emit_opcode(ii,fo)
    emit_modrm(fo)
    if special_index_cases(ii):
        fo.add_code_eol('emit_sib(r)', 'for vsib/sibmem')
    else:
        fo.add_code('if (get_has_sib(r))')
        fo.add_code_eol('    emit_sib(r)')
        
    if space == 'evex':
        if dispsz == 0:
            # if form has no displacment, then we sometimes have to
            # add a zero displacement to create an allowed modrm/sib
            # encoding.
            emit_synthetic_disp(fo)
        elif dispsz == 8:
            fo.add_code_eol('emit_i8(r,{})'.format(var_disp8))
        else:
            emit_evex_disp(env,fo)
        
    else:
        if dispsz == 8:
            fo.add_code_eol('emit_i8(r,{})'.format(var_disp8))
        elif dispsz == 16:
            fo.add_code_eol('emit_i16(r,{})'.format(var_disp16))
        elif dispsz == 32:
            fo.add_code_eol('emit_i32(r,{})'.format(var_disp32))
        elif dispsz == 0 and env.asz != 16:
            # if form has no displacment, then we sometimes have to
            # add a zero displacement to create an allowed modrm/sib
            # encoding.
            emit_synthetic_disp(fo)
    if immw:
        emit_immv(fo,immw)
        
def emit_modrm(fo):
    fo.add_code_eol('emit_modrm(r)')
    
def emit_sib(fo):
    fo.add_code('if (get_has_sib(r))') 
    fo.add_code_eol('    emit_sib(r)')

def emit_synthetic_disp(fo):
    fo.add_code('if (get_has_disp8(r))')
    fo.add_code_eol('   emit_i8(r,0)')
    fo.add_code('else if (get_has_disp32(r))')
    fo.add_code_eol('   emit_i32(r,0)')



    
def add_evex_displacement_var(fo):
    fo.add_code_eol('xed_int32_t use_displacement')
    
def chose_evex_scaled_disp(fo, ii, dispsz, broadcasting=False): # WIP
    disp_fix = '16' if dispsz == 16 else ''
    
    if ii.avx512_tuple == 'NO_SCALE':
        memop_width_bytes = 1
    elif broadcasting:
        memop_width_bytes = ii.element_size // 8
    else:
        memop_width_bytes = ii.memop_width // 8

    fo.add_code_eol('use_displacement = xed_chose_evex_scaled_disp{}(r, disp{}, {})'.format(
        disp_fix,
        dispsz,
        memop_width_bytes))
    
def emit_evex_disp(env,fo):
    fo.add_code('if (get_has_disp8(r))')
    fo.add_code_eol('   emit_i8(r,use_displacement)')
    if env.asz == 16:
        fo.add_code('else if (get_has_disp16(r))')
        fo.add_code_eol('   emit_i16(r,use_displacement)')
    else:
        fo.add_code('else if (get_has_disp32(r))')
        fo.add_code_eol('   emit_i32(r,use_displacement)')
    
    

def mov_without_modrm(ii):
    if ii.iclass == 'MOV' and not ii.has_modrm:
        if 'UIMM' in ii.pattern: # avoid 0xB0/0xB8 related mov's
            return False
        return True
    return False


def create_legacy_mov_without_modrm(env,ii):
    '''This if for 0xA0...0xA3 MOVs without MODRM'''
    global enc_fn_prefix, arg_request, arg_reg0, bits_to_widths
    # in XED, MEMDISPv is a misnomer - the displacement size is
    # modulated by the EASZ!  The actual width of the memory reference
    # is OSZ modulated (66, rex.w) normally.
    
    byte_width = False
    for op in _gen_opnds(ii):
        if op.oc2 and op.oc2 == 'b':
            byte_width = True
            break
    if byte_width:
        osz_list = [8]
    else:
        osz_list = get_osz_list(env)
        
    disp_width = env.asz
    
    for osz in osz_list:
        opsig = make_opnd_signature(env,ii,osz)        
        fname = "{}_{}_{}_d{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      opsig, 
                                      env.asz) # FIXME redundant with asz

        fo = make_function_object(env,ii,fname,asz=env.asz)
        fo.add_comment("created by create_legacy_mov_without_modrm")
        fo.add_arg(arg_request,'req')
        add_arg_disp(fo,disp_width)

        # MEMDISPv is EASZ-modulated. 
        if disp_width == 16 and env.asz != 16:
            emit_67_prefix(fo)
        elif disp_width == 32 and  env.asz != 32:
            emit_67_prefix(fo)

        rexw_forced = emit_legacy_osz(env,ii,fo,osz)
        emit_rex(env, fo, rexw_forced)

        emit_opcode(ii,fo)
        emit_disp(fo,disp_width)
        add_enc_func(ii,fo)

def is_enter_instr(ii):
    return ii.iclass == 'ENTER' # imm0-w, imm1-b

def is_mov_seg(ii):
    if ii.iclass in ['MOV']:
        for op in _gen_opnds(ii):
            if op_seg(op):
                return True
    return False

def is_mov_cr_dr(ii):
    return ii.iclass in ['MOV_CR','MOV_DR']


def create_legacy_gprv_seg(env,ii,op_info):
    global arg_reg_type, gprv_names
    reg1 = 'seg'
    osz_list = get_osz_list(env)
    for osz in osz_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  opsig)
        fo = make_function_object(env,ii,fname)
        fo.add_comment('created by create_legacy_gprv_seg')
        fo.add_arg(arg_request,'req')
        reg0 = gprv_names[osz]
        fo.add_arg(arg_reg_type + reg0,'gpr{}'.format(osz))
        fo.add_arg(arg_reg_type + reg1,'seg')
        
        emit_required_legacy_prefixes(ii,fo)
        if not ii.osz_required:
            if osz == 16 and env.mode != 16:
                # add a 66 prefix outside of 16b mode, to create 16b osz
                fo.add_code_eol('emit(r,0x66)')
            if osz == 32 and env.mode == 16:
                # add a 66 prefix outside inside 16b mode to create 32b osz
                fo.add_code_eol('emit(r,0x66)')
        if osz == 64:
            fo.add_code_eol('set_rexw(r)')
        fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format('rm',reg0,reg0))
        fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format('reg',op_info[1],reg1))
        if osz == 64:
            fo.add_code_eol('emit_rex(r)')
        elif env.mode == 64:
            fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        emit_modrm(fo)
        add_enc_func(ii,fo)
            

def create_legacy_mem_seg(env,ii,op_info):  
    '''order varies: MEM-SEG or SEG-MEM'''
    global arg_reg_type
    dispsz_list = get_dispsz_list(env)

    opnd_sig = make_opnd_signature(env,ii)
    ispace = itertools.product(get_index_vals(ii), dispsz_list)
    for use_index, dispsz  in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = '{}_{}_{}_{}'.format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opnd_sig,
                                     memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment('created by create_legacy_mem_seg')
        fo.add_arg(arg_request,'req')
        for opi in op_info:
            if opi == 'mem':
                add_memop_args(env, ii, fo, use_index, dispsz) 
            elif opi == 'seg':
                reg0 = 'seg'
                fo.add_arg(arg_reg_type + reg0, 'seg')
            else:
                die("NOT REACHED")
                
        emit_required_legacy_prefixes(ii,fo)
        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))
        fo.add_code_eol('enc_modrm_reg_seg(r,{})'.format(reg0))
        encode_mem_operand(env, ii, fo, use_index, dispsz)
        finish_memop(env, ii, fo,  dispsz, immw=0, rexw_forced=False, space='legacy')
        add_enc_func(ii,fo)


def create_mov_seg(env,ii): 
    '''mov-seg. operand order varies'''
    op_info=[] # for encoding the modrm fields
    mem = False
    scalable=False
    for i,op in enumerate(_gen_opnds(ii)):
        if op_gprv(op):
            op_info.append('gprv')
            scalable=True
        elif op_gpr16(op):
            op_info.append('gpr16')
        elif op_seg(op):
            op_info.append('seg')
        elif op_mem(op):
            mem=True
            op_info.append('mem')

    if op_info == ['gprv','seg']:  # gprv, seg -- scalable, special handling
        create_legacy_gprv_seg(env,ii,op_info)
        return
    elif op_info == ['mem','seg']: # mem,seg
        create_legacy_mem_seg(env,ii,op_info)
        return
    elif op_info == ['seg','mem']: # seg,mem
        create_legacy_mem_seg(env,ii,op_info)
        return
    elif op_info == ['seg','gpr16']: # seg,gpr16
        opsig = 'SR' # handled below
    else:
        die("Unhandled mov-seg case")
            
    fname = "{}_{}_{}".format(enc_fn_prefix, ii.iclass.lower(),opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_mov_seg")
    fo.add_arg(arg_request,'req')
    fo.add_arg('xed_reg_enum_t ' + op_info[0], 'seg')
    fo.add_arg('xed_reg_enum_t ' + op_info[1], 'gpr16')

    if modrm_reg_first_operand(ii):
        f1, f2, = 'reg','rm'
    else:
        f1, f2, = 'rm','reg' 
    fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(f1, op_info[0], op_info[0]))
    fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(f2, op_info[1], op_info[1]))
    
    emit_required_legacy_prefixes(ii,fo)
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

def create_mov_cr_dr(env,ii): 
    '''mov-cr and mov-dr. operand order varies'''
    op_info=[] # for encoding the modrm fields
    for op in _gen_opnds(ii):
        if op_gpr32(op):
            op_info.append('gpr32')
        elif op_gpr64(op):
            op_info.append('gpr64')
        elif op_cr(op):
            op_info.append('cr')
        elif op_dr(op):
            op_info.append('dr')
            
    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix, ii.iclass.lower(),opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_mov_cr_dr")
    fo.add_arg(arg_request,'req')
    fo.add_arg('xed_reg_enum_t ' + op_info[0], op_info[0])
    fo.add_arg('xed_reg_enum_t ' + op_info[1], op_info[1])

    if modrm_reg_first_operand(ii):
        f1, f2, = 'reg','rm'
    else:
        f1, f2, = 'rm','reg' 
    fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(f1, op_info[0], op_info[0]))
    fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(f2, op_info[1], op_info[1]))
    
    emit_required_legacy_prefixes(ii,fo)
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

    
def create_legacy_enter(env,ii): 
    '''These are 3 unusual instructions: enter and AMD SSE4a extrq, insrq'''
    global arg_imm16, var_imm16
    global arg_imm8_2, var_imm8_2

    fname = "{}_{}".format(enc_fn_prefix, ii.iclass.lower())

    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_legacy_enter")
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_imm16,'imm16')
    fo.add_arg(arg_imm8_2,'imm8')
    
    emit_required_legacy_prefixes(ii,fo)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)

    fo.add_code_eol('emit_u16(r,{})'.format(var_imm16))
    fo.add_code_eol('emit(r,{})'.format(var_imm8_2))
    add_enc_func(ii,fo)

def is_mov_crc32(ii):
    return ii.iclass == 'CRC32'

def is_lsl_regreg(ii):
    if ii.iclass == 'LSL':
        if not has_memop(ii):
            return True
    return False

def has_memop(ii):
    for op in _gen_opnds(ii):
        if op_mem(op):
            return True
    return False


def get_opnds(ii):
    opnds = []
    for op in _gen_opnds(ii):
        opnds.append(op)
    return opnds

def compute_widths_crc32(env,ii): 
    '''return a dict by osz of {op1-width,op2-width}. Also for LSL '''
    opnd_types = get_opnd_types_short(ii)
    if env.mode == 16:
        if opnd_types == ['y','v']:
            return { 16:{32,16}, 32:{32,32} }
        elif opnd_types == ['y','b']:
            return { 16:{32,8} }
        elif opnd_types == ['v','z']:
            return { 16:{16,16}, 32:{32,32} }
    elif env.mode == 32:
        if opnd_types == ['y','v']:
            return { 16: {32,16}, 32:{32,32} }
        elif opnd_types == ['y','b']:
            return { 32:{32,8} }
        elif opnd_types == ['v','z']:
            return { 16:{16,16}, 32:{32,32} }
    elif env.mode == 64:
        if opnd_types == ['y','v']:
            return { 16: {32,16}, 32:{32,32}, 64:{64,64} }
        elif opnd_types == ['y','b']:
            return { 32:{32,8}, 64:{64,8} }
        elif opnd_types == ['v','z']:
            return { 16:{16,16}, 32:{32,32}, 64:{64,32} }
    die("not reached")
        
    

def create_legacy_crc32_mem(env,ii):
    '''GPRy+MEMv or GPRy+MEMb'''
    global gpry_names, arg_request, enc_fn_prefix
    config =  compute_widths_crc32(env,ii)
    osz_list = list(config.keys())
    dispsz_list = get_dispsz_list(env)
    opnd_types = get_opnd_types_short(ii)

    ispace = itertools.product(osz_list, get_index_vals(ii), dispsz_list)
    for osz, use_index, dispsz in ispace:
        #op_widths = config[osz]
        opsig = make_opnd_signature(env,ii,osz)
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = '{}_{}_{}_{}'.format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opsig,
                                     memaddrsig)
                                     
        fo = make_function_object(env,ii,fname,asz=env.asz)
        fo.add_comment("created by create_legacy_crc32_mem")
        fo.add_arg(arg_request,'req')
        op = first_opnd(ii)
        if op.oc2 == 'y':
            reg = gpry_names[osz]
            fo.add_arg(arg_reg_type + reg, reg)
        else:
            die("NOT REACHED")
        add_memop_args(env, ii, fo, use_index, dispsz, osz=osz)
        
        rexw_forced = emit_legacy_osz(env,ii,fo,osz)
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(reg, reg))
        emit_required_legacy_prefixes(ii,fo)
        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))
        encode_mem_operand(env, ii, fo, use_index, dispsz)
        immw=0
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced, space='legacy')
        add_enc_func(ii,fo)

def cond_emit_rexw(env,ii,fo,osz):        
    rexw_forced = False
    if env.mode == 64:
        if ii.rexw_prefix == '1':
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)', 'required by instr')
        elif osz == 64 and not ii.default_64b:
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)', 'required by osz=64')
    return rexw_forced


def emit_legacy_osz(env,ii,fo,osz):
    if env.mode in [32,64] and osz == 16:
        fo.add_code_eol('emit(r,0x66)','to set osz=16')
    elif env.mode == 16 and osz == 32:
        fo.add_code_eol('emit(r,0x66)','to set osz=32')
    rexw_forced = cond_emit_rexw(env,ii,fo,osz)
    return rexw_forced


def create_legacy_crc32_reg(env,ii):
    '''CRC32-reg (GPRy-GPR{v,b}) and LSL (GPRv+GPRz)'''
    global gprv_names, gpry_names, gprz_names
    config =  compute_widths_crc32(env,ii)
    osz_list = list(config.keys())
    opnd_types = get_opnd_types_short(ii)
    
    for osz in osz_list:
        opsig = make_opnd_signature(env,ii,osz)
        fname = "{}_{}_{}".format(enc_fn_prefix, ii.iclass.lower(), opsig)
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_legacy_crc32_reg")
        fo.add_arg(arg_request,'req')
        reg_types_names =[]
        for i,otype in enumerate(opnd_types):
            if otype == 'y':
                reg = gpry_names[osz]
            elif otype == 'z':
                reg = gprz_names[osz]
            elif otype == 'b':
                reg = 'gpr8'
            elif otype == 'v':
                reg = gprv_names[osz]
            arg_name = '{}_{}'.format(reg,i)
            fo.add_arg(arg_reg_type +  arg_name, reg)
            reg_types_names.append((reg,arg_name))

        if modrm_reg_first_operand(ii):
            modrm_order = ['reg','rm']
        else:
            modrm_order = ['rm','reg']

        rexw_forced = emit_legacy_osz(env,ii,fo,osz)
        for i,(reg,arg) in enumerate(reg_types_names):
            fo.add_code_eol('enc_modrm_{}_{}(r,{})'.format(modrm_order[i], reg, arg))

        emit_required_legacy_prefixes(ii,fo)
        emit_rex(env, fo, rexw_forced)
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        emit_modrm(fo)
        add_enc_func(ii,fo)
            

def create_legacy_crc32(env,ii): 
    '''CRC32 is really strange. First operand is GPRy. Second operand is GPRv or GPR8 or MEMv or MEMb
       and bizarrely also LSL gprv+gprz'''
    if has_memop(ii):
        create_legacy_crc32_mem(env,ii)
    else:
        create_legacy_crc32_reg(env,ii)



def is_movdir64_or_enqcmd(ii):
    return ii.iclass in [ 'MOVDIR64B', 'ENQCMD', 'ENQCMDS']

def create_legacy_movdir64_or_enqcmd(env,ii):
    '''MOVDIR64B and ENQCMD* are a little unusual. They have 2 memops, one
       in an address-space-sized A_GPR_R and the other a normal
       memop.'''
    global arg_request, enc_fn_prefix, gprv_names
    ispace = itertools.product( get_index_vals(ii), get_dispsz_list(env))
    for use_index, dispsz in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        fname = '{}_{}_{}'.format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  memaddrsig)

        fo = make_function_object(env,ii,fname,asz=env.asz)
        fo.add_comment("created by create_legacy_movdir64")
        fo.add_arg(arg_request,'req')
        
        reg = gpry_names[env.asz]  # abuse the gprv names
        fo.add_arg(arg_reg_type +  reg, reg)
        add_memop_args(env, ii, fo, use_index, dispsz)

        # This operation is address-size modulated In 64b mode, 64b
        # addressing is the default. For non default 32b addressing in
        # 64b mode, we need a 67 prefix.
        if env.mode == 64 and env.asz == 32:
            emit_67_prefix(fo)
            
        # FIXME: REWORD COMMENT In 32b mode, we usually, but not always have
        # 32b addressing.  It is perfectly legit to have 32b mode with
        # 16b addressing in which case a 67 is not needed. Same (other
        # way around) for 16b mode. So we really do not need the 67
        # prefix ever outside of 64b mode as users are expected to use
        # the appropriate library for their addressing mode.
        #
        #elif env.mode == 32 and env.asz == 16:
        #    emit_67_prefix(fo)
        #elif env.mode == 16 and asz == 32:
        #    emit_67_prefix(fo)
        
        rexw_forced = False
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(reg, reg))
        emit_required_legacy_prefixes(ii,fo)
        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))
        encode_mem_operand(env, ii, fo, use_index, dispsz)
        immw=0
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced, space='legacy')
        add_enc_func(ii,fo)



def is_umonitor(ii):
    return ii.iclass == 'UMONITOR'

def create_legacy_umonitor(env,ii):
    '''ASZ-based GPR_B.'''
    global arg_request, enc_fn_prefix, gprv_names
    fname = '{}_{}'.format(enc_fn_prefix,
                           ii.iclass.lower())

    fo = make_function_object(env,ii,fname,asz=env.asz)
    fo.add_comment("created by create_legacy_umonitor")
    fo.add_arg(arg_request,'req')
    reg = gpry_names[env.asz]  # abuse the gprv names
    fo.add_arg(arg_reg_type +  reg, reg)

    # This operation is address-size modulated In 64b mode, 64b
    # addressing is the default. For non default 32b addressing in
    # 64b mode, we need a 67 prefix.
    if env.mode == 64 and env.asz == 32:
        emit_67_prefix(fo)
    # FIXME: REWORD COMMENT In 32b mode, we usually, but not always
    # have 32b addressing.  It is perfectly legit to have 32b mode
    # with 16b addressing in which case a 67 is not needed. Same
    # (other way around) for 16b mode. So we really do not need the 67
    # prefix ever outside of 64b mode as users are expected to use the
    # appropriate library for their addressing mode.
    #
    #elif env.mode == 32 and env.asz == 16:
    #    emit_67_prefix(fo)
    #elif env.mode == 16 and asz == 32:
    #    emit_67_prefix(fo)

    fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(reg, reg))
    if ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required),
                            'reg opcode extension')
    if ii.mod_required != 'unspecified':
        if ii.mod_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(ii.mod_required))

    emit_required_legacy_prefixes(ii,fo)
    emit_rex(env,fo,rex_forced=False)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

def is_ArAX_implicit(ii): # allows one implicit fixed reg
    a,implicit_fixed=0,0
    for op in _gen_opnds(ii):
        if op_luf_start(op,'ArAX'):
            a += 1
        elif op_reg(op) and op_implicit_specific_reg(op):
            implicit_fixed += 1
        else:
            return False
    return a==1 and implicit_fixed <= 1
        

def create_legacy_ArAX_implicit(env,ii):
    global arg_request, enc_fn_prefix
    fname = '{}_{}'.format(enc_fn_prefix,
                           ii.iclass.lower())

    fo = make_function_object(env,ii,fname, asz=env.asz)
    fo.add_comment("created by create_legacy_ArAX_implicit")
    fo.add_arg(arg_request,'req')

    # This operation is address-size modulated In 64b mode, 64b
    # addressing is the default. For non default 32b addressing in
    # 64b mode, we need a 67 prefix.
    if env.mode == 64 and env.asz == 32:
        emit_67_prefix(fo)
    # FIXME: REWORD COMMENT In 32b mode, we usually, but not always
    # have 32b addressing.  It is perfectly legit to have 32b mode
    # with 16b addressing in which case a 67 is not needed.  Same
    # (other way around) for 16b mode. So we really do not need the 67
    # prefix ever outside of 64b mode as users are expected to use the
    # appropriate library for their addressing mode.
    #
    #elif env.mode == 32 and env.asz == 16:
    #    emit_67_prefix(fo)
    #elif env.mode == 16 and asz == 32:
    #    emit_67_prefix(fo)


    if ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required),
                            'reg opcode extension')
    if ii.rm_required != 'unspecified':
        if ii.rm_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required),
                            'rm opcode extension')
    if ii.mod_required != 'unspecified':
        if ii.mod_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(ii.mod_required))

    emit_required_legacy_prefixes(ii,fo)
    #emit_rex(env,fo,rex_forced=False)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)

    
        
def _enc_legacy(env,ii):
        
    if is_ArAX_implicit(ii): # must be before one_nonmem_operand and zero_operands
        create_legacy_ArAX_implicit(env,ii)
    elif is_umonitor(ii): # must be before one_nonmem_operand and zero_oprands
        create_legacy_umonitor(env,ii)

    elif zero_operands(ii):# allows all-implicit too
        create_legacy_zero_operands(env,ii)
    elif one_implicit_gpr_imm8(ii):
        create_legacy_one_implicit_reg(env,ii,imm8=True)

    elif mov_without_modrm(ii):  # A0...A3, not B0,B8
        create_legacy_mov_without_modrm(env,ii)
        
    elif one_gpr_reg_one_mem_zp(ii):
        create_legacy_one_gpr_reg_one_mem_scalable(env,ii)
    elif one_gpr_reg_one_mem_scalable(ii):
        create_legacy_one_gpr_reg_one_mem_scalable(env,ii)
    elif one_scalable_gpr_and_one_mem(ii): # mem fixed or scalable, optional imm8,immz
        create_legacy_one_gpr_reg_one_mem_scalable(env,ii) # GPRyor GPRv with MEMv 
        
    elif one_gpr_reg_one_mem_fixed(ii):
        create_legacy_one_gpr_reg_one_mem_fixed(env,ii)
    elif two_gpr8_regs(ii):
        create_legacy_two_gpr8_regs(env,ii)
    elif two_scalable_regs(ii): # allow optional imm8,immz
        create_legacy_two_scalable_regs(env,ii,[16,32,64])
        
    elif two_gpr_one_scalable_one_fixed(ii): 
        create_legacy_two_gpr_one_scalable_one_fixed(env,ii)
        
    elif two_fixed_gprs(ii):
        create_legacy_two_fixed_gprs(env,ii)
    elif one_xmm_reg_imm8(ii):     # also SSE4 2-imm8 instr
        create_legacy_one_xmm_reg_imm8(env,ii)
    elif one_mmx_reg_imm8(ii):        
        create_legacy_one_mmx_reg_imm8(env,ii)
        
    elif two_fixed_regs_opti8(ii): 
        create_legacy_two_fixed_regs_opti8(env,ii)
        
    elif one_x87_reg(ii):
        create_legacy_one_x87_reg(env,ii)
    elif two_x87_reg(ii): # one implicit
        create_legacy_two_x87_reg(env,ii)
    elif one_x87_implicit_reg_one_memop(ii):
        create_legacy_one_mem_common(env,ii,imm=0)

    elif one_gprv_one_implicit(ii):  
        create_legacy_one_scalable_gpr(env, ii, [16,32,64], 'v')        
    elif one_gpr8_one_implicit(ii):  
        create_legacy_one_scalable_gpr(env, ii, [8], '8')
        
    elif one_nonmem_operand(ii):  
        create_legacy_one_nonmem_opnd(env,ii)  # branches out
    elif gpr8_imm8(ii):
        create_legacy_gpr_imm8(env,ii,[8])
    elif gprv_imm8(ii):
        create_legacy_gpr_imm8(env,ii,[16,32,64])
        
    elif gprv_immz(ii):
        create_legacy_gprv_immz(env,ii)
    elif gprv_immv(ii):
        create_legacy_gprv_immv(env,ii,imm=True)
    elif gprv_implicit_orax(ii):
        create_legacy_gprv_immv(env,ii,imm=False)
    elif orax_immz(ii):
        create_legacy_orax_immz(env,ii)
        
    elif is_far_xfer_nonmem(ii): 
        create_legacy_far_xfer_nonmem(env,ii)
    elif is_far_xfer_mem(ii): 
        create_legacy_far_xfer_mem(env,ii)
    elif one_mem_common(ii): # b,w,d,q,dq, v,y
        create_legacy_one_mem_common(env,ii,imm=0)
    elif one_mem_common_one_implicit_gpr(ii): # b,w,d,q,dq, v,y
        create_legacy_one_mem_common(env,ii,imm=0)
    elif one_mem_fixed_imm8(ii): 
        create_legacy_one_mem_common(env,ii,imm='8')
    elif one_mem_fixed_immz(ii): 
        create_legacy_one_mem_common(env,ii,imm='z')
    elif one_xmm_reg_one_mem_fixed_opti8(ii): # allows gpr32, gpr64, mmx too
        create_legacy_one_xmm_reg_one_mem_fixed(env,ii)
    elif is_enter_instr(ii):
        create_legacy_enter(env,ii)        
    elif is_mov_cr_dr(ii):
        create_mov_cr_dr(env,ii)        
    elif is_mov_seg(ii):
        create_mov_seg(env,ii)        
    elif is_mov_crc32(ii) or is_lsl_regreg(ii):
        create_legacy_crc32(env,ii)
    elif is_movdir64_or_enqcmd(ii):
        create_legacy_movdir64_or_enqcmd(env,ii)


def several_xymm_gpr_imm8(ii): # optional imm8
    i,x,y,d,q = 0,0,0,0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            x += 1
        elif op_reg(op) and op_ymm(op):
            y += 1
        elif op_gpr32(op) or op_vgpr32(op):
            d += 1
        elif op_gpr64(op) or op_vgpr64(op):
            q += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    simd = x + y
    gpr =  d + q
    if simd == 4 and gpr == 0:
        return True
    sum = simd + gpr
    return simd <= 3 and gpr <= 3  and i<=1 and sum<=3 and sum>0


def several_xymm_gpr_mem_imm8(ii): # optional imm8
    m,i,x,y,d,q,k = 0,0,0,0,0,0,0
    for op in _gen_opnds(ii):
        if op_mem(op):
            m += 1
        elif op_mask_reg(op):
            k += 1
        elif op_reg(op) and op_xmm(op):
            x += 1
        elif op_reg(op) and op_ymm(op):
            y += 1
        elif op_gpr32(op) or op_vgpr32(op):
            d += 1
        elif op_gpr64(op) or op_vgpr64(op):
            q += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    simd = x + y
    gpr =  d + q
    if m==1 and simd == 4 and gpr == 0:
        return True
    sum = simd + gpr + k
    return m==1 and simd <= 3 and gpr <= 3  and k <= 1 and i<=1 and sum<=3 and (sum>0 or m==1)


def two_ymm_and_mem(ii):
    m,n = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_ymm(op):
            n += 1
        elif op_mem(op):
            m += 1
        else:
            return False
    return n==2 and m==1

def set_vex_pp(ii,fo):
    # XED encodes VEX_PREFIX=2,3 values for F2,F3 so they need to be recoded before emitting.
    translate_pp_values = { 0:0, 1:1, 2:3, 3:2 }
    vex_prefix = re.compile(r'VEX_PREFIX=(?P<prefix>[0123])')
    m = vex_prefix.search(ii.pattern)
    if m:
        ppval = int(m.group('prefix'))
        real_pp = translate_pp_values[ppval]
        if real_pp:
            fo.add_code_eol('set_vexpp(r,{})'.format(real_pp))
    else:
        die("Could not find the VEX.PP pattern")

def largest_vl_vex(ii): # and evex
    vl = 0
    for op in _gen_opnds(ii):
        if op_xmm(op):
            vl = vl | 1
        elif op_ymm(op):
            vl = vl | 2
        elif op_zmm(op):
            vl = vl | 4
            
    if vl >= 4:
        return 'zmm'
    elif vl >= 2:
        return 'ymm'
    return 'xmm'


def get_type_size(op):
    a = re.sub(r'_.*','',op.lookupfn_name)
    a = re.sub('MASK','kreg',a)
    return re.sub(r'^[Vv]','',a).lower()


def count_operands(ii): # skip imm8
    x = 0
    for op in _gen_opnds(ii):
        if op_imm8(op):
            continue
        x += 1
    return x


def create_vex_simd_reg(env,ii):
    """Handle 2/3/4 xymm or gprs regs and optional imm8.  This is coded to
       allow different type and size for each operand.  Different
       x/ymm show up on converts. Also handles 2-imm8 SSE4a instr.   """
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_reg3,  var_reg3

    nopnds = count_operands(ii) # not imm8
    opnd_sig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opnd_sig)


    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_vex_simd_reg opnd_sig={} nopnds={}".format(opnd_sig,nopnds))
    fo.add_arg(arg_request,'req')
    opnd_types = get_opnd_types(env,ii)
    fo.add_arg(arg_reg0,opnd_types[0])
    if nopnds >= 2:
        fo.add_arg(arg_reg1, opnd_types[1])
        if nopnds >= 3:
            fo.add_arg(arg_reg2, opnd_types[2])
            if nopnds >= 4:
                fo.add_arg(arg_reg3, opnd_types[3])
    cond_add_imm_args(ii,fo)

    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    
    if ii.vl == '256': # ZERO INIT OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')
        
    fo.add_code_eol('set_mod(r,3)')

    vars = [var_reg0, var_reg1, var_reg2, var_reg3]

    var_r, var_b, var_n, var_se = None, None, None, None
    for i,op in enumerate(_gen_opnds(ii)):
        if op.lookupfn_name:
            if op.lookupfn_name.endswith('_R'):
                var_r,sz_r = vars[i], get_type_size(op)
            elif op.lookupfn_name.endswith('_B'):
                var_b,sz_b = vars[i], get_type_size(op)
            elif op.lookupfn_name.endswith('_N'):
                var_n,sz_n = vars[i], get_type_size(op)
            elif op.lookupfn_name.endswith('_SE'):
                var_se,sz_se = vars[i],get_type_size(op)
            else:
                die("SHOULD NOT REACH HERE")
    if ii.rexw_prefix == '1':
        fo.add_code_eol('set_rexw(r)')

    if var_n:
        fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        
    if var_r:
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(sz_r, var_r))
    elif ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
        
    if var_b:
        fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(sz_b, var_b))
    elif ii.rm_required != 'unspecified':
        if ii.rm_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
        
    if var_se:
        fo.add_code_eol('enc_imm8_reg_{}(r,{})'.format(sz_se, var_se))

    emit_vex_prefix(env, ii,fo,register_only=True)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    if ii.has_imm8:
        cond_emit_imm8(ii,fo)
    elif var_se:
        fo.add_code_eol('emit_se_imm8_reg(r)')
    add_enc_func(ii,fo)
    

def find_mempos(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if op_mem(op):
            return i
    die("NOT REACHED")
    
def create_vex_regs_mem(env,ii): 
    """0, 1, 2 or 3 xmm/ymm/gpr32/gpr64/kreg and 1 memory operand. allows imm8 optionally"""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_reg3,  var_reg3
    global arg_imm8

    nopnds = count_operands(ii) # skips imm8
    op = first_opnd(ii)
    width = op.oc2
    opsig = make_opnd_signature(env,ii)
    vlname = 'ymm' if ii.vl == '256' else 'xmm'
    immw=0
    if ii.has_imm8:
        immw=8
    dispsz_list = get_dispsz_list(env)
    opnd_types_org = get_opnd_types(env,ii)
    arg_regs = [ arg_reg0, arg_reg1, arg_reg2, arg_reg3 ]
    var_regs = [ var_reg0, var_reg1, var_reg2, var_reg3 ]
        
    ispace = itertools.product(get_index_vals(ii), dispsz_list)
    for use_index, dispsz  in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)

        fname = "{}_{}_{}_{}".format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opsig,
                                     memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_vex_regs_mem")
        fo.add_arg(arg_request,'req')
        opnd_types = copy.copy(opnd_types_org)

        regn = 0
        for i,optype in enumerate(opnd_types_org):
            if optype in ['xmm','ymm','zmm', 'gpr32', 'gpr64', 'kreg']:
                fo.add_arg(arg_regs[regn], opnd_types.pop(0))
                regn += 1
            elif optype in ['mem']:
                add_memop_args(env, ii, fo, use_index, dispsz, immw=0)
                opnd_types.pop(0)
            elif optype in 'int8':
                fo.add_arg(arg_imm8,'int8')
                opnd_types.pop(0) # imm8 is last so we technically can skip this pop
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))

        if ii.vl == '256': # Not setting VL=128 since that is ZERO OPTIMIZATION
            fo.add_code_eol('set_vexl(r,1)')
        
        # FIXME REFACTOR function-ize this
        var_r, var_b, var_n, var_se = None,None,None,None
        sz_r,  sz_b,  sz_n,  sz_se  = None,None,None,None
        for i,op in enumerate(_gen_opnds_nomem(ii)): # use no mem version to skip memop if a store-type op
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R'):
                    var_r,sz_r = var_regs[i],get_type_size(op)
                elif op.lookupfn_name.endswith('_B'):
                    var_b,sz_b = var_regs[i],get_type_size(op)
                elif op.lookupfn_name.endswith('_SE'):
                    var_se,sz_se = var_regs[i],get_type_size(op)
                elif op.lookupfn_name.endswith('_N'):
                    var_n,sz_n = var_regs[i],get_type_size(op)
                else:
                    die("SHOULD NOT REACH HERE")

        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if var_n == None:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        else:
            fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
            
        if var_r:
            fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(sz_r, var_r))
        elif ii.reg_required != 'unspecified':
            if ii.reg_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

        if var_b:
            fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(sz_b, var_b))
        elif ii.rm_required != 'unspecified':
            if ii.rm_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
                
        if var_se:
            if immw:
                immw=0
                fo.add_code_eol('enc_imm8_reg_{}_and_imm(r,{},{})'.format(sz_se, var_se, var_imm8))
            else:
                fo.add_code_eol('enc_imm8_reg_{}(r,{})'.format(sz_se, var_se))

        encode_mem_operand(env, ii, fo, use_index, dispsz)
        emit_vex_prefix(env, ii,fo,register_only=False)
        

        finish_memop(env, ii, fo, dispsz, immw,  space='vex')
        if var_se:
            fo.add_code_eol('emit_se_imm8_reg(r)')
        add_enc_func(ii,fo)


def create_vex_one_mask_reg_and_one_gpr(env,ii): 
    # FIXME: REFACTOR NOTE: could combine with create_vex_all_mask_reg
    #  if we handle 3 reg args and optional imm8.
    global arg_reg0, arg_reg1, var_reg0, var_reg1
    opsig = make_opnd_signature(env,ii)
    opnd_types = get_opnd_types(env,ii)
    arg_regs = [ arg_reg0, arg_reg1 ]
    var_regs = [ var_reg0, var_reg1 ]

    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_vex_one_mask_reg_and_one_gpr")
    fo.add_arg(arg_request,'req')
    
    for i,op in enumerate(opnd_types):
        fo.add_arg(arg_regs[i], opnd_types[i])
        
    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    if ii.vl == '256': # ZERO INIT OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')
        
    var_r, var_b, var_n = None,None,None
    for i,op in enumerate(_gen_opnds(ii)): 
        if op.lookupfn_name:
            if op.lookupfn_name.endswith('_R'):
                var_r,sz_r = var_regs[i],get_type_size(op)
            elif op.lookupfn_name.endswith('_B'):
                var_b,sz_b = var_regs[i],get_type_size(op)
            elif op.lookupfn_name.endswith('_N'):
                var_n,sz_n = var_regs[i],get_type_size(op)
            else:
                die("SHOULD NOT REACH HERE")
                
    fo.add_code_eol('set_mod(r,3)')
    if ii.rexw_prefix == '1':
        fo.add_code_eol('set_rexw(r)')

    if var_n:
        fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        
    if var_r:
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(sz_r, var_r))
    elif ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
        
    if var_b:
        fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(sz_b, var_b))
    elif ii.rm_required != 'unspecified':
        if ii.rm_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
            
    # FIXME: if kreg in MODRM.RM, we know we don't need to check rex.b
    # before picking c4/c5. MINOR PERF OPTIMIZATION
    emit_vex_prefix(env, ii,fo,register_only=True)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    add_enc_func(ii,fo)
        
def create_vex_all_mask_reg(env,ii):
    '''Allows optional imm8'''
    global enc_fn_prefix, arg_request
    global arg_kreg0, var_kreg0
    global arg_kreg1, var_kreg1
    global arg_kreg2, var_kreg2

    opsig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opsig)
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_vex_all_mask_reg")
    fo.add_arg(arg_request,'req')
    fo.add_arg(arg_kreg0,'kreg')
    if 'k_k' in opsig:
        fo.add_arg(arg_kreg1,'kreg')
    if 'k_k_k' in opsig:
        fo.add_arg(arg_kreg2,'kreg')
    if ii.has_imm8:
        add_arg_immv(fo,8)
        
    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    if ii.vl == '256': # Not setting VL=128 since that is ZERO OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')

    vars = [var_kreg0, var_kreg1, var_kreg2]
    var_r,var_b,var_n=None,None,None
    for i,op in enumerate(_gen_opnds(ii)):
        if op.lookupfn_name:
            if op.lookupfn_name.endswith('_R'):
                var_r = vars[i]
            elif op.lookupfn_name.endswith('_B'):
                var_b = vars[i]
            elif op.lookupfn_name.endswith('_N'):
                var_n = vars[i]
            else:
                die("SHOULD NOT REACH HERE")
    if ii.rexw_prefix == '1':
        fo.add_code_eol('set_rexw(r)')
    if var_n:
        fo.add_code_eol('enc_vex_vvvv_kreg(r,{})'.format(var_n))
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")

    if var_r:
        fo.add_code_eol('enc_modrm_reg_kreg(r,{})'.format(var_r))
    elif ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

    if var_b:
        fo.add_code_eol('enc_modrm_rm_kreg(r,{})'.format(var_b))
    elif ii.rm_required != 'unspecified':
        if ii.rm_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
    
    fo.add_code_eol('set_mod(r,3)')

    emit_vex_prefix(env, ii,fo,register_only=True)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    if ii.has_imm8:
        cond_emit_imm8(ii,fo)
    add_enc_func(ii,fo)

def vex_amx_mem(ii):
    if 'AMX' in ii.isa_set:
        for op in _gen_opnds(ii):
            if op_mem(op):
                return True
    return False

def vex_amx_reg(ii):
    if 'AMX' in ii.isa_set:
        for op in _gen_opnds(ii):
            if op_mem(op):
                return False
        return True
    return False

def create_vex_amx_reg(env,ii): # FIXME: XXX
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_reg3,  var_reg3

    nopnds = count_operands(ii) # not imm8
    opnd_sig = make_opnd_signature(env,ii)
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              opnd_sig)

    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_vex_amx_reg opnd_sig={} nopnds={}".format(opnd_sig,nopnds))
    fo.add_arg(arg_request,'req')
    opnd_types = get_opnd_types(env,ii)
    if nopnds >= 1:
        fo.add_arg(arg_reg0,opnd_types[0])
    if nopnds >= 2:
        fo.add_arg(arg_reg1, opnd_types[1])
        if nopnds >= 3:
            fo.add_arg(arg_reg2, opnd_types[2])
            if nopnds >= 4:
                fo.add_arg(arg_reg3, opnd_types[3])
    cond_add_imm_args(ii,fo)

    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    
    if ii.vl == '256': # ZERO INIT OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')
        
    fo.add_code_eol('set_mod(r,3)')

    vars = [var_reg0, var_reg1, var_reg2, var_reg3]

    var_r, var_b, var_n, var_se = None, None, None, None
    for i,op in enumerate(_gen_opnds(ii)):
        if op.lookupfn_name:
            if op.lookupfn_name.endswith('_R'):
                var_r,sz_r = vars[i], get_type_size(op)
            elif op.lookupfn_name.endswith('_B'):
                var_b,sz_b = vars[i], get_type_size(op)
            elif op.lookupfn_name.endswith('_N'):
                var_n,sz_n = vars[i], get_type_size(op)
            else:
                die("SHOULD NOT REACH HERE")
    if ii.rexw_prefix == '1':
        fo.add_code_eol('set_rexw(r)')

    if var_n:
        fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        
    if var_r:
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(sz_r, var_r))
    elif ii.reg_required != 'unspecified':
        if ii.reg_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
        
    if var_b:
        fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(sz_b, var_b))
    elif ii.rm_required != 'unspecified':
        if ii.rm_required: # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
        
    emit_vex_prefix(env, ii,fo,register_only=True)
    emit_opcode(ii,fo)
    emit_modrm(fo)
    if ii.has_imm8:
        cond_emit_imm8(ii,fo)
    elif var_se:
        fo.add_code_eol('emit_se_imm8_reg(r)')
    add_enc_func(ii,fo)
    

def create_vex_amx_mem(env,ii): # FIXME: XXX
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_reg3,  var_reg3
    global arg_imm8

    nopnds = count_operands(ii) # skips imm8
    op = first_opnd(ii)
    width = op.oc2
    opsig = make_opnd_signature(env,ii)
    immw=0
    if ii.has_imm8:
        immw=8
    dispsz_list = get_dispsz_list(env)
    opnd_types_org = get_opnd_types(env,ii)
    arg_regs = [ arg_reg0, arg_reg1, arg_reg2, arg_reg3 ]
    var_regs = [ var_reg0, var_reg1, var_reg2, var_reg3 ]
        
    ispace = itertools.product(get_index_vals(ii), dispsz_list)
    for use_index, dispsz  in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)

        fname = "{}_{}_{}_{}".format(enc_fn_prefix,
                                     ii.iclass.lower(),
                                     opsig,
                                     memaddrsig)

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_vex_amx_mem")
        fo.add_arg(arg_request,'req')
        opnd_types = copy.copy(opnd_types_org)

        regn = 0
        for i,optype in enumerate(opnd_types_org):
            if optype in ['tmm','xmm','ymm','zmm', 'gpr32', 'gpr64', 'kreg']:
                fo.add_arg(arg_regs[regn], opnd_types.pop(0))
                regn += 1
            elif optype in ['mem']:
                add_memop_args(env, ii, fo, use_index, dispsz, immw=0)
                opnd_types.pop(0)
            elif optype in 'int8':
                fo.add_arg(arg_imm8,'int8')
                opnd_types.pop(0) # imm8 is last so we technically can skip this pop
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))

        if ii.vl == '256': # Not setting VL=128 since that is ZERO OPTIMIZATION
            fo.add_code_eol('set_vexl(r,1)')
        
        # FIXME REFACTOR function-ize this
        var_r, var_b, var_n, var_se = None,None,None,None
        sz_r,  sz_b,  sz_n,  sz_se  = None,None,None,None
        for i,op in enumerate(_gen_opnds_nomem(ii)): # use no mem version to skip memop if a store-type op
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R'):
                    var_r,sz_r = var_regs[i],get_type_size(op)
                elif op.lookupfn_name.endswith('_B'):
                    var_b,sz_b = var_regs[i],get_type_size(op)
                elif op.lookupfn_name.endswith('_N'):
                    var_n,sz_n = var_regs[i],get_type_size(op)
                else:
                    die("SHOULD NOT REACH HERE")

        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if var_n == None:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        else:
            fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
            
        if var_r:
            fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(sz_r, var_r))
        elif ii.reg_required != 'unspecified':
            if ii.reg_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

        if var_b:
            fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(sz_b, var_b))
        elif ii.rm_required != 'unspecified':
            if ii.rm_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
                
        encode_mem_operand(env, ii, fo, use_index, dispsz)
        emit_vex_prefix(env, ii,fo,register_only=False)
        
        finish_memop(env, ii, fo, dispsz, immw,  space='vex')
        add_enc_func(ii,fo)

    
def _enc_vex(env,ii):
    if several_xymm_gpr_imm8(ii):
        create_vex_simd_reg(env,ii)
    elif several_xymm_gpr_mem_imm8(ii): # very generic
        create_vex_regs_mem(env,ii)
    elif vex_all_mask_reg(ii): # allows imm8
        create_vex_all_mask_reg(env,ii)
    elif vex_one_mask_reg_and_one_gpr(ii):
        create_vex_one_mask_reg_and_one_gpr(env,ii)
    elif vex_vzero(ii):
        create_vex_vzero(env,ii)
    elif vex_amx_reg(ii):
        create_vex_amx_reg(env,ii)
    elif vex_amx_mem(ii):
        create_vex_amx_mem(env,ii)
    
        
def vex_vzero(ii):
    return ii.iclass.startswith('VZERO')
    
def create_vex_vzero(env,ii): 
    fname = "{}_{}".format(enc_fn_prefix,
                           ii.iclass.lower())
    fo = make_function_object(env,ii,fname)
    fo.add_comment("created by create_vex_vzero")
    fo.add_arg(arg_request,'req')
    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    if ii.vl == '256': # ZERO INIT OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')
    if ii.rexw_prefix == '1': # could skip this because we know...
        fo.add_code_eol('set_rexw(r)')
    fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
    emit_vex_prefix(env, ii,fo,register_only=True) # could force C5 since we know...
    emit_opcode(ii,fo)  # no modrm on vzero* ... only exception in VEX space.
    add_enc_func(ii,fo)

    
def vex_all_mask_reg(ii): # allow imm8
    i,k = 0,0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            k += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return k>=2 and i<=1

def vex_one_mask_reg_and_one_gpr(ii): 
    g,k = 0,0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            k += 1
        elif op_gpr32(op) or op_gpr64(op):
            g += 1
        else:
            return False
    return k == 1 and g == 1


def evex_xyzmm_and_gpr(ii):
    i,d,q,x,y,z=0,0,0,0,0,0
    for op in _gen_opnds(ii):
        if op_xmm(op):
            x += 1
        elif op_ymm(op):
            y += 1
        elif op_zmm(op):
            z +=1
        elif op_imm8(op):
            i += 1
        elif op_gpr32(op):
            d += 1
        elif op_gpr64(op):
            q += 1
        else:
            return False
    simd = x + y + z 
    gprs = d + q
    return gprs == 1 and simd > 0 and simd < 3 and i <= 1

    
def evex_2or3xyzmm(ii): # allows for mixing widths of registers
    x,y,z=0,0,0
    for op in _gen_opnds(ii):
        if op_xmm(op):
            x = x + 1
        elif op_ymm(op):
            y = y + 1
        elif op_zmm(op):
            z = z + 1
        elif op_imm8(op):
            continue
        else:
            return False
    sum = x + y + z
    return sum == 2 or sum == 3


def evex_regs_mem(ii): #allow imm8 and kreg, gpr
    d,q, k,i,x, y,z,m = 0,0, 0,0,0, 0,0,0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            k += 1
        elif op_xmm(op):
            x += 1
        elif op_ymm(op):
            y += 1
        elif op_zmm(op):
            z += 1
        elif op_imm8(op):
            i += 1
        elif op_mem(op):
            m += 1
        elif op_gpr32(op) or op_vgpr32(op):
            d += 1
        elif op_gpr64(op) or op_vgpr64(op):
            q += 1
        else:
            return False
        simd = x+y+z
        gpr = d+q
    return m==1 and (gpr+simd)<3 and i<=1 and k <= 1


def create_evex_xyzmm_and_gpr(env,ii): 
    '''1,2,or3 xyzmm regs and 1 gpr32/64 and optional imm8 '''
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_kmask, var_kmask
    global arg_zeroing, var_zeroing
    global arg_rcsae, var_rcsae
    global arg_imm8, var_imm8
    global vl2names

    sae,rounding,imm8,masking_allowed=False,False,False,False
    if ii.sae_form:
        sae = True
    elif ii.rounding_form:
        rounding = True
    if ii.has_imm8:
        imm8 = True
    if ii.write_masking:
        masking_allowed = True
        
    vl = vl2names[ii.vl]
    mask_variant_name  = { False:'', True: '_msk' }

    opnd_sig = make_opnd_signature(env,ii)
        
    mask_versions = [False]
    if masking_allowed:
        mask_versions.append(True)

    reg_type_names = []
    for op in _gen_opnds(ii):
        if op_xmm(op):
            reg_type_names.append('xmm')
        elif op_ymm(op):
            reg_type_names.append('ymm')
        elif op_zmm(op):
            reg_type_names.append('zmm')
        elif op_gpr32(op):
            reg_type_names.append('gpr32')
        elif op_gpr64(op):
            reg_type_names.append('gpr64')

    nregs = len(reg_type_names)

    opnd_types_org = get_opnd_types(env,ii)    
    for masking in mask_versions:
        fname = "{}_{}_{}{}".format(enc_fn_prefix,
                                    ii.iclass.lower(),
                                    opnd_sig,
                                    mask_variant_name[masking])
        fo = make_function_object(env,ii,fname)
        fo.add_comment("created by create_evex_xyzmm_and_gpr")
        fo.add_arg(arg_request,'req')
        opnd_types = copy.copy(opnd_types_org)

        fo.add_arg(arg_reg0,opnd_types.pop(0))
        if masking:
            fo.add_arg(arg_kmask,'kreg')
            if not ii.write_masking_merging_only:
                fo.add_arg(arg_zeroing,'zeroing')
            
        fo.add_arg(arg_reg1,opnd_types.pop(0))
        if nregs == 3:
            fo.add_arg(arg_reg2, opnd_types.pop(0))
        if imm8:
            fo.add_arg(arg_imm8,'int8')
        if rounding:
            fo.add_arg(arg_rcsae,'rcsae')

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_mod(r,3)')

        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        set_evexll_vl(ii,fo,vl)
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
        if rounding:
            fo.add_code_eol('set_evexb(r,1)', 'set rc+sae')
            fo.add_code_eol('set_evexll(r,{})'.format(var_rcsae))
        elif sae:
            fo.add_code_eol('set_evexb(r,1)', 'set sae')
            # ZERO INIT OPTIMIZATION for EVEX.LL/RC = 0
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
            
        # ENCODE REGISTERS
        vars = [var_reg0, var_reg1, var_reg2]
        var_r, var_b, var_n = None, None, None
        for i,op in enumerate(_gen_opnds(ii)):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3') or op.lookupfn_name.endswith('_R'):
                    var_r, ri = vars[i], i
                elif op.lookupfn_name.endswith('_B3') or op.lookupfn_name.endswith('_B'):
                    var_b, bi = vars[i], i
                elif op.lookupfn_name.endswith('_N3') or op.lookupfn_name.endswith('_N'):
                    var_n, ni = vars[i], i
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(reg_type_names[ni], var_n))
        else:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")
            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(reg_type_names[ri], var_r))
        elif ii.reg_required != 'unspecified':
            if ii.reg_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
            
        if var_b:
            fo.add_code_eol('enc_evex_modrm_rm_{}(r,{})'.format(reg_type_names[bi], var_b))        
        elif ii.rm_required != 'unspecified':
            if ii.rm_required: # ZERO INIT OPTIMIZATION
                fo.add_code_eol('set_rm(r,{})'.format(ii.rm_required))
            
        fo.add_code_eol('emit_evex(r)')
        emit_opcode(ii,fo)
        emit_modrm(fo)
        if imm8:
            fo.add_code_eol('emit(r,{})'.format(var_imm8))
        add_enc_func(ii,fo)


def create_evex_regs_mem(env, ii):   
    """Handles 0,1,2 simd/gpr regs and one memop (including vsib) Allows imm8 also."""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    
    global arg_kmask, var_kmask
    global arg_zeroing, var_zeroing
    global arg_imm8, var_imm8
    var_regs = [var_reg0, var_reg1, var_reg2]
    arg_regs = [ arg_reg0, arg_reg1, arg_reg2 ]
    
    imm8=False
    if ii.has_imm8:
        imm8 = True

    vl = vl2names[ii.vl]
    mask_variant_name  = { False:'', True: '_msk' }
    

    mask_versions = [False]
    if ii.write_masking_notk0:
        mask_versions = [True]
    elif ii.write_masking:
        mask_versions = [False, True]
    else:
        mask_versions = [False]
        
    dispsz_list = get_dispsz_list(env)
    
    if ii.broadcast_allowed:
        bcast_vals = ['nobroadcast','broadcast']
    else:
        bcast_vals = ['nobroadcast']
    bcast_variant_name = {'nobroadcast':'', 'broadcast':'_bcast' }
    opnd_types_org = get_opnd_types(env,ii)

    
    # flatten a 4-deep nested loop using itertools.product()
    ispace = itertools.product(bcast_vals, get_index_vals(ii), dispsz_list, mask_versions)
    for broadcast, use_index, dispsz, masking in ispace:
        broadcast_bool = True if broadcast == 'broadcast' else False
        opnd_sig = make_opnd_signature(env,ii, broadcasting=broadcast_bool)
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        opnd_types = copy.copy(opnd_types_org)
        fname = "{}_{}_{}{}_{}{}".format(enc_fn_prefix,
                                         ii.iclass.lower(),
                                         opnd_sig,
                                         mask_variant_name[masking],
                                         memaddrsig,
                                         bcast_variant_name[broadcast])
        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_evex_regs_mem")
        fo.add_arg(arg_request,'req')

        # ==== ARGS =====
        def _add_mask_arg(ii,fo):
            global arg_kmask, arg_zeroing
            if ii.write_masking_notk0:
                kreg_comment = 'kreg!0'
            else:
                kreg_comment = 'kreg'
            fo.add_arg(arg_kmask,kreg_comment)

            if ii.write_masking_merging_only == False:
                fo.add_arg(arg_zeroing,'zeroing')
                
        gather_prefetch = is_gather_prefetch(ii)
        regn = 0
        for i,optype in enumerate(opnd_types_org):
            if i == 0 and  masking and gather_prefetch:
                _add_mask_arg(ii,fo)

            if optype in ['xmm','ymm','zmm','kreg','gpr32','gpr64']:
                fo.add_arg(arg_regs[regn], opnd_types.pop(0))
                regn += 1
            elif optype in ['mem']:
                add_memop_args(env, ii, fo, use_index, dispsz)
                opnd_types.pop(0)
            elif optype in 'int8':
                fo.add_arg(arg_imm8,'int8')
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))
            # add masking after 0th argument except for gather prefetch
            if i == 0 and  masking and not gather_prefetch:
                _add_mask_arg(ii,fo)

        # ===== ENCODING ======
        if dispsz in [16,32]: # the largest displacements 16 for 16b addressing, 32 for 32/64b addressing
            add_evex_displacement_var(fo)

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        set_evexll_vl(ii,fo,vl)
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
        if broadcast == 'broadcast': # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_evexb(r,1)')
            
        # ENCODE REGISTERS

        var_r, var_b, var_n = None, None, None
        sz_r,  sz_b,  sz_n  = None, None, None
        for i,op in enumerate(_gen_opnds_nomem(ii)):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3') or op.lookupfn_name.endswith('_R'):
                    var_r,sz_r = var_regs[i], get_type_size(op)
                elif op.lookupfn_name.endswith('_B3') or op.lookupfn_name.endswith('_B'):
                    var_b,sz_b = var_regs[i], get_type_size(op)
                elif op.lookupfn_name.endswith('_N3') or op.lookupfn_name.endswith('_N'):
                    var_n,sz_n = var_regs[i], get_type_size(op)
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(sz_n, var_n))
        else:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")
            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(sz_r, var_r))
        else:
            # some instructions use _N3 as dest (like rotates)
            #fo.add_code_eol('set_rexr(r,1)')
            #fo.add_code_eol('set_evexrr(r,1)')
            if ii.reg_required != 'unspecified':
                if ii.reg_required: # ZERO INIT OPTIMIZATION
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

        if var_b:
            die("SHOULD NOT REACH HERE")
            
        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            if mod == 2:
                broadcasting = True if broadcast == 'broadcast' else False
                chose_evex_scaled_disp(fo, ii, dispsz, broadcasting)
            else:
                fo.add_code_eol('set_mod(r,{})'.format(mod))
        
        encode_mem_operand(env, ii, fo, use_index, dispsz)  
        immw=8 if imm8 else 0
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced=False, space='evex')
        add_enc_func(ii,fo)

def evex_mask_dest_reg_only(ii): # optional imm8
    i,m,xyz=0,0,0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            m += 1
        elif op_xmm(op) or op_ymm(op) or op_zmm(op):
            xyz += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return m==1 and xyz > 0 and i <= 1


def evex_mask_dest_mem(ii): # optional imm8
    i,msk,xyz,mem=0,0,0,0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            msk += 1
        elif op_xmm(op) or op_ymm(op) or op_zmm(op):
            xyz += 1
        elif op_mem(op):
            mem += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return msk==1 and xyz > 0 and i <= 1 and mem==1


def create_evex_evex_mask_dest_reg_only(env, ii): # allows optional imm8
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    
    global arg_kmask, var_kmask # write mask
    global arg_kreg0, var_kreg0 # normal operand
    global arg_zeroing, var_zeroing
    global arg_imm8, var_imm8, arg_rcsae, var_rcsae

    imm8 = True if ii.has_imm8 else False
    vl = vl2names[ii.vl]
    mask_variant_name  = { False:'', True: '_msk' }
    opnd_sig = make_opnd_signature(env,ii)

    mask_versions = [False]
    if ii.write_masking_notk0:
        mask_versions = [True]
    elif ii.write_masking:
        mask_versions = [False, True]
    else:
        mask_versions = [False]
        
    opnd_types_org = get_opnd_types(env,ii)
    arg_regs = [ arg_reg0, arg_reg1 ]

    for masking in mask_versions:
        opnd_types = copy.copy(opnd_types_org)
        fname = "{}_{}_{}{}".format(enc_fn_prefix,
                                    ii.iclass.lower(),
                                    opnd_sig,
                                    mask_variant_name[masking])

        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_evex_evex_mask_dest_reg_only")
        fo.add_arg(arg_request,'req')

        # ==== ARGS =====

        regn = 0
        for i,optype in enumerate(opnd_types_org):
            if optype in [ 'kreg', 'kreg!0' ]:
                fo.add_arg(arg_kreg0, optype)
                opnd_types.pop(0)
            elif optype in ['xmm','ymm','zmm']:
                fo.add_arg(arg_regs[regn], opnd_types.pop(0))
                regn += 1
            elif optype in ['mem']:
                die("NOT REACHED")
            elif optype in 'int8':
                fo.add_arg(arg_imm8,'int8')
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))
            # add masking after 0th argument. 
            if i == 0 and  masking:
                if ii.write_masking_notk0:
                    kreg_comment = 'kreg!0'
                else:
                    kreg_comment = 'kreg'
                fo.add_arg(arg_kmask,kreg_comment)
                if ii.write_masking_merging_only == False:
                    fo.add_arg(arg_zeroing,'zeroing')
        if ii.rounding_form:
            fo.add_arg(arg_rcsae,'rcsae')

        # ===== ENCODING ======

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        set_evexll_vl(ii,fo,vl)
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
            
        if ii.rounding_form:
            fo.add_code_eol('set_evexb(r,1)', 'set rc+sae')
            fo.add_code_eol('set_evexll(r,{})'.format(var_rcsae))
        elif ii.sae_form:
            fo.add_code_eol('set_evexb(r,1)', 'set sae')
            # ZERO INIT OPTIMIZATION for EVEX.LL/RC = 0
            
        # ENCODE REGISTERS
        vars = [var_reg0, var_reg1, var_reg2]
        kvars = [var_kreg0, var_kreg1, var_kreg2]        
        i, var_r, var_b, var_n = 0, None, None, None
        j, kvar_r, kvar_b, kvar_n = 0, None, None, None
        for op in _gen_opnds_nomem(ii):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3'):
                    var_r = vars[i]
                    i += 1
                elif op.lookupfn_name.endswith('_B3'):
                    var_b = vars[i]
                    i += 1
                elif op.lookupfn_name.endswith('_N3'):
                    var_n = vars[i]
                    i += 1
                elif op_luf(op,'MASK_R'):
                    kvar_r = kvars[j]
                    j += 1
                elif op_luf(op,'MASK_B'):
                    kvar_b = kvars[j]
                    j += 1
                elif op_luf(op,'MASK_N'):
                    kvar_n = kvars[j]
                    j += 1
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(vl, var_n))
        elif kvar_n:
            fo.add_code_eol('enc_evex_vvvv_kreg(r,{})'.format(kvar_n))
        else:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")
            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(vl, var_r))
        elif kvar_r:
            fo.add_code_eol('enc_evex_modrm_reg_kreg(r,{})'.format(kvar_r))
        else:
            # some instructions use _N3 as dest (like rotates)
            #fo.add_code_eol('set_rexr(r,1)')
            #fo.add_code_eol('set_evexrr(r,1)')
            if ii.reg_required != 'unspecified':
                if ii.reg_required: # ZERO INIT OPTIMIZATION
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
                    
        if var_b:
            fo.add_code_eol('enc_evex_modrm_rm_{}(r,{})'.format(vl, var_b))        
        elif kvar_b:
            fo.add_code_eol('enc_evex_modrm_rm_kreg(r,{})'.format(kvar_b))        

        fo.add_code_eol('set_mod(r,3)')
        fo.add_code_eol('emit_evex(r)')
        emit_opcode(ii,fo)
        emit_modrm(fo)
        cond_emit_imm8(ii,fo)
        add_enc_func(ii,fo)


def create_evex_evex_mask_dest_mem(env, ii): # allows optional imm8
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    
    global arg_kmask, var_kmask # write mask
    global arg_kreg0, var_kreg0 # normal operand
    global arg_zeroing, var_zeroing
    global arg_imm8, var_imm8, arg_rcsae, var_rcsae

    imm8 = True if ii.has_imm8 else False
    vl = vl2names[ii.vl]
    mask_variant_name  = { False:'', True: '_msk' }


    mask_versions = [False]
    if ii.write_masking_notk0:
        mask_versions = [True]
    elif ii.write_masking:
        mask_versions = [False, True]
    else:
        mask_versions = [False]

    dispsz_list = get_dispsz_list(env)
    
    if ii.broadcast_allowed:
        bcast_vals = ['nobroadcast','broadcast']
    else:
        bcast_vals = ['nobroadcast']
    bcast_variant_name = {'nobroadcast':'', 'broadcast':'_bcast' }

    opnd_types_org = get_opnd_types(env,ii)
    arg_regs = [ arg_reg0, arg_reg1 ]
    
    # flatten a 4-deep nested loop using itertools.product()
    ispace = itertools.product(bcast_vals, get_index_vals(ii), dispsz_list, mask_versions)
    for broadcast, use_index, dispsz, masking in ispace:
        broadcast_bool = True if broadcast == 'broadcast' else False
        opnd_sig = make_opnd_signature(env,ii,broadcasting=broadcast_bool)
        memaddrsig = get_memsig(env.asz, use_index, dispsz)
        opnd_types = copy.copy(opnd_types_org)
        fname = "{}_{}_{}{}_{}{}".format(enc_fn_prefix,
                                         ii.iclass.lower(),
                                         opnd_sig,
                                         mask_variant_name[masking],
                                         memaddrsig,
                                         bcast_variant_name[broadcast])
        fo = make_function_object(env,ii,fname, asz=env.asz)
        fo.add_comment("created by create_evex_evex_mask_dest_mem")
        fo.add_arg(arg_request,'req')

        # ==== ARGS =====

        def _add_mask_arg(ii,fo):
            global arg_kmask, arg_zeroing
            if ii.write_masking_notk0:
                kreg_comment = 'kreg!0'
            else:
                kreg_comment = 'kreg'
            fo.add_arg(arg_kmask,kreg_comment)

            if ii.write_masking_merging_only == False:
                fo.add_arg(arg_zeroing,'zeroing')

        regn = 0
        for i,optype in enumerate(opnd_types_org):
            if optype in [ 'kreg' ]:
                fo.add_arg(arg_kreg0, optype)
                opnd_types.pop(0)
            elif optype in ['xmm','ymm','zmm']:
                fo.add_arg(arg_regs[regn], opnd_types.pop(0))
                regn += 1
            elif optype in ['mem']:
                add_memop_args(env, ii, fo, use_index, dispsz)
                opnd_types.pop(0)
            elif optype in 'int8':
                fo.add_arg(arg_imm8,'int8')
            else:
                die("UNHANDLED ARG {} in {}".format(optype, ii.iclass))
                
            # add masking after 0th argument
            if i == 0 and masking:
                _add_mask_arg(ii,fo)
                
        if ii.rounding_form:
            fo.add_arg(arg_rcsae,'rcsae')
                
        # ===== ENCODING ======
        if dispsz in [16,32]: # the largest displacements 16 for 16b addressing, 32 for 32/64b addressing
            add_evex_displacement_var(fo)

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        set_evexll_vl(ii,fo,vl)
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
        if broadcast == 'broadcast': # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_evexb(r,1)')
            
        if ii.rounding_form:
            fo.add_code_eol('set_evexb(r,1)', 'set rc+sae')
            fo.add_code_eol('set_evexll(r,{})'.format(var_rcsae))
        elif ii.sae_form:
            fo.add_code_eol('set_evexb(r,1)', 'set sae')
            # ZERO INIT OPTIMIZATION for EVEX.LL/RC = 0
            
        # ENCODE REGISTERS
        vars = [var_reg0, var_reg1, var_reg2]
        kvars = [var_kreg0, var_kreg1, var_kreg2]        
        i, var_r, var_b, var_n = 0, None, None, None
        j, kvar_r, kvar_b, kvar_n = 0, None, None, None
        for op in _gen_opnds_nomem(ii):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3'):
                    var_r = vars[i]
                    i += 1
                elif op.lookupfn_name.endswith('_B3'):
                    var_b = vars[i]
                    i += 1
                elif op.lookupfn_name.endswith('_N3'):
                    var_n = vars[i]
                    i += 1
                elif op_luf(op,'MASK_R'):
                    kvar_r = kvars[j]
                    j += 1
                elif op_luf(op,'MASK_B'):
                    kvar_b = kvars[j]
                    j += 1
                elif op_luf(op,'MASK_N'):
                    kvar_n = kvars[j]
                    j += 1
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(vl, var_n))
        elif kvar_n:
            fo.add_code_eol('enc_evex_vvvv_kreg(r,{})'.format(kvar_n))
        else:
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")
            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(vl, var_r))
        elif kvar_r:
            fo.add_code_eol('enc_evex_modrm_reg_kreg(r,{})'.format(kvar_r))
        else:
            # some instructions use _N3 as dest (like rotates)
            #fo.add_code_eol('set_rexr(r,1)')
            #fo.add_code_eol('set_evexrr(r,1)')
            if ii.reg_required != 'unspecified':
                if ii.reg_required: # ZERO INIT OPTIMIZATION
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
                    
        if var_b or kvar_b:
            die("SHOULD NOT REACH HERE")
        #if var_b:
        #    fo.add_code_eol('enc_evex_modrm_rm_{}(r,{})'.format(vl, var_b))        
        #elif kvar_b:
        #    fo.add_code_eol('enc_evex_modrm_rm_kreg(r,{})'.format(kvar_b))
        
        mod = get_modval(dispsz)
        if mod:  # ZERO-INIT OPTIMIZATION
            if mod == 2:
                broadcasting = True if broadcast == 'broadcast' else False
                chose_evex_scaled_disp(fo, ii, dispsz, broadcasting)
            else:
                fo.add_code_eol('set_mod(r,{})'.format(mod))

        encode_mem_operand(env, ii, fo, use_index, dispsz)  
        immw=8 if imm8 else 0
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced=False, space='evex')
        add_enc_func(ii,fo)

        
        
def _enc_evex(env,ii):
    # handles rounding, norounding, imm8, no-imm8, masking/nomasking
    if evex_2or3xyzmm(ii):
        create_evex_xyzmm_and_gpr(env,ii)
    elif evex_xyzmm_and_gpr(ii):
        create_evex_xyzmm_and_gpr(env,ii)

    elif evex_regs_mem(ii):  # opt imm8, very broad coverage including kreg(dest) ops
        create_evex_regs_mem(env, ii)
        
    elif evex_mask_dest_reg_only(ii): 
        create_evex_evex_mask_dest_reg_only(env, ii)
    elif evex_mask_dest_mem(ii): 
        create_evex_evex_mask_dest_mem(env, ii) # FIXME: no longer used

        
def _enc_xop(env,ii):
    pass # FIXME: could support XOP instr -- not planned as AMD deprecating them.

def prep_instruction(ii):
    setattr(ii,'encoder_functions',[])
    setattr(ii,'encoder_skipped',False)

    ii.write_masking = False
    ii.write_masking_notk0 = False
    ii.write_masking_merging_only = False # if true, no zeroing allowed
    ii.rounding_form = False
    ii.sae_form = False
    
    if ii.space == 'evex':
        for op in ii.parsed_operands:
            if op.lookupfn_name == 'MASK1':
                ii.write_masking = True
            elif op.lookupfn_name == 'MASKNOT0':
                ii.write_masking = True
                ii.write_masking_notk0 = True

        if ii.write_masking:
            if 'ZEROING=0' in ii.pattern:
                ii.write_masking_merging_only = True
                
        if 'AVX512_ROUND()' in ii.pattern:
            ii.rounding_form = True
        if 'SAE()' in ii.pattern:
            ii.sae_form = True


def xed_mode_removal(env,ii):
    if 'CLDEMOTE=0' in ii.pattern:
        return True
    if 'LZCNT=0' in ii.pattern:
        return True
    if 'TZCNT=0' in ii.pattern:
        return True
    if 'WBNOINVD=0' in ii.pattern:
        return True
    if 'P4=0' in ii.pattern:
        return True
    if 'MODEP5=1' in ii.pattern:
        return True
    if 'CET=0' in ii.pattern:
        return True
    if env.short_ud0:
        if 'MODE_SHORT_UD0=0' in ii.pattern: # long UD0
            return True # skip
    else: #  long ud0
        if 'MODE_SHORT_UD0=1' in ii.pattern: # short UD0
            return True # skip
    return False

    
def create_enc_fn(env, ii):
    if env.asz == 16:
        if special_index_cases(ii):
            ii.encoder_skipped = True
            return
        
    if xed_mode_removal(env,ii):
        ii.encoder_skipped = True
        return
    
    elif env.mode == 64:
        if ii.mode_restriction == 'not64' or ii.mode_restriction in [0,1]:
            # we don't need an encoder function for this form in 64b mode
            ii.encoder_skipped = True 
            return
        if ii.easz == 'a16':
            # 16b addressing not accessible from 64b mode
            ii.encoder_skipped = True 
            return
            
    elif env.mode == 32:
        if ii.mode_restriction in [0,2]:
            # we don't need an encoder function for this form in 32b mode
            ii.encoder_skipped = True 
            return
        if ii.easz == 'a64':
            # 64b addressing not accessible from 64b mode
            ii.encoder_skipped = True 
            return
        if ii.space == 'legacy' and (ii.eosz == 'o64' or ii.rexw_prefix == '1'):
            # legacy ops with REX.W=1 or EOSZ=3 are 64b mode only
            ii.encoder_skipped = True 
            return
            

    elif env.mode == 16:
        if ii.mode_restriction in [1,2]:
            # we don't need an encoder function for this form in 16b mode
            ii.encoder_skipped = True 
            return
        if ii.easz == 'a64':
            # 64b addressing not accessible from 16b mode
            ii.encoder_skipped = True 
            return
        if ii.space == 'legacy' and (ii.eosz == 'o64' or ii.rexw_prefix == '1'):
            # legacy ops with REX.W=1 or EOSZ=3 are 64b mode only
            ii.encoder_skipped = True 
            return

    if ii.space == 'legacy':
        _enc_legacy(env,ii)
    elif ii.space == 'vex':
        _enc_vex(env,ii)
    elif ii.space == 'evex':
        _enc_evex(env,ii)
    elif ii.space == 'xop':
        _enc_xop(env,ii)
    else:
        die("Unhandled encoding space: {}".format(ii.space))
        
def spew(ii):
    """Print information about the instruction. Purely decorative"""
    s = [ii.iclass.lower()]
    if ii.iform:
        s.append(ii.iform)
    else:
        s.append("NOIFORM")
    s.append(ii.space)
    s.append(ii.isa_set)
    s.append(hex(ii.opcode_base10))
    s.append(str(ii.map))
    #dbg('XA: {}'.format(" ".join(s)))
    # dump_fields(ii)

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

    if ii.space == 'evex':
        if ii.avx512_tuple:
            mwc = ii.memop_width_code if hasattr(ii,'memop_width_code') else 'MWC???'
            mw = ii.memop_width if hasattr(ii,'memop_width') else 'MW???'
            s.append("TUP:{}-{}-{}-{}".format(ii.avx512_tuple,ii.element_size,mwc,mw))
        else:
            s.append("no-tuple")
        if ii.write_masking:
            s.append('masking')
            if ii.write_masking_merging_only:
                s.append('nz')
            if ii.write_masking_notk0:
                s.append('!k0')
        else:
            s.append('nomasking')

    if ii.space == 'evex':
        if ii.rounding_form:
            s.append('rounding')
        elif ii.sae_form:
            s.append('sae')
        else:
            s.append('noround')
        
    for op in _gen_opnds(ii):
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
            if ii.avx512_vsib:
                s[-1] = s[-1] + '-uvsib-{}'.format(ii.avx512_vsib)
            elif ii.avx_vsib:
                s[-1] = s[-1] + '-vsib-{}'.format(ii.avx_vsib)
                
    if ii.encoder_functions:            
        dbg("//DONE {}".format(" ".join(s)))
    elif ii.encoder_skipped:
        dbg("//SKIP {}".format(" ".join(s)))
    else:
        dbg("//TODO {}".format(" ".join(s)))


def gather_stats(db):
    global numbered_functions
    unhandled = 0
    forms = len(db)
    generated_fns = 0
    skipped_fns = 0
    skipped_mpx = 0
    handled = 0
    not_done = { 'evex':0, 'vex':0, 'legacy':0, 'xop':0 }
    for ii in db:
        if ii.encoder_skipped:
            skipped_fns += 1
        elif ii.isa_set in ['MPX']:
            skipped_mpx += 1
        else:
            gen_fn = len(ii.encoder_functions)
            if gen_fn == 0:
                unhandled  = unhandled + 1
                not_done[ii.space] += 1
            else:
                handled += 1
                generated_fns += gen_fn
            
    skipped = skipped_mpx + skipped_fns
    tot_focus = handled + unhandled + skipped # not counting various skipped
    dbg("// Forms:       {:4d}".format(forms))
    dbg("// Handled:     {:4d}  ({:6.2f}%)".format(handled, 100.0*handled/tot_focus ))
    dbg("// Irrelevant:  {:4d}  ({:6.2f}%)".format(skipped, 100.0*skipped/tot_focus ))
    dbg("// Not handled: {:4d}  ({:6.2f}%)".format(unhandled, 100.0*unhandled/tot_focus))
    dbg("// Numbered functions:           {:5d}".format(numbered_functions))
    dbg("// Generated Encoding functions: {:5d}".format(generated_fns))
    dbg("// Skipped Encoding functions:   {:5d}".format(skipped_fns))
    dbg("// Skipped MPX instr:            {:5d}".format(skipped_mpx))
    for space in not_done.keys():
        dbg("// not-done {:8s}:   {:5d}".format(space, not_done[space]))

# object used for the env we pass to the generator
class enc_env_t(object):
    def __init__(self, mode, asz, width_info_dict, test_checked_interface=False, short_ud0=False):
        self.mode = mode
        self.asz = asz
        self.function_names = {}
        self.test_checked_interface = test_checked_interface
        self.tests_per_form = 1
        self.short_ud0 = short_ud0
        # dictionary by oc2 of the various memop bit widths. 
        self.width_info_dict = width_info_dict  
    def __str__(self):
        s = []
        s.append("mode {}".format(self.mode))
        s.append("asz {}".format(self.asz))
        return ", ".join(s)
    
    def mem_bits(self, width_name, osz=0):
        wi = self.width_info_dict[width_name]
        indx = osz if osz else 32
        return wi.widths[indx]



def dump_output_file_names(fn, fe_list):
    ofn = os.path.join(fn)
    o = open(ofn,"w")
    for fe in fe_list:
        o.write(fe.full_file_name + "\n")
    o.close()



def emit_encode_functions(args,
                          env,
                          xeddb,
                          function_type_name='encode',
                          fn_list_attr='encoder_functions',
                          config_prefix='',
                          srcdir='src',
                          extra_headers=None):
    msge("Writing encoder '{}' functions to .c and .h files".format(function_type_name))
    # group the instructions by encoding space to allow for
    # better link-time garbage collection.
    func_lists = collections.defaultdict(list)
    for ii in xeddb.recs:
        func_lists[ii.space].extend( getattr(ii, fn_list_attr) )
    func_list = []
    for space in func_lists.keys():
        func_list.extend(func_lists[space])

    config_descriptor = 'enc2-m{}-a{}'.format(env.mode, env.asz)                
    fn_prefix = 'xed-{}{}'.format(config_prefix,config_descriptor)

    gen_src_dir = os.path.join(args.gendir, config_descriptor, srcdir)
    gen_hdr_dir = os.path.join(args.gendir, config_descriptor, 'hdr', 'xed')
    mbuild.cmkdir(gen_src_dir)
    mbuild.cmkdir(gen_hdr_dir)

    file_emitters = codegen.emit_function_list(func_list,
                                               fn_prefix,
                                               args.xeddir,
                                               gen_src_dir,
                                               gen_hdr_dir,
                                               other_headers = extra_headers,
                                               max_lines_per_file=15000,
                                               is_private_header=False,
                                               extra_public_headers=['xed/xed-interface.h'])

    return file_emitters


    
def work():
    
    arg_parser = argparse.ArgumentParser(description="Create XED encoder2")
    arg_parser.add_argument('-short-ud0',
                            help='Encode 2-byte UD0 (default is long UD0 as  implemented on modern Intel Core processors. Intel Atom processors implement short 2-byte UD0)',
                            dest='short_ud0',
                            action='store_true',
                            default=False)

    arg_parser.add_argument('-m64',
                            help='64b mode (default)',
                            dest='modes', action='append_const', const=64)
    arg_parser.add_argument('-m32',
                            help='32b mode',
                            dest='modes', action='append_const', const=32)
    arg_parser.add_argument('-m16' ,
                            help='16b mode',
                            dest='modes', action='append_const', const=16)
    arg_parser.add_argument('-a64',
                            help='64b addressing (default)',
                            dest='asz_list', action='append_const', const=64)
    arg_parser.add_argument('-a32',
                            help='32b addressing',
                            dest='asz_list', action='append_const', const=32)
    arg_parser.add_argument('-a16' ,
                            help='16b addressing',
                            dest='asz_list', action='append_const', const=16)
    arg_parser.add_argument('-all',
                            action="store_true",
                            default=False,
                            help='all modes and addressing')
    arg_parser.add_argument('-chk',
                            action="store_true",
                            default=False,
                            help='Test checked interface')
    arg_parser.add_argument('--gendir',
                            help='output directory, default: "obj"',
                            default='obj')
    arg_parser.add_argument('--xeddir',
                            help='XED source directory, default: "."',
                            default='.')
    arg_parser.add_argument('--output-file-list',
                            dest='output_file_list',
                            help='Name of output file containing list of output files created. ' +
                            'Default: GENDIR/enc2-list-of-files.txt')


    args = arg_parser.parse_args()
    args.prefix = os.path.join(args.gendir,'dgen')
    if args.output_file_list == None:
        args.output_file_list = os.path.join(args.gendir, 'enc2-list-of-files.txt')
    def _mkstr(lst):
        s = [str(x) for x in lst]
        return  ":".join(s)
    dbg_fn = os.path.join(args.gendir,'enc2out-m{}-a{}.txt'.format(_mkstr(args.modes),
                                                                   _mkstr(args.asz_list)))
    msge("Writing {}".format(dbg_fn))
    set_dbg_output(open(dbg_fn,"w"))
    
    gen_setup.make_paths(args)
    msge('Reading XED db...')
    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename,
                                     args.cpuid_filename,
                                     args.map_descriptions)


    width_info_dict = xeddb.get_width_info_dict()
    for k in width_info_dict.keys():
        print("{} -> {}".format(k,width_info_dict[k]))
    
    # all modes and address sizes, filtered appropriately later
    if args.all:
        args.modes = [16,32,64]
        args.asz_list = [16,32,64]

    # if you just specify a mode, we supply the full set of address sizes
    if args.modes == [64]:
        if not args.asz_list:
            args.asz_list = [32,64]
    elif args.modes == [32]:
        if not args.asz_list:
            args.asz_list = [16,32]
    elif args.modes == [16]:
        if not args.asz_list:
            args.asz_list = [16,32]

    # default 64b mode, 64b address size
    if not args.modes:
        args.modes = [ 64 ]
        if not args.asz_list:
            args.asz_list = [ 64 ]
    
    for ii in xeddb.recs:
        prep_instruction(ii)
        
    def prune_asz_list_for_mode(mode,alist):
        '''make sure we only use addressing modes appropriate for our mode'''
        for asz in alist:
            if mode == 64:
                if asz in [32,64]:
                    yield asz
            elif asz != 64:
                yield asz


    output_file_emitters = []
        
    
    #extra_headers =  ['xed/xed-encode-direct.h']
    for mode in args.modes:
        for asz in prune_asz_list_for_mode(mode,args.asz_list):
            env = enc_env_t(mode, asz, width_info_dict,
                            short_ud0=args.short_ud0)
            enc2test.set_test_gen_counters(env)
            env.tests_per_form = 1
            env.test_checked_interface = args.chk
            
            msge("Generating encoder functions for {}".format(env))
            for ii in xeddb.recs:
                # create encoder function. sets ii.encoder_functions
                create_enc_fn(env, ii) 
                spew(ii)
                # create test(s) sets ii.enc_test_functions
                enc2test.create_test_fn_main(env, ii)
                # create arg checkers.  sets ii.enc_arg_check_functions
                enc2argcheck.create_arg_check_fn_main(env, ii) 

            fel = emit_encode_functions(args,
                                        env,
                                        xeddb,
                                        function_type_name='encode',
                                        fn_list_attr='encoder_functions',
                                        config_prefix='',
                                        srcdir='src')
            output_file_emitters.extend(fel)
            
            fel = emit_encode_functions(args,
                                        env,
                                        xeddb,
                                        function_type_name='encoder-check',
                                        fn_list_attr='enc_arg_check_functions',
                                        config_prefix='chk-',
                                        srcdir='src-chk',
                                        extra_headers = [ 'xed/xed-enc2-m{}-a{}.h'.format(env.mode, env.asz) ])
            output_file_emitters.extend(fel)


            msge("Writing encoder 'test' functions to .c and .h files")
            func_list = []
            iclasses = []
            for ii in xeddb.recs:
                func_list.extend(ii.enc_test_functions)
                # this is for the validation test to check  the iclass after decode
                n = len(ii.enc_test_functions)
                if n:
                    iclasses.extend(n*[ii.iclass])
                
            config_descriptor = 'enc2-m{}-a{}'.format(mode,asz)
            fn_prefix = 'xed-test-{}'.format(config_descriptor)
            test_fn_hdr='{}.h'.format(fn_prefix)
            enc2_fn_hdr='xed/xed-{}.h'.format(config_descriptor)
            enc2_chk_fn_hdr='xed/xed-chk-{}.h'.format(config_descriptor)            
            gen_src_dir = os.path.join(args.gendir, config_descriptor, 'test', 'src')
            gen_hdr_dir = os.path.join(args.gendir, config_descriptor, 'test', 'hdr')
            mbuild.cmkdir(gen_src_dir)
            mbuild.cmkdir(gen_hdr_dir)
                                       
            file_emitters = codegen.emit_function_list(func_list,
                                                       fn_prefix,
                                                       args.xeddir,
                                                       gen_src_dir,
                                                       gen_hdr_dir,
                                                       other_headers = [enc2_fn_hdr, enc2_chk_fn_hdr],
                                                       max_lines_per_file=15000)

            output_file_emitters.extend(file_emitters)


            

            # emit a C file initializing two arrays: one array with
            # test function names, and another of the functdion names
            # as strings so I can find them when I need to debug them.
            fe = codegen.xed_file_emitter_t(args.xeddir,
                                            gen_src_dir,
                                            'testtable-m{}-a{}.c'.format(mode,asz))

            fe.add_header(test_fn_hdr)
            fe.start()
            array_name = 'test_functions_m{}_a{}'.format(mode,asz)
            fe.add_code_eol('typedef xed_uint32_t (*test_func_t)(xed_uint8_t* output_buffer)')
            fe.add_code('test_func_t {}[] = {{'.format(array_name))
            for fn in func_list:
                fe.add_code('{},'.format(fn.get_function_name()))
            fe.add_code('0')
            fe.add_code('};')


            fe.add_code('char const* {}_str[] = {{'.format(array_name))
            for fn in func_list:
                fe.add_code('"{}",'.format(fn.get_function_name()))
            fe.add_code('0')
            fe.add_code('};')

            fe.add_code('const xed_iclass_enum_t {}_iclass[] = {{'.format(array_name))
            for iclass in iclasses:
                fe.add_code('XED_ICLASS_{},'.format(iclass))
            fe.add_code('XED_ICLASS_INVALID')
            fe.add_code('};')
            
            fe.close()
            output_file_emitters.append(fe)

            
            
    gather_stats(xeddb.recs)
    dump_numbered_function_creators()
    dump_output_file_names( args.output_file_list,
                            output_file_emitters )
    return 0

if __name__ == "__main__":
    r = work()
    sys.exit(r)
