#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
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
"""
Test function generation for the enc2 encoder.

This module generates test functions that validate the enc2 encoder by encoding
instructions with known operand values and checking the results. Creates C test
code for verifying encoder correctness.
"""
from __future__ import print_function
import sys
import collections
import codegen
from enc2common import *
from read_xed_db import Restriction

def _make_test_function_object(env, enc_fn):
    encoder_fn = enc_fn.get_function_name()
    versions = env.test_function_names[encoder_fn]
    fname = 'test_{}_{}'.format(versions, encoder_fn)
    if env.test_checked_interface:
        fname = '{}_chk'.format(fname)
    env.test_function_names[encoder_fn] += 1
    
    fo = codegen.function_object_t(fname, return_type='xed_uint32_t')
    return fo


def _add_test_function(ii,fo):
    ii.enc_test_functions.append(fo)
    dbg("TEST FUNCTION:")
    dbg(fo.emit())

# generate all the register names
gpr64 = "RAX RCX RDX RBX RSI RDI RBP RSP R8 R9 R10 R11 R12 R13 R14 R15".split()
egpr64 = gpr64 + "R16 R17 R18 R19 R20 R21 R22 R23 R24 R25 R26 R27 R28 R29 R30 R31".split()

egpr64_norsp = egpr64.copy()
egpr64_norsp.remove("RSP")

gpr64_index = "RAX RCX RDX RBX RSI RDI RBP R8 R9 R10 R11 R12 R13 R14 R15".split()
egpr64_index = gpr64_index + "R16 R17 R18 R19 R20 R21 R22 R23 R24 R25 R26 R27 R28 R29 R30 R31".split()

# EGPRs are only directly accessible within 64-bit mode.

gpr32_not64 = "EAX ECX EDX EBX ESI EDI EBP ESP".split()

gpr32_index_not64 = "EAX ECX EDX EBX ESI EDI EBP".split()

gpr32_m64 = gpr32_not64 + "R8D R9D R10D R11D R12D R13D R14D R15D".split()
egpr32_m64 = gpr32_m64 + "R16D R17D R18D R19D R20D R21D R22D R23D R24D R25D R26D R27D R28D R29D R30D R31D".split()

gpr32_index_m64 = gpr32_index_not64 + "R8D R9D R10D R11D R12D R13D R14D R15D".split()
egpr32_index_m64 = gpr32_index_m64 + "R16D R17D R18D R19D R20D R21D R22D R23D R24D R25D R26D R27D R28D R29D R30D R31D".split()

gpr16_not64 = "AX CX DX BX SI DI BP SP".split()

gpr16_index = "SI DI".split()

gpr16_m64 = gpr16_not64 + "R8W R9W R10W R11W R12W R13W R14W R15W".split()
egpr16_m64 = gpr16_m64 + "R16W R17W R18W R19W R20W R21W R22W R23W R24W R25W R26W R27W R28W R29W R30W R31W".split()

gpr8_not64  = "AL CL DL BL".split()

gpr8_m64  = gpr8_not64  + "SIL DIL BPL SPL R8B R9B R10B R11B R12B R13B R14B R15B".split()
egpr8_m64 = gpr8_m64 + "R16B R17B R18B R19B R20B R21B R22B R23B R24B R25B R26B R27B R28B R29B R30B R31B".split()

RELATIVE_DISP32 = -1430532899

gpr8h = "AH CH DH BH".split()

mmx = [ 'MMX{}'.format(i) for i in range(0,8)]
x87 = [ 'ST{}'.format(i) for i in range(0,8)]
kreg = [ 'K{}'.format(i) for i in range(0,8)]
kreg_not0 = [ 'K{}'.format(i) for i in range(1,8)]

xmm_vex_m64 = [ 'XMM{}'.format(i) for i in range(0,16)]
ymm_vex_m64 = [ 'YMM{}'.format(i) for i in range(0,16)]

xmm_evex_m64 = [ 'XMM{}'.format(i) for i in range(0,32)]
ymm_evex_m64 = [ 'YMM{}'.format(i) for i in range(0,32)]
zmm_evex_m64 = [ 'ZMM{}'.format(i) for i in range(0,32)]

xmm_not64 = [ 'XMM{}'.format(i) for i in range(0,8)]
ymm_not64 = [ 'YMM{}'.format(i) for i in range(0,8)]
zmm_not64 = [ 'ZMM{}'.format(i) for i in range(0,8)]

tmm = [ 'TMM{}'.format(i) for i in range(0,8)]

seg = 'ES CS SS DS FS GS'.split()
seg_no_cs = 'ES SS DS FS GS'.split()
cr_64 = 'CR0 CR2 CR3 CR4 CR8'.split()
cr_not64 = 'CR0 CR2 CR3 CR4'.split()
dr = [ 'DR{}'.format(i) for i in range(0,8)]

rcsae = [0,1,2,3]
scale = [1,2,4,8]
zeroing = [0,1]
dfv = list(range(16))


def set_test_gen_counters(env):
    env.test_gen_counters = collections.defaultdict(int)

    env.test_gen_regs = {
        # the index versions skip ESP/RSP as it cannot be an index register
        'gpr64_index': gpr64_index,
        'egpr64_index': egpr64_index,
        'gpr32_index': gpr32_index_m64 if env.mode==64 else gpr32_index_not64,
        'egpr32_index': egpr32_index_m64,
        'gpr16_index': gpr16_index,
        'gpr64': gpr64,
        'gpr64_not0': gpr64[1:],
        'egpr64': egpr64,
        'egpr64_norsp': egpr64_norsp,
        'gpr32': gpr32_m64 if env.mode==64 else gpr32_not64,
        'gpr32_not0': gpr32_m64[1:] if env.mode==64 else gpr32_not64[1:],
        'egpr32': egpr32_m64,
        'gpr16': gpr16_m64 if env.mode==64 else gpr16_not64,
        'gpr16_not0': gpr16_m64[1:] if env.mode==64 else gpr16_not64[1:],
        'egpr16': egpr16_m64,
        'gpr8':  gpr8_m64  if env.mode==64 else gpr8_not64,
        'egpr8': egpr8_m64,
        'gpr8h': gpr8h,
        'mmx' :  mmx,
        'x87' :  x87,
        # FIXME: avoiding k0 to avoid uncontrolled interactions ith
        #zeroing bit. XED ILD checks for evex.aaa=0b000 with evex.z=1.
        #'kreg': kreg,
        'kreg':  kreg_not0, 
        'kreg!0': kreg_not0,
        
        'xmm':  xmm_vex_m64 if env.mode==64 else xmm_not64,
        'ymm':  ymm_vex_m64 if env.mode==64 else ymm_not64,
        'tmm':  tmm if env.mode==64 else [],
        
        'xmm_evex':  xmm_evex_m64 if env.mode==64 else xmm_not64,
        'ymm_evex':  ymm_evex_m64 if env.mode==64 else ymm_not64,
        'zmm_evex':  zmm_evex_m64 if env.mode==64 else zmm_not64,
        # FIXME: avoiding CS because of MOV SEG limitation
        #'seg':  seg,
        'seg':  seg_no_cs,
        'cr' :  cr_64 if env.mode==64 else cr_not64,
        'dr' :  dr,
        'rcsae' : rcsae,
        'zeroing': zeroing,
        'scale' : scale,
        'dfv': dfv
        }

    env.test_gen_reg_limit = {}
    for k in env.test_gen_regs.keys():
        env.test_gen_reg_limit[k] = len(env.test_gen_regs[k])
        
    # the xmm,ymm,zmm regs have the same limit. Just using zmm to get
    # a limit value
    env.test_gen_reg_limit['simd_unified'] = len(env.test_gen_regs['xmm'])
    env.test_gen_reg_limit['simd_unified_evex'] = len(env.test_gen_regs['zmm_evex'])



def get_bump(env, regkind):
    v = env.test_gen_counters[regkind]
    testreg = env.test_gen_regs[regkind][v]

    # increment and roll the counter based on the limits for tht reg kind
    n = v + 1
    if n >= env.test_gen_reg_limit[regkind]:
        n = 0
    env.test_gen_counters[regkind] = n
    return testreg


def get_bump_unified(env,regkind,evex):
    '''Gathers require that we use different regs for the simd registers
    but often gathers use different vector length reg for the
    different things if addresses and data are different sizes. So we
    make a common counter that gathers can use to avoid accidental
    independent counters lining up for xmm,ymm and zmm... which does
    happen.'''

    if evex:
        special_regkind = 'simd_unified_evex'
    else:
        special_regkind = 'simd_unified'
    v = env.test_gen_counters[special_regkind]
    try:
        testreg = env.test_gen_regs[regkind][v] # use regkind to get the register name
    except:
        sys.stderr.write("ERROR: EVEX={} REGKIND={} V={}\n".format(evex,regkind,v))
        sys.exit(1)

    # increment and roll the counter based on the limits for tht reg kind
    n = v + 1
    if n >= env.test_gen_reg_limit[special_regkind]:
        n = 0
    env.test_gen_counters[special_regkind] = n
    return testreg

def supports_extended_gpr(env, ii):
    if env.mode == 64:
        if ii.space == 'evex':
            return True
        elif ii.space == 'legacy':
            if ii.rex2_restriction != Restriction.PROHIBITED:
                return True
    return False

def no_rsp_reg(ii):
    # some instructions cannot use RSP reg
    for op in ii.parsed_operands:
        if op.lookupfn_name and 'NORSP' in op.lookupfn_name:
            return True
    return False

def no_srm0(ii):
    # some instructions have SRM !=0 restriction
    return 'SRM!=0' in ii.pattern

def  gen_reg_simd_unified(env,regkind, evex=True):
    return 'XED_REG_{}'.format(get_bump_unified(env,regkind,evex))

def gen_reg(env,regkind):
    return 'XED_REG_{}'.format(get_bump(env,regkind))
def gen_int(env,regkind):
    return '{}'.format(get_bump(env,regkind))

# can vary output randomly, vary by number of calls in this
# instruction, etc.
def  get_gpr64_index(env, ii):
    if supports_extended_gpr(env, ii):
        return gen_reg(env,'egpr64_index')
    return gen_reg(env,'gpr64_index')

def  get_gpr32_index(env, ii):
    if supports_extended_gpr(env, ii):
        return gen_reg(env,'egpr32_index')
    return gen_reg(env,'gpr32_index')

def  get_gpr16_index(env, ii):
    return gen_reg(env,'gpr16_index')

def  get_gpr64(env, ii):
    if no_srm0(ii):
        return gen_reg(env,'gpr64_not0')
    elif supports_extended_gpr(env, ii):
        if no_rsp_reg(ii):
            return gen_reg(env,'egpr64_norsp')
        else:
            return gen_reg(env,'egpr64')
    return gen_reg(env,'gpr64')

def  get_gpr32(env, ii):
    if no_srm0(ii):
        return gen_reg(env,'gpr32_not0')
    elif supports_extended_gpr(env, ii):
        return gen_reg(env,'egpr32')
    return gen_reg(env,'gpr32')

def  get_gpr16(env, ii):
    if no_srm0(ii):
        return gen_reg(env,'gpr16_not0')
    if supports_extended_gpr(env, ii):
        return gen_reg(env,'egpr16')
    return gen_reg(env,'gpr16')

def  get_gpr8(env, ii):  # FIXME: figure out how to use gpr8h values
    if supports_extended_gpr(env, ii):
        return gen_reg(env,'egpr8')
    return gen_reg(env,'gpr8')


def is_gather(ii):
    return 'GATHER' in ii.iclass

def  get_xmm(env, ii):
    if is_gather(ii):
        if ii.space == 'evex':
            return gen_reg_simd_unified(env,'xmm_evex', True)
        return gen_reg_simd_unified(env,'xmm', False)
        
    if ii.space == 'evex':
        return gen_reg(env,'xmm_evex')
    return gen_reg(env,'xmm')
    

def  get_ymm(env, ii):
    if is_gather(ii):
        if ii.space == 'evex':
            return gen_reg_simd_unified(env,'ymm_evex', True)
        return gen_reg_simd_unified(env,'ymm', False)
    
    if ii.space == 'evex':
        return gen_reg(env,'ymm_evex')
    return gen_reg(env,'ymm')

def  get_zmm(env, ii):
    if is_gather(ii):
        return gen_reg_simd_unified(env,'zmm_evex', True)
    return gen_reg(env,'zmm_evex')

def  get_tmm(env, ii):
    return gen_reg(env,'tmm')

def  get_kreg(env, ii):
    return gen_reg(env,'kreg')
def  get_kreg_not0(env, ii):
    return gen_reg(env,'kreg!0')

def  get_x87(env, ii):
    return gen_reg(env,'x87')

def  get_mmx(env, ii):
    return gen_reg(env,'mmx')

def  get_cr(env, ii):
    return gen_reg(env,'cr')

def  get_dr(env, ii):
    return gen_reg(env,'dr')

def  get_seg(env, ii):
    return gen_reg(env,'seg')


# INTEGER VALUES
def  get_zeroing(env, ii): # 0(merging),1(zeroing)
    return gen_int(env,'zeroing')

def  get_rcsae(env, ii):  # 0,1,2
    return gen_int(env,'rcsae')

def  get_scale(env, ii): # 1,2,4,8
    return gen_int(env,'scale')

def  get_dfv(env, ii): # 0-15
    return gen_int(env,'dfv')

# FIXED VALUES
def  get_ax(env, ii): # always this value
    return 'XED_REG_AX'

def  get_eax(env, ii): # always this value
    return 'XED_REG_EAX'

def  get_rax(env, ii): # always this value
    return 'XED_REG_RAX'
    

# IMMEDIATES AND DISPLACMENTS - FIXME VARY THESE
def  get_imm8(env, ii):  # FIXME: signed vs unsigned. These are used for displacements too currently
    return '0x7E'

def  get_imm16(env, ii):
    return '0x7EED'

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


arginfo2value_creator = {
     'gpr64_index': get_gpr64_index,
     'gpr32_index': get_gpr32_index,
     'gpr16_index': get_gpr16_index,
     'gpr64': get_gpr64,
     'gpr32': get_gpr32,
     'gpr16': get_gpr16,
     'gpr8': get_gpr8,
     'xmm': get_xmm,
     'ymm': get_ymm,
     'zmm': get_zmm,
     'tmm': get_tmm,
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
     'dfv': get_dfv,
     'ax': get_ax,
     'eax': get_eax,
     'rax': get_rax
 }

trivial_arg_getter = {
    'base': 'xed3_operand_get_base0',
    'disp8': 'xed3_operand_get_disp',
    'disp16': 'xed3_operand_get_disp',
    'disp64': '(xed_uint64_t)xed3_operand_get_disp',
    'relb_disp8': 'xed3_operand_get_disp',
    'relb_disp16': 'xed3_operand_get_disp',
    'relb_disp64': 'xed3_operand_get_disp',
    'index': 'xed3_operand_get_index',
    'scale': 'xed3_operand_get_scale',
    'dfv'  : 'xed3_operand_get_dfv',
    'index_xmm' : 'xed3_operand_get_index',
    'index_ymm' : 'xed3_operand_get_index',
    'index_zmm' : 'xed3_operand_get_index',
    'gpr8_0': 'xed3_operand_get_reg0',
    'gpr8_1': 'xed3_operand_get_reg1',
    'gpr16_0': 'xed3_operand_get_reg0',
    'gpr16_1': 'xed3_operand_get_reg1',
    'gpr32_0': 'xed3_operand_get_reg0',
    'gpr32_1': 'xed3_operand_get_reg1',
    'gpr64_0': 'xed3_operand_get_reg0',
    'gpr64_1': 'xed3_operand_get_reg1',
}

def get_mask0_index(ii, testfn):
    """returns a list of mask0 operand indices for instructions with k0 masks
    and an empty list otherwise"""
    i = 0
    mask_indices = []
    for op in ii.parsed_operands:
        if op.name.startswith('MEM'):
            continue
        if op.lookupfn_name in ['MASK1']:
            mask_indices.append(i)
        i = i + 1
    # Make sure instruction uses mask0
    # instructions with mask!=0 have msk operand in their name
    if len(mask_indices) == testfn.get_function_name().count('_msk'):
        return []
    return mask_indices

def get_skipped_idx_lst(ii, testfn) -> list:
    """
    Returns a list of indices to be skipped from the operand compare step,
    including SUPP/IMPL operands and mask0 operand indices for instructions with k0 masks
    """
    skip_indices = get_mask0_index(ii, testfn)  # init with mask0 indices

    for i, op in enumerate(ii.parsed_operands):
        if op.visibility in ['SUPPRESSED', 'IMPLICIT']:
            skip_indices.append(i)
    
    return skip_indices

def _create_enc_test_functions(env, ii, encfn):
    
    # a mapping of each operand to its randomly/fixed assigned value
    operand2value = {}
    
    # add arguments to the test function
    testfn = _make_test_function_object(env,encfn)
    testfn.add_arg('xed_uint8_t* output_buffer')
    testfn.add_arg('xed_decoded_inst_t* xedd')

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

    # argument variables' declarations
    for i,(argtype,argname,arginfo) in enumerate(args):
        testfn.add_code_eol('{} {}'.format(argtype, argname))

    # common configuration
    testfn.add_code_eol('xed_enc2_req_t request')
    testfn.add_code_eol('xed_uint32_t enc2_len')
    testfn.add_code_eol('xed_error_enum_t err')
    
    # set vars to test values 
    for argtype,argname,arginfo in args:
        if arginfo == 'req':
            # set up the request structure and output buffer
            testfn.add_code_eol('xed_enc2_req_t_init(&request, output_buffer)')
            testfn.add_code_eol('{} = &request'.format(request_arg) )
        else:
            if not arginfo:
                die("NO ARGINFO FOR {} {} in {}".format(argtype, argname, ii.iclass))
            try:
                vfn = arginfo2value_creator[arginfo]
            except:
                die("FIXME: MESSED UP ARGUMENTS FOR {} {} {} from {}".format(argtype, argname, arginfo, ii.iclass))
            v = vfn(env,ii)
            operand2value[argname] = v
            testfn.add_code_eol('{} = {}'.format(argname, v))            
    
    # call to argument checker function which subsequently calls enc2 function
    s = []
    fname =  encfn.get_function_name()
    if env.test_checked_interface:
        fname = '{}_chk'.format(fname)
    s.append(  fname )
    s.append( '(' )
    for i,(argtype,argname,arginfo) in enumerate(args):
        if i>0:
            s.append(',')
        s.append("{} /*{}*/".format(argname,arginfo))
    s.append( ')' )
    testfn.add_code_eol(''.join(s))

    # get enc2 encoded string length and validate it
    testfn.add_code_eol('enc2_len = xed_enc2_encoded_length({})'.format(request_arg))
    testfn.add_code(f'if (enc2_len == 0)')
    testfn.add_code_eol(f'  return 0')

    # decode the encoded string and validate it
    testfn.add_code_eol('err = xed_decode(xedd, output_buffer, enc2_len)')
    testfn.add_code(f'if (err != XED_ERROR_NONE)')
    testfn.add_code_eol(f'  return 0')
    
    if env.operand_check:
        
        j = 0   # index used for generic ith operand getters
        imm2value = {'imm32': 2864434397, 'imm16': 32493, 'imm8': 126}
        skip_indices = get_skipped_idx_lst(ii, testfn)  # indices to skip
        expression = []

        # validate decoded operands' values
        for argtype,argname,arginfo in args:
            if argname in trivial_arg_getter.keys():
                # arguments that have "well-defined" getters
                expression.append(f'({trivial_arg_getter[argname]}(xedd) == {operand2value[argname]})')
            elif argname in ['cr', 'dr', 'gpr8', 'gpr16', 'gpr32', 'gpr64','seg', 'reg3','reg2','reg1','reg0',
                                     'kreg0', 'kreg1', 'kreg2', 'kmask']:
                # arguments with generic xed3_operand_get_reg[i] getter
                if j in skip_indices:
                    # special cases where we need to skip to next operand (suppressed ST0, mask0)
                    # as get ith reg returns the values of these operands instead of the current ones
                    j = j + 1
                expression.append(f'(xed3_operand_get_reg{j}(xedd) == {operand2value[argname]})')
                j = j + 1
            # disp32 is stored relatively (abs value requires complex calculations), so check pre-calculated val
            elif argname == 'relb_disp32':
                expression.append(f'(xed3_operand_get_disp(xedd) == {RELATIVE_DISP32})')
            elif argname == 'disp32':
                expression.append(f'(xed_operand_values_get_memory_displacement_int64(xedd) == {RELATIVE_DISP32})')
            elif argname in ['imm8', 'imm32', 'imm16']:
                # imm values are fixed, compare with uint instead of hex
                expression.append(f'(xed_operand_values_get_immediate_uint64(xedd) == {imm2value[argname]})')

        if expression:
            testfn.add_code_eol('xed_bool_t conditions_satisfied = ' + " &&\n    ".join(expression))
            testfn.add_code('if (conditions_satisfied == 0)')
            testfn.add_code_eol('   return 0')

    # return the output length
    testfn.add_code_eol('return enc2_len')
    
    _add_test_function(ii, testfn)
    
    
def create_test_fn_main(env, ii):
    env.test_function_names = collections.defaultdict(int)
    ii.enc_test_functions = []

    for encfn in ii.encoder_functions:
        for n in range(0,env.tests_per_form):
            _create_enc_test_functions(env, ii, encfn)

    
