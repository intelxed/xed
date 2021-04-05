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

import collections

import ild_nt
import ildutil
import codegen
import ild_eosz
import ild_easz
import ild_info
import ild_codegen
import operand_storage
import mbuild

_disp_token        = 'DISP_WIDTH'
_brdisp_token      = 'BRDISP_WIDTH'
_ild_t_disp_member = 'disp_width'
_l3_c_fn           = 'xed-ild-disp-l3.c'
_l2_c_fn           = 'xed-ild-disp-l2.c'
_l3_header_fn      = 'xed-ild-disp-l3.h'
_l2_header_fn      = 'xed-ild-disp-l2.h'
_l1_header_fn      = 'xed-ild-disp-l1.h'
_const_suffix      = 'CONST'
_empty_fn          = 'xed_lookup_function_EMPTY_DISP_CONST_l2'

_disp_lu_header_fn = 'xed-ild-disp-bytes.h'

def get_disp_nt_seq(ptrn_wrds, disp_nts):
    """
    @param ptrn_wrds: list of tokens in instructions pattern
    @type ptrn_wrds: [string]
    @param disp_nts: list of names of [BR]?DISP_WIDTH-binding NTs
    @type disp_nts: [string]
    
    @return nt_names: list of names of [BR]?DISP_WIDTH binding NTs
    @type nt_names: [string]
    
    Returns a list of names of [BR]?DISP_WIDTH NTs in the pattern.
    """
    return ild_nt.get_nt_seq(ptrn_wrds, list(disp_nts))



def get_all_disp_seq(instr_by_map_opcode):
    """@param instr_by_map_opcode: dict(map,opcode) -> list
    ild_info.ild_info_t objects representing current ISA. 
    
    @return seq_list: list of all variations of DISP-binding NT sequences in
    instr_by_map_opcode.
    @type seq_list: [ [string] ]    """
    
    all_seq = set()
    infos = instr_by_map_opcode.get_all_infos()
    #infos = plist
    for info in infos:
        #lists are unhashable, hence we have to use tuples instead
        all_seq.add(tuple(info.disp_nt_seq))
    #convert back to lists, in order not to surprise user
    return_list = []
    for nt_tuple in all_seq:
        return_list.append(list(nt_tuple))
    return return_list


def get_disp_binding_nts(agi):
    """
    Go through all defined NTs in agi and return names of those,
    that bind DISP_WIDTH
    """
    return ild_nt.get_setting_nts(agi, _disp_token)

def get_brdisp_binding_nts(agi):
    """
    Go through all defined NTs in agi and return names of those,
    that bind BRDISP_WIDTH
    """
    return ild_nt.get_setting_nts(agi, _brdisp_token)



def get_l2_fn_from_info(info, disp_dict):
    """
    Return L2 function name defined by the info.
    disp_dict is a dictionary from [BR]DISP NT name to codegen.array
    of the corresponding NT.
    """
    is_const = ild_codegen.is_constant_l2_func(info.disp_nt_seq, disp_dict)
    if len(info.disp_nt_seq) == 0:
        return _empty_fn
    disp_nt = disp_dict[info.disp_nt_seq[0]]
    disp_token = disp_nt.get_target_opname()
    if ild_eosz.get_target_opname() in disp_nt.get_arg_names():
        argname = ild_eosz.get_target_opname()
        arg_seq = info.eosz_nt_seq
    else:
        argname = ild_easz.get_target_opname()
        arg_seq = info.easz_nt_seq
    
    if is_const:
        argname = None
        arg_seq = []

    l2_fn = ild_codegen.get_l2_fn(info.disp_nt_seq, disp_token, 
                                  arg_seq,
                                  argname,
                                  _empty_fn, is_const)
    return l2_fn

def _is_disp_conflict(info_list, disp_dict):
    """
    Return True|False whether infos in info_list conflict on L2
    functions (and then we need to define L1 function for this list).
    """
    if len(info_list) <= 1:
        return False
    first = info_list[0]
    l2_fn_first = get_l2_fn_from_info(first, disp_dict)
    for info in info_list[1:]:
        l2_fn_cur = get_l2_fn_from_info(info, disp_dict)
        if l2_fn_first != l2_fn_cur:
            return True
    return False

#a list of conflict resolution functions to use when we have conflicts 
#between info objects in the same map-opcode
_resolution_functions = [ ild_codegen.gen_l1_byreg_resolution_function,
                          ild_codegen.gen_l1_bymode_resolution_function ]

def _resolve_conflicts(agi, info_list, disp_dict):
    """Try to resolve conflicts by applying the conflict resolution
    functions defined in _resolution_functions list.
    
    @param info_list: list of info objects to that have a conflict
    @type info_list: [ild_info.ild_info_t
    
    @param disp_dict: dictionary from DISP-NT names to corresponding
    codegen.array_t objects describing those NTs
    @type disp_dict: { string(nt_name) : codegen.array_t(nt_arr) }
    
    @return: codegen.function_object_t defining the conflict resolution (L1)
    function for info_list's map-opcode
    
    """
    for func in _resolution_functions:
        fo = func(agi, info_list, disp_dict, _is_disp_conflict,
                        get_l2_fn_from_info, 'DISP') 
        if fo:
            return fo
    return None

_hardcoded_res_functions_disp = {}

def gen_l1_functions_and_lookup(agi, instr_by_map_opcode, disp_dict):
    """Compute L1(conflict resolution) functions list and disp_bytes lookup 
    tables dict.
    @param agi: all generators info
    
    @param instr_by_map_opcode: the 2D lookup by map-opcode to info objects list.
    instr_by_map_opcode['0x0']['0x78'] == [ild_info1, ild_info2, ... ]
    @type instr_by_map_opcode: 
    {string(insn_map) : {string(opcode): [ild_info.ild_info_t]} }    """
    #list of L1 function objects that resolve conflicts in map-opcodes
    #functions. This list will be dumped to xed-ild--disp-l1.h
    l1_resolution_fos = []
    
    #dictionary l1_lookup[insn_map][opcode] = l1_function_name
    #this dictionary will be used to dump the has_disp lookup tables
    l1_lookup = {}
    
    #dictionary from function body(as string) to list of function objects
    #with that body.
    #This dict will be used to bucket identical functions in order to
    #not define same functions more than once.
    l1_bucket_dict = collections.defaultdict(list)
    
    for insn_map in ild_info.get_dump_maps_disp(agi):
        l1_lookup[insn_map] = {}
        for opcode in range(0, 256):
            #look in the hardcoded resolution functions
            if (insn_map, hex(opcode)) in _hardcoded_res_functions_disp:
                l1_fn = _hardcoded_res_functions_disp[(insn_map, hex(opcode))]
                l1_lookup[insn_map][hex(opcode)] = l1_fn
                continue
            info_list = instr_by_map_opcode.get_info_list(insn_map, hex(opcode))
            #get only info objects with minimum priority
            info_list = ild_info.get_min_prio_list(info_list)
            is_conflict = _is_disp_conflict(info_list, disp_dict)
            if len(info_list) > 1 and is_conflict:
                l1_fo = _resolve_conflicts(agi, info_list, disp_dict)
                if not l1_fo:
                    ildutil.ild_err('FAILED TO GENERATE L1 CONFLICT ' +
                    'RESOLUTION FUNCTION FOR DISP\n infos: %s' %
                    "\n".join([str(info) for info in info_list]))
                l1_bucket_dict[l1_fo.emit_body()].append(l1_fo)
                l1_fn = l1_fo.function_name
            
            elif len(info_list) == 0:
                #if map-opcode pair is undefined the lookup function ptr is
                #NULL.
                #This will happen for opcodes like 0F in 0F map - totally 
                #illegal opcodes, that should never be looked up in runtime.
                #We define NULL pointer for such map-opcodes
                
                l1_fn = _empty_fn
            else:
                #there are no conflicts, we can use L2 function as L1
                info = info_list[0]
                l1_fn = get_l2_fn_from_info(info, disp_dict)
            l1_lookup[insn_map][hex(opcode)] = l1_fn
    
    #there are 18 L1 functions with same body (currently, may change 
    #in future) 
    #we are going to bucket L1 functions with identical body but different
    #names in order to have only one function for each unique body
    #FIXME: the bucketed function name is not self descriptive
    bucket_name = 'xed_lookup_function_DISP_BUCKET_%s_l1'
    cur_bucket = 0
    for res_fun_list in list(l1_bucket_dict.values()):
        if len(res_fun_list) == 1:
            #only one such function - we should define it as is
            l1_resolution_fos.append(res_fun_list[0])
        else:
            #more than one L1 function with identical body
            #we should define L1 function with that body
            #and fix references in the lookup table
            
            #the function name
            cur_buck_name = bucket_name % cur_bucket
            cur_bucket += 1
            
            #fix references in the lookup table
            for res_fun in res_fun_list:
                for insn_map in l1_lookup.keys():
                    for opcode in l1_lookup[insn_map].keys():
                        cur_fn = l1_lookup[insn_map][opcode]
                        if cur_fn == res_fun.function_name:
                            l1_lookup[insn_map][opcode] = cur_buck_name
            #define the L1 function and add it to the list of L1 functions
            #to dump
            buck_fo = res_fun_list[0]
            buck_fo.function_name = cur_buck_name
            l1_resolution_fos.append(buck_fo)
                
    return l1_resolution_fos,l1_lookup
   


def _gen_empty_function(agi):
    """This function is for patterns that don't set [BR]DISP_WIDTH tokens.
    These patterns have disp_bytes set earlier in xed-ild.c and we
    define a L2 lookup function that does nothing    """
    
    operand_storage = agi.operand_storage
    return_type = 'void'
    fo = codegen.function_object_t(_empty_fn, return_type,
                                   static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)
    fo.add_code('/*This function does nothing for map-opcodes whose')
    fo.add_code('disp_bytes value is set earlier in xed-ild.c')
    fo.add_code('(regular displacement resolution by modrm/sib)*/\n')
    fo.add_code('/*pacify the compiler*/')
    fo.add_code_eol('(void)%s' % data_name)
    return fo



def _gen_l3_array_dict(agi, nt_names, target_op):
    """
    For each NT from nt_names, generate and codegen.array_t object
    return a dictionary from nt_name to array_t.
    """
    nt_dict = {}
    for nt_name in nt_names:
        array = ild_nt.gen_nt_lookup(agi, nt_name, target_op, 
                        target_type=ildutil.ild_c_op_type, level='l3')
        nt_dict[nt_name] = array
    return nt_dict

       
def work(agi, instr_by_map_opcode,  disp_nts, brdisp_nts, ild_gendir, 
         eosz_dict, easz_dict, debug):
    """Main entry point of the module.  Generates all the L1-3 functions
    and dumps disp_bytes lookup tables.    """
    
    #get all used DISP NT sequences that appear in patterns
    #we are going to generate L1-3 functions only for these sequences
    all_disp_seq = get_all_disp_seq(instr_by_map_opcode)
    
    #check that all sequences are actually single NTs 
    #(each sequence has only one NT)
    #my observation is that they really are. This simplifies things
    #and we are going to rely on that.
    all_nts = []
    for ntseq in all_disp_seq:
        if len(ntseq) > 1:
            ildutil.ild_err("Unexpected DISP NT SEQ %s" % ntseq)
        if len(ntseq) == 0:
            continue #the empty NT sequence
        all_nts.append(ntseq[0])
    
    #get only those NTs that actually appear in PATTERNs
    disp_nts = list(filter(lambda nt: nt in all_nts, disp_nts))
    brdisp_nts = list(filter(lambda nt: nt in all_nts, brdisp_nts))

    debug.write('DISP SEQS: %s\n' % all_disp_seq)
    debug.write('DISP NTs: %s\n' % disp_nts)
    debug.write('BRDISP NTs: %s\n' % brdisp_nts)
    
    brdisp_dict = _gen_l3_array_dict(agi, brdisp_nts, _brdisp_token)
    disp_dict   = _gen_l3_array_dict(agi, disp_nts,   _disp_token)
    
    nt_arr_list = ([v for (k,v) in sorted(brdisp_dict.items())] +
                   [v for (k,v) in sorted(disp_dict.items())])
    #create function that calls all initialization functions
    init_f = ild_nt.gen_init_function(nt_arr_list, 'xed_ild_disp_l3_init')
    
    #dump L3 functions
    ild_nt.dump_lu_arrays(agi, nt_arr_list, _l3_c_fn,
                          mbuild.join('include-private',_l3_header_fn),
                          init_f)
    
    #create L2 functions
    
    #We need to know for each DISP NT whether it depends on EOSZ or
    #EASZ and supply appropriate arg_dict to gen_l2_func_list()
    l2_functions = []
    eosz_op = ild_eosz.get_target_opname()
    easz_op = ild_easz.get_target_opname()
    for nt_name,array in sorted(disp_dict.items()) + sorted(brdisp_dict.items()):
        #Some DISP NTs depend on EOSZ, others on EASZ, we need to know
        #that when we generate L2 functions
        if eosz_op in array.get_arg_names():
            arg_dict = eosz_dict
        else:
            arg_dict = easz_dict
        flist = ild_codegen.gen_l2_func_list(agi, {nt_name:array},
                        arg_dict, _ild_t_disp_member)
        l2_functions.extend(flist)
    
    #create the doing-nothing L2 function for map-opcodes
    #with regular displacement resolution
    l2_functions.append(_gen_empty_function(agi))
    
    #dump L2 functions
    l2_headers = [ild_eosz.get_ntseq_header_fn(),
                  ild_easz.get_ntseq_header_fn(),
                  _l3_header_fn, ildutil.ild_private_header,
                  operand_storage.get_operand_accessors_fn()]
    ild_codegen.dump_flist_2_header(agi, _l2_header_fn, l2_headers, 
                                    l2_functions)
    
    #create the L1 functions and lookup tables
    
    #join the brdisp and disp dictionaries
    disp_dict.update(brdisp_dict)
    
    #generate L1 functions and lookup tables
    l1_functions, l1_lookup = gen_l1_functions_and_lookup(agi,
                                                          instr_by_map_opcode,
                                                          disp_dict)
    #dump L1 functions
    ild_codegen.dump_flist_2_header(agi,
                                    _l1_header_fn,
                                    [_l2_header_fn], 
                                    l1_functions)
    #dump lookup tables
    headers = [ _l1_header_fn,
                ildutil.ild_private_header,
                operand_storage.get_operand_accessors_fn() ]
    ild_codegen.dump_lookup(agi,
                            l1_lookup,
                            _ild_t_disp_member, 
                            _disp_lu_header_fn,
                            headers, 
                            ildutil.l1_ptr_typename)


