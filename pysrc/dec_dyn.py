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

# dynamic decode for:
#   (a) part 1 (for OSZ/ASZ NTs),
#   (b) part 2 (for NTs within in instr patterns), and
#   (c) operands (mostly register NTLUFs).
import os
import collections

import ildutil
import ild_nt
import ild_cdict
import mbuild
import codegen
import ild_codegen
import operand_storage
import verbosity
import tup2int

_key_ctype         = 'xed_uint32_t'
_xed3_err_op       = 'error'
_xed3_gen_error    = 'XED_ERROR_GENERAL_ERROR'
_xed_reg_error_val = 'XED_ERROR_BAD_REGISTER'
_xed_no_err_val    = 'XED_ERROR_NONE'
_xed_op_type       = 'xed_operand_values_t'

def _vlog(f,s):
    if verbosity.vcapture():
        f.write(s)

def get_ii_constraints(ii, state_space):
    """returns constraints[xed_operand_name][xed_operand_val] = True
    
    where xed_operand_name and xed_operand_val correspond to operands
    encountered in ii (both operand deciders and constant prebindings)"""
    
    constraints = collections.defaultdict(dict)
    #set constraints that come from operands deciders
    ild_nt.add_op_deciders(ii.ipattern, state_space, constraints)
    #set constraints that come from prebindings
    for name,binding in list(ii.prebindings.items()):
        if binding.is_constant():
            #if name not in constraints:
            #    constraints[name] = {}
            val = int(binding.get_value(), 2)
            constraints[name][val] = True
    return constraints

def _get_all_cnames(gi):
    """
    Returns a set of all constraints used by a given gi
    (generator_info - represents a single NT)
    """
    cnames = []
    for rule in gi.parser_output.instructions:
        cnames.extend(list(rule.xed3_constraints.keys()))
    return set(cnames)
    
def _gen_cdict(agi, nt_name, all_state_space):
    """Creates a ild_cdict.constraint_dict_t corresponding to NT defined
    by gi.    """
    
    gi = agi.generator_dict[nt_name]
    options = agi.common.options
    
    state_space = {}
    for opname in all_state_space:
        state_space[opname] = list(all_state_space[opname].keys())

    for rule in gi.parser_output.instructions:
        rule.xed3_constraints = get_ii_constraints(rule, state_space)
    
    cnames = _get_all_cnames(gi)
    cdict_list = []        
    for rule in gi.parser_output.instructions:
        cdict = ild_cdict.constraint_dict_t(
                                    cnames, 
                                    rule.xed3_constraints, 
                                    all_state_space,
                                    rule)
        cdict_list.append(cdict)
        
    msg = "cdict conflict in NT %s\n" % nt_name
    all_cdict = ild_cdict.constraint_dict_t.unite_dicts(
                                            cdict_list, 
                                            msg, 
                                            cnames)
    return all_cdict


_xed3_capture_fn_pfx = 'xed3_capture'

def _get_xed3_nt_capture_fn(nt_name):
    """
    Return a xed3 capture function name for a given NT name.
    """
    return '%s_nt_%s' % (_xed3_capture_fn_pfx, nt_name)

def _get_xed3_capture_chain_fn(nt_names, is_ntluf=False):
    """
    Return a xed3 chain capture function name from a given list of
    NT names.
    is_ntluf==True for operands chain functions.
    """
    suffix = '_'.join(nt_names)
    if is_ntluf:
        suffix = 'ntluf_%s' % suffix
    return '%s_chain_%s' % (_xed3_capture_fn_pfx, suffix)

def _add_cgen_key_lines(fo, 
                       nt_name,
                       gi, 
                       all_ops_widths,
                       key_str='key',
                       inst='d'):
    """
    Add C code to compute the key from constraints' values.
    """
    fo.add_code_eol('%s %s = 0' % (_key_ctype, key_str))
    cdict = gi.xed3_cdict
    bit_shift = 0
    for i,cname in enumerate(cdict.cnames):
        #eosz_set=True indicates that current value of EOSZ is correct 
        #in the _operands array and we can take it from there.
        #Otherwise we would have to use special eosz computing functions
        #the same way as we do in ILD.
        #eosz_set=True here because we are doing dynamic decoding
        #and have processed the NTs that come before the current NT.
        access_str = ild_codegen.emit_ild_access_call(cname, inst, 
                                                      eoasz_set=True)
        
        #constraints might have 1,2 or 3 bit widths
        #and we allocate bits in the key vector appropriately
        #e.g REXB operand gets only 1 bit in the key
        #and RM gets 3 bits
        shift_val = ('(%s)' % bit_shift)
        bit_shift += all_ops_widths[cname]
        fo.add_code_eol('%s += (%s) << (%s)' % (key_str,access_str, shift_val))

def _get_pattern_nts(rule):
    """
    Return a list of NT names present in given rule.
    """
    nt_names = []
    for bt in rule.ipattern.bits:
        if bt.is_nonterminal():
            nt_name = bt.nonterminal_name()
            nt_names.append(nt_name)
    return nt_names

def _is_error_rule(rule):
    for op in rule.operands:
        if op.type == 'error':
            return True
    return False

def _add_capture_nt_call(fo, nt_name, inst='d', indent=0):
    capture_fn = _get_xed3_nt_capture_fn(nt_name)
    indent = '    ' * indent
    fo.add_code_eol('%s%s(%s)' % (indent, capture_fn, inst))

def _add_op_assign_stmt(fo, opname, opval, inst='d', op=None,
                        indent=0):
    if op:
        fo.add_code('/* op.type=%s */' % op.type)
    setter_fn = operand_storage.get_op_setter_fn(opname)
    set_stmt = '%s(%s, %s)' %(setter_fn, inst, opval)
    indentstr = '    ' * indent
    fo.add_code_eol(indentstr + set_stmt)

def _is_reg_error_op(op):
    return op.bits in ['XED_REG_ERROR']

def _add_nt_rhs_assignments(fo, nt_name, gi, rule, inst='d'):
    #fo.add_code("/* %s */" % rule)
    
    #first if it's error, we set general_error and quit
    if _is_error_rule(rule):
        _add_op_assign_stmt(fo, _xed3_err_op, _xed3_gen_error, 
                            inst, indent=1)
        return
    
    #now check if there are NT calls in pattern, we need to call them first
    pattern_nts = _get_pattern_nts(rule)
    for nt_name in pattern_nts:
        _add_capture_nt_call(fo, nt_name, inst, indent=1)
    
    #now let's do the RHS - for each operand assign value
    #FIXME: if we assign ERROR_REG or INVALID_REG set also error?
    for op in rule.operands:
        if op.name == 'ENCODER_PREFERRED':
            #skip encoder preferred
            continue
        if op.type == 'imm':
            #skip prebindings
            continue
        if op.type == 'nt_lookup_fn':
            #NT as RHS, we call its capturing function
            #and then assign op.name to OUTREG
            _add_capture_nt_call(fo, op.lookupfn_name, inst, indent=1)
            #now copy the outreg to op.name (unless it is outreg too!)
            if  op.name != 'OUTREG':
                getter_fn = operand_storage.get_op_getter_fn('outreg')
                outreg_expr = '%s(%s)' % (getter_fn, inst) 
                _add_op_assign_stmt(fo, op.name, outreg_expr, inst, indent=1)

        else: #assignment of an operand to a constant
            _add_op_assign_stmt(fo, op.name, op.bits, inst, indent=1)
            if _is_reg_error_op(op):
                _add_op_assign_stmt(fo, _xed3_err_op, 
                                    _xed_reg_error_val, inst, indent=1)
    fo.add_code('/*pacify the compiler */')            
    fo.add_code_eol('(void)%s' % inst)
    
def _add_case_lines(fo, nt_name, gi, rule, inst='d'):
    _add_nt_rhs_assignments(fo, nt_name, gi, rule, inst=inst)
    fo.add_code_eol('    break')

def _add_switchcase_lines(fo,
                          nt_name,
                          gi,
                          all_ops_widths,
                          key_str='key',
                          inst='d'):
    cdict = gi.xed3_cdict
    fo.add_code('switch(%s) {' %key_str)
    
    int2key = {}
    key2int = {}
    for key in cdict.tuple2rule.keys():
        keyval = tup2int.tuple2int(key, cdict.cnames, all_ops_widths)
        #This checks for a nasty conflict that should never happen:
        #when two different tuple keys have the same integer value.
        #This conflict can happen when bit widths of all constraints are
        #bigger than 32 bit (key is uint32 currently).
        #In general such error will be caught by C compiler when we try
        #to build a key and shift more than 32 bits.
        #Checking here too just to be sure.
        #FIXME: add an assertion to constraint_dict_t constructor to check
        #for that?
        #FIXME: this doesn't really checks for integer overflow, because 
        #python autmatically extends int32 if it overflows to int64.
        #Need better checking.
        if keyval in int2key:
            msg = []
            msg.append('CDICT TUPLE VALUE CONFLICT in nt %s !!!!' % nt_name)
            msg.append('keyval %s' % keyval)
            msg.append('key1 %s, key2 %s' % (key, int2key[keyval]))
            msg.append('cdict %s')
            msg = '\n'.join(msg)
            ildutil.ild_err(msg)
        int2key[keyval] = key 
        key2int[key] = keyval 
    
    covered_rules = set()
    
    #we want cases sorted by value - prettier
    for keyval in sorted(int2key.keys()):
        key = int2key[keyval]
        rule = cdict.tuple2rule[key]
        if rule in covered_rules:
            continue
        covered_rules.add(rule)
        keys = cdict.get_all_keys_by_val(rule)
        for key in keys:
            #FIXME: move tuple2int to ild_cdict?
            keyval = key2int[key]
            fo.add_code('case %s: /*%s -> %s*/' %(keyval, key, rule))
        _add_case_lines(fo, nt_name, gi, rule)
    fo.add_code('default:')
    if gi.parser_output.otherwise_ok:
        fo.add_code('/* otherwise_ok */')
    else:
        #FIXME: temporary using general error, later
        #define more specific error enum
        errval = 'XED_ERROR_GENERAL_ERROR'
        _add_op_assign_stmt(fo, _xed3_err_op, errval, 
                            inst, indent=1)
    fo.add_code_eol('    break')
    fo.add_code('}')
    

def _gen_capture_fo(agi, nt_name, all_ops_widths):
    """
    Generate xed3 capturing function for a given NT name.
    """
    gi = agi.generator_dict[nt_name]
    cdict = gi.xed3_cdict
    fname = _get_xed3_nt_capture_fn(nt_name)
    inst = 'd'
    keystr = 'key'
    fo = codegen.function_object_t(fname,
                                   return_type='void', 
                                   static=True, 
                                   inline=True)
    fo.add_arg(ildutil.xed3_decoded_inst_t + '* %s' % inst)
    if len(cdict.cnames) > 0:
        _add_cgen_key_lines(fo, nt_name, gi, all_ops_widths, keystr, inst)
        fo.add_code('/* now switch code..*/')
        _add_switchcase_lines(fo, nt_name, gi, all_ops_widths, keystr, inst)
    else: 
        rule = cdict.rule
        _add_nt_rhs_assignments(fo, nt_name, gi, rule)
    return fo
    
def _get_op_nt_names_from_ii(ii):
    nt_names = []
    for op in ii.operands:
        if op.type == 'nt_lookup_fn':
            nt_names.append(op.name + '_' + op.lookupfn_name)
        elif op.type == 'imm_const':
            suffix = '_const%s' % op.bits
            nt_names.append(op.name + suffix)
        elif op.type == 'reg':
            suffix = '_%s' % op.bits
            nt_names.append(op.name + suffix)
    return nt_names

def _get_nt_names_from_ii(ii):
    """
    @param ii - instruction_info_t
    @return list of NT names in ii's pattern
    """
    nt_names = []
    for bt in ii.ipattern.bits:
        if bt.is_nonterminal():
            name = bt.nonterminal_name()
            if not name:
                ildutil.ild_err('Failed to get NT name in %s for %s' % (ii,bt))
            nt_names.append(name)
    return nt_names

def _gen_ntluf_capture_chain_fo(nt_names, ii):
    """
    Given a list of OP_NAME_NT_NAME strings(nt_names), generate a function 
    object (function_object_t)
    that calls corresponding xed3 NT capturing functions.
    Each such function captures everything that xed2 decode graph would
    capture for a given pattern with operands that have nt_lokkupfns.
    The difference between this function and  _gen_capture_chain_fo
    is that this function creates chain capturing functions for
    operand decoding - assigns the REG[0,1] operands, etc.
    """
    fname = _get_xed3_capture_chain_fn(nt_names, is_ntluf=True)
    inst = 'd'
    fo = codegen.function_object_t(fname,
                                   return_type=_xed3_chain_return_t, 
                                   static=True, 
                                   inline=True)
    fo.add_arg(ildutil.xed3_decoded_inst_t + '* %s' % inst)
    
    for op in ii.operands:
        if op.type == 'nt_lookup_fn':
            nt_name = op.lookupfn_name
            capture_fn = _get_xed3_nt_capture_fn(nt_name)
            capture_stmt = '%s(%s)' % (capture_fn, inst)
            fo.add_code_eol(capture_stmt)
            #if we have NTLUF functions, we need to assign OUTREG
            getter_fn = operand_storage.get_op_getter_fn('outreg')
            outreg_expr = '%s(%s)' % (getter_fn, inst) 
            fo.add_code('/*opname %s */' % op.name)
            _add_op_assign_stmt(fo, op.name, outreg_expr, inst)
            #now check if we have errors in current NT
            #we don't need to check if there was a reg_error because
            #we assign error operand inside the called nt_capture function
            #if there was a reg_error
            getter_fn = operand_storage.get_op_getter_fn(_xed3_err_op)
            errval = '%s(%s)' % (getter_fn, inst)
            fo.add_code('if (%s) {' % errval)
            fo.add_code_eol('return %s' % errval)
            fo.add_code('}')
        elif op.type in ['imm_const', 'reg']:
            opval = op.bits
            _add_op_assign_stmt(fo, op.name, opval, inst)
            
    
    fo.add_code_eol('return %s' % _xed_no_err_val)
    return fo

def _gen_capture_chain_fo(nt_names, fname=None):
    """
    Given a list of NT names, generate a function object (function_object_t)
    that calls corresponding xed3 NT capturing functions.
    Each such function captures everything that xed2 decode graph would
    capture for a given pattern with NTs (nt_names) in it.
    """
    if not fname:
        fname = _get_xed3_capture_chain_fn(nt_names)
    inst = 'd'
    fo = codegen.function_object_t(fname,
                                   return_type=_xed3_chain_return_t, 
                                   static=True, 
                                   inline=True)
    fo.add_arg(ildutil.xed3_decoded_inst_t + '* %s' % inst)
    
    for name in nt_names:
        capture_fn = _get_xed3_nt_capture_fn(name)
        capture_stmt = '%s(%s)' % (capture_fn, inst)
        fo.add_code_eol(capture_stmt)
        #now check if we have errors in current NT
        getter_fn = operand_storage.get_op_getter_fn(_xed3_err_op)
        errval = '%s(%s)' % (getter_fn, inst)
        fo.add_code('if (%s) {' % errval)
        fo.add_code_eol('return %s' % errval)
        fo.add_code('}')
    
    fo.add_code_eol('return %s' % _xed_no_err_val)
    return fo

_xed3_chain_header         = 'xed3-chain-capture.h'
_xed3_op_chain_header      = 'xed3-op-chain-capture.h'
_xed3_chain_lu_header      = 'xed3-chain-capture-lu.h'
_xed3_op_chain_lu_header   = 'xed3-op-chain-capture-lu.h'
_xed3_nt_capture_header    = 'xed3-nt-capture.h'
_xed3_capture_lu_header    = 'xed3-nt-capture-lu.h'
_xed3_empty_capture_func   = 'xed3_capture_nt_nop'
_xed3_chain_return_t       = 'xed_error_enum_t'
_xed3_dynamic_part1_header = 'xed3-dynamic-part1-capture.h'
    

def _gen_empty_capture_fo(is_ntluf=False):
    """
    Generate capture function that does nothing. 
    For patterns without NTs.
    """
    inst = 'd'
    if is_ntluf:
        fname = '%s_ntluf' % _xed3_empty_capture_func
    else:
        fname = _xed3_empty_capture_func
    fo = codegen.function_object_t(fname,
                                   return_type=_xed3_chain_return_t, 
                                   static=True, 
                                   inline=True)
    fo.add_arg(ildutil.xed3_decoded_inst_t + '* %s' % inst)
    fo.add_code_eol('(void)%s' % inst)
    fo.add_code_eol('return %s' % _xed_no_err_val)
    return fo

def _dump_op_capture_chain_fo_lu(agi, patterns):
    """
    Creates chain capturing functions for operands - for each pattern,
    dumps those functions definitions, dumps a mapping
    from inum(xed_inst_t index) to those functions.
    """
    fn_2_fo = {}
    inum_2_fn = {}
    nop_fo = _gen_empty_capture_fo(is_ntluf=True)
    fn_2_fo[nop_fo.function_name] = nop_fo
    for ptrn in patterns:
        ii = ptrn.ii
        nt_names = _get_op_nt_names_from_ii(ii)
        if len(nt_names) == 0:
            #if no NTs we use empty capturing function
            fn = nop_fo.function_name
        else:
            fn = _get_xed3_capture_chain_fn(nt_names, is_ntluf=True)
        if fn not in fn_2_fo:
            fo = _gen_ntluf_capture_chain_fo(nt_names, ii)
            fn_2_fo[fn] = fo
        inum_2_fn[ii.inum] = (fn, ii.operands)
    
    
    #dump chain functions
    headers = [_xed3_nt_capture_header]
    ild_codegen.dump_flist_2_header(agi, 
                                    _xed3_op_chain_header, 
                                    headers, 
                                    list(fn_2_fo.values()), 
                                    is_private=True)
    
    lu_size = max(inum_2_fn.keys()) + 1
    
    xeddir = os.path.abspath(agi.common.options.xeddir)
    gendir = mbuild.join(agi.common.options.gendir,'include-private')
    
    h_file = codegen.xed_file_emitter_t(xeddir,gendir,
                                _xed3_op_chain_lu_header, shell_file=False, 
                                is_private=True)
    h_file.add_header(_xed3_op_chain_header)
    h_file.start()
    lu_name = 'xed3_op_chain_fptr_lu'
    xed3_op_chain_f_t = 'xed3_op_chain_function_t'
    
    fptr_typedef = 'typedef %s(*%s)(%s*);' % (_xed3_chain_return_t,
                                              xed3_op_chain_f_t,
                                              ildutil.xed3_decoded_inst_t)
    
    h_file.add_code(fptr_typedef)
    h_file.add_code('static {} {}[{}] = {{'.format(xed3_op_chain_f_t,
                                                   lu_name,
                                                   lu_size))
    
    empty_line = '/*NO PATTERN*/ (%s)0,' % xed3_op_chain_f_t

    for inum in range(0, lu_size):
        if inum in inum_2_fn:
            (fn, oplist) = inum_2_fn[inum]
            op_str = '\n'.join([str(op) for op in oplist])
            entry_str = '/*%s inum=%s*/ %s,' % (op_str,inum, fn)
        else:
            entry_str = empty_line
        h_file.add_code(entry_str)
    h_file.add_code('};')
    h_file.close()
    

def _dump_capture_chain_fo_lu(agi, patterns):
    """
    Creates chain capturing functions - for each pattern,
    dumps those functions definitions, dumps a mapping
    from inum(xed_inst_t index) to those functions.
    """
    fn_2_fo = {}
    inum_2_fn = {}
    
    nop_fo = _gen_empty_capture_fo()
    fn_2_fo[nop_fo.function_name] = nop_fo
    for ptrn in patterns:
        ii = ptrn.ii
        nt_names = _get_nt_names_from_ii(ii)
        if len(nt_names) == 0:
            #if no NTs we use empty capturing function
            fn = nop_fo.function_name
        else:
            fn = _get_xed3_capture_chain_fn(nt_names)
        if fn not in fn_2_fo:
            fo = _gen_capture_chain_fo(nt_names)
            fn_2_fo[fn] = fo
        inum_2_fn[ii.inum] = (fn, ptrn.ptrn)
    
    
    #dump chain functions
    headers = [_xed3_nt_capture_header]
    ild_codegen.dump_flist_2_header(agi, 
                                    _xed3_chain_header, 
                                    headers, 
                                    list(fn_2_fo.values()), 
                                    is_private=True)
    
    lu_size = max(inum_2_fn.keys()) + 1
    
    xeddir = os.path.abspath(agi.common.options.xeddir)
    gendir = mbuild.join(agi.common.options.gendir,'include-private')
    
    h_file = codegen.xed_file_emitter_t(xeddir,gendir,
                                _xed3_chain_lu_header, shell_file=False, 
                                is_private=True)
    h_file.add_header(_xed3_chain_header)
    h_file.start()
    lu_name = 'xed3_chain_fptr_lu'
    xed3_chain_f_t = 'xed3_chain_function_t'
    
    fptr_typedef = 'typedef %s(*%s)(%s*);' % (_xed3_chain_return_t,
                                              xed3_chain_f_t,
                                              ildutil.xed3_decoded_inst_t)
    
    h_file.add_code(fptr_typedef)
    
    h_file.add_code('static {} {}[{}] = {{'.format(xed3_chain_f_t,
                                                   lu_name,
                                                   lu_size))
    
    empty_line = '/*NO PATTERN*/ (%s)0,' % xed3_chain_f_t

    for inum in range(0, lu_size):
        if inum in inum_2_fn:
            (fn, ptrn_str) = inum_2_fn[inum]
            entry_str = '/*\n%s\ninum=%s*/ %s,' % (ptrn_str, inum,fn)
        else:
            entry_str = empty_line
        h_file.add_code(entry_str)
    h_file.add_code('};')
    h_file.close()
        
def _dump_dynamic_part1_f(agi):
    """
    Dumps the xed3_dynamic_decode_part1 function that captures all the
    NTs in the spine that come before INSTRUCTIONS NT.
    """
    fo = _gen_dynamic_part1_fo(agi)
    #dump the function
    headers = [_xed3_nt_capture_header]
    ild_codegen.dump_flist_2_header(agi, 
                                    _xed3_dynamic_part1_header, 
                                    headers, 
                                    [fo], 
                                    is_private=True)        

#things that are covered by ILD and static decoding
#FIXME: is there a better way to determine them instead of just
#hardcoding their names?
_nts_to_skip = ['PREFIXES',  'ISA']
_spine_nt_name = 'ISA'
_dynamic_part1_fn = 'xed3_dynamic_decode_part1'

def _skip_nt(nt_name):
    """
    Return True if there is no need to generate a capturing 
    function for a given NT name.
    """
    return (nt_name in _nts_to_skip or
            'INSTRUCTIONS' in nt_name or
            'SPLITTER' in nt_name)

def _gen_dynamic_part1_fo(agi):
    """
    Generate the xed3_dynamic_decode_part1 function that
    captures all the NTs that come before INSTRUCTIONS.
    The generated function should be called after ILD and before
    static decoding.
    """
    gi = agi.generator_dict[_spine_nt_name]
    if len(gi.parser_output.instructions) != 1:
        ildutil.ild_err("Failed to gen dynamic part1 function!\n" +
                        "Unexpected number of rules in %s NT: %s" % 
                        (_spine_nt_name, len(gi.parser_output.instructions)))
    # This ISA spine has one rule so we work on that one.
    rule = gi.parser_output.instructions[0]
    nt_names = _get_nt_names_from_ii(rule)
    
    #filter NTs that we want to skip, leaving typially the OSZ_NONTERM
    #and the ASZ_NONTERM.
    nt_names = list(filter(lambda x: not _skip_nt(x), nt_names))
    fo = _gen_capture_chain_fo(nt_names, fname=_dynamic_part1_fn)
    return fo
    


def work(agi, all_state_space, all_ops_widths, patterns):
    """
    Main entry point of the module.
    For each NT generate a capturing function.
    Then for each sequence of NTs in patterns generate a
    chain capturing function that would call single capturing functions
    for each NT.
    Then for each combination of operands generate operands chain captuirng
    function.
    Also generate lookup tables to obtain those chain capturing functions
    from inum (xed_inst_t index).
    """
    gendir = ild_gendir = agi.common.options.gendir
    logfn = mbuild.join(gendir, 'xed3_nt_cdicts.txt')
    log_f = open(logfn, 'w')
    
    #generate NT capturing functions
    capture_fn_list = []
    for nt_name in agi.nonterminal_dict.keys():
        #skip nonterminals that we don't want to capture:
        #PREFIXES, AVX_SPLITTER, *ISA, etc.
        if _skip_nt(nt_name):
            continue

        _vlog(log_f,'processing %s\n' % nt_name)
        #create a constraint_dict_t for each NT
        nt_cdict = _gen_cdict(agi, nt_name, all_state_space)
        _vlog(log_f,'NT:%s:\n%s\n' % (nt_name, nt_cdict))
        gi = agi.generator_dict[nt_name]
        gi.xed3_cdict = nt_cdict #just for transporting
        #create a function_object_t for the NT
        fo = _gen_capture_fo(agi, nt_name, all_ops_widths)
        gi.xed3_capture_fo = fo
        capture_fn_list.append(fo)
        _vlog(log_f,fo.emit())
    
    #dump NT capturing functions
    headers = [operand_storage.get_operand_accessors_fn(), ildutil.ild_header]
    ild_codegen.dump_flist_2_header(agi, 
                                    _xed3_nt_capture_header, 
                                    headers, 
                                    capture_fn_list, 
                                    is_private=True)
    
    #in each pattern we have a number of NTs,
    #now that we have a capturing function for each NT
    #we can create a create a function that would call
    #needed capturing functions for each pattern.
    #Also dump lookup tables from inum(xed_inst_t index) to
    #chain capturing functions
    _dump_capture_chain_fo_lu(agi, patterns)
    
    #do the same for operands of each xed_inst_t
    _dump_op_capture_chain_fo_lu(agi, patterns)
    
    #create chain capturing functions for the NTs that come from
    #spine, before the INSTRUCTIONS NT
    _dump_dynamic_part1_f(agi)
    
    log_f.close()    
    
    
    


