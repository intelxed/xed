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
import mbuild
import ild_info
import operand_storage

_arg_const_suffix = 'CONST'

_dec_strings = {'obj_str'      : 'd',
                'obj_type'     : 'xed_decoded_inst_t',
                'obj_const'    : 'const ',
                'lu_namespace' : 'dec',
                'static'       : True
               }
_dec_strings.update(ildutil.xed_strings)

def get_derived_op_getter_fn(op_nts, opname):
    return ild_nt.get_lufn(op_nts, opname) + '_getter'

def get_l2_fn(target_nt_names, target_opname, arg_nts, arg_name,
              empty_seq_name, is_const):
    """Generate L2 function name from IMM NT names list and EOSZ NT names list.

    Each L2 function is defined by a single PATTERN row in xed's grammar.
    (By pattern's IMM-binding and EOSZ-binding NTs)
    Hence, it is enough to know the IMM NTs sequence and EOSZ NTs sequence to
    define a L2 function. Or in this case to define a L2 function name.

    ATTENTION: as we decided to hardcode special AMD's double immediate
    instruction's L1 functions, the length of imm_nt_names can be ONLY 1

    @param imm_nt_names: list of IMM-binding NT names
    @param eosz_nt_names: list of EOSZ-binding NT names

    @return: L2 function name

    """
    #if there are no target NTs in pattern, then L2 function is
    #the default function for empty sequences
    #(return 0 for immediates and return; for disp)
    if len(target_nt_names) == 0:
        return empty_seq_name

    #currently there are no supported target NT sequences that have more
    #than 1 NT. Check that.
    if len(target_nt_names) > 1:
        ildutil.ild_err("Cannot generate L2 function name for NT seq %s" %
                        target_nt_names)

    if is_const:
        arg_suffix = _arg_const_suffix
    else:
        arg_suffix = "_".join(arg_nts + [arg_name])
    #L2 function name is a concatenation of L3 function name and possible
    #argument(e.g EOSZ or EASZ) NT names
    l3_prefix = ild_nt.get_lufn(target_nt_names, target_opname)
    return l3_prefix + '_%s_l2' % arg_suffix


#generate L2 function that doesn't depend on arguments
def gen_const_l2_function(agi, nt_name, target_opname, ild_t_member):
    return_type = 'void'
    l3_fn = ild_nt.get_lufn([nt_name], target_opname, flevel='l3')
    l2_fn = get_l2_fn([nt_name], target_opname, [], None,
              None, True)

    fo = codegen.function_object_t(l2_fn, return_type,
                                       static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)

    temp_var = '_%s' % ild_t_member
    ctype = ildutil.ild_c_op_type
    fo.add_code_eol('%s %s' % (ctype, temp_var))

    fcall = l3_fn + '()'
    fo.add_code_eol('%s = (%s)%s' % (temp_var, ctype, fcall))
    setter_fn = operand_storage.get_op_setter_fn(ild_t_member)
    fo.add_code_eol('%s(%s, %s)' % (setter_fn, data_name,temp_var))
    return fo

def gen_derived_operand_getter(agi, opname, op_arr, op_nt_names):
    return_type = agi.operand_storage.get_ctype(opname)

    op_lufn = ild_nt.get_lufn(op_nt_names, opname)
    getter_fn = get_derived_op_getter_fn(op_nt_names, opname)

    fo = codegen.function_object_t(getter_fn, return_type, static=True,
                                   inline=True)
    data_name = 'x'
    fo.add_arg('const ' +ildutil.ild_c_type + ' %s' % data_name)

    for range_tuple in op_arr.ranges:
        range_type, range_min, range_max, paramname = range_tuple
        param_name = '_%s' % paramname.lower()
        fo.add_code_eol(ildutil.ild_c_op_type + ' %s' % param_name)

    params = []
    for range_tuple in op_arr.ranges:
        range_type, range_min, range_max, paramname = range_tuple
        param_name = '_%s' % paramname.lower()
        access_call = emit_ild_access_call(paramname, data_name)

        fo.add_code_eol('%s = (%s)%s' %(param_name, ildutil.ild_c_op_type,
                                        access_call))
        params.append(param_name)

    lu_fn = op_arr.lookup_fn.function_name

    lu_call = lu_fn + '(%s)'
    lu_call = lu_call % (', '.join(params))
    fo.add_code_eol('return %s' %  lu_call)
    return fo

#generate L2 function that depends on argument
def gen_scalable_l2_function(agi, nt_name, target_opname,
                             ild_t_member,
                             arg_arr, arg_nt_names):
    return_type = 'void'
    l3_fn = ild_nt.get_lufn([nt_name], target_opname, flevel='l3')
    arg_name = arg_arr.get_target_opname()
    l2_fn = get_l2_fn([nt_name], target_opname, arg_nt_names, arg_name,
              None, False)

    fo = codegen.function_object_t(l2_fn, return_type,
                                       static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)
    arg_type = agi.operand_storage.get_ctype(arg_name)
    arg_var = '_%s' % arg_name.lower()
    fo.add_code_eol('%s %s' % (arg_type, arg_var))

    temp_var = '_%s' % ild_t_member
    ctype = ildutil.ild_c_op_type
    fo.add_code_eol('%s %s' % (ctype, temp_var))



    for range_tuple in arg_arr.ranges:
        range_type, range_min, range_max, paramname = range_tuple
        param_name = '_%s' % paramname.lower()
        fo.add_code_eol(ildutil.ild_c_op_type + ' %s' % param_name)

    params = []
    for range_tuple in arg_arr.ranges:
        range_type, range_min, range_max, paramname = range_tuple
        param_name = '_%s' % paramname.lower()
        access_call = emit_ild_access_call(paramname, data_name)

        fo.add_code_eol('%s = (%s)%s' %(param_name, ildutil.ild_c_op_type,
                                        access_call))
        params.append(param_name)

    arg_fn = arg_arr.lookup_fn.function_name

    arg_call = arg_fn + '(%s)'
    arg_call = arg_call % (', '.join(params))
    fo.add_code_eol('%s = %s' % (arg_var, arg_call))

    fcall = '%s(%s)' % (l3_fn, arg_var)

    fo.add_code_eol('%s = (%s)%s' % (temp_var, ctype, fcall))
    setter_fn = operand_storage.get_op_setter_fn(ild_t_member)
    fo.add_code_eol('%s(%s, %s)' % (setter_fn, data_name,temp_var))
    return fo


def gen_l2_func_list(agi, target_nt_dict, arg_nt_dict,
                     ild_t_member):
    """generate L2 functions"""
    l2_func_list = []
    for (nt_name,array) in sorted(target_nt_dict.items()):
        target_opname = array.get_target_opname()
        if array.is_const_lookup_fun():
            fo = gen_const_l2_function(agi, nt_name,
                                target_opname, ild_t_member)
            l2_func_list.append(fo)
        else:
            for arg_nt_seq,arg_arr in sorted(arg_nt_dict.items()):
                fo = gen_scalable_l2_function(agi, nt_name,
                     target_opname, ild_t_member, arg_arr, list(arg_nt_seq))
                l2_func_list.append(fo)
    return l2_func_list

def dump_flist_2_header(agi, fname, headers, functions,
                        is_private=True,
                        emit_headers=True,
                        emit_bodies=True):
    if is_private:
        h_file = agi.open_file(mbuild.join('include-private', fname),
                                  start=False)
    else:
        h_file = agi.open_file(fname, start=False)
    
    codegen.dump_flist_2_header(h_file, functions, headers,
                                emit_headers,
                                emit_bodies)
    
def is_constant_l2_func(nt_seq, nt_dict):
    if len(nt_seq) == 0:
        return True
    if len(nt_seq) > 1:
        ildutil.ild_err("Unexpected NT SEQ while determining" +
                        " constness of a l3 function: %s" % nt_seq)
    nt_arr = nt_dict[nt_seq[0]]
    return nt_arr.is_const_lookup_fun()

_ordered_maps = ['']

def _test_map_all_zero(vv, phash_map_lu):
    """phash_map_lu is a dict[maps][0...255] pointing to a 2nd level
       lookup or it might be None indicating an empty map."""
    all_zero_map= collections.defaultdict(bool) # Default False
    for xmap in phash_map_lu.keys():
        omap = phash_map_lu[xmap]
        if omap == None:
            all_zero_map[xmap]=True
            mbuild.msgb("ALL ZEROS", "VV={} MAP={}".format(vv, xmap))
    return all_zero_map
            

def gen_static_decode(agi,
                      vv_lu,
                      op_lu_list,
                      h_fn='xed3-phash.h'):
    """generate static decoder"""
    
    phash_headers = ['xed-ild-eosz-getters.h',
                     'xed-ild-easz-getters.h',
                     'xed-internal-header.h',
                     'xed-ild-private.h']
    maplu_headers = []
    all_zero_by_map = {}
    for vv in sorted(vv_lu.keys()):
        (phash_map_lu, lu_fo_list) = vv_lu[vv]
        all_zero_by_map[vv] = _test_map_all_zero(vv, phash_map_lu)

        # dump a file w/prototypes and per-opcode functions pointed to
        # by the elements of the various 256-entry arrays.
        pheader = 'xed3-phash-vv{}.h'.format(vv)
        dump_flist_2_header(agi, pheader, ['xed3-operand-lu.h'], lu_fo_list)

        # dump 256-entry arrays for each (vv,map)
        map_lu_cfn = 'xed3-phash-lu-vv{}.c'.format(vv)
        map_lu_hfn = 'xed3-phash-lu-vv{}.h'.format(vv)
        maplu_headers.append(map_lu_hfn)
        
        name_pfx = 'xed3_phash_vv{}'.format(vv)
        elem_type = 'xed3_find_func_t'

        dump_lookup(agi,  #dump 256-entry arrays for maps in this encspace
                    phash_map_lu,
                    name_pfx,
                    map_lu_cfn,
                    [pheader],
                    elem_type,
                    output_dir=None,
                    all_zero_by_map=all_zero_by_map[vv])

        # dump a header with the decls for the 256-entry arrays or
        # #define NAME 0 for the empty arrays.
        h_file = agi.open_file(mbuild.join('include-private',map_lu_hfn),
                               start=False)
        h_file.start()
        for insn_map in sorted(phash_map_lu.keys()):
            arr_name = _get_map_lu_name(name_pfx, insn_map)
            if all_zero_by_map[vv][insn_map]:
                #h_file.add_code("#define {} 0".format(arr_name))
                pass
            else:
                h_file.add_code("extern const {} {}[256];".format(
                    elem_type, arr_name))
        h_file.close()                    

    #dump all the operand lookup functions in the list to a header file
    hdr = 'xed3-operand-lu.h'
    dump_flist_2_header(agi, hdr,
                        phash_headers,
                        op_lu_list,
                        emit_bodies=False)
    dump_flist_2_header(agi, 'xed3-operand-lu.c',
                        [hdr],
                        op_lu_list,
                        is_private=False,
                        emit_headers=False)

    # write xed3-phash.h (top most thing).
    #
    # xed3-pash.h contains a table indexed by encoding-space &
    # decoding-map mapping to functions handling decoding that part of
    # the space.
    h_file = agi.open_file(mbuild.join('include-private',h_fn),
                                  start=False)
    for header in maplu_headers:
        h_file.add_header(header)
    h_file.start()

    maps = ild_info.get_maps(agi)

    vv_num = [ int(x) for x in vv_lu.keys() ]
    vv_max = max(vv_num) + 1
    max_maps = ild_info.get_maps_max_id(agi) + 1
    arr_name = 'xed3_phash_lu'
    h_file.add_code('#define XED_PHASH_MAP_LIMIT {}'.format(max_maps))
    h_file.add_code('const xed3_find_func_t* {}[{}][XED_PHASH_MAP_LIMIT] = {{'.format(
         arr_name, vv_max))

    for vv in range(0,vv_max):
        maps = ild_info.get_maps_for_space(agi,vv)
        dmap = {mi.map_id:mi for mi in maps} # dict indexed by map_id

        init_vals = ['0'] * max_maps 
        for imap in range(0,max_maps):
            if imap in dmap:
                mi = dmap[imap]
                # if there are maps without instructions, then there
                # won't be top-level variables to look at for those
                # maps.
                if all_zero_by_map[str(vv)][mi.map_name]:
                    init_vals[imap] = '0'
                else:
                    init_vals[imap] = _get_map_lu_name( 'xed3_phash_vv{}'.format(vv),
                                                        mi.map_name )
        h_file.add_code('{{ {} }},'.format(', '.join(init_vals)))

    h_file.add_code('};')
    h_file.close()

def _get_map_lu_name(pfx, insn_map):
    return '%s_map_%s' % (pfx, insn_map)

def dump_lookup_new(agi,
                    l1_lookup,
                    name_pfx,
                    lu_h_fn,
                    headers,
                    lu_elem_type,
                    define_dict=None,
                    all_zero_by_map=None,
                    output_dir='include-private'):
    
    if output_dir:
        ofn = mbuild.join(output_dir,lu_h_fn)
    else:
        ofn = lu_h_fn
    h_file = agi.open_file(ofn, start=False)
    for header in headers:
        h_file.add_header(header)
    h_file.start()

    if define_dict:
        print_defines(h_file, define_dict)

    array_names = _dump_lookup_low(agi,
                                   h_file,
                                   l1_lookup,
                                   name_pfx,
                                   lu_elem_type,
                                   all_zero_by_map)

    _dump_top_level_dispatch_array(agi,
                                   h_file,
                                   array_names,
                                   'xed_ild_{}_table'.format(name_pfx),
                                   lu_elem_type)
    
    h_file.close()


def _dump_top_level_dispatch_array(agi,
                                   h_file,
                                   array_names,
                                   emit_array_name,
                                   sub_data_type):
    vv_max = max( [ ild_info.encoding_space_to_vexvalid(mi.space)
                    for mi in agi.map_info ] )
    max_maps = ild_info.get_maps_max_id(agi) + 1
    h_file.add_code('#if !defined(XED_MAP_ROW_LIMIT)')
    h_file.add_code('# define XED_MAP_ROW_LIMIT {}'.format(max_maps))
    h_file.add_code('#endif')
    h_file.add_code('#if !defined(XED_VEXVALID_LIMIT)')
    h_file.add_code('# define XED_VEXVALID_LIMIT {}'.format(vv_max+1))
    h_file.add_code('#endif')
    h_file.add_code('const {}* {}[XED_VEXVALID_LIMIT][XED_MAP_ROW_LIMIT] = {{'.format(
                                                                            sub_data_type,
                                                                            emit_array_name))

    for vv in range(0,vv_max+1):
        maps = ild_info.get_maps_for_space(agi,vv)
        dmap = {mi.map_id:mi for mi in maps} # dict indexed by map_id

        init_vals = ['0'] * max_maps 
        for imap in range(0,max_maps):
            if imap in dmap:
                mi = dmap[imap]
                if mi.map_name in array_names:
                    init_vals[imap] = array_names[mi.map_name]
        h_file.add_code('{{ {} }},'.format(', '.join(init_vals)))
    h_file.add_code('};')

    
def dump_lookup(agi,
                l1_lookup,
                name_pfx,
                lu_h_fn,
                headers,
                lu_elem_type,
                define_dict=None,
                all_zero_by_map=None,
                output_dir='include-private'):
    """Dump the lookup tables - from opcode value to
    the L1 function pointers (in most cases they are L2 function pointers,
    which doesn't matter, because they have the same signature)
    @param l1_lookup: 2D dict so that
    l1_lookup[string(insn_map)][string(opcode)] == string(L1_function_name)
    all 0..255 opcode values should be set in the dict, so that if 0x0,0x0F
    map-opcode is illegal, then l1_lookup['0x0']['0x0F'] should be set
    to some string indicating that L1 function is undefined.

    all_zero_by_map is an optional dict[map] -> {True,False}. If True
    skip emitting the map.
   
    return a dictionary of the array names generated.   """
    if output_dir:
        ofn = mbuild.join(output_dir,lu_h_fn)
    else:
        ofn = lu_h_fn
    h_file = agi.open_file(ofn, start=False)
    for header in headers:
        h_file.add_header(header)
    h_file.start()

    if define_dict:
        print_defines(h_file, define_dict)

    array_names = _dump_lookup_low(agi,
                                   h_file,
                                   l1_lookup,
                                   name_pfx, 
                                   lu_elem_type, 
                                   all_zero_by_map)
    h_file.close()
    return array_names


def _dump_lookup_low(agi,
                     h_file,
                     l1_lookup,
                     name_pfx, 
                     lu_elem_type, 
                     all_zero_by_map=None):
    """Dump the lookup tables - from opcode value to
    the L1 function pointers (in most cases they are L2 function pointers,
    which doesn't matter, because they have the same signature)
    @param l1_lookup: 2D dict so that
    l1_lookup[string(insn_map)][string(opcode)] == string(L1_function_name)
    all 0..255 opcode values should be set in the dict, so that if 0x0,0x0F
    map-opcode is illegal, then l1_lookup['0x0']['0x0F'] should be set
    to some string indicating that L1 function is undefined.

    all_zero_by_map is an optional dict[map] -> {True,False}. If True
    skip emitting the map.
   
    return a dictionary of the array names generated.   """
    array_names = {}
    for insn_map in sorted(l1_lookup.keys()):
        arr_name = _get_map_lu_name(name_pfx, insn_map)
        if all_zero_by_map==None or all_zero_by_map[insn_map]==False:
            ild_dump_map_array(l1_lookup[insn_map], arr_name,
                               lu_elem_type, h_file)
        array_names[insn_map] = arr_name
        
    return array_names


def _gen_bymode_fun_dict(machine_modes, info_list, nt_dict, is_conflict_fun,
                        gen_l2_fn_fun):
    fun_dict = {}
    insn_map = info_list[0].insn_map
    opcode = info_list[0].opcode

    for mode in machine_modes:
        #get info objects with the same modrm.reg bits
        infos = list(filter(lambda info: mode in info.mode, info_list))
        if len(infos) == 0:
            ildutil.ild_warn('BY MODE resolving: No infos for mode' +
                             '%s opcode %s map %s' % (mode, opcode, insn_map))
            #we need to allow incomplete modrm.reg mappings for the
            #case of map 0 opcode 0xC7 where we have infos only for
            #reg 0 (MOV) and 7
            continue
        #if these info objects conflict, we cannot refine by modrm.reg
        is_conflict = is_conflict_fun(infos, nt_dict)
        if is_conflict == None:
            return None
        if is_conflict:
            ildutil.ild_warn('BY MODE resolving:Still conflict for mode' +
                             '%s opcode %s map %s' % (mode, opcode, insn_map))
            return None
        l2_fn = gen_l2_fn_fun(infos[0], nt_dict)
        if not l2_fn:
            return None
        fun_dict[mode] = l2_fn
    return fun_dict

def _gen_byreg_fun_dict(info_list, nt_dict, is_conflict_fun,
                        gen_l2_fn_fun):
    fun_dict = {}
    insn_map = info_list[0].insn_map
    opcode = info_list[0].opcode
    for reg in range(0,8):
        #get info objects with the same modrm.reg bits
        infos = list(filter(lambda info: info.ext_opcode==reg, info_list))
        if len(infos) == 0:
            ildutil.ild_warn('BYREG resolving: No infos for reg' +
                             '%s opcode %s map %s' % (reg, opcode, insn_map))
            #we need to allow incomplete modrm.reg mappings for the
            #case of map 0 opcode 0xC7 where we have infos only for
            #reg 0 (MOV) and 7 
            continue
        #if these info objects conflict, we cannot refine by modrm.reg
        is_conflict = is_conflict_fun(infos, nt_dict)
        if is_conflict == None:
            return None
        if is_conflict:
            ildutil.ild_warn('BYREG resolving:Still conflict for reg' +
                             '%s opcode %s map %s' % (reg, opcode, insn_map))
            return None
        l2_fn = gen_l2_fn_fun(infos[0], nt_dict)
        if not l2_fn:
            return None
        fun_dict[reg] = l2_fn
    return fun_dict

def _gen_intervals_dict(fun_dict):
    """If there are keys that map to the same value, we want to unite
    them to intervals in order to have less conditional branches in
    code.  For example if fun_dict is something like: 
    {0:f1, 1:f1,  2:f2, 3:f2 , ...} then we will generate dict
    {(0,1):f1, (2,3,4,5,6,7):f2} """
    
    sorted_keys = sorted(fun_dict.keys())
    cur_int = [sorted_keys[0]]
    int_dict = {}
    for key in sorted_keys[1:]:
        if fun_dict[key] == fun_dict[key-1]:
            cur_int.append(key)
        else:
            int_dict[tuple(cur_int)] = fun_dict[key-1]
            cur_int = [key]
    int_dict[tuple(cur_int)] = fun_dict[sorted_keys[-1]]
    return int_dict

def gen_l1_byreg_resolution_function(agi,info_list, nt_dict, is_conflict_fun,
                        gen_l2_fn_fun, fn_suffix):
    if len(info_list) < 1:
        ildutil.ild_warn("Trying to resolve conflict for empty info_list")
        return None
    insn_map = info_list[0].insn_map
    opcode = info_list[0].opcode
    ildutil.ild_warn('generating by reg fun_dict for opcode %s map %s' %
                          (opcode, insn_map))
    fun_dict = _gen_byreg_fun_dict(info_list, nt_dict, is_conflict_fun,
                        gen_l2_fn_fun)
    if not fun_dict:
        #it is not ild_err because we might have other conflict resolution
        #functions to try.
        #In general we have a list of different conflict resolution functions
        #that we iterate over and try to resolve the conflict
        ildutil.ild_warn('Failed to generate by reg fun_dict for opcode '
                         '%s map %s' % (opcode, insn_map))
        return None

    #if not all modrm.reg values have legal instructions defined, we don't
    #have full 0-7 dict for modrm.reg here, and we can't generate the interval
    #dict
    if len(list(fun_dict.keys())) == 8:
        int_dict = _gen_intervals_dict(fun_dict)
    else:
        int_dict = None

    lufn = ild_nt.gen_lu_names(['RESOLVE_BYREG'], fn_suffix)[2]
    lufn += '_map%s_op%s_l1' % (insn_map, opcode)
    operand_storage = agi.operand_storage
    return_type = 'void'
    fo = codegen.function_object_t(lufn, return_type,
                                       static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)

    reg_type = 'xed_uint8_t'
    reg_var = '_reg'
    fo.add_code_eol('%s %s' % (reg_type, reg_var))

    #get modrm value
    fo.add_code_eol("%s = %s" % (reg_var,
                        emit_ild_access_call('REG', data_name)))

    #now emit the resolution code, that checks conditions from dict
    #(in this case the modrm.reg value)
    #and calls appropriate L2 function for each condition

    #if we have an interval dict, we can emit several if statements
    if int_dict:
        _add_int_dict_dispatching(fo, int_dict, reg_var, data_name)
    #if we don't have interval dict, we emit switch statement
    else:
        _add_switch_dispatching(fo, fun_dict, reg_var, data_name)

    return fo

def _add_int_dict_dispatching(fo, int_dict, dispatch_var, data_name):
    cond_starter = 'if'
    for interval in int_dict.keys():
        min = interval[0]
        max = interval[-1]
        #avoid comparing unsigned int to 0, this leads to build errors
        if int(min) == 0 and int(max) != 0:
            condition = '%s(%s <= %s) {' % (cond_starter, dispatch_var, max)
        elif min != max:
            condition = '%s((%s <= %s) && (%s <= %s)) {' % (cond_starter ,min,
                                            dispatch_var, dispatch_var, max)
        else:
            condition = '%s(%s == %s) {' % (cond_starter, min, dispatch_var)
        fo.add_code(condition)
        call_stmt = '%s(%s)' % (int_dict[interval], data_name)
        fo.add_code_eol(call_stmt)
        fo.add_code_eol('return')
        fo.add_code('}')
        cond_starter = 'else if'

def _add_switch_dispatching(fo, fun_dict, dispatch_var, data_name):
    fo.add_code("switch(%s) {" % dispatch_var)
    for key in fun_dict.keys():
        fo.add_code('case %s:' % key)
        call_stmt = '%s(%s)' % (fun_dict[key], data_name)
        fo.add_code_eol(call_stmt)
        fo.add_code_eol('break')
    fo.add_code("/*We should only get here for #UDs and those have no defined architectural length*/")
    fo.add_code_eol('default: ')
    fo.add_code("}")

def gen_l1_bymode_resolution_function(agi,info_list, nt_dict, is_conflict_fun,
                        gen_l2_fn_fun, fn_suffix):
    if len(info_list) < 1:
        ildutil.ild_warn("Trying to resolve conflict for empty info_list")
        return None
    insn_map = info_list[0].insn_map
    opcode = info_list[0].opcode
    ildutil.ild_warn('generating by mode fun_dict for opcode %s map %s' %
                          (opcode, insn_map))
    machine_modes = agi.common.get_state_space_values('MODE')
    fun_dict = _gen_bymode_fun_dict(machine_modes,
                                    info_list, nt_dict, is_conflict_fun,
                                    gen_l2_fn_fun)
    if not fun_dict:
        #it is not ild_err because we might have other conflict resolution
        #functions to try.
        #In general we have a list of different conflict resolution functions
        #that we iterate over and try to resolve the conflict
        ildutil.ild_warn('Failed to generate by mode fun_dict for opcode '+
                         '%s map %s' % (opcode, insn_map))
        return None

    #if not all modrm.reg values have legal instructions defined, we don't
    #have full 0-7 dict for modrm.reg here, and we can't generate the interval
    #dict
    if len(list(fun_dict.keys())) == len(machine_modes):
        int_dict = _gen_intervals_dict(fun_dict)
    else:
        int_dict = None

    lufn = ild_nt.gen_lu_names(['RESOLVE_BYMODE'], fn_suffix)[2]
    lufn += '_map%s_op%s_l1' % (insn_map, opcode)
    operand_storage = agi.operand_storage
    return_type = 'void'
    fo = codegen.function_object_t(lufn, return_type,
                                       static=True, inline=True)
    data_name = 'x'
    fo.add_arg(ildutil.ild_c_type + ' %s' % data_name)


    mode_type = ildutil.ild_c_op_type
    mode_var = '_mode'
    fo.add_code_eol(mode_type + ' %s' % mode_var)
    #get MODE value
    access_call = emit_ild_access_call("MODE", data_name)
    if not access_call:
          return None

    fo.add_code_eol('%s = (%s)%s' %(mode_var, mode_type, access_call))

    #now emit the resolution code, that checks condtions from dict
    #(in this case the MODE value)
    #and calls appropriate L2 function for each condition

    #if we have an interval dict, we can emit several if statements
    if int_dict:
        _add_int_dict_dispatching(fo, int_dict, mode_var, data_name)
    #if we don't have interval dict, we emit switch statement
    else:
        _add_switch_dispatching(fo, fun_dict, mode_var, data_name)

    return fo

def print_defines(file, define_dict):
    for def_name in sorted(define_dict.keys()):
        def_val = define_dict[def_name]
        file.add_code("#define %s %s\n" %(def_name, def_val))
    file.add_code("\n")


def ild_dump_map_array(opcode_dict, arr_name, arr_elem_type, xfile):
    xfile.add_code('const %s %s[256] = {' % (arr_elem_type, arr_name))
    for opcode in range(0, 256):
        ops = hex(opcode)
        value = opcode_dict[ops]
        xfile.add_code("/*opcode %s*/ %s," % (ops, value))
    xfile.add_code_eol('}')



xed_mode_cvt_fn = 'xed_ild_cvt_mode'

#FIXME: add REG here too?
_special_ops_dict = {
                     #Don't need special care for RM since we renamed
                     #partial opcodes with SRM
                     #'RM' : 'xed_ild_get_rm'
                    }

#FIXME: need more descriptive name.
def _is_special_op(opname):
    """
    Some operands are "special" - like RM: Sometimes we don't have modrm,
    but grammar still likes to use RM operand - in this case it is first
    3 bits of the opcode.
    In this case we can't just use regular RM operand scanned with ILD -
    we must check if MODRM exists and if not take 3 LSB nits from opcode.
    This is what getter should do for RM, that's why RM is special.
    REG is probably the same.
    is_special_op(opname) checks if the operand has special getter.
    """
    return opname in _special_ops_dict

#FIXME: need more descriptive name.
def _get_special_op_getter_fn(opname):
    """
    Returns special operand's getter name.
    See is_special_op comment.
    """
    return _special_ops_dict[opname]

def emit_ild_access_call(opname, data_name, eoasz_set=False):
    """
    @param opname: the name of the operand of xed grammar.
    @type opname: string

    @param data_name: the name of xed_decoded_inst_t* pointer
    @type data_name: string

    @param eoasz_set: when doing static decoding EOSZ and EASZ are not
    yet set correctly in the operands structure and we have to use
    special ILD getters to get their correct value.
    After dynamic decoding (and before we do operands decoding) EOSZ
    and EASZ are already set and we can use regular getter for them.
    @type eoasz_set: boolean

    IMPORTANT: EASZ and EOSZ cannot be computed with this function,
    see how it's done in ild_imm and ild_disp for these two.

    @return: C statement (no semicolon, no eol) that returns the
    value of corresponding operand.
    """

    if opname in ['EASZ', 'EOSZ'] and not eoasz_set:
        #EASZ and EOSZ should be computed in a special way
        #see how it's done in ild_phash.phash_t.add_cgen_lines
        ildutil.ild_err('No simple getter for %s operand' % opname)
    elif _is_special_op(opname):
        getter_fn = _get_special_op_getter_fn(opname)
    else:
        getter_fn = operand_storage.get_op_getter_fn(opname)

    call_str = '%s(%s)' % (getter_fn, data_name)
    return call_str


