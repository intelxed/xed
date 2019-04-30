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

import genutil
import codegen
import read_xed_db
import gen_setup

def die(s):
    genutil.die(s)

PY3 = sys.version_info > (3,)
def is_python3():
    global PY3
    return PY3
if is_python3() == False:
    die("This script requires python3\n")

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

var_base = 'base'
arg_base = 'xed_reg_enum_t ' + var_base
var_index = 'index'
arg_index = 'xed_reg_enum_t ' + var_index
var_scale = 'scale'
arg_scale = 'xed_uint_t ' + var_scale

var_disp8 = 'disp8'
arg_disp8 = 'xed_int8_t ' + var_disp8

var_disp16 = 'disp16'
arg_disp16 = 'xed_int16_t ' + var_disp16

var_disp32 = 'disp32'
arg_disp32 = 'xed_int32_t ' + var_disp32

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
var_imm32 = 'imm32'
arg_imm32 = 'xed_uint32_t ' + var_imm32
var_imm64 = 'imm64'
arg_imm64 = 'xed_uint64_t ' + var_imm64

dbg_output = sys.stdout

def dbg(s):
    global dbg_output
    print(s, file=dbg_output)

def msge(s):
    print(s, file=sys.stderr, flush=True)
def warn(s):
    print("\t"+s, file=sys.stderr, flush=True)
    #genutil.warn(s)
    
def _dump_fields(x):
    for fld in sorted(x.__dict__.keys()):
        msge("{}: {}".format(fld,getattr(x,fld)))
    msge("\n\n")

def _gen_opnds(ii): # generator
    # filter out write-mask operands and suppressed operands
    for op in ii.parsed_operands:
        if op.lookupfn_name == 'MASK1':
            continue
        if op.lookupfn_name == 'MASKNOT0':
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
    if op.lookupfn_name:
        if 'MASK' in op.lookupfn_name:
            return True
    return False
    
        
def op_scalable_v(op):
    if op.lookupfn_name:
        if 'GPRv' in op.lookupfn_name:
            return True
    if op.oc2 == 'v':
        return True
    return False
def op_gpr8(op):
    if op.lookupfn_name:
        if 'GPR8' in op.lookupfn_name:
            return True
    if op.oc2 == 'b':
        return True
    return False
def op_gprv(op):
    if op.lookupfn_name:
        if 'GPRv' in op.lookupfn_name:
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

def one_gpr_reg_one_mem_scalable(ii):
    n,r = 0,0
    for op in _gen_opnds(ii):
        if op_agen(op) or (op_mem(op) and op.oc2 in ['v']):
            n = n + 1
        elif op_gprv(op):
            r = r + 1
        else:
            return False
    return n==1 and r==1

def one_gpr_reg_one_mem_fixed(ii): # FIXME starting with 'b', expand...
    n,r = 0,0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b']:
            n = n + 1
        elif op_gpr8(op):
            r = r + 1
        else:
            return False
    return n==1 and r==1

simd_widths = ['xud', 'qq', 'dq', 'q', 'ps','pd', 'ss', 'sd', 'd', 'm384', 'xuq', 'zd']

def one_xmm_reg_one_mem_fixed(ii):
    global simd_widths
    n = 0
    r = 0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in simd_widths:
            n = n + 1
        elif op_reg(op) and op.oc2 in simd_widths:
            r = r + 1
        else:
            return False
    return n==1 and r==1
def one_xmm_reg_one_mem_fixed_imm8(ii): 
    global simd_widths
    i,r,n=0,0,0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in simd_widths:
            n = n + 1
        elif op_reg(op) and op.oc2 in simd_widths:
            r = r + 1
        elif op_imm8(op):
            i = i + 1
        else:
            return False
    return n==1 and r==1 and i==1

def one_mem_common(ii): # b,w,d,q,dq, v, y, etc.
    n = 0
    for op in _gen_opnds(ii):
        if op_mem(op) and op.oc2 in ['b','w','d','q','dq','v', 'y',
                                     'mem14','mem28','mem94','mem108',
                                     'mxsave', 'mprefetch' ]:
            n = n + 1
        else:
            return False
    return n==1

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
    
    
def two_scalable_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_scalable_v(op):
            n = n + 1
        else:
            return False
    return n==2
def op_implicit(op):
    return op.visibility == 'IMPLICIT'
    
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


def zero_operands(ii):
    n = 0
    for op in _gen_opnds(ii):
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

def two_xmm_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
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
def one_xmm_reg_imm8(ii):
    n = 0
    for i,op in enumerate(_gen_opnds(ii)):
        if op_reg(op) and op_xmm(op):
            n = n + 1
        elif i == 1 and op_imm8(op):
            continue
        else:
            return False
    return n==1
    
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

def two_mmx_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_mmx(op):
            n = n + 1
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
    if op.lookupfn_name and  op.lookupfn_name.endswith('_R'):
        return True
    return False

def emit_required_legacy_prefixes(ii,fo):
    if ii.iclass.endswith('_LOCK'):
        fo.add_code_eol('emit(r,0xF0)')
    if ii.f2_required:
        fo.add_code_eol('emit(r,0xF2)')
    if ii.f3_required:
        fo.add_code_eol('emit(r,0xF3)')
    if ii.osz_required:
        fo.add_code_eol('emit(r,0x66)')
def emit_required_legacy_map_escapes(ii,fo):
    if ii.map == 1:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 1')
    elif ii.map == 2:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 2')
        fo.add_code_eol('emit(r,0x38)', 'escape map 2')
    elif ii.map == 3:
        fo.add_code_eol('emit(r,0x0F)', 'escape map 3')
        fo.add_code_eol('emit(r,0x3A)', 'escape map 3')

def _gather_implicit_regs(ii):
    names = []
    for op in _gen_opnds(ii):
        if op_implicit(op):
            if op.name.startswith('REG'):
                if op.bits and op.bits.startswith('XED_REG_'):
                    reg_name = re.sub('XED_REG_','',op.bits).lower()
                    names.append(reg_name)
    return names

def emit_vex_prefix(ii,fo,register_only=False):
    if ii.map == 1 and ii.rexw_prefix != '1':
        # if any of x,b are set, need c4, else can use c5
        
        # performance: we know statically if something is register
        #        only.  In which case, we can avoid testing rexx.
        if register_only:
            fo.add_code('if  (get_rexb(r))')
        else:
            fo.add_code('if  (get_rexx(r) || get_rexb(r))')
        fo.add_code_eol('    emit_vex_c4(r)')
        fo.add_code('else')
        fo.add_code_eol('    emit_vex_c5(r)') 
    else:
        fo.add_code_eol('emit_vex_c4(r)')
    
def emit_opcode(ii,fo):
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
        fo.add_code_eol('set_mod(r,{})'.format(mod))
        fo.add_code_eol('set_reg(r,{})'.format(reg))
        fo.add_code_eol('set_rm(r,{})'.format(rm))
    return modrm_required

def make_function_object(env, fname, return_value='void'):
    if fname in env.function_names:
        t = env.function_names[fname] + 1
        env.function_names[fname] = t
        fname = fname + '_vr' + str(t)
        msge("Numbered function name for: {}".format(fname))
    else:
        env.function_names[fname] = 0

    fo = codegen.function_object_t(fname, return_value)
    return fo

def create_legacy_one_scalable_gpr(env,ii,osz_values,oc2):  
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0
    
    extra_names = _gather_implicit_regs(ii)
    if extra_names:
        extra_names = '_' + "_".join(extra_names)
    else:
        extra_names = ''

    for osz in osz_values:
        
        fname = "{}_{}{}_{}{}".format(enc_fn_prefix,
                                        ii.iclass.lower(),
                                        extra_names,
                                        'r' + oc2,
                                        '_o{}'.format(osz) if osz != 8 else '')
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_one_scalable_gpr")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        emit_required_legacy_prefixes(ii,fo)
        
        rexw_forced = False

        if env.mode == 64 and osz == 16:
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 64 and osz == 32 and ii.default_64b == True:
            continue # not encodable
        elif env.mode == 64 and osz == 64 and ii.default_64b == False:
            fo.add_code_eol('set_rexw(r)')
            rexw_forced = True
        elif env.mode == 32 and osz == 16:
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and osz == 32:
            fo.add_code_eol('emit(r,0x66)')
        elif ii.eosz in ['osznot16', 'osznot64']:  #FIXME
            fo.add_comment("Check handling of {}".format(ii.eosz))
            warn("Check handling of {} for: {} / {}".format(ii.eosz, ii.iclass, ii.iform))
        elif ii.eosz in ['oszall']: 
            pass

            
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
                _dump_fields(ii)
                die("SHOULD NOT HAVE A VALUE FOR  PARTIAL OPCODES HERE {} / {}".format(ii.iclass, ii.iform))

        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
                
        if ii.partial_opcode:
            emit_partial_opcode_variable_srm(ii,fo)
        else:
            emit_opcode(ii,fo)
            fo.add_code_eol('emit_modrm(r)')

        dbg(fo.emit())
        ii.encoder_functions.append(fo)


def create_legacy_one_gprv_partial(env,ii):
    pass  # FIXME    
def create_legacy_asz_rax(env,ii):
    pass # FIXME
def create_legacy_asz_gpr(env,ii):
    pass # FIXME
def create_legacy_one_imm_scalable(env,ii, osz_values):
    pass # FIXME

def create_legacy_one_gpr_fixed(env,ii,width_bits):
    global enc_fn_prefix, arg_request
    fname = "{}_{}_o{}".format(enc_fn_prefix, ii.iclass.lower(), width_bits)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_gpr_fixed")
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)    
    if width_bits == 8:
        pass
    elif width_bits == 16:
        pass
    elif width_bits == 32:
        pass
    elif width_bits == 64:
        pass
    else:
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
    fo.add_code_eol('emit_modrm(r)')
    dbg(fo.emit())
    ii.encoder_functions.append(fo)



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
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_relbr")
        fo.add_arg(arg_request)
        if osz == 8:
            fo.add_arg(arg_disp8)
        elif osz == 16:
            fo.add_arg(arg_disp16)
        elif osz == 32:
            fo.add_arg(arg_disp32)
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
            fo.add_code_eol('emit_modrm(r)')
        if osz == 8:
            fo.add_code_eol('emit_i8(r,{})'.format(var_disp8))
        elif osz == 16:
            fo.add_code_eol('emit_i16(r,{})'.format(var_disp16))
        elif osz == 32:
            fo.add_code_eol('emit_i32(r,{})'.format(var_disp32))
        dbg(fo.emit())
        ii.encoder_functions.append(fo)


def create_legacy_one_imm_fixed(env,ii):
    global enc_fn_prefix, arg_request

    fname = "{}_{}".format(enc_fn_prefix,
                           ii.iclass.lower())
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_imm_fixed")
    op = first_opnd(ii)

    fo.add_arg(arg_request)
    if op.oc2 == 'b':
        fo.add_arg(arg_imm8)
    elif op.oc2 == 'w':
        fo.add_arg(arg_imm16)
    else:
        die("not handling imm width {}".format(op.oc2))
        
    modrm_required = create_modrm_byte(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    if modrm_required:
        fo.add_code_eol('emit_modrm(r)')
    if op.oc2 == 'b':
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    elif op.oc2 == 'w':
        fo.add_code_eol('emit(r,{}&0xFF)'.format(var_imm16))
        fo.add_code_eol('emit(r,({}>>8)&0xFF)'.format(var_imm16))


    dbg(fo.emit())
    ii.encoder_functions.append(fo)


def create_legacy_one_implicit_reg(env,ii,imm8=False):
    global enc_fn_prefix, arg_request, arg_imm8, var_imm8

    sig = '_i8' if imm8 else ''
    fname = "{}_{}{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              sig)
    # "push es" needs the es as part of the function name
    extra_names = _gather_implicit_regs(ii)
    if extra_names:
        fname = fname + '_' + "_".join(extra_names)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_implicit_reg")

    fo.add_arg(arg_request)
    if imm8:
        fo.add_arg(arg_imm8)
    modrm_required = create_modrm_byte(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    if modrm_required:
        fo.add_code_eol('emit_modrm(r)')
    if imm8:
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    dbg(fo.emit())
    ii.encoder_functions.append(fo)
    
    
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
        elif op.lookupfn_name.startswith('GPRv_SB'):
            create_legacy_one_gprv_partial(env,ii)
        elif op.lookupfn_name.startswith('ArAX'):
            create_legacy_asz_rax(env,ii)
        elif op.lookupfn_name.startswith('A_GPR_'):
            create_legacy_asz_gpr(env,ii)
        else:
            warn("Need to handle {} in {}".format(
                op.lookupfn_name,
                "create_legacy_one_nonmem_opnd"))
    elif op_implicit(op) and op.name.startswith('REG'):
        create_legacy_one_implicit_reg(env,ii,imm8=False)
    else:
        warn("Need to handle {} in {}".format(
            op, "create_legacy_one_nonmem_opnd"))


def create_legacy_no_operands(env,ii):
    global enc_fn_prefix, arg_request
    
    if env.mode == 64 and ii.easz == 'a16':
        ii.encoder_skipped = True
        return
    
    fname = "{}_{}".format(enc_fn_prefix,
                           ii.iclass.lower())
    if ii.easz in ['a16','a32','a64']:
        fname = fname + '_' + ii.easz
    if ii.eosz in ['o16','o32','o64']:
        fname = fname + '_' + ii.eosz
        
    fo = make_function_object(env,fname)
    fo.add_comment("created by created_legacy_no_operands")
    fo.add_arg(arg_request)

    modrm_required = create_modrm_byte(ii,fo)
    
    # twiddle ASZ if specified
    if env.mode == 64 and ii.easz == 'a32':
        fo.add_code_eol('emit(r,0x67)')
    elif env.mode == 32 and ii.easz == 'a16':
        fo.add_code_eol('emit(r,0x67)')
    elif env.mode == 16 and ii.easz == 'a32':
        fo.add_code_eol('emit(r,0x67)')

    # twiddle OSZ ... FIXME: might need to do something for oszall
    if not ii.osz_required:
        if env.mode == 64 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 64 and ii.eosz == 'o64' and ii.default_64b == False:
            fo.add_code_eol('set_rexw(r)')
        elif env.mode == 32 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif ii.eosz in ['osznot16', 'osznot64']:  #FIXME
            fo.add_comment("Check handling of {}".format(ii.eosz))
            warn("Check handling of {} for: {} / {}".format(ii.eosz, ii.iclass, ii.iform))
        elif ii.eosz in ['oszall']:  # FIXME
            fo.add_comment("Check handling of oszall.")
            warn("Check handling of {} for: {} / {}".format(ii.eosz, ii.iclass, ii.iform))
            

    emit_required_legacy_prefixes(ii,fo)

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
            fo.add_code_eol('emit_modrm(r)')
    dbg(fo.emit())
    ii.encoder_functions.append(fo)

        

def two_fixed_gprs(ii):
    width = None
    n = 0 # count of the number of GPR32 or GPR64 stuff we encounter
    c = 0 # operand count, avoid stray stuff
    for op in _gen_opnds(ii):
        c += 1
        for w in [32,64]:
            if op_luf_start(op,'GPR{}'.format(w)):
                if not width:
                    width = w
                    n += 1
                elif width != w:
                    return False
                else:
                    n += 1
    return width and n == 2 and c == 2
        
def create_legacy_two_fixed_gprs(env,ii):
    op = first_opnd(ii)
    if op_luf_start(op,'GPR32'):
        create_legacy_two_scalable_regs(env,ii,[32])
    elif op_luf_start(op,'GPR64'):
        create_legacy_two_scalable_regs(env,ii,[64])
    else:
        die("NOT REACHED")
        
def create_legacy_two_scalable_regs(env, ii, osz_list):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    
    for osz in gen_osz_list(env.mode,osz_list):
        fname = "{}_{}_{}_o{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      'rvrv',
                                      osz)
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_two_scalable_regs")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        fo.add_arg(arg_reg1)
        emit_required_legacy_prefixes(ii,fo)
        if not ii.osz_required:
            if osz == 16 and env.mode != 16:
                # add a 66 prefix outside of 16b mode, to create 16b osz
                fo.add_code_eol('emit(r,0x66)')
            if osz == 32 and env.mode == 16:
                # add a 66 prefix outside inside 16b mode to create 32b osz
                fo.add_code_eol('emit(r,0x66)')

        rexw_forced = False
        if osz == 64 and ii.default_64b == False:
            rexw_forced = True
            fo.add_code_eol('set_rexw(r)')

        if modrm_reg_first_operand(ii):
            f1, f2 = 'reg','rm'
        else:
            f1, f2 = 'rm','reg'
        fo.add_code_eol('enc_modrm_{}_gpr{}(r,reg0)'.format(f1,osz))
        fo.add_code_eol('enc_modrm_{}_gpr{}(r,reg1)'.format(f2,osz))
        
        # checking rexw_forced saves a conditional branch in 64b operations
        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
        else:
            emit_opcode(ii,fo)
            fo.add_code_eol('emit_modrm(r)')
        dbg(fo.emit())
        ii.encoder_functions.append(fo)
            


def create_legacy_two_gpr8_regs(env, ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              'r8r8')
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_two_gpr8_regs")
            
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    fo.add_arg(arg_reg1)
    emit_required_legacy_prefixes(ii,fo)

    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_gpr8(r,reg0)'.format(f1))
    fo.add_code_eol('enc_modrm_{}_gpr8(r,reg1)'.format(f2))
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)

    if ii.partial_opcode:
        die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
    else:
        emit_opcode(ii,fo)
        fo.add_code_eol('emit_modrm(r)')
    dbg(fo.emit())
    ii.encoder_functions.append(fo)
        
def cond_emit_imm8(ii,fo):
    global arg_imm8, arg_imm8_2
    if ii.has_imm8:
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
    if ii.has_imm8_2:
        fo.add_code_eol('emit(r,{})'.format(var_imm8_2))
def cond_add_imm_args(ii,fo):
    global arg_imm8, arg_imm8_2
    if ii.has_imm8:
        fo.add_arg(arg_imm8)
    if ii.has_imm8_2:
        fo.add_arg(arg_imm8_2)

    
def create_legacy_two_xmm_regs(env,ii,imm8=False):
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_reg1, var_reg1
    global arg_imm8, var_imm8

    category = 'xmm' if imm8==False else 'xmmi'
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  category)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_two_xmm_regs")
        
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    fo.add_arg(arg_reg1)
        
    cond_add_imm_args(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('set_mod(r,3)')
    fo.add_code_eol('enc_modrm_{}_xmm(r,reg0)'.format(f1))
    fo.add_code_eol('enc_modrm_{}_xmm(r,reg1)'.format(f2))
    if env.mode == 64:
        fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    
    dbg(fo.emit())
    ii.encoder_functions.append(fo)


def create_legacy_one_mmx_reg_imm8(env,ii):
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_imm8, var_imm8

    category = 'mmxi'
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  category)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_mmx_reg_imm8")
        
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
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
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    dbg(fo.emit())
    ii.encoder_functions.append(fo)



def create_legacy_one_xmm_reg_imm8(env,ii):
    global enc_fn_prefix, arg_request
    global arg_reg0, var_reg0
    global arg_imm8, var_imm8

    category = 'xmmi'
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  category)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_xmm_reg_imm8")
        
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    cond_add_imm_args(ii,fo)
    
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_xmm(r,reg0)'.format(f1))
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
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    
    dbg(fo.emit())
    ii.encoder_functions.append(fo)
    

def create_legacy_two_mmx_regs(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'mmx')
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_two_mmx_regs")
        
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    fo.add_arg(arg_reg1)
    cond_add_imm_args(ii,fo)

    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_mmx(r,reg0)'.format(f1))
    fo.add_code_eol('enc_modrm_{}_mmx(r,reg1)'.format(f2))
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    dbg(fo.emit())
    ii.encoder_functions.append(fo)


def create_legacy_two_x87_reg(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0
    fname = "{}_{}_{}_st0".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'x87')
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_two_x87_reg")    
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    emit_required_legacy_prefixes(ii,fo)
    fo.add_code_eol('set_mod(r,3)')
    if ii.reg_required == 'unspecified':
        die("Need a value for MODRM.REG in x87 encoding")
    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    fo.add_code_eol('enc_modrm_rm_x87(r,reg0)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    dbg(fo.emit())
    ii.encoder_functions.append(fo)
    
def create_legacy_one_x87_reg(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'x87')
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_legacy_one_x87_reg")    
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    emit_required_legacy_prefixes(ii,fo)
    if ii.mod_required == 3:
        fo.add_code_eol('set_mod(r,3)')
    else:
        die("FUNKY MOD on x87 op: {}".format(ii.mod_required))
    if ii.reg_required == 'unspecified':
        die("Need a value for MODRM.REG in x87 encoding")
    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    fo.add_code_eol('enc_modrm_rm_x87(r,reg0)')
    emit_required_legacy_map_escapes(ii,fo)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    dbg(fo.emit())
    ii.encoder_functions.append(fo)

def gpr8_imm8(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and op_luf_start(op,'GPR8'): 
                continue
            else:
                return False
        elif i == 1:
            if op.name == 'IMM0' and op.oc2 == 'b':
                continue
            else:
                return False
        else:
            return False
    return True
            
def gprv_imm8(ii):
    for i,op in enumerate(_gen_opnds(ii)):
        if i == 0:
            if op.name == 'REG0' and  op_luf_start(op,'GPRv'):
                continue
            else:
                return False
        elif i == 1:
            if op.name == 'IMM0' and op.oc2 == 'b':
                continue
            else:
                return False
        else:
            return False
    return True

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
    global enc_fn_prefix, arg_request, arg_reg0, var_reg0, arg_imm8,  var_imm8
    
    for osz in gen_osz_list(env.mode,width_list):
        fname = "{}_{}_{}_o{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      'ri',
                                      osz)
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_gpr_imm8")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        fo.add_arg(arg_imm8)
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        if osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        # FIXME exclude osz=32 if df64
        rexw_forced = False            
        if env.mode == 64:
            if osz == 64 and ii.default_64b == False:
                rexw_forced = True
                fo.add_code_eol('set_rexw(r)')

        if ii.partial_opcode:
            fo.add_code_eol('enc_srm_gpr{}(r,{})'.format(osz, var_reg0))
        else:
            if modrm_reg_first_operand(ii):
                f1, f2 = 'reg','rm'
            else:
                f1, f2 = 'rm','reg'
            fo.add_code_eol('enc_modrm_{}_gpr{}(r,{})'.format(f1,osz,var_reg0))
            
        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            emit_partial_opcode_variable_srm(ii,fo)
        else:
            emit_opcode(ii,fo)
            fo.add_code_eol('emit_modrm(r)')
        fo.add_code_eol('emit(r,{})'.format(var_imm8))
        
        dbg(fo.emit())
        ii.encoder_functions.append(fo)


def create_legacy_gprv_immz(env,ii):
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_imm16, var_imm16
    global arg_imm32, var_imm32
    width_list = [16,32,64]
    arg_imm = { 16: arg_imm16, 32: arg_imm32, 64: arg_imm32 }
    var_imm = { 16: var_imm16, 32: var_imm32, 64: var_imm32 }
    emit_width_immz = { 16:16, 32:32, 64:32 }
    for osz in gen_osz_list(env.mode,width_list):
        fname = "{}_{}_{}_o{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      'ri',
                                      osz)
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_gprv_immz")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        fo.add_arg(arg_imm[osz])
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        if osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        # FIXME exclude osz=32 if df64
        rexw_forced = False            
        if env.mode == 64:
            if osz == 64 and ii.default_64b == False:
                rexw_forced = True
                fo.add_code_eol('set_rexw(r)')
                
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
        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        fo.add_code_eol('emit_modrm(r)')
        fo.add_code_eol('emit_u{}(r,{})'.format(emit_width_immz[osz],
                                                var_imm[osz]))
        
        dbg(fo.emit())
        ii.encoder_functions.append(fo)


def create_legacy_orax_immz(env,ii): 
    """Handles OrAX+IMMz. No MODRM byte"""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_imm16, var_imm16
    global arg_imm32, var_imm32

    width_list = [16,32,64]
    arg_imm = { 16: arg_imm16, 32: arg_imm32, 64: arg_imm32 }
    var_imm = { 16: var_imm16, 32: var_imm32, 64: var_imm32 }
    emit_width_immz = { 16:16, 32:32, 64:32 }

    rax_names = { 16: '_ax', 32:'_eax', 64:'_rax' }
    
    for osz in gen_osz_list(env.mode,width_list):
        fname = "{}_{}{}_{}_o{}".format(enc_fn_prefix,
                                        ii.iclass.lower(),
                                        rax_names[osz],
                                        'ri',
                                        osz)

        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_orax_immz")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        fo.add_arg(arg_imm[osz])
        
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        if osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        # FIXME exclude osz=32 if df64
        rexw_forced = False            
        if env.mode == 64:
            if osz == 64 and ii.default_64b == False:
                rexw_forced = True
                fo.add_code_eol('set_rexw(r)')

        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        emit_opcode(ii,fo)
        fo.add_code_eol('emit_u{}(r,{})'.format(emit_width_immz[osz],
                                                var_imm[osz]))
        
        dbg(fo.emit())
        ii.encoder_functions.append(fo)


def create_legacy_gprv_immv(env,ii,imm=False, implicit_orax=False):
    """Handles GPRv_SB-IMMv partial reg opcodes and GPRv_SB+OrAX implicit"""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_imm16, var_imm16
    global arg_imm32, var_imm32
    global arg_imm64, var_imm64
    width_list = [16,32,64]
    arg_imm = { 16: arg_imm16, 32: arg_imm32, 64: arg_imm64 }
    var_imm = { 16: var_imm16, 32: var_imm32, 64: var_imm64 }
    emit_width_immv = { 16:16, 32:32, 64:64 }

    rax_names = { 16: '_ax', 32:'_eax', 64:'_rax' }
    
    for osz in gen_osz_list(env.mode,width_list):
        if implicit_orax:
            extra_names = rax_names[osz]
        else:
            extra_names = ''
        fname = "{}_{}{}_{}o{}".format(enc_fn_prefix,
                                        ii.iclass.lower(),
                                        extra_names,
                                        'ri_' if imm else '',
                                        osz)

        fo = make_function_object(env,fname)
        fo.add_comment("created by create_legacy_gprv_immv")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        if imm:
            fo.add_arg(arg_imm[osz])
        emit_required_legacy_prefixes(ii,fo)
        if osz == 16 and env.mode != 16:
            # add a 66 prefix outside of 16b mode, to create 16b osz
            fo.add_code_eol('emit(r,0x66)')
        if osz == 32 and env.mode == 16:
            # add a 66 prefix outside inside 16b mode to create 32b osz
            fo.add_code_eol('emit(r,0x66)')
        # FIXME exclude osz=32 if df64
        rexw_forced = False            
        if env.mode == 64:
            if osz == 64 and ii.default_64b == False:
                rexw_forced = True
                fo.add_code_eol('set_rexw(r)')

        # WE know this is a SRM partial opcode instr
        if not ii.partial_opcode:
            die("Expecting partial opcode instruction in create_legacy_gprv_immv")

        op = first_opnd(ii)
        if op_luf(op,'GPRv_SB'):
            fo.add_code_eol('enc_srm_gpr{}(r,{})'.format(osz, var_reg0))
        else:
            die("NOT REACHED")

        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        emit_partial_opcode_variable_srm(ii,fo)
        if imm:
            # emits 16/32/64-bit  immediate
            fo.add_code_eol('emit_u{}(r,{})'.format(emit_width_immv[osz],
                                                    var_imm[osz]))
        
        dbg(fo.emit())
        ii.encoder_functions.append(fo)
        

def emit_partial_opcode_variable_srm(ii,fo):
    opcode = "0x{:02X}".format(ii.opcode_base10)
    fo.add_code_eol('emit(r,{} | get_opcode_srm(r))'.format(opcode),
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

dvars = { 0: '', 8: var_disp8, 16: var_disp16, 32: var_disp32 }  # index by dispsz

def get_memsig(asz, using_indx, dispz):
    global memsig_str_16
    global memsig_str_32or64
    
    if asz == 16:
        return memsig_str_16[using_indx][dispz]
    return memsig_str_32or64[using_indx][dispz]

arg_dvars = { 8: arg_disp8, 16: arg_disp16, 32: arg_disp32 }  # index by dispsz

arg_imm_dct = { 8: arg_imm8, 16: arg_imm16, 32: arg_imm32 }
var_imm_dct = { 8: var_imm8, 16: var_imm16, 32: var_imm32 }

def add_memop_args(env, fo, use_index, dispsz, immw=0, reg=-1):
    """reg=-1 -> no reg opnds, 
       reg=0  -> first opnd is reg,
       reg=1  -> 2nd opnd is reg """
    global arg_reg0
    global arg_base, arg_index, arg_scale
    global arg_disp8, arg_disp16, arg_disp32 
    global arg_imm_dct
    global arg_dvars
    
    if reg == 0:
        fo.add_arg(arg_reg0)
    fo.add_arg(arg_base)
    if use_index:
        fo.add_arg(arg_index)
        if env.asz in [32,64]:
            fo.add_arg(arg_scale)  # a32, a64

    if dispsz != 0:
        fo.add_arg(arg_dvars[dispsz]) 
    if reg == 1:
        fo.add_arg(arg_reg0)

    if immw:
        fo.add_arg(arg_imm_dct[immw])

def create_legacy_one_xmm_reg_one_mem_fixed(env,ii,imm8=False):
    global var_reg0
    
    op = first_opnd(ii)
    width = op.oc2
    immw = 8 if imm8 else 0
    i = 0 if modrm_reg_first_operand(ii) else 1    # i determines argument order
    opsig = 'rm' if i==0 else 'mr'
    if imm8:
        opsig = opsig + 'i'

    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]
        
    for use_index in [ False, True ]:
        for dispsz in dispsz_list:
            memaddrsig = get_memsig(env.asz, use_index, dispsz)
            fname = "{}_{}_{}_{}_{}_a{}".format(enc_fn_prefix,
                                                ii.iclass.lower(),
                                                opsig,
                                                width,
                                                memaddrsig,
                                                env.asz)

            fo = make_function_object(env,fname)
            fo.add_comment("created by create_legacy_one_xmm_reg_one_mem_fixed")
            fo.add_arg(arg_request)
            add_memop_args(env, fo, use_index, dispsz, immw, reg=i)

            rexw_forced = False
            if ii.eosz == 'o16' and env.mode in [32,64]:
                fo.add_code_eol('emit(r,0x66)', 'xx: fixed width with 16b osz')
            elif ii.eosz == 'o32' and env.mode == 16:
                fo.add_code_eol('emit(r,0x66)')
            elif (ii.eosz == 'o64' and env.mode == 64 and ii.default_64b == False) or ii.rexw_prefix == '1':
                rexw_forced = True
                fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')

            emit_required_legacy_prefixes(ii,fo)

            mod = modvals[dispsz]
            if mod:  # ZERO-INIT OPTIMIZATION
                fo.add_code_eol('set_mod(r,{})'.format(mod))

            # the sole reg is reg0 whether it is first or 2nd operand...
            fo.add_code_eol('enc_modrm_reg_xmm(r,{})'.format(var_reg0))

            encode_mem_operand(env, ii, fo, use_index, dispsz)
            finish_memop(env, ii, fo, dispsz, immw, rexw_forced, space='legacy')
            dbg(fo.emit())
            ii.encoder_functions.append(fo)

def create_legacy_one_gpr_reg_one_mem_fixed(env,ii):  
    """REGb-GPRb or GPRb-REGb to start"""
    global var_reg0
    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]

    op = first_opnd(ii)
    widths = ['b']

    mem_reg_order,regn = ('mr',1)  if op.name == 'MEM0' else ('rm',0)
    widths_to_bits = {'b':8, 'w':16, 'd':32, 'q':64 }

    for width in widths:
        for use_index in [ False, True ]:
            for dispsz in dispsz_list:
                memaddrsig = get_memsig(env.asz, use_index, dispsz)
                fname = "{}_{}_{}_{}_{}_a{}".format(enc_fn_prefix,
                                                    ii.iclass.lower(),
                                                    mem_reg_order,
                                                    width,
                                                    memaddrsig,
                                                    env.asz)
                
                fo = make_function_object(env,fname)
                fo.add_comment("created by create_legacy_one_gpr_reg_one_mem_fixed")
                fo.add_arg(arg_request)
                add_memop_args(env, fo, use_index, dispsz, immw=0, reg=regn)

                emit_required_legacy_prefixes(ii,fo)

                mod = modvals[dispsz]
                if mod:  # ZERO-INIT OPTIMIZATION
                    fo.add_code_eol('set_mod(r,{})'.format(mod))

                # the sole reg is reg0 whether it is first or 2nd operand...
                fo.add_code_eol('enc_modrm_reg_gpr{}(r,{})'.format(widths_to_bits[width],
                                                                   var_reg0))
                    
                encode_mem_operand(env, ii, fo, use_index, dispsz)
                finish_memop(env, ii, fo,  dispsz, immw=False, rexw_forced=False, space='legacy')
                dbg(fo.emit())
                ii.encoder_functions.append(fo)

def create_legacy_one_gpr_reg_one_mem_scalable(env,ii):
    """REGV- GPRv or GPRV-REGv"""
    global var_reg0
    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]

    op = first_opnd(ii)
    widths = ['w','d']
    if env.mode == 64:
        widths.append('q')

    mem_reg_order,regn = ('mr',1)  if op.name == 'MEM0' else ('rm',0)
    widths_to_bits = { 'w':16, 'd':32, 'q':64 }
    var_regs = [ var_reg0, var_reg1 ]

    for width in widths:
        for use_index in [ False, True ]:
            for dispsz in dispsz_list:
                memaddrsig = get_memsig(env.asz, use_index, dispsz)
                fname = "{}_{}_{}_{}_{}_a{}".format(enc_fn_prefix,
                                                    ii.iclass.lower(),
                                                    mem_reg_order,
                                                    width,
                                                    memaddrsig,
                                                    env.asz)
                
                fo = make_function_object(env,fname)
                fo.add_comment("created by create_legacy_one_gpr_reg_one_mem_scalable")
                fo.add_arg(arg_request)
                add_memop_args(env, fo, use_index, dispsz, immw=0, reg=regn)

                rexw_forced = False

                if width == 'w' and env.mode != 16:
                    fo.add_code_eol('emit(r,0x66)')
                elif width == 'd' and  env.mode == 16:
                    fo.add_code_eol('emit(r,0x66)')
                elif width == 'q' and  ii.default_64b == False:
                    rexw_forced = True
                    fo.add_code_eol('set_rexw(r)', 'forced rexw on memop')

                emit_required_legacy_prefixes(ii,fo)

                mod = modvals[dispsz]
                if mod:  # ZERO-INIT OPTIMIZATION
                    fo.add_code_eol('set_mod(r,{})'.format(mod))

                # the sole reg is reg0 whether it is first or 2nd operand...
                fo.add_code_eol('enc_modrm_reg_gpr{}(r,{})'.format(widths_to_bits[width],
                                                                   var_reg0))
                    
                encode_mem_operand(env, ii, fo, use_index, dispsz)
                finish_memop(env, ii, fo,  dispsz, immw=False, rexw_forced=rexw_forced, space='legacy')
                dbg(fo.emit())
                ii.encoder_functions.append(fo)



def create_legacy_one_mem_common(env,ii,imm=0):
    """Handles one memop, fixed or scalable."""
    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]
    
    op = first_opnd(ii)
    if op.oc2 == 'v':
        widths = ['w','d']
        if env.mode == 64:
            widths.append('q')
    elif op.oc2 == 'y':
        widths = ['d']
        if env.mode == 64:
            widths.append('q')
    else:
        widths = [op.oc2]

    immz_dict = { 'w': 16, 'd': 32, 'q': 32 }
    for width in widths:

        immw = 0
        if imm == '8':
            immw = 8
        elif imm == 'z':
            immw = immz_dict[width]
            
        extra_names = _gather_implicit_regs(ii)
        if extra_names:
            extra_names = '_' + '_'.join( extra_names )
        else:
            extra_names = ''
            
        for use_index in [ False, True ]:
            for dispsz in dispsz_list:
                memaddrsig = get_memsig(env.asz, use_index, dispsz)
                fname = '{}_{}{}_{}_{}_{}_a{}'.format(enc_fn_prefix,
                                                      ii.iclass.lower(),
                                                      extra_names,
                                                      'memi{}'.format(immw) if imm else 'mem',
                                                      width,
                                                      memaddrsig,
                                                      env.asz)

                fo = make_function_object(env,fname)
                fo.add_comment('created by create_legacy_one_mem_common')
                fo.add_arg(arg_request)
                add_memop_args(env, fo, use_index, dispsz, immw)

                rexw_forced = False

                if op.oc2 in [ 'y','v']:                  # handle scalable ops
                    if width == 'w' and env.mode != 16:
                        fo.add_code_eol('emit(r,0x66)')
                    elif width == 'd' and  env.mode == 16:
                        fo.add_code_eol('emit(r,0x66)')
                    elif width == 'q' and  ii.default_64b == False:
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

                mod = modvals[dispsz]
                if mod:  # ZERO-INIT OPTIMIZATION
                    fo.add_code_eol('set_mod(r,{})'.format(mod))
                else:
                    fo.add_comment('mod=0, zero init optimization')

                if ii.reg_required != 'unspecified':
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

                encode_mem_operand(env, ii, fo, use_index, dispsz)
                finish_memop(env, ii, fo,  dispsz, immw, rexw_forced, space='legacy')
                dbg(fo.emit())
                ii.encoder_functions.append(fo)

            
def encode_mem_operand(env, ii, fo, use_index, dispsz):
    global var_base, var_index, var_scale
    
    # this may overwrite modrm.mod
    memaddrsig = get_memsig(env.asz, use_index, dispsz)

    if use_index:
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
    global var_disp8
    global var_disp16
    global var_disp32
    global var_imm_dct

    if space == 'legacy':
        if env.mode == 64:
            if rexw_forced:
                fo.add_code_eol('emit_rex(r)')
            else:
                fo.add_code_eol('emit_rex_if_needed(r)')

        emit_required_legacy_map_escapes(ii,fo)
    elif space =='evex':
        fo.add_code_eol('emit_evex(r)')

        
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    fo.add_code('if (get_has_sib(r))')
    fo.add_code_eol('    emit_sib(r)')

    if dispsz == 8:
        fo.add_code_eol('emit_i8(r,{})'.format(var_disp8))
    elif dispsz == 16:
        fo.add_code_eol('emit_i16(r,{})'.format(var_disp16))
    elif dispsz == 32:
        fo.add_code_eol('emit_i32(r,{})'.format(var_disp32))
    elif dispsz == 0:
        # if form has no displacment, then we sometimes have to
        # add a zero displacement to create an allowed modrm/sib
        # encoding.  
        fo.add_code('if (get_has_disp8(r))')
        fo.add_code_eol('   emit_i8(r,0)')
        fo.add_code('else if (get_has_disp32(r))')
        fo.add_code_eol('   emit_i32(r,0)')
    if immw:
        fo.add_code_eol('emit_u{}(r,{})'.format(immw, var_imm_dct[immw]),
                        'mem-fxd-imm{}'.format(immw))
    
    
def _enc_legacy(env,ii):
    if env.mode == 64:
        if ii.mode_restriction == 'not64' or ii.mode_restriction in [0,1]:
            # we don't need an encoder function for this form in 64b mode
            ii.encoder_skipped = True 
            return
    elif env.mode == 32:
        if ii.mode_restriction in [0,2]:
            # we don't need an encoder function for this form in 32b mode
            ii.encoder_skipped = True 
            return
    elif env.mode == 16:
        if ii.mode_restriction in [1,2]:
            # we don't need an encoder function for this form in 16b mode
            ii.encoder_skipped = True 
            return

    if zero_operands(ii):
        create_legacy_no_operands(env,ii)
    elif one_implicit_gpr_imm8(ii):
        create_legacy_one_implicit_reg(env,ii,imm8=True)        
    elif one_gpr_reg_one_mem_scalable(ii):
        create_legacy_one_gpr_reg_one_mem_scalable(env,ii)
    elif one_gpr_reg_one_mem_fixed(ii):
        create_legacy_one_gpr_reg_one_mem_fixed(env,ii)
    elif two_gpr8_regs(ii):
        create_legacy_two_gpr8_regs(env,ii)
    elif two_scalable_regs(ii):
        create_legacy_two_scalable_regs(env,ii,[16,32,64])
    elif two_fixed_gprs(ii):
        create_legacy_two_fixed_gprs(env,ii)
    elif two_xmm_regs(ii):
        create_legacy_two_xmm_regs(env,ii)
    elif two_xmm_regs_imm8(ii):
        create_legacy_two_xmm_regs(env,ii,imm8=True)
    elif one_xmm_reg_imm8(ii):        
        create_legacy_one_xmm_reg_imm8(env,ii)
    elif one_mmx_reg_imm8(ii):        
        create_legacy_one_mmx_reg_imm8(env,ii)
    elif two_mmx_regs(ii):
        create_legacy_two_mmx_regs(env,ii)
        
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
        create_legacy_gprv_immv(env,ii,imm=False, implicit_orax=True)
    elif orax_immz(ii):
        create_legacy_orax_immz(env,ii)
        
    elif one_mem_common(ii): # b,w,d,q,dq, v,y
        create_legacy_one_mem_common(env,ii,imm=0)
    elif one_mem_common_one_implicit_gpr(ii): # b,w,d,q,dq, v,y
        create_legacy_one_mem_common(env,ii,imm=0)
    elif one_mem_fixed_imm8(ii): 
        create_legacy_one_mem_common(env,ii,imm='8')
    elif one_mem_fixed_immz(ii): 
        create_legacy_one_mem_common(env,ii,imm='z')
    elif one_xmm_reg_one_mem_fixed(ii):
        create_legacy_one_xmm_reg_one_mem_fixed(env,ii, imm8=False)
    elif one_xmm_reg_one_mem_fixed_imm8(ii):
        create_legacy_one_xmm_reg_one_mem_fixed(env,ii, imm8=True)
def two_xmm_opti8(ii):
    n,i = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            n += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return n==2 and i <= 1
  
def two_ymm_opti8(ii):
    n,i = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_ymm(op):
            n += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return n==2 and i <= 1
def three_xmm_opti8(ii):
    n,i = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            n += 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return n==3 and i <= 1
  
def three_ymm_opti8(ii):
    n,i = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_ymm(op):
            n = n + 1
        elif op_imm8(op):
            i += 1
        else:
            return False
    return n==3 and i <= 1

def two_xymm_and_mem(ii):
    m,x,y = 0,0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            x = x + 1
        elif op_reg(op) and op_ymm(op):
            y = y + 1
        elif op_mem(op):
            m = m + 1
        else:
            return False
    return  m==1 and ((x==2 and y==0) or (x==0 and y==2))

def one_xymm_and_mem(ii):
    m,x,y = 0,0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            x = x + 1
        elif op_reg(op) and op_ymm(op):
            y = y + 1
        elif op_mem(op):
            m = m + 1
        else:
            return False
    return  m==1 and ((x==1 and y==0) or (x==0 and y==1))

def two_ymm_and_mem(ii):
    m,n = 0,0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_ymm(op):
            n = n + 1
        elif op_mem(op):
            m = m + 1
        else:
            return False
    return n==2 and m==1

def set_vex_pp(ii,fo):
    vex_prefix = re.compile(r'VEX_PREFIX=(?P<prefix>[0123])')
    m = vex_prefix.search(ii.pattern)
    if m:
        ppval = m.group('prefix')
        if ppval != 0:
            fo.add_code_eol('set_vexpp(r,{})'.format(ppval))
    else:
        die("Could not find the VEX.PP pattern")

def create_vex_simd_reg(env,ii,nopnds): 
    """Handle 2/3 xmm or ymm regs and optional imm8"""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_imm8,  var_imm8

    imm8 = ii.has_imm8
    xmm = op_xmm(first_opnd(ii))# if not xmm, then ymm
    fn_category = category = 'xmm' if xmm else 'ymm'
    if imm8:
        fn_category += 'i'
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              str(nopnds) + fn_category)
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_vex_simd_reg")
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    fo.add_arg(arg_reg1)
    if nopnds == 3:
        fo.add_arg(arg_reg2)
    if imm8:
        fo.add_arg(arg_imm8)

    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    if not xmm:
        fo.add_code_eol('set_vexl(r,1)')

    vars = [var_reg0, var_reg1, var_reg2]

    var_r, var_b, var_n = None, None, None
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

    setregs = 0
    if var_n:
        fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(category, var_n))
        setregs += 1
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
        
    if var_r:
        fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(category, var_r))
        setregs += 1
        
    if var_b:
        fo.add_code_eol('enc_modrm_rm_{}(r,{})'.format(category, var_b))
        setregs += 1
        
    if setregs != nopnds:
        die("Set wrong number of registers: {} vs {}".format(setregs,nopnds))

    emit_vex_prefix(ii,fo,register_only=True)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')
    if imm8:
        fo.add_code_eol('emit(r,{})'.format(var_imm8))


    dbg(fo.emit())
    ii.encoder_functions.append(fo)

def create_vex_simd_2reg_mem(env,ii, nopnds=3): # FIXME
    """One or two xmm/ymm and memory."""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1

    op = first_opnd(ii)
    width = op.oc2
    mem_first = True if op.name.startswith('MEM') else False
    
    xmm = op_xmm(first_opnd(ii))# if not xmm, then ymm
    vlname = 'xmm' if xmm else 'ymm'
    if nopnds == 2:
        if mem_first:
            category = 'mx' if xmm else 'my'
        else:
            category = 'xm' if xmm else 'ym'
    else:
        if mem_first:
            category = 'mxx' if xmm else 'myy'
        else:
            category = 'xxm' if xmm else 'yym'
        
    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]
        
    for use_index in [ False, True ]:
        for dispsz in dispsz_list:
            memaddrsig = get_memsig(env.asz, use_index, dispsz)

            fname = "{}_{}_{}_{}_{}_a{}".format(enc_fn_prefix,
                                                ii.iclass.lower(),
                                                category,
                                                width,
                                                memaddrsig,
                                                env.asz)
            fo = make_function_object(env,fname)
            fo.add_comment("created by create_vex_simd_2reg_mem")
            fo.add_arg(arg_request)
            fo.add_arg(arg_reg0)
            if nopnds == 3:
                fo.add_arg(arg_reg1)
            add_memop_args(env, fo, use_index, dispsz) 

            set_vex_pp(ii,fo)
            fo.add_code_eol('set_map(r,{})'.format(ii.map))
            if not xmm:
                fo.add_code_eol('set_vexl(r,1)')

            # FIXME function-ize this
            vars = [var_reg0, var_reg1, var_reg2]
            for i,op in enumerate(_gen_opnds_nomem(ii)): # use no mem version to skip memop if a store-type op
                if op.lookupfn_name:
                    if op.lookupfn_name.endswith('_R'):
                        var_r = vars[i]
                    elif op.lookupfn_name.endswith('_B'):
                        var_b = vars[i]
                        die("Unexpected RM reg operand in mem instr: {}".format(ii.iclass))
                    elif op.lookupfn_name.endswith('_N'):
                        var_n = vars[i]
                        if nopnds == 2:
                            die("Unexpected VVVV reg operand in 2-opnd reg+mem instr: {}".format(ii.iclass))
                    else:
                        die("SHOULD NOT REACH HERE")

            if ii.rexw_prefix == '1':
                fo.add_code_eol('set_rexw(r)')
            if nopnds == 2:
                fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            else:
                fo.add_code_eol('enc_vvvv_reg_{}(r,{})'.format(vlname, var_n))
            fo.add_code_eol('enc_modrm_reg_{}(r,{})'.format(vlname, var_r))

            encode_mem_operand(env, ii, fo, use_index, dispsz)
            emit_vex_prefix(ii,fo,register_only=False)
            immw=0
            finish_memop(env, ii, fo, dispsz, immw,  space='vex')
            dbg(fo.emit())
            ii.encoder_functions.append(fo)
            
def create_vex_all_mask_reg(env,ii):
    global enc_fn_prefix, arg_request
    global arg_kreg0, var_kreg0
    global arg_kreg1, var_kreg1
    global arg_kreg2, var_kreg2
    
    nopnds = 0
    for op in _gen_opnds(ii):
        nopnds = nopnds + 1
        
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              str(nopnds) + 'k')
        
    fo = make_function_object(env,fname)
    fo.add_comment("created by create_vex_all_mask_reg")
    fo.add_arg(arg_request)
    fo.add_arg(arg_kreg0)
    fo.add_arg(arg_kreg1)
    if nopnds == 3:
        fo.add_arg(arg_kreg2)

    set_vex_pp(ii,fo)
    fo.add_code_eol('set_map(r,{})'.format(ii.map))
    if ii.vl == 256: # Not setting VL=128 since that is ZERO OPTIMIZATION
        fo.add_code_eol('set_vexl(r,1)')

    vars = [var_kreg0, var_kreg1, var_kreg2]
    
    for i,op in enumerate(_gen_opnds(ii)):
        if op.lookupfn_name:
            if op.lookupfn_name.endswith('_R'):
                var_r = vars[i]
            elif op.lookupfn_name.endswith('_B'):
                var_b = vars[i]
            elif op.lookupfn_name.endswith('_N'):
                if nopnds == 2:
                    die("Unexpected VVVV operand in 2 operand instr: {}".format(ii.iclass))
                var_n = vars[i]
            else:
                die("SHOULD NOT REACH HERE")
    if ii.rexw_prefix == '1':
        fo.add_code_eol('set_rexw(r)')
    if nopnds == 3:   
        fo.add_code_eol('enc_vex_vvvv_kreg(r,{})'.format(var_n))
    else:
        fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
    fo.add_code_eol('enc_vex_modrm_reg_kreg(r,{})'.format(var_r))
    fo.add_code_eol('enc_vex_modrm_rm_kreg(r,{})'.format(var_b))        
    emit_vex_prefix(ii,fo,register_only=True)
    emit_opcode(ii,fo)
    fo.add_code_eol('emit_modrm(r)')

    dbg(fo.emit())
    ii.encoder_functions.append(fo)

        
def _enc_vex(env,ii):
    if three_xmm_opti8(ii) or three_ymm_opti8(ii):
        create_vex_simd_reg(env,ii,3)
    elif two_xmm_opti8(ii) or two_ymm_opti8(ii):
        create_vex_simd_reg(env,ii,2)
        
    elif two_xymm_and_mem(ii):
        create_vex_simd_2reg_mem(env,ii)
    elif one_xymm_and_mem(ii):
        create_vex_simd_2reg_mem(env,ii,nopnds=2)
    elif vex_all_mask_reg(ii):
        create_vex_all_mask_reg(env,ii)
        
def vex_all_mask_reg(ii):
    k = 0
    for op in _gen_opnds(ii):
        if op_mask_reg(op):
            k = k + 1
        else:
            return False
    return k>=2
    

def evex_3xyzmm(ii):
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
    return (x==0 and y==0 and z==3) or (x==0 and y==3 and z==0) or (x==3 and y==0 and z==0)


def evex_2xyzmm(ii):
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
    return (x==0 and y==0 and z==2) or (x==0 and y==2 and z==0) or (x==2 and y==0 and z==0)

def evex_2xyzmm_mem(ii): 
    x,y,z,m=0,0,0,0
    for op in _gen_opnds(ii):
        if op_xmm(op):
            x = x + 1
        elif op_ymm(op):
            y = y + 1
        elif op_zmm(op):
            z = z + 1
        elif op_imm8(op):
            continue
        elif op_mem(op):
            m += 1
        else:
            return False
    return m==1 and ((x==0 and y==0 and z==2) or (x==0 and y==2 and z==0) or (x==2 and y==0 and z==0))
def evex_1xyzmm_mem(ii): 
    x,y,z,m=0,0,0,0
    for op in _gen_opnds(ii):
        if op_xmm(op):
            x = x + 1
        elif op_ymm(op):
            y = y + 1
        elif op_zmm(op):
            z = z + 1
        elif op_imm8(op):
            continue
        elif op_mem(op):
            m += 1
        else:
            return False
    return m==1 and (x+y+z)==1





def create_evex_3xyzmm(env,ii,nopnds=3):
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    global arg_reg2,  var_reg2
    global arg_kmask, var_kmask
    global arg_zeroing, var_zeroing
    global arg_rcsae, var_rcsae
    global arg_imm8, var_imm8

    rounding,imm8,masking_allowed=False,False,False
    if ii.rounding_form:
        rounding = True
    if ii.has_imm8:
        imm8 = True
    if ii.write_masking:
        masking_allowed = True

    op = first_opnd(ii)
    if op.lookupfn_name.startswith('XMM'):
        vl = 'xmm'
    elif op.lookupfn_name.startswith('YMM'):
        vl = 'ymm'
    elif op.lookupfn_name.startswith('ZMM'):
        vl = 'zmm'
    else:
        die("SHOULD NOT REACH HERE")


    mask_variant_name  = { False:'', True: '_msk' }
    vlmap = { 'xmm': 0, 'ymm': 1, 'zmm': 2 }

    pattern_name = nopnds*vl[0]
    if imm8:
        pattern_name = pattern_name + 'i'
    if rounding:
        pattern_name = pattern_name + 'rc'

    mask_versions = [False]
    if masking_allowed:
        mask_versions.append(True)
    
    for masking in mask_versions:
        fname = "{}_{}_{}{}".format(enc_fn_prefix,
                                    ii.iclass.lower(),
                                    pattern_name,
                                    mask_variant_name[masking])
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_evex_3xyzmm")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        if masking:
            fo.add_arg(arg_kmask)
            if not ii.write_masking_merging_only:
                fo.add_arg(arg_zeroing)
        fo.add_arg(arg_reg1)
        if nopnds == 3:
            fo.add_arg(arg_reg2)
        if imm8:
            fo.add_arg(arg_imm8)
        if rounding:
            fo.add_arg(arg_rcsae) 

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        fo.add_code_eol('set_evexll(r,{})'.format(vlmap[vl]))
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
        if rounding:
            fo.add_code_eol('set_evexb(r,1)')
            fo.add_code_eol('set_evexll(r,{})'.format(var_rcsae))
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
            
        # ENCODE REGISTERS
        vars = [var_reg0, var_reg1, var_reg2]
        var_r, var_b, var_n = None, None, None
        for i,op in enumerate(_gen_opnds(ii)):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3'):
                    var_r = vars[i]
                elif op.lookupfn_name.endswith('_B3'):
                    var_b = vars[i]
                elif op.lookupfn_name.endswith('_N3'):
                    var_n = vars[i]
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(vl, var_n))
        else:
            if nopnds == 3:
                die("SHOULD NOT REACH HERE")
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(vl, var_r))
        if var_b:
            fo.add_code_eol('enc_evex_modrm_rm_{}(r,{})'.format(vl, var_b))        
            
        fo.add_code_eol('emit_evex(r)')
        emit_opcode(ii,fo)
        fo.add_code_eol('emit_modrm(r)')
        if imm8:
            fo.add_code_eol('emit(r,{})'.format(var_imm8))
    
        dbg(fo.emit())
        ii.encoder_functions.append(fo)  

def create_evex_1or2xyzmm_mem(env, ii, nregs=2):  
    """Allows imm8 also"""
    global enc_fn_prefix, arg_request
    global arg_reg0,  var_reg0
    global arg_reg1,  var_reg1
    
    global arg_kmask, var_kmask
    global arg_zeroing, var_zeroing
    global arg_imm8, var_imm8

    imm8,masking_allowed=False,False
    if ii.has_imm8:
        imm8 = True
    if ii.write_masking:
        masking_allowed = True


    op = first_opnd_nonmem(ii)
    if op_luf_start(op,'XMM'):
        vl = 'xmm'
    elif op_luf_start(op,'YMM'):
        vl = 'ymm'
    elif op_luf_start(op,'ZMM'):
        vl = 'zmm'
    else:
        die("SHOULD NOT REACH HERE")


    mask_variant_name  = { False:'', True: '_msk' }
    vlmap = { 'xmm': 0, 'ymm': 1, 'zmm': 2 }

    pattern_name = nregs*vl[0] + 'm'
    if imm8:
        pattern_name += 'i'

    mask_versions = [False]
    if masking_allowed:
        mask_versions.append(True)

    modvals = { 0: 0,    8: 1,    16: 2,   32: 2 }  # index by dispsz
    dispsz_list = [0,8,16] if env.asz == 16 else [0,8,32]
    
    if ii.broadcast_allowed:
        bcast_vals = ['nobroadcast','broadcast']
    else:
        bcast_vals = ['nobroadcast']
    bcast_variant_name = {'nobroadcast':'', 'broadcast':'_bcast' }
    index_vals = [False, True]

    # flatten a 4-deep nested loop using itertools.product()
    ispace = itertools.product(bcast_vals, index_vals, dispsz_list, mask_versions)
    for broadcast, use_index, dispsz, masking in ispace:
        memaddrsig = get_memsig(env.asz, use_index, dispsz)

        fname = "{}_{}_{}{}_{}{}_a{}".format(enc_fn_prefix,
                                             ii.iclass.lower(),
                                             pattern_name,
                                             mask_variant_name[masking],
                                             memaddrsig,
                                             bcast_variant_name[broadcast],
                                             env.asz)
        fo = make_function_object(env,fname)
        fo.add_comment("created by create_evex_1or2xyzmm_mem")
        fo.add_arg(arg_request)
        fo.add_arg(arg_reg0)
        if masking:
            fo.add_arg(arg_kmask)
            if ii.write_masking_merging_only == False:
                fo.add_arg(arg_zeroing)
        if nregs == 2:
            fo.add_arg(arg_reg1)
        
        add_memop_args(env, fo, use_index, dispsz) 
            
        if imm8:
            fo.add_arg(arg_imm8)

        set_vex_pp(ii,fo)
        fo.add_code_eol('set_map(r,{})'.format(ii.map))
        fo.add_code_eol('set_evexll(r,{})'.format(vlmap[vl]))
        if ii.rexw_prefix == '1':
            fo.add_code_eol('set_rexw(r)')
            
        if masking:
            if not ii.write_masking_merging_only:
                fo.add_code_eol('set_evexz(r,{})'.format(var_zeroing))
            fo.add_code_eol('enc_evex_kmask(r,{})'.format(var_kmask))
        if broadcast == 'broadcast': # ZERO INIT OPTIMIZATION
            fo.add_code_eol('set_evexb(r,1)')
            
        # ENCODE REGISTERS
        vars = [var_reg0, var_reg1, var_reg2]
        var_r, var_b, var_n = None, None, None
        for i,op in enumerate(_gen_opnds_nomem(ii)):
            if op.lookupfn_name:
                if op.lookupfn_name.endswith('_R3'):
                    var_r = vars[i]
                elif op.lookupfn_name.endswith('_B3'):
                    var_b = vars[i]
                elif op.lookupfn_name.endswith('_N3'):
                    var_n = vars[i]
                else:
                    die("SHOULD NOT REACH HERE")
        if var_n:
            fo.add_code_eol('enc_evex_vvvv_reg_{}(r,{})'.format(vl, var_n))
        else:
            if nregs == 3:
                die("SHOULD NOT REACH HERE")
            fo.add_code_eol('set_vvvv(r,0xF)',"must be 1111")
            fo.add_code_eol('set_evexvv(r,1)',"must be 1")            
        if var_r:
            fo.add_code_eol('enc_evex_modrm_reg_{}(r,{})'.format(vl, var_r))
        else:
            # some instructions use _N3 as dest (like rotates)
            #fo.add_code_eol('set_rexr(r,1)')
            #fo.add_code_eol('set_evexrr(r,1)')
            if ii.reg_required != 'unspecified':
                if ii.reg_required: # ZERO INIT OPTIMIZATION
                    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))

        if var_b:
            die("SHOULD NOT REACH HERE")
            
        mod = modvals[dispsz]
        if mod:  # ZERO-INIT OPTIMIZATION
            fo.add_code_eol('set_mod(r,{})'.format(mod))
            
        
        encode_mem_operand(env, ii, fo, use_index, dispsz)  
        immw=8 if imm8 else 0
        finish_memop(env, ii, fo, dispsz, immw, rexw_forced=False, space='evex')
    
        dbg(fo.emit())
        ii.encoder_functions.append(fo)  
    
        

        
def _enc_evex(env,ii):
    # handles rounding, norounding, imm8, no-imm8, masking/nomasking
    if evex_3xyzmm(ii):
        create_evex_3xyzmm(env, ii, nopnds=3)
    elif evex_2xyzmm(ii):
        create_evex_3xyzmm(env, ii, nopnds=2)
    elif evex_2xyzmm_mem(ii): 
        create_evex_1or2xyzmm_mem(env, ii, nregs=2)
    elif evex_1xyzmm_mem(ii): 
        create_evex_1or2xyzmm_mem(env, ii, nregs=1)

        
def _enc_xop(env,ii):
    pass # FIXME

def prep_instruction(ii):
    setattr(ii,'encoder_functions',[])
    setattr(ii,'encoder_skipped',False)

    ii.write_masking = False
    ii.write_masking_notk0 = False
    ii.write_masking_merging_only = False # if true, no zeroing allowed
    ii.rounding_form = False
    ii.broadcast_allowed = False
    
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

        for op in ii.parsed_operands:
            if op_mem(op):
                if 'BCRC=0' not in ii.pattern:
                    ii.broadcast_allowed = True
                break
            

    
def create_enc_fn(env, ii):
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
    s = [ii.iclass.lower()]
    s.append(ii.space)
    s.append(ii.isa_set)
    s.append(hex(ii.opcode_base10))
    s.append(str(ii.map))
    #dbg('XA: {}'.format(" ".join(s)))
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

    if ii.space == 'evex':
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
                
    if ii.encoder_functions:            
        dbg("//DONE {}".format(" ".join(s)))
    elif ii.encoder_skipped:
        dbg("//SKIP {}".format(" ".join(s)))
    else:
        dbg("//TODO {}".format(" ".join(s)))


def gather_stats(db):
    unhandled = 0
    forms = len(db)
    generated_fns = 0
    skipped_fns = 0
    not_done = { 'evex':0, 'vex':0, 'legacy':0, 'xop':0 }
    for ii in db:
        gen_fn = len(ii.encoder_functions)
        if gen_fn == 0:
            unhandled  = unhandled + 1
            not_done[ii.space] =  not_done[ii.space] + 1
        generated_fns = generated_fns + gen_fn
        if ii.encoder_skipped:
            skipped_fns = skipped_fns + 1
        
    dbg("// Forms:       {:4d}".format(forms))
    dbg("// Handled:     {:4d}  ({:6.2f}%)".format(forms-unhandled, 100.0*(forms-unhandled)/forms ))
    dbg("// Not handled: {:4d}  ({:6.2f}%)".format(unhandled, 100.0*unhandled/forms))
    dbg("// Generated Encoding functions: {:5d}".format(generated_fns))
    dbg("// Skipped Encoding functions:   {:5d}".format(skipped_fns))
    for space in not_done.keys():
        dbg("// not-done {:8s}:   {:5d}".format(space, not_done[space]))

# object used for the env we pass to the generator
class enc_env_t(object):
    def __init__(self, mode, asz):
        self.mode = mode
        self.asz = asz
        self.function_names = {}
    def __str__(self):
        s = []
        s.append("mode {}".format(self.mode))
        s.append("asz {}".format(self.asz))
        return ", ".join(s)
    

def dump_output_file_names(fn, fe_list):
    global output_file_emitters
    ofn = os.path.join(fn)
    o = open(ofn,"w")
    for fe in fe_list:
        o.write(fe.full_file_name + "\n")
    o.close()

def work():
    global dbg_output
    
    arg_parser = argparse.ArgumentParser(description="Create XED encoder2")
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
    
    dbg_fn = os.path.join(args.gendir,'enc2out.txt')
    msge("Writing {}".format(dbg_fn))
    dbg_output = open(dbg_fn,"w")
    
    gen_setup.make_paths(args)
    msge('Reading XED db...')
    xeddb = read_xed_db.xed_reader_t(args.state_bits_filename,
                                     args.instructions_filename,
                                     args.widths_filename,
                                     args.element_types_filename,
                                     args.cpuid_filename)

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
            env = enc_env_t(mode, asz)
            msge("Generating encoder functions for {}".format(env))
            for ii in xeddb.recs:
                create_enc_fn(env, ii)
                spew(ii)


            msge("Writing functions to .c and .h files")
            func_list = []
            for ii in xeddb.recs:
                func_list.extend(ii.encoder_functions)
            fn_prefix = 'xed-enc2-m{}-a{}'.format(mode,asz)
            file_emitters = codegen.emit_function_list(func_list, fn_prefix,
                                                       args.xeddir,
                                                       args.gendir, args.gendir,
                                                       #other_headers = extra_headers,
                                                       max_lines_per_file=15000)
            output_file_emitters.extend(file_emitters)
                
    gather_stats(xeddb.recs)
    
    dump_output_file_names( args.output_file_list,
                            output_file_emitters )
    return 0

if __name__ == "__main__":
    r = work()
    sys.exit(r)
