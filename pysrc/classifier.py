#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2023 Intel Corporation
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
import re
import genutil
import codegen


def _emit_function(fe, isa_sets, name):
    fo = codegen.function_object_t('xed_classify_{}'.format(name)) 
    fo.add_arg('const xed_decoded_inst_t* d')
    fo.add_code_eol('    const xed_isa_set_enum_t isa_set = xed_decoded_inst_get_isa_set(d)')
    # FIXME: 2017-07-14 optimization: could use a static array for faster checking, smaller code
    switch = codegen.c_switch_generator_t('isa_set', fo)
    isa_sets_sorted = sorted(isa_sets)
    for c in isa_sets_sorted:
        switch.add_case('XED_ISA_SET_{}'.format(c.upper()),[],do_break=False)
    if len(isa_sets) > 0:
        switch.add('return 1;')
    switch.add_default(['return 0;'], do_break=False)
    switch.finish()
    
    fo.emit_file_emitter(fe)


def find_avx512_insts(agi) -> set:
    """pre-processing step, where all AVX512 main ISA are assembled"""
    avx512_main_isa = set()
    for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if genutil.field_check(ii, 'iclass'):
             # if the instruction has 512 VL variant or AVX512 prefix
             if re.search('^AVX512_|_512$',ii.isa_set):
                avx512_main_isa.add(ii.isa_set.rsplit('_', 1)[0])
    return avx512_main_isa


def is_avx512_inst(isa_set: str, avx512_main_isa: set):
    """Checks whether the given ISA belongs to the AVX512 family"""
    # removes the suffix from the ISA-SET
    return isa_set.rsplit('_', 1)[0] in avx512_main_isa


def work(agi):
    sse_isa_sets = set([])
    avx_isa_sets = set([])
    avx512_isa_sets = set([])
    avx512_kmask_op = set([])
    amx_isa_sets = set([])

    avx512_main_isa = find_avx512_insts(agi)    # contains the main forms of AVX512 ISA

    for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if genutil.field_check(ii, 'iclass'):
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
    fe.close()
    return
