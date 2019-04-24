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
import codegen
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

enc_fn_prefix = "xed_encode"

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

def _gen_opnds(ii): # generator
    # filter out write-mask operands and suppressed operands
    for op in ii.parsed_operands:
        if op.lookupfn_name == 'MASK1':
            continue
        if op.lookupfn_name == 'MASKNOT0':
            continue
        if op.visibility == 'SUPPRESSED':
            continue
        yield op
        
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

def op_reg(op):
    if 'REG' in op.name:
        return True
    return False
def op_xmm(op):
    if op.lookupfn_name:
        if 'XMM' in op.lookupfn_name:
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
    return False
    
def two_scalable_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_scalable_v(op):
            n = n + 1
    return n==2
def one_x87_reg(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_x87(op):
            n = n + 1
    return n==1
def zero_operands(ii):
    n = 0
    for op in _gen_opnds(ii):
        n = n + 1
    return n == 0

    
def two_gpr8_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_gpr8(op):
            n = n + 1
    return n==2

def two_xmm_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_xmm(op):
            n = n + 1
    return n==2
def two_mmx_regs(ii):
    n = 0
    for op in _gen_opnds(ii):
        if op_reg(op) and op_mmx(op):
            n = n + 1
    return n==2
    
def gen_osz_list(mode, osz_list):
    """skip osz 64 outside of 64b mode"""
    for osz in osz_list:
        if mode != 64 and osz == 64:
            continue
        yield osz
        
def modrm_reg_first_operand(ii):
    # only look at first operand
    for op in  _gen_opnds(ii):
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
        fo.add_code_eol('emit(r,0x0F)')
    elif ii.map == 2:
        fo.add_code_eol('emit(r,0x0F)')
        fo.add_code_eol('emit(r,0x38)')
    elif ii.map == 3:
        fo.add_code_eol('emit(r,0x0F)')
        fo.add_code_eol('emit(r,0x3A)')

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
        
    fo = codegen.function_object_t(fname, 'void')
    fo.add_arg(arg_request)

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
            fo.add_code_eol('set_rexw()')
        elif env.mode == 32 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif env.mode == 16 and ii.eosz == 'o16':
            fo.add_code_eol('emit(r,0x66)')
        elif ii.eosz in ['osznot16', 'osznot64']:  #FIXME
            fo.add_comment("Check handling of {}".format(ii.eosz))
            genutil.warn("Check handling of {} for: {} / {}".format(ii.eosz, ii.iclass, ii.iform))
        elif ii.eosz in ['oszall']:  # FIXME
            fo.add_comment("Check handling of oszall.")
            genutil.warn("Check handling of {} for: {} / {}".format(ii.eosz, ii.iclass, ii.iform))
            

    emit_required_legacy_prefixes(ii,fo)

    emit_required_legacy_map_escapes(ii,fo)
    if ii.partial_opcode:
        genutil.warn("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
        ii.encoder_skipped = True
        return
    else:
        fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
        if modrm_required:
            fo.add_code_eol('emit_modrm(r)')
    print(fo.emit())
    ii.encoder_functions.append(fo)

        
    
    
def create_legacy_two_scalable_regs(env, ii, osz_list):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    
    for osz in gen_osz_list(env.mode,osz_list):
        fname = "{}_{}_{}_o{}".format(enc_fn_prefix,
                                      ii.iclass.lower(),
                                      'rvrv',
                                      osz)
        fo = codegen.function_object_t(fname, 'void')
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
        if rexw_forced:
            fo.add_code_eol('emit_rex(r)')
        else:
            fo.add_code_eol('emit_rex_if_needed(r)')
        emit_required_legacy_map_escapes(ii,fo)
        if ii.partial_opcode:
            genutil.die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
        else:
            fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
            fo.add_code_eol('emit_modrm(r)')
        print(fo.emit())
        ii.encoder_functions.append(fo)
            


def create_legacy_two_gpr8_regs(env, ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    
    fname = "{}_{}_{}".format(enc_fn_prefix,
                              ii.iclass.lower(),
                              'r8r8')
    fo = codegen.function_object_t(fname, 'void')
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
    fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)

    if ii.partial_opcode:
        genutil.die("NOT HANDLING PARTIAL OPCODES YET: {} / {}".format(ii.iclass, ii.iform))
    else:
        fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
        fo.add_code_eol('emit_modrm(r)')
    print(fo.emit())
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

    
def create_legacy_two_xmm_regs(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'xmm')
    fo = codegen.function_object_t(fname, 'void')
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    fo.add_arg(arg_reg1)
    cond_add_imm_args(ii,fo)
    emit_required_legacy_prefixes(ii,fo)
    if modrm_reg_first_operand(ii):
        f1, f2 = 'reg','rm'
    else:
        f1, f2 = 'rm','reg'
    fo.add_code_eol('enc_modrm_{}_xmm(r,reg0)'.format(f1))
    fo.add_code_eol('enc_modrm_{}_xmm(r,reg1)'.format(f2))
    fo.add_code_eol('emit_rex_if_needed(r)')
    emit_required_legacy_map_escapes(ii,fo)
    fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    
    print(fo.emit())
    ii.encoder_functions.append(fo)


def create_legacy_two_mmx_regs(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0, arg_reg1
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'mmx')
    fo = codegen.function_object_t(fname, 'void')
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
    fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
    fo.add_code_eol('emit_modrm(r)')
    cond_emit_imm8(ii,fo)
    print(fo.emit())
    ii.encoder_functions.append(fo)


def create_legacy_one_x87_reg(env,ii):
    global enc_fn_prefix, arg_request, arg_reg0
    fname = "{}_{}_{}".format(enc_fn_prefix,
                                  ii.iclass.lower(),
                                  'x87')
    fo = codegen.function_object_t(fname, 'void')
    fo.add_arg(arg_request)
    fo.add_arg(arg_reg0)
    emit_required_legacy_prefixes(ii,fo)
    fo.add_code_eol('set_mod(r,3)')
    if ii.reg_required == 'unspecified':
        genutil.die("Need a value for MODRM.REG in x87 encoding")
    fo.add_code_eol('set_reg(r,{})'.format(ii.reg_required))
    fo.add_code_eol('enc_modrm_rm_x87(r,reg0)')
    emit_required_legacy_map_escapes(ii,fo)
    fo.add_code_eol('emit(r,{})'.format(hex(ii.opcode_base10)))
    fo.add_code_eol('emit_modrm(r)')
    print(fo.emit())
    ii.encoder_functions.append(fo)
    

    
def _enc_legacy(agi,env,ii):
    if zero_operands(ii):
        create_legacy_no_operands(env,ii)
    if two_gpr8_regs(ii):
        create_legacy_two_gpr8_regs(env,ii)
    elif two_scalable_regs(ii):
        create_legacy_two_scalable_regs(env,ii,[16,32,64])
    elif two_xmm_regs(ii):
        create_legacy_two_xmm_regs(env,ii)
    elif two_mmx_regs(ii):
        create_legacy_two_mmx_regs(env,ii)
    elif one_x87_reg(ii):
        create_legacy_one_x87_reg(env,ii)

    
def _enc_vex(agi,env,ii):
    print("VEX encoding still TBD")
def _enc_evex(agi,env,ii):
    print("EVEX encoding still TBD")
def _enc_xop(agi,env,ii):
    print("XOP encoding still TBD")

def _create_enc_fn(agi, env, ii):
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


    if ii.space == 'legacy':
        _enc_legacy(agi,env,ii)
    elif ii.space == 'vex':
        _enc_vex(agi,env,ii)
    elif ii.space == 'evex':
        _enc_evex(agi,env,ii)
    elif ii.space == 'xop':
        _enc_xop(agi,env,ii)
    else:
        genutil.die("Unhandled encoding space: {}".format(ii.space))
        
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
        print("XX {}".format(" ".join(s)))
    else:
        print("YY {}".format(" ".join(s)))


def gather_stats(db):
    unhandled = 0
    forms = len(db)
    generated_fns = 0
    skipped_fns = 0
    for ii in db:
        gen_fn = len(ii.encoder_functions)
        if gen_fn == 0:
            unhandled  = unhandled + 1
        generated_fns = generated_fns + gen_fn
        if ii.encoder_skipped:
            skipped_fns = skipped_fns + 1
        
    print("Forms:       {:4d}".format(forms))
    print("Handled:     {:4d}  ({:6.2f}%)".format(forms-unhandled, 100.0*(forms-unhandled)/forms ))
    print("Not handled: {:4d}  ({:6.2f}%)".format(unhandled, 100.0*unhandled/forms))
    print("Generated Encoding functions: {}".format(generated_fns))
    print("Skipped Encoding functions:   {}".format(skipped_fns))
        
          
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

    env  = dummy_t()
    env.mode = 64
    
    for ii in xeddb.recs:
        setattr(ii,'encoder_functions',[])
        setattr(ii,'encoder_skipped',False)
        _create_enc_fn(agi,env,ii)
            
    gather_stats(xeddb.recs)
