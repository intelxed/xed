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

import re

import ild_nt
import mbuild
import ild_codegen
import operand_storage
import genutil
import ildutil
import ild_info

_easz_token           = 'EASZ'
_easz_binding_pattern = re.compile(r'EASZ=(?P<rhs>[0-9]+)')

#FIXME: we can get default NT by looking at the spine
_easz_default_nt      = 'ASZ_NONTERM'

_easz_lookup_def_str  = 'XED_ILD_EASZ_LOOKUP'

_easz_defines = {
                 'XED_ILD_EASZ_0' : 0,
                 'XED_ILD_EASZ_1' : 1,
                 'XED_ILD_EASZ_2' : 2,
                 'XED_ILD_EASZ_3' : 3,
                 }
#set up LOOKUP define to be the biggest defined value
_easz_defines[_easz_lookup_def_str] = len(_easz_defines)

#reverted _eosz_defines
_easz_defines_reverse = dict((v,k) for k, v in _easz_defines.items())

_easz_c_fn = 'xed-ild-easz.c'
_easz_header_fn = 'xed-ild-easz.h'

def get_getter_fn(ptrn_list):
    if len(ptrn_list) == 0:
        genutil.die("P2341: SHOULD NOT REACH HERE")
    first = ptrn_list[0]
    for cur in ptrn_list[1:]:
        if first.easz_nt_seq != cur.easz_nt_seq:
            #conflict in easz resolution functions.. should not happen
            return None 
    return ild_codegen.get_derived_op_getter_fn(first.easz_nt_seq, _easz_token)

def is_easz_conflict(info_list):
    """
    Return True/False if info list conflicts
    on EASZ resolution function (EOSZ NT sequence). 
    """
    first_info = info_list[0]
    for cur_info in info_list[1:]:
        if first_info.easz_nt_seq != cur_info.easz_nt_seq:
            return True
    return False

def gen_getter_fn_lookup(agi, united_lookup, easz_dict): # NOT USED
    """Compute L1(conflict resolution) functions list and easz 
    lookup tables dict.
    @param agi: all generators info
    
    @param united_lookup: the 2D lookup by map-opcode to info objects list.
    united_lookup['0x0']['0x78'] == [ild_info1, ild_info2, ... ]
    @type united_lookup: 
    {string(insn_map) : {string(opcode): [ild_info.ild_info_t]} }
    
    
    """
    l1_lookup = {}
    for insn_map in united_lookup.get_maps():
        l1_lookup[insn_map] = {}
        for opcode in range(0, 256):
            info_list = united_lookup.get_info_list(insn_map, hex(opcode))
            #get only info objects with minimum priority
            info_list = ild_info.get_min_prio_list(info_list)
            is_conflict = False
            if len(info_list) > 1:
                is_conflict = is_easz_conflict(info_list)
            
            if is_conflict:
                l1_fn = None
            #if map-opcode pair is undefined the lookup function ptr is NULL
            #this will happen for opcodes like 0F in 0F map - totally illegal
            #opcodes, that should never be looked up in runtime.
            elif len(info_list) == 0:
                l1_fn = '(%s)0' % (ildutil.l1_ptr_typename)
            else:
                #there are no conflicts, we can use the eosz_nt_seq
                #function
                info = info_list[0]
                l1_fn = ild_nt.get_lufn(info.easz_nt_seq, _easz_token)
            l1_lookup[insn_map][hex(opcode)] = l1_fn
    return l1_lookup


#returns a list of names of EASZ-binding NTs in the pattern
def get_easz_nt_seq(ptrn_wrds, easz_nts):
    return ild_nt.get_nt_seq(ptrn_wrds, easz_nts, 
                             implied_nt=_easz_default_nt)


#returns a list of all sequences of EOSZ setting NTs in patterns
#each sequence is a list of strings (NT names)
def get_all_easz_seq(united_lookup):
    all_seq = set()
    for info in united_lookup.get_all_infos():
        #lists are unhaashable, hence we have to use tuples instead
        all_seq.add(tuple(info.easz_nt_seq))
    #convert back to lists, in order not to surprise user
    return_list = []
    for nt_tuple in all_seq:
        return_list.append(list(nt_tuple))
    return return_list

#Parameters: agi - all generator info object
#returns a list of names of NTs that bind EASZ operand
def get_easz_binding_nts(agi):
    return ild_nt.get_setting_nts(agi, _easz_token)

def get_target_opname():
    return _easz_token

def get_ntseq_header_fn():
    return _easz_header_fn

#dumps the xed_ild_easz.c file that defines all lookup functions
#for EASZ resolution
#FIXME: should dump header file too
def work(agi, united_lookup, easz_nts, ild_gendir, debug):
    
    #dump lookup tables for each NT
    #just for debugging
    nt_arrays = []
    for nt_name in easz_nts:
        array = ild_nt.gen_nt_lookup(agi, nt_name, 'EASZ')
        if not array:
            return
        nt_arrays.append(array)
    ild_nt.dump_lu_arrays(agi, nt_arrays, 'ild_easz_debug.txt',
                          'ild_easz_debug_header.txt')
        
    all_easz_seq = get_all_easz_seq(united_lookup)
    debug.write('EASZ SEQS: %s\n' % all_easz_seq)

    nt_seq_arrays = {}
    for nt_seq in all_easz_seq:
        array = ild_nt.gen_nt_seq_lookup(agi, nt_seq, _easz_token)
        if not array:
            return
        nt_seq_arrays[tuple(nt_seq)] = array
    #init function calls all single init functions for the created tables
    nt_seq_values = [v for (k,v) in sorted(nt_seq_arrays.items())]
    init_f = ild_nt.gen_init_function(nt_seq_values,
                                       'xed_ild_easz_init')
    ild_nt.dump_lu_arrays(agi, nt_seq_values, _easz_c_fn, 
                          mbuild.join('include-private', _easz_header_fn),
                          init_f)
    getter_fos = []
    for names in nt_seq_arrays.keys():
        arr = nt_seq_arrays[names]
        getter_fo = ild_codegen.gen_derived_operand_getter(agi, _easz_token,
                                                           arr, list(names))
        getter_fos.append(getter_fo)
    
    headers = [ildutil.ild_private_header,
               _easz_header_fn, 
               operand_storage.get_operand_accessors_fn()]
    ild_codegen.dump_flist_2_header(agi, 'xed-ild-easz-getters.h',
                                    headers, 
                                    getter_fos)
    
    #getter_lookup = gen_getter_fn_lookup(agi, united_lookup, nt_seq_arrays)
    
    return nt_seq_arrays

