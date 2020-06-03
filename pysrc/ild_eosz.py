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
import ild_info
import genutil
import ildutil
import operand_storage
import ild_codegen

_eosz_token           = 'EOSZ'
_eosz_binding_pattern = re.compile(r'EOSZ=(?P<rhs>[0-9]+)')
#FIXME: we can get default NT by looking at the spine
_eosz_default_nt      = 'OSZ_NONTERM'
_eosz_c_fn            = 'xed-ild-eosz.c'
_eosz_header_fn       = 'xed-ild-eosz.h'


#FIXME: I hope there are no conflicts on EOSZ in map,opcodes which
#patterns have EOSZ as an operand decider.
#If it is true, then in general case we can postpone resolving EOSZ 
#to the stage when xed_inst_t is already known, 
#and resolve EOSZ before that stage only when it is really
#needed - for immediate, displacement and pattern dispatching where
#EOSZ is in constraint dict.

#IF there are such conflicts, then we need to develop a general mechanism
#for conflict resolution based on patterns' constraints.
#Probably use the constraint dict for that. That would be similar to xed2's
#decoding graph generation. I hope there is no need for that.    
def _resolve_conflicts(agi, info_list, nt_dict):  # NOT USED
    """Try to resolve conflicts by applying the conflict resolution
    functions defined in _resolution_functions list.
    
    @param info_list: list of info objects to that have a conflict
    @type info_list: [ild_info.ild_info_t
    
    @param nt_dict: dictionary from EOSZ-NT names to corresponding
    codegen.array_t objects describing those NTs
    @type nt_dict: { string(nt_name) : codegen.array_t(nt_arr) }
    
    @return: codegen.function_object_t defining the conflict resolution (L1)
    function for info_list's map-opcode
    
    """
    for func in _resolution_functions:
        fo = func(agi,info_list, imm_dict, is_eosz_conflict,
                        get_l2_fn_from_info, _eosz_token) 
        if fo:
            return fo
    return None

#FIXME: use info_list instead?
def get_getter_fn(ptrn_list):
    if len(ptrn_list) == 0:
        genutil.die("P2342: SHOULD NOT REACH HERE")

    first = ptrn_list[0]
    for cur in ptrn_list[1:]:
        if first.eosz_nt_seq != cur.eosz_nt_seq:
            #conflict in eosz resolution functions.. should not happen
            return None 
    return ild_codegen.get_derived_op_getter_fn(first.eosz_nt_seq, _eosz_token)
    
def gen_getter_fn_lookup(agi, united_lookup, eosz_dict): # NOT USED
    """Compute L1(conflict resolution) functions list and eosz 
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
                is_conflict = is_eosz_conflict(info_list)
            
            if is_conflict:
                genutil.msg("EOSZ CONFLICT MAP/OPCODE:{}/{}".format(insn_map, opcode))
#                l1_fo = _resolve_conflicts(agi, info_list, nt_dict)
#                if not l1_fo:
#                    ildutil.ild_err('FAILED TO GENERATE CONFLICT ' +
#                    'RESOLUTION FUNCTION FOR EOSZ\n infos:\n %s' %
#                    "\n".join([str(info) for info in info_list]))
#                    
#                l1_resolution_fos.append(l1_fo)
#                l1_fn = l1_fo.function_name
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
                l1_fn = ild_nt.get_lufn(info.eosz_nt_seq, _eosz_token)
            l1_lookup[insn_map][hex(opcode)] = l1_fn
    return l1_lookup


def is_eosz_conflict(info_list):
    """
    Return True/False if info list conflicts
    on EOSZ resolution function (EOSZ NT sequence). 
    """
    first_info = info_list[0]
    for cur_info in info_list[1:]:
        if first_info.eosz_nt_seq != cur_info.eosz_nt_seq:
            return True
    return False

#returns a list of names  of EOSZ-binding NTs in the pattern
def get_eosz_nt_seq(ptrn_wrds, eosz_nts):
    return ild_nt.get_nt_seq(ptrn_wrds, eosz_nts, 
                             implied_nt=_eosz_default_nt)


#returns a list of all sequences of EOSZ setting NTs in patterns
#each sequence is a list of strings (NT names)
def get_all_eosz_seq(united_lookup):
    all_seq = set()
    for info in united_lookup.get_all_infos():
        #lists are unhaashable, hence we have to use tuples instead
        all_seq.add(tuple(info.eosz_nt_seq))
    #convert back to lists, in order not to surprise user
    return_list = []
    for nt_tuple in all_seq:
        return_list.append(list(nt_tuple))
    return return_list

#Parameters: agi - all generator info object
#returns a list of names of NTs that bind EOSZ operand
def get_eosz_binding_nts(agi):
    return ild_nt.get_setting_nts(agi, _eosz_token)


def get_target_opname():
    return _eosz_token

def get_ntseq_header_fn():
    return _eosz_header_fn

#dumps the xed-ild-eosz.c file that defines all lookup functions
#for EOSZ resolution
#FIXME: should dump header file too
def work(agi, united_lookup, eosz_nts, ild_gendir, debug):
    
    #dump lookup tables for each NT
    #just for debugging
    nt_arrays = []
    for nt_name in eosz_nts:
        array = ild_nt.gen_nt_lookup(agi, nt_name, 'EOSZ')
        if not array:
            return None
        nt_arrays.append(array)
    ild_nt.dump_lu_arrays(agi, nt_arrays, 'ild_eosz_debug.txt',
                          'ild_eosz_debug_header.txt')
    
    #get all sequences of NTs that set EOSZ 
    #we will use these sequences to create EOSZ-computing functions     
    all_eosz_seq = get_all_eosz_seq(united_lookup)
    debug.write('EOSZ SEQS: %s\n' % all_eosz_seq)
    
    #for each EOSZ sequence create a lookup array
    nt_seq_arrays = {}
    for nt_seq in all_eosz_seq:
        array = ild_nt.gen_nt_seq_lookup(agi, nt_seq, _eosz_token)
        if not array:
            return None
        nt_seq_arrays[tuple(nt_seq)] = array
    #init function calls all single init functions for the created tables
    nt_seq_values = [v for (k,v) in sorted(nt_seq_arrays.items())]
    init_f = ild_nt.gen_init_function(nt_seq_values, 
                                      'xed_ild_eosz_init')
    #dump init and lookup functions for EOSZ sequences
    ild_nt.dump_lu_arrays(agi, nt_seq_values, _eosz_c_fn,
                          mbuild.join('include-private', _eosz_header_fn),
                          init_f)
    #generate EOSZ getter functions - they get xed_decoded_inst_t*
    #and return EOSZ value (corresponding to EOSZ NT sequence 
    #that they represent) 
    getter_fos = []
    for names in nt_seq_arrays.keys():
        arr = nt_seq_arrays[names]
        getter_fo = ild_codegen.gen_derived_operand_getter(agi, _eosz_token,
                                                           arr, list(names))
        getter_fos.append(getter_fo)
    
    ild_codegen.dump_flist_2_header(agi, 'xed-ild-eosz-getters.h', 
            [ildutil.ild_private_header, 
             _eosz_header_fn, 
             operand_storage.get_operand_accessors_fn()], getter_fos)
    
    #getter_lookup = gen_getter_fn_lookup(agi, united_lookup, nt_seq_arrays)
    
    return nt_seq_arrays
    

