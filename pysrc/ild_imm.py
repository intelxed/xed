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

import ild_nt
import mbuild
import ildutil
import codegen
import ild_eosz
import ild_info
import ild_codegen
import operand_storage

_imm_token         = 'IMM_WIDTH'
_ild_t_imm_member  = 'imm_width'
_uimm1_nt          = 'UIMM8_1'
_l3_header_fn      = 'xed-ild-imm-l3.h'
_l2_header_fn      = 'xed-ild-imm-l2.h'
_l1_header_fn      = 'xed-ild-imm-l1.h'
_l3_c_fn           = 'xed-ild-imm-l3.c'
_l2_c_fn           = 'xed-ild-imm-l2.c'
_imm0_fn           = 'xed_lookup_function_0_IMM_WIDTH_CONST_l2'
_imm_lu_header_fn  = 'xed-ild-imm-bytes.h'


def get_imm_nt_seq(ptrn_wrds, imm_nts):
    """
    @param ptrn_wrds: list of tokens in instructions pattern
    @type ptrn_wrds: [string]
    @param imm_nts: list of names of IMM_WIDTH-binding NTs
    @type imm_nts: [string]
    
    @return nt_names: list of names of IMM_WIDTH binding NTs
    @type nt_names: [string]
    
    Returns a list of names of IMM-binding NTs in the pattern.
    generally there is only one NT for IMM_WIDTH. 
    But ENTER, EXTRQ and INSERTQ instructions have two immediate
    NTs in pattern. This strange NT UIMM8_1 doesn't bind IMM_WIDTH.
    We should take special care of it.
    It is also possible to track captured operands and to check if UIMM1
    is among them, that would be a more generic way, but more complicated
    and it seems a waste to implement it for just one rare UIMM_1 NT.
    """
    return ild_nt.get_nt_seq(ptrn_wrds, list(imm_nts) + [_uimm1_nt])



def get_all_imm_seq(instr_by_map_opcode):
    """
    @param instr_by_map_opcode: lookup of ild_info.ild_info_t objects representing
    current ISA. This lookup should have been built from storage+grammar
    @type instr_by_map_opcode: ild_info.ild_storage_t
    
    @return seq_list: list of all variations of IMM-binding NT sequences in
    instr_by_map_opcode.
    @type seq_list: [ [string] ]
    """
    all_seq = set()
    infos = instr_by_map_opcode.get_all_infos()
    for info in infos:
        #lists are unhashable, hence we have to use tuples instead
        all_seq.add(tuple(info.imm_nt_seq))
    #convert back to lists, in order not to surprise user
    return_list = []
    for nt_tuple in all_seq:
        return_list.append(list(nt_tuple))
    return return_list


def get_imm_binding_nts(agi):
    """
    @param agi: all generator info object. main data structure of generator.
    
    @return nt_list: list of names of NTs in the grammar that bind IMM_WIDTH
    operand.
    @type nt_list: [string]
    """
    nt_names = ild_nt.get_setting_nts(agi, _imm_token)
    #filter ONE nt
    #FIXME: remove ONE nt from  grammar
    return list(filter(lambda x: x!='ONE', nt_names))


def get_target_opname():
    """
    @return opname: name of the IMM operand - IMM_WIDTH
    @type opname: string
    """
    return _imm_token
    

def get_l2_fn_from_info(info, imm_dict):
    is_const = ild_codegen.is_constant_l2_func(info.imm_nt_seq, imm_dict)
    
    if is_const:
        l2_fn = ild_codegen.get_l2_fn(info.imm_nt_seq,
                                      _imm_token,
                                      [],
                                      None,
                                      _imm0_fn,
                                      True)
    else:
        l2_fn = ild_codegen.get_l2_fn(info.imm_nt_seq,
                                      _imm_token, 
                                      info.eosz_nt_seq,
                                      ild_eosz.get_target_opname(),
                                      _imm0_fn,
                                      False)
    return l2_fn
  


def _gen_imm0_function(agi):
    """for patterns that don't set IMM_WIDTH token these patterns have
    has_imm==0p and we define a L2 lookup function that returns 0"""
    
    #return_type = operand_storage.get_ctype(_imm_token)
    return_type = 'void'
    fo = codegen.function_object_t(_imm0_fn, return_type,
                                       static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)
    setter_fn = operand_storage.get_op_setter_fn(_ild_t_imm_member)
    fo.add_code_eol('%s(%s, %s)' % (setter_fn, data_name,'0'))
    return fo


def _is_imm_conflict(info_list, imm_dict):
    """Check if info list conflicts on imm_bytes property.
    Sometimes info objects conflict on L2 function name, but those 
    different functions actually return same values. 
    For example:
    L2 functions defined by UIMM8() and SIMM8() NTs have different names
    but both are const functions returning 8. If info list has those
    two L2 functions, we should discover that and return that there is no
    conflict
    
    @param info_list: list of info objects to check
    @type info_list: [ild_info.ild_info_t
    
    @param imm_dict: dictionary from IMM-NT names to corresponding
    codegen.array_t objects describing those NTs
    @type imm_dict: { string(nt_name) : codegen.array_t(nt_arr) }
    
    @return: True|False - if there is a conflict in lookup function name
     
    """
    if len(info_list) <= 1:
        return False
    first = info_list[0]
    l2_fn_first = get_l2_fn_from_info(first, imm_dict)
    
    for info in info_list[1:]:
        l2_fn_cur = get_l2_fn_from_info(info, imm_dict)
        
        if l2_fn_first != l2_fn_cur:
            #there are const l3 functions that return only one value:
            #SIMM8 UIMM8 etc. If they return same value, they should not
            #conflict
            nt_seq1 = first.imm_nt_seq
            nt_seq2 = info.imm_nt_seq
            
            #check if we have double imm patterns
            if len(nt_seq1) > 1 or len(nt_seq2) > 1:
                #function names are different, hence conflict
                return True
            
            if len(nt_seq1) != len(nt_seq2):
                return True
            imm_arr1 = imm_dict[nt_seq1[0]]
            imm_arr2 = imm_dict[nt_seq2[0]]
            val_space1 = imm_arr1.get_values_space()
            val_space2 = imm_arr2.get_values_space()
            if len(val_space1) == len(val_space2) == 1:
                if val_space1[0] == val_space2[0]:
                    continue
            return True
    return False

#fixme: write a good comment about conflict resolution in eosz and imm
#a list of conflict resolution functions to use when we have conflicts 
#between info objects in the same map-opcode
#for example map 0, opcode c7 has xbegin and mov instructions that have 
#different immediate nts - SIMMz for mov and no imm for xbegin
#and we decide by REG field which lookup function to use
_resolution_functions = [
                         #it seems that one resolution function is enough
                        ild_codegen.gen_l1_byreg_resolution_function,
                       ]

#these are for second immediate guys.
#It also happens that AMD second immediate guys define uneasy conflicts
#so we are killing two birds with one stone 
_hardcoded_res_functions_imm = {
    #(map, opcode)          :  L1_function_name 
    ('legacy_map1', '0x78') : 'xed_ild_hasimm_map0x0F_op0x78_l1',
    ('legacy_map0', '0xc8') : 'xed_ild_hasimm_map0x0_op0xc8_l1'
}

def _resolve_conflicts(agi, info_list, imm_dict):
    """Try to resolve conflicts by applying the conflict resolution
    functions defined in _resolution_functions list.
    
    @param info_list: list of info objects to that have a conflict
    @type info_list: [ild_info.ild_info_t
    
    @param imm_dict: dictionary from IMM-NT names to corresponding
    codegen.array_t objects describing those NTs
    @type imm_dict: { string(nt_name) : codegen.array_t(nt_arr) }
    
    @return: codegen.function_object_t defining the conflict resolution (L1)
    function for info_list's map-opcode
    
    """
    #FIXME: we can use ild_cdict.constraint_dict_t for resolving
    #conflicts it would work for any patterns (now we try to resolve
    #only by REG operand)
    for func in _resolution_functions:
        fo = func(agi,info_list, imm_dict, _is_imm_conflict,
                        get_l2_fn_from_info, _imm_token) 
        if fo:
            return fo
    return None

def gen_l1_functions_and_lookup(agi, instr_by_map_opcode, imm_dict):
    """Compute L1(conflict resolution) functions list and imm_bytes 
    lookup tables dict.
    @param agi: all generators info
    
    @param instr_by_map_opcode: the 2D lookup by map-opcode to info objects list.
    instr_by_map_opcode['0x0']['0x78'] == [ild_info1, ild_info2, ... ]
    @type instr_by_map_opcode: 
    {string(insn_map) : {string(opcode): [ild_info.ild_info_t]} }
    
    
    """
    l1_resolution_fos = []
    l1_lookup = {}
    for insn_map in ild_info.get_dump_maps_imm(agi):
        l1_lookup[insn_map] = {}
        for opcode in range(0, 256):
            #look in the hard-coded resolution functions
            #they are manually written for the two-immediates instructions
            if (insn_map, hex(opcode)) in _hardcoded_res_functions_imm:
                l1_fn = _hardcoded_res_functions_imm[(insn_map, hex(opcode))]
                l1_lookup[insn_map][hex(opcode)] = l1_fn
                continue
            info_list = instr_by_map_opcode.get_info_list(insn_map, hex(opcode))
            #get only info objects with minimum priority
            info_list = ild_info.get_min_prio_list(info_list)
            is_conflict = _is_imm_conflict(info_list, imm_dict)
            
            if len(info_list) > 1 and is_conflict:
                l1_fo = _resolve_conflicts(agi, info_list, imm_dict)
                if not l1_fo:
                    ildutil.ild_err('FAILED TO GENERATE L1 CONFLICT ' +
                    'RESOLUTION FUNCTION FOR IMM\n infos:\n %s' %
                    "\n".join([str(info) for info in info_list]))
                    
                l1_resolution_fos.append(l1_fo)
                l1_fn = l1_fo.function_name
            #if map-opcode pair is undefined the lookup function ptr is NULL
            #this will happen for opcodes like 0F in 0F map - totally illegal
            #opcodes, that should never be looked up in runtime.
            elif len(info_list) == 0:
                l1_fn = _imm0_fn
            else:
                #there are no conflicts, we can use L2 function as L1
                info = info_list[0]
                l1_fn = get_l2_fn_from_info(info, imm_dict)
                if not l1_fn:
                    return None
            l1_lookup[insn_map][hex(opcode)] = l1_fn
    return l1_resolution_fos,l1_lookup

def _filter_uimm1_nt(imm_nt_names):
    """Filter UIMM8_1 NT from list"""
    return list(filter(lambda x: x!=_uimm1_nt, imm_nt_names))

       
def work(agi, instr_by_map_opcode, imm_nts, ild_gendir, eosz_dict, 
         debug):
    """main entry point of the module."""
    #dump lookup functions for each NT
    #Let's call these function Level3 functions (L3)
    nt_dict = {}
    
    #generate the L3 functions
    #Every NT, that changes IMM_WIDTH, defines a L3 function.
    #For example SIMM8() NT defines a L3 function that returns 1 (1 byte).
    #And SIMMv() NT defines a function that gets EOSZ and returns IMM_WIDTH
    #value depending on EOSZ.
    
    #UIMM8_1 doesn't bind IMM_WIDTH operand, it is a special case
    #there is nothing to generate for it. 
    for nt_name in _filter_uimm1_nt(imm_nts):
        array = ild_nt.gen_nt_lookup(agi, nt_name, _imm_token, 
                                     target_type=ildutil.ild_c_op_type,
                                     level='l3')
        nt_dict[nt_name] = array

    nt_dict_values = [v for (k,v) in sorted(nt_dict.items())]

    #create function that calls all initialization functions for L3
    init_f = ild_nt.gen_init_function(nt_dict_values,
                                      'xed_ild_imm_l3_init')
    
    #dump L3 functions
    ild_nt.dump_lu_arrays(agi, nt_dict_values, _l3_c_fn,
                          mbuild.join('include-private',_l3_header_fn),
                          init_f)
    
    #get all IMM NT sequences that are used in patterns
    #The only case of IMM sequence is when we have UIMM1() NT - the second
    #immediate NT.    
    all_imm_seq = get_all_imm_seq(instr_by_map_opcode)
    debug.write('IMM SEQS: %s\n' % all_imm_seq)

    # L2 / Level2 functions: set imm_width
    # Now we define functions that compute EOSZ value (using one of
    # the EOSZ-resolution functions) and then use 
    # one of the L3 functions(that need EOSZ) to set IMM_WIDTH.

    # The names of these functions should be something like 
    # xed_ild_SIMMz_OSZ_NONTERM_DF64 - to define the imm-binding nonterm 
    # and to define the EOSZ-resolution NT sequence.
    # L2 functions are defined by single ild_info_t object - by its
    # eosz_nt_seq and imm_nt_seq
    l2_functions = ild_codegen.gen_l2_func_list(agi, nt_dict, eosz_dict,
                                                _ild_t_imm_member)
    #append function for imm_bytes==0
    l2_functions.append(_gen_imm0_function(agi))
    
    l2_headers = [ ild_eosz.get_ntseq_header_fn(),
                   _l3_header_fn,
                   ildutil.ild_header,
                   operand_storage.get_operand_accessors_fn() ]
    ild_codegen.dump_flist_2_header(agi, _l2_header_fn, l2_headers, 
                                    l2_functions)

    # L1 / Level1 functions:
    # Now we define functions that resolve conflicts (if any)
    # using modrm.reg bits, and that way decide which L2 function to
    # call to set the IMM value.
    # These functions will be the value of map,opcode lookup tables.
    
    # These functions should be dumped after we have a look on the
    # instr_by_map_opcode mapping in order to know what conflicts exist and
    # for each conflict to create a resolution lookup table.
    
    # L1 functions are defined by a list of ild_info_t objects that
    # have same map,opcode.
    l1_functions,l1_lookup = gen_l1_functions_and_lookup(agi,
                                                         instr_by_map_opcode,
                                                         nt_dict)

    ild_codegen.dump_flist_2_header(agi, _l1_header_fn, [_l2_header_fn], 
                                    l1_functions)
    
    headers = [ _l1_header_fn,
                ildutil.ild_private_header, 
                operand_storage.get_operand_accessors_fn() ]
    ild_codegen.dump_lookup_new(agi,
                                l1_lookup,
                                _ild_t_imm_member, 
                                _imm_lu_header_fn,
                                headers, 
                                ildutil.l1_ptr_typename)

