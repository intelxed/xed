#!/usr/bin/env python
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
Instruction classifier code generation.

This module generates C code for classifying instructions into extension groups
(e.g., APX, AVX, SSE). Classifiers are used to determine if an instruction
belongs to a specific architectural extension based on its ISA-set.
"""

from __future__ import print_function
import re
import genutil
import codegen

def _emit_isa_switch_cases(fo, isa_sets):
    # builds a switch case that catches all of the extension's ISA
    # and defaultly returns 0 otherwise
    switch = codegen.c_switch_generator_t('isa_set', fo)
    isa_sets_sorted = sorted(isa_sets)
    for c in isa_sets_sorted:
        switch.add_case('XED_ISA_SET_{}'.format(c.upper()),[],do_break=False)
    if len(isa_sets) > 0:
        switch.add('return 1;')
    switch.add_default(['return 0;'], do_break=False)
    switch.finish()

def _emit_apx_classifier(fe):
    # Catches APX encoding legacy instructions, as well as new APX instructions
    # using the apx_foundation XED classifier.
    SPACE = ' ' * 4
    fo = codegen.function_object_t('xed_classify_apx') 
    fo.add_arg('const xed_decoded_inst_t* d')
    fo.add_code('#if defined(XED_SUPPORTS_AVX512)')
    
    fo.add_code(f'{SPACE}// REX2 Prefix is detected')
    fo.add_code_eol(f'{SPACE}if (xed3_operand_get_rex2(d)) return 1')

    fo.add_code(f'{SPACE}// The instruction has EGPR reg or mem operand (Detects non-APX EVEX instructions)')
    fo.add_code_eol(f'{SPACE}if (xed3_operand_get_has_egpr(d)) return 1')

    fo.add_code(f'{SPACE}// APX EVEX bits are set but ignored (e.g. instructions with no MEM/GPR operand)')
    fo.add_code(f'{SPACE}// EVEX.B4 is set')
    fo.add_code_eol(f'{SPACE}if (xed3_operand_get_rexb4(d)) return 1')

    fo.add_code(f'{SPACE}// EVEX.X4 is zero (reverted -> logically set)')
    fo.add_code(f'{SPACE}// REXX4 = ~EVEX.X4')
    # check XED-ILD for more info
    fo.add_code_eol(f'{SPACE}if (xed3_operand_get_rexx4(d) && xed3_operand_get_ubit(d)) return 1')
    fo.add_code_eol(f'{SPACE}return xed_classify_apx_foundation(d);')
    fo.add_code('#endif')
    fo.add_code_eol('(void)d')  # pacify compiler
    fo.add_code_eol('return 0') # fallback safety
    fo.emit_file_emitter(fe)


def _emit_function(fe, isa_sets, name):
    # builds a function that indicates whether a decoded instruction's ISA falls
    # under the given extension (name)
    fo = codegen.function_object_t('xed_classify_{}'.format(name)) 
    fo.add_arg('const xed_decoded_inst_t* d')
    fo.add_code_eol('    const xed_isa_set_enum_t isa_set = xed_decoded_inst_get_isa_set(d)')
    _emit_isa_switch_cases(fo, isa_sets)
    fo.emit_file_emitter(fe)


def find_avx512_insts(agi) -> set:
    """pre-processing step, where all AVX512 main ISA are assembled"""
    avx512_main_isa = set()
    for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if genutil.field_check(ii, 'iclass'):
             # if the instruction has 512 VL variant or AVX512 prefix (AVX10 too for now)
             if re.search('^AVX(512|10)_|_512$',ii.isa_set):
                avx512_main_isa.add(ii.isa_set.rsplit('_', 1)[0])
    return avx512_main_isa


def is_avx512_inst(isa_set: str, avx512_main_isa: set):
    """Checks whether the given ISA belongs to the AVX512 family"""
    # removes the suffix from the ISA-SET
    if re.search('_(128|256|512|SCALAR|KOP)',isa_set):
        # rarely, an IFORM exists independently with and without VL (e.g. SM4)
        # Make sure to skip these IFORMs
        return isa_set.rsplit('_', 1)[0] in avx512_main_isa
    return False


def work(agi):
    sse_isa_sets = set([])
    avx_isa_sets = set([])
    avx512_isa_sets = set([])
    avx512_kmask_op = set([])
    amx_isa_sets = set([])
    apx_isa_sets = set()

    avx512_main_isa = find_avx512_insts(agi)    # contains the main forms of AVX512 ISA

    for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if genutil.field_check(ii, 'iclass'):
             if re.search('APX',ii.isa_set):
                 apx_isa_sets.add(ii.isa_set)
             if re.search('AMX',ii.isa_set):
                 amx_isa_sets.add(ii.isa_set)
             elif is_avx512_inst(ii.isa_set, avx512_main_isa):
                 avx512_isa_sets.add(ii.isa_set)
                 if re.search('KOP',ii.isa_set):
                     avx512_kmask_op.add(ii.isa_set)
             elif re.search('AVX',ii.isa_set) or ii.isa_set in ['F16C', 'FMA']:
                 avx_isa_sets.add(ii.isa_set)
             elif re.search('SSE',ii.isa_set) or ii.isa_set in ['AES','PCLMULQDQ']:
                 # Exclude MMX instructions that come in with SSE2 &
                 # SSSE3. The several purely MMX instr in SSE are
                 # "SSE-opcodes" with memop operands. One can look for
                 # those with SSE2MMX and SSSE3MMX xed isa_sets.
                 #
                 # Also exclude the SSE_PREFETCH operations; Those are
                 # just memops.
                 if (not re.search('MMX',ii.isa_set) and not re.search('PREFETCH',ii.isa_set)
                     and not re.search('X87',ii.isa_set) and not re.search('MWAIT',ii.isa_set)):
                     sse_isa_sets.add(ii.isa_set)

    fe = agi.open_file('xed-classifiers.c') # xed_file_emitter_t
    _emit_function(fe, amx_isa_sets, 'amx')
    _emit_function(fe, avx512_isa_sets, 'avx512')
    _emit_function(fe, avx512_kmask_op, 'avx512_maskop')
    _emit_function(fe, avx_isa_sets,    'avx')
    _emit_function(fe, sse_isa_sets,    'sse')
    _emit_function(fe, apx_isa_sets,    'apx_foundation')
    _emit_apx_classifier(fe)
    fe.close()
    return
