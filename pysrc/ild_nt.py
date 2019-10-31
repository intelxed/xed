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

import genutil
import ildutil
import codegen
import opnds


def is_target_op(agi, op, target_op):
    """
    @param op: instruction_info_t.operands[i] - the binded operand by an NT row
    @param target_op: string - the name of the target operand
    @param agi: all_generator_info_t - the main generator's data structure
    (as usual)
    Function returns true if op's name is target_op or if op is a macro which
    expansion contains target_op
    """
    state_dict = agi.common.state_bits
    return (op.name.upper() == target_op or
            (op.name.lower() in state_dict and 
            target_op in state_dict[op.name.lower()].dump_str()))

#Parameters:

def get_setting_nts(agi, opname):
    """
    @param opname: string - name of the operand
    Function returns a list of strings which are the names of NTs that bind 
    an operand with name opname 
    """
    state_dict = agi.common.state_bits
    nt_set = set()
    for nt_name in agi.nonterminal_dict.keys():
        gi = agi.generator_dict[nt_name]
        parser = gi.parser_output
        for rule in parser.instructions:
            for op in rule.operands:
                if is_target_op(agi, op, opname):
                    nt_set.add(nt_name)
    return nt_set


def get_nt_seq(ptrn_wrds, nt_list, implied_nt=None):
    """
    @param ptrn_wrds: [string] - list of tokens of pattern string of an 
    instruction (result of split() on pattern string)
    
    @param nt_list: [string] - list of strings which are names of NTs that
    we look for in the pattern
    
    @param implied_nt: string - name of an NT which is prepended to the
    output list this NT is implied and doesn't appear in the instruction's 
    pattern (e.g. OSZ_NONTERM) 

    @return: a list of strings which are names of NTs from nt_list that 
    were found in ptrn_wrds first NT is implied default NT (for EOSZ for
    example it's OSZ_NONTERM)
    """
    seq = []
    if implied_nt:
        seq.append(implied_nt)
         
    for w in ptrn_wrds:
        no_brackets = re.sub('[(][)]', '',w)
        if no_brackets in nt_list:
            seq.append(no_brackets)
    return seq


def gen_nt_seq_lookup(agi, nt_seq, target_op, target_type=None):
    """
    @param nt_seq: [string] - list of strings which are names of the NTs that
    bind the target_op. Nts appear in the same order as they were found 
    in instruction's pattern (e.g [OSZ_NONTERM, DF64] 

    @param target_op: string - name of the operand that is bound by NTs 
    (e.g. EOSZ)

    @param target_type: string - the type of target operand 
    (xed_bits_t for example).
    Used when we need to override the type specified in grammar.

    @return: codegen.array_gen_t lookup array which defines a mapping
    from certain operand deciders to the value of target_op
    e.g. a mapping from {OSZ, MOD, REXW} to EOSZ
    This mapping is defined by the sequence of NTs (nt_seq)
    by collapsing individual mapping of each NT into one combined mapping
    """
    
    #first NT in sequence is the implicit base one
    #for EOSZ and EASZ. For immediate lookup we don't have such 
    #a notion of implicit base NT.
    state_space = agi.common.state_space
    gi = agi.generator_dict[nt_seq[0]]
    argnames = generate_lookup_function_basis(gi,state_space)
    base_dict = _gen_lookup_dict(agi, nt_seq[0], target_op, argnames)
    if not base_dict:
        return None
    map_list = []
    for nt_name in nt_seq[1:]:
        lookup_dict = _gen_lookup_dict(agi, nt_name, target_op, argnames)
        if not lookup_dict:
            return None
        map_list.append(lookup_dict)
    
    comb_map = combine_mapping_seq(base_dict, map_list)
    if not comb_map:
        return None
    return _gen_lookup_array(agi, nt_seq, comb_map, target_op, argnames,
                             target_type)

#nt_name: string - the name of NT that defines the mapping
#target_opname: string - the name of the operand the mapping maps to
#(e.g. EOSZ)
#argnames: {string -> { string -> Boolean } } a dict of dicts 
#first key is operand decider name, second key is operand decider value
#argnames['MOD']['0'] == True iff operand decider MOD can have value '0'
#Returns list of tuples 
# [ ([{token:string -> index_value:string}], return-value:string) ]
#this list defines a mapping from operand deciders values to target_op value
#described by given NT (with nt_name)
#FIXME: sometimes (ONE():: NT) target_op bounded by all different rows has 
#same value. It happens when there are other operands bounded too. We need
#to detect such cases and generate empty dict so that constant function would
#be generated for such NTs.
def _gen_lookup_dict(agi, nt_name, target_opname, argnames):
    gi = agi.generator_dict[nt_name]
    options = agi.common.options
    state_space = agi.common.state_space
    operand_storage = agi.operand_storage
    

    all_values = [] 
    for ii in gi.parser_output.instructions:
        #First check if current rule sets the operand, if not
        #go to next rule
        target_op = None
        for op in ii.operands:
            if is_target_op(agi, op, target_opname):
                target_op = op
                break
        
        if not target_op:
            continue
        
        state_dict = agi.common.state_bits
        #if binding operand is a macro
        if target_op.name.lower() in state_dict:
            op_spec = state_dict[target_op.name.lower()].list_of_str
            found_op = False
            for w in op_spec:
                if w.startswith(target_opname):
                    found_op = True
                    break
            if not found_op:
                ildutil.ild_err("Failed to find operand %s" % str(target_op))
            expansion = w
            target_op = opnds.parse_one_operand(expansion)
        
        # the operand is the table output value
        if target_op.bits: # RHS of the 1st operand
            this_row_output = target_op.bits
        else:
            ildutil.ild_err("NTLUF operand %s" % str(target_op))
        # Now we must get the table index values as a dictionary
        indices = _generate_lookup_function_indices(ii,state_space,argnames)
        all_values.append((indices,this_row_output))
    return all_values

def get_nt_from_lufname(fname):
    suffix = re.sub('xed_lookup_function_', '', fname)
    nt = re.sub('_getter', '', suffix)
    return nt

def get_lufn_suffix(array):
    lufn = array.lookup_fn.function_name
    suffix = re.sub('xed_lookup_function_', '', lufn)
    return suffix


def get_lufn(nt_seq, target_op, flevel=''):
    lu_name = '_'.join(nt_seq)
     
    lu_fn = 'xed_lookup_function_%s_%s' % (lu_name, target_op)
    if len(flevel) > 0:
        lu_fn += '_%s' % flevel
    return lu_fn

def gen_lu_names(nt_seq, target_op, level=''):
    """
    @param nt_seq: List of NT names.
    @type nt_seq: C{[string]}
    
    @param target_op: Name of bounded operand.
    @type target_op: C{string}
    
    @return (lu_arr, init_fn, lu_fn): 
        Tuple of 3 names: lookup array name, init function name and
        lookup function name.
    """
    lu_name = '_'.join(nt_seq)
    lu_arr = 'xed_lookup_%s_%s' % (lu_name, target_op)
    init_fn = 'xed_lookup_function_init_%s_%s' % (lu_name, target_op)
    lu_fn = get_lufn(nt_seq, target_op, flevel=level)
    return (lu_arr, init_fn, lu_fn)

def get_luf_name_suffix(luf_name):
    return re.sub('xed_lookup_function_', '', luf_name)


def _is_constant_mapping(val_dict):
    """
    @param val_dict:
    Defines the mapping, by defining an output value for each row of 
    constrains. Each row is defined by a dictionary of operand names to
    operand values.
    @type val_dict:
    [ ([ dict(opname:string -> opval:string) ], value:string) ]
    The return type of _gen_lookup_dict function
    
    @return bool: True if mapping defined by val_dict always returns same 
    value. And hence we can define a constant function, not dependent on
    parameters.
    This is relevant for ONE() NT that has same IMM_WIDTH output operand
    value for several different index values. 
    A good question is why it was defined that way.
    """
    #check if we have same output values for all rows,
    #then we should generate a constant function, independent from parameters
    #This happens in ONE() NT for IMM_WIDTH
    #ONE() seems to be pretty useless NT.
    (_first_indices, first_output) = val_dict[0]
    all_same = True
    for _indices,out_val in val_dict[1:]:
        if out_val != first_output:
            all_same = False
            break
    return all_same


#Parameters:
#nt_seq: [string] - list of NT names that define the mapping
#val_dict: [ ([{token:string -> index_value:string}], return-value:string) ]
#(the type returned by _gen_lookup_dict), it defines the mapping
#opname: string - the name of target operand e.g. EOSZ
#argnames: {string -> { string -> Boolean } } a dict of dicts 
#optype: string - the type of target op (the return type of the 
#lookup function). If optype is specified it is used instead of 
#agi's defined operand type for opname. Useful for IMM_WIDTH which is defined
#as xed_uint8_t by grammar, but for ILD purposes should be natural int 
#(xed_bits_t), because byte-sized operations are sub-optimal in performance in
#32 or 64 modes.
#first key is operand decider name, second key is operand decider value
#argnames['MOD']['0'] == True iff operand decider MOD can have value '0'
#returns codegen.array_gen_t lookup array that defines the mapping
def _gen_lookup_array(agi, nt_seq, val_dict, opname, argnames,
                      optype=None, flevel=''):
    operand_storage = agi.operand_storage
    (lu_arr, init_fn, lu_fn) = gen_lu_names(nt_seq, opname, level=flevel)
    if not optype:
        luf_return_type = operand_storage.get_ctype(opname)
    else:
        luf_return_type = optype
    array= codegen.array_gen_t(lu_arr, type=luf_return_type, target_op=opname)
    
    #check if the mapping is constant (ONE() NT), if so,
    #redefine the mapping to have no index operands so that
    #we will have lookup function with no parameters for this 
    #mapping
    if _is_constant_mapping(val_dict):
        argnames = {}
        (_first_indices, value) = val_dict[0]
        val_dict = [([{}], value)]
    
    for od in argnames.keys():
        values = list(argnames[od].keys())
        array.add_dimension(operand_storage.get_ctype(od),
                            min(values),
                            max(values) + 1,
                            argname = od)
    # fill in all the values
    for list_of_dict_of_indices, value in val_dict:
        for index_dict in list_of_dict_of_indices:
            array.add_value(index_dict, value)
    
    static = True
    
    #FIXME: these functions should be inline, but that leads to a compilation
    #error on linux :
    # cc1: warnings being treated as errors
    # error: inline function ... declared but never defined
    #making it not inline until I figure out how to fix that warning
    inline = True
    array.gen_lookup_function(lu_fn, static=static, inline=inline, 
                              check_const=True)
         
    array.make_initialization_function(init_fn)
    return array

#Parameters:
#array_list: [codegen.array_t] - list of arrays, each of them defines
#a c array, array init function and array lookup function
#c_fn: string - name of the c file, where the arrays and function definitions
#should be dumped
#header_fn: string - name of the .h file where declarations of functions should
#be dumped
#Dumps arrays and init and lookup functions if c and h files 
def dump_lu_arrays(agi, array_list, c_fn, header_fn, init_f=None):
    c_file = agi.open_file(c_fn, start=False)
    header_file = agi.open_file(header_fn, start=False)
    #header_file.replace_headers(['xed-types.h', 'xed-reg-enum.h'])
    header_file.start() 
    
    c_file.start()
    for array in array_list:
        #the optimization for constant functions - we do not need
        #arrays for them since their lookup functions are just "return const;"
        if not array.is_const_lookup_fun():
            c_file.add_code("/*Array declaration*/")
            c_file.add_code(array.emit_declaration(static=False))
            c_file.add_code("/*Array initialization*/")
            array.init_fn.emit_file_emitter(c_file)
    
            init_decl = array.emit_initialization_function_header()
            header_file.add_code(init_decl)
    
    #lookup functions need to be inline, hence we should put them 
    #in header
    for array in array_list:
        #the optimization for constant functions - we do not need
        #arrays for them since their lookup functions are just "return const;"
        if not array.is_const_lookup_fun():
            #declare the lookup arrays
            header_file.add_code("/*Array declaration*/")
            header_file.add_code(array.emit_declaration(static=False, 
                                                        extern=True))
        
        #define the function
        header_file.add_code("/*Lookup function*/")
        array.lookup_fn.emit_file_emitter(header_file)
    
    if init_f:
        init_f.emit_file_emitter(c_file)
        init_decl = init_f.emit_header()
        header_file.add_code(init_decl)
    c_file.close()
    header_file.close()
    

def gen_init_function(arr_list, name):
    #make a function_object_t to call all the individual init routines
    overall_init_f = codegen.function_object_t(name,return_type='void')
    for array in arr_list:
        if not array.is_const_lookup_fun():
            overall_init_f.add_code_eol(array.init_fn.function_name + '()')
    return overall_init_f

#just for debugging. 
#Parameters:
#nt_name: string - the name of the NT
#target_op: string - the name of the target operand
#target_type: string - the type of target operand (xed_bits_t for example).
#Used when we need to override the type specified in grammar.
#return lookup array:codegen.array_t and for a single NT
def gen_nt_lookup(agi, nt_name, target_op, target_type=None, level=''):
    state_space = agi.common.state_space
    gi = agi.generator_dict[nt_name]
    argnames = generate_lookup_function_basis(gi,state_space)
    all_values = _gen_lookup_dict(agi, nt_name, target_op, argnames)
    return _gen_lookup_array(agi, [nt_name], all_values, target_op, argnames,
                             target_type, flevel=level)

#Parameters:
#base_row: {op_name:string -> op_val:string}
#row: {op_name:string -> op_val:string}
#Rows here are the dispatching rows in NT definitions in grammar.
#something like
#MOD=0 |
#MOD=1 |
#MOD=2 |
#each one of these is a row.
#base_row matches a row if all constrains that are true in row are true
#also in base_row
#for example base_row REXW=0 MOD=0 matches a row MOD=0
#ASSUMPTION: base_row has all operands mentioned,
#e.g for EOSZ base_row dict must have OSZ,MOD,REXW operands as keys
def row_match(base_row, row):
    #ildutil.ild_err("ILD_DEBUG BASE ROW %s" % (base_row,))
    for (op, val) in list(row.items()):
        if op in base_row:
            if  base_row[op] != val:
                return False
        else:
            ildutil.ild_err("BASE ROW %s doesn't have OD %s from row %s" %
                             (base_row, op, row))
            return None
    return True

#base_mapping and all_values are both of the type
#[ ([dict token->index_value], return-value) ] 
#the _gen_lookup_dict return type.
#For each row defined in all_values mapping that matches a row from bas_mapping
#this function sets the mapped value to the all_values mapping value.
#For example when we have OSZ_NONTERM-CR_BASE NT sequence,
#base_mapping is defined by OSZ_NONTERM and all_values mapping is 
#defined by CR_BASE
#and we need to override the value of EOSZ in those rows of OSZ_NONTERM
#mapping, that match rows from CR_BASE mapping.
#This function behaves similarly to what decode graph traversing does to EOSZ
#operand value when it sees two EOSZ-binding NTs in the pattern.
def override_mapping(base_mapping, all_values):
    for indices,value in all_values:
        for row in indices:
            temp_map = []
            for base_indices,base_value in base_mapping:
                for base_row in base_indices:
                    #if indices match (it is the same logical constraint)
                    #we override the value those indices map to
                    is_match = row_match(base_row, row)
                    #None is returned on internal error.
                    #We do not exit on this because we don't want to break
                    #xed's build if ild's build fails.
                    #This is temporary.
                    if is_match == None:
                        return None
                    elif row_match(base_row, row): # FIXME: redundant call with line 437
                        temp_map.append(([base_row], value))
                    else: 
                        temp_map.append(([base_row], base_value))
            base_mapping = temp_map
    return base_mapping        
            

#Parameters:
#base_mapping: [ ([{token:string -> index_value:string}], return-value:string)]
#the _gen_lookup_dict return type, it is the object that defines the mapping
#map_list: list of objects of the same type with base_mapping
#take a list of mapping objects and return a mapping
#object that is a result of overriding of first mapping by next ones
def combine_mapping_seq(base_mapping, map_list):
    cur_map = base_mapping
    for all_values in map_list:
        #this one overrides values of those entries in base_mapping
        #that match entries in all_values mapping
        #stores overridden mapping in cur_map
        cur_map = override_mapping(cur_map, all_values)
        if not cur_map:
            return None
    return cur_map
 

    
#Parameters:
#ii: generator.instruction_info_t - a row from NT definition
#state_space: {opname:string -> [op_val:string] } a dict from operand
#name to a list of its possible values. Obtained from generator
#argnames: {string -> { string -> Boolean } } a dict of dicts 
#first key is operand decider name, second key is operand decider value
#argnames['MOD']['0'] == True iff operand decider MOD can have value '0'
#Returns [{opname:string -> op_val:string}] - a list of dicts, each
#defining a row in NT definition. It is a list, because ii can define
#several logical rows e.g for EOSZ:
#if ii represents row: MOD=0 OSZ!=0
#then we will return representation of rows:
#MOD=0 OSZ=1 REXW=1
#MOD=0 OSZ=1 REXW=0 
def _generate_lookup_function_indices(ii,state_space,argnames):
   """Return a list of dictionaries where each dictionary is a
   complete set of token->index_value"""
   
   indices = {} #  dict describing index -> value or list of vlaues
   for bt in ii.ipattern.bits:
      if bt.is_operand_decider():

         if bt.test == 'eq':
            indices[bt.token] = bt.requirement
         elif bt.test == 'ne':
            all_values_for_this_od = state_space[bt.token]
            trimmed_vals = list(filter(lambda x: x != bt.requirement,
                                  all_values_for_this_od))
            #Add the list of values; We flaten it later
            indices[bt.token] = trimmed_vals
         else:
            ildutil.ild_err("Bad bit test (not eq or ne) in " + ii.dump_str())
      elif bt.is_nonterminal():
         pass # FIXME make a better test
      else:
         #We should ignore non-operand deciders: IMM Nts have captures in their
         #rules, and it is OK, they don't affect mappings defined by NTs
         pass
         #ildutil.ild_err("Bad pattern bit (not an operand decider) in %s" %
         #                ii.dump_str())
         #return None
     
   #in order to match lookup rows correctly, we need to have all indices
   #mentioned in the "indices" dict.
   #For example if all operand deciders are [OSZ, REXW, MOD] and in the
   #ii.ipattern we have only MOD=0 mentioned, it means that this row matches
   #all combinations of MOD=0 with all other values for OSZ and REXW.
   #We need to add all those combinations explicitly here, otherwise later
   #when we match rows MOD=0 row may match MOD=0 OSZ=0 row and also
   #MOD=0 OSZ=1 row and these rows define different binding value, we will not
   #know which value to choose.
   #of course there are other ways to solve this problem, but this seems to be
   #the easiest.
   for bt_token in argnames.keys():
       if bt_token not in indices:
           indices[bt_token] = list(argnames[bt_token].keys())


   ### NOW, we must flatten any list-valued RHS's & return a list of
   ### dicts where the RHS is always a scalar.
   indices_flattened = genutil.flatten_dict(indices)
   
   return indices_flattened    

def add_op_deciders_temp(ipattern, state_space, argnames): # NOT USED
    """
    @param ipattern: the ipattern member of instruction_info_t
    @param state_space: dictionary from op deciders tokens to list 
    of their legal values.
    
    @param argnames: dict where to append op deciders values:
    2D argnames[op_decider_token][accepted_value]=True
    """
    for bt in ipattern.bits:
        if bt.is_operand_decider():
            if bt.token not in argnames:
               argnames[bt.token] = {}

            if bt.test == 'eq':
               argnames[bt.token][bt.requirement]=True
            elif bt.test == 'ne':
                  argnames[bt.token]['!=' + ('%s'%bt.requirement)]=True
            else:
               ildutil.ild_err("Bad bit test (not eq or ne) in %s" %
                                ipattern)
    return

def add_op_deciders(ipattern, state_space, argnames):
    """
    @param ipattern: the ipattern member of instruction_info_t
    @param state_space: dictionary from op deciders tokens to list 
    of their legal values.
    
    @param argnames: dict where to append op deciders values:
    2D argnames[op_decider_token][accepted_value]=True
    """
    for bt in ipattern.bits:
        if bt.is_operand_decider():
            if bt.token not in argnames:
               argnames[bt.token] = {}

            if bt.test == 'eq':
               argnames[bt.token][bt.requirement]=True
            elif bt.test == 'ne':
               all_values_for_this_od = state_space[bt.token]
               trimmed_vals = list(filter(lambda x: x != bt.requirement,
                                     all_values_for_this_od))
               for tv in trimmed_vals:
                  argnames[bt.token][tv]=True
            else:
               ildutil.ild_err("Bad bit test (not eq or ne) in %s" %
                                ipattern)
    return

def extend_2d_dict(dst, src): # NOT USED
    for key1 in src:
        if key1 in dst:
            dst[key1].update(src[key1])
        else:
            dst[key1] = src[key1]
    return

def generate_lookup_function_basis(gi,state_space):
   """Return a dictionary whose values are dictionaries of all the values
      that the operand decider might have"""
   argnames = {}  # tokens -> list of all values for that token 
   for ii in gi.parser_output.instructions:
      add_op_deciders(ii.ipattern, state_space, argnames)
   return argnames

