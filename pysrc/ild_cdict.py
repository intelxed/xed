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
ILD constraint dictionary and conflict resolution.

This module handles constraint-based lookup table generation for ILD. It
resolves conflicts when multiple patterns share the same key, organizes
patterns by constraints, and generates layered lookup functions for the
instruction length decoder.
"""
from enum import Enum, auto
import math
import copy
import collections

import genutil
import ildutil
import ild_info
import opnds
import ild_phash
import ild_codegen
import ild_eosz
import ild_easz
import ild_nt
import ild
import actions_codegen
import actions
import verbosity
import tup2int
import operand_storage

# _token_2_module is for fields that might be modified in the pattern.
# if fields are modified in the pattern by some NT, then we must be
# consistent across buckets (legacy/vex/evex, opcode,map). This is
# only relevant for fields that would be used in the "dynamic decode
# part 1".

# EASZ is only rarely modified in experimental extensions.
_token_2_module = {'EOSZ':ild_eosz, 'EASZ':ild_easz}

_find_fn_pfx = 'xed3_phash_find'

def _log(f,s):
    if verbosity.vild():
        f.write(s)

def _set_state_space_from_ii(agi, ii, state_space):
    """
    state_space is a 2D dictionary, ii is generator.instruction_info_t
    this functions sets:
    state_space[OPNAME][OPVAL] = True for every operand decider or prebinding
    with name OPNAME and value OPVAL legal for the given ii.
    """
    for bt in ii.ipattern.bits:
        if bt.is_operand_decider():
            if bt.test == 'eq':
                state_space[bt.token][bt.requirement] = True
    #look at prebindings too
    #for things like ZEROING that don't have all possible
    #values mentioned in patterns
    for (name, binding) in list(ii.prebindings.items()):

        bitnum = len(binding.bit_info_list)
        #dirty hack: we don't want big prebindings to explode
        #our dictionaries
        #FIXME: this assumes that all constraints used for
        #pattern dispatching (all constraints explicitly mentioned
        #in patterns) have bit widths up to 3 bits.
        #This is true now, but might change later. Should put an
        #assertion somewhere.
        #Also better to use a genutil.max_constraint_bitwidth than
        #3.
        if bitnum < 4:
            if not name in state_space:
                state_space[name] = {}
            for val in range(0, 2**bitnum):
                state_space[name][val] = True
        elif binding.is_constant():
            val = int(binding.get_value(), 2)
            state_space[name][val] = True

def _set_space_from_operands(agi, operands, state_space):
    state_dict = agi.common.state_bits
    for op in operands:
        ops = []
        #if binding operand is a macro
        if op.name.lower() in state_dict:
            op_spec = state_dict[op.name.lower()].list_of_str
            found_op = False
            for w in op_spec:
                exapnded_op = opnds.parse_one_operand(w)
                ops.append(exapnded_op)
        else:
            ops.append(op)

        for op in ops:
            if (op.bits and op.name in state_space and
                op.type == 'imm_const'):
                op_val = int(op.bits, 16)
                state_space[op.name][op_val] = True

def get_all_constraints_state_space(agi):
    """Returns a 2D dictionary state_space.

    state_space[OPNAME][OPVAL] == True if there is an operand with
    name OPNAME and value OPVAL.

    The dictionary contains all legal values for operands in grammar.

    Only operands that appear as operand deciders, prebindings, or
    instruction operands are added to the returned dictionary.    """
    
    state_space = collections.defaultdict(dict)
    for g in agi.generator_list:
        for ii in g.parser_output.instructions:
            _set_state_space_from_ii(agi, ii, state_space)
    #set state_space from operands
    #These are NTs partition tables right parts
    for g in agi.generator_list:
        ii = g.parser_output.instructions[0]
        if genutil.field_check(ii,'iclass'):
            continue #only real NTs, not instructions
        for ii in g.parser_output.instructions:
            _set_space_from_operands(agi, ii.operands, state_space)

    # in some configurations xed can be build without any AVX
    # instructions, in this case the operand VEXVALID will no be added.
    # the ild relies on this operand so we add it manually
    if 'VEXVALID' not in state_space:
        state_space['VEXVALID'][0] = True 
    else: # AVX/EVEX builds...
        # 2014-10-10: when I got rid of the NTs for decoding the
        # VEX/EVEX/XOP prefixes, I ended up losing the only NTs that
        # mention ZEROING=1 and VLBAD (VL=3). So we add them here.
        # They are required for proper splattering of don't care
        # cases.  in the hash function generation.  For example when,
        # EVEX.RC is rounding control and co-opting the EVEX.LL field,
        # we need to have the value of VL=3 because it is not
        # "corrected" when we are still picking an instruction (aka
        # 'static decode').
        state_space['ZEROING'][1] = True 
        state_space['VL'][3] = True 

    return state_space

def get_state_op_widths(agi, state_space):
    """
    Returns a dictionary from operand name to operands bit width
    """
    widths_dict = {}
    for opname,val_dict in list(state_space.items()):
        if opname in agi.operand_storage.get_operands():
            opnd = agi.operand_storage.get_operand(opname)
            widths_dict[opname] = int(opnd.bitwidth)
            continue
        maxval = max(val_dict.keys())
        if maxval == 0:
            #log doesn't work on 0 so well
            width = 1
        else:
            width = int(math.floor(math.log(maxval, 2))) + 1
        widths_dict[opname] = width
    #Special, "compressed" operands
    #FIXME: we can add these special operands widths in grammar
    widths_dict[_bin_MOD3] = 1
    widths_dict[_vd_token_7_ones] = 1
    widths_dict[_vd_token_1f_ones] = 1
    widths_dict[_rm_token_4] = 1
    widths_dict[_mask_token_n0] = 1
    widths_dict[_mask_token_zero] = 1
    #constraints on uimm0 operands are 8 bits width max
    widths_dict['UIMM0'] = 8
    return widths_dict

#Following functions are for operands compressing

_bin_MOD3 = 'MOD3'
def _is_binary_MOD3(ptrn_list):
    mod3_eq = 'MOD=3'
    mod3_neq = 'MOD!=3'
    for ptrn in ptrn_list:
        if not (mod3_eq in ptrn.ptrn or mod3_neq in ptrn.ptrn):
            return False
    return True

def _replace_MOD_with_MOD3(cnames, ptrn_list):
    cnames.remove('MOD')
    cnames.add(_bin_MOD3)
    for ptrn in ptrn_list:
        if 'MOD=3' in ptrn.ptrn:
            ptrn.constraints[_bin_MOD3] = {1: True}
        else:
            ptrn.constraints[_bin_MOD3] = {0: True}

_vd_token = 'VEXDEST'
_vd_token210 = f'{_vd_token}210'
_vd_token3 = f'{_vd_token}3'
_vd_token4 = f'{_vd_token}4'

_vd_token_7_ones   = f'{_vd_token}210_7'
_vd_token_1f_ones = f'{_vd_token}_1F'

def _has_VEXDEST210_equals_7_restriction(cnames, ptrn_list):
    """Return true if all patterns (in the list of input pattern_t's ptrn_list)
       with a VEXDEST restriction have a VEXDEST210=7 constraint. If that occurs, 
       we can replace all VEXDEST210 restricions since there are no other kinds of 
       VVVV restrictions.    """
    if _vd_token210 not in cnames:
        return False
    
    for ptrn in ptrn_list:
        if _vd_token_7_ones in ptrn.constraints:
            genutil.die("XXX VEXDEST210_7 already exists in the patterns.")
    
    for ptrn in ptrn_list:
        if _vd_token210 in ptrn.constraints:
            cvals = ptrn.constraints[_vd_token210]
            if len(cvals) == 1 and 7 not in cvals:
                return False
    # _vd_token210=7 is the only _vd_token210 restriction in ptrn_list.
	# Execute the VEXDEST210_7 optimization:
    return True

def _replace_VEXDEST210_with_VD2107(cnames, ptrn_list):
    ''' Replace VEXDEST210 with all-ones optimized constraint '''
    cnames.remove(_vd_token210)
    cnames.add(_vd_token_7_ones)
    
    for ptrn in ptrn_list:
        found = False
        for bt in ptrn.ii.ipattern.bits:
            if bt.token == _vd_token210:
                if bt.test == 'eq':
                    found = True
                    ptrn.constraints[_vd_token_7_ones] = {1:True}
                    break
        if not found:
            #vd7==0 says any VD
            ptrn.constraints[_vd_token_7_ones] = {0:True, 1:True}


# Bit ENUM representation
class bit(Enum):
    ONE   = auto()
    ZERO  = auto()
    DCARE = auto() # Don't-care

def get_constraint_bit(constraints : dict[str, dict], op : str,
                       all_ops_widths: dict ) -> bit:
    """
    Represent XED operand constraint as a bit, if possible.

    Args:
        constraints (dict[str, dict]): All pattern constraints
        op (str): Convert this operand constraints into bit representation
        all_ops_widths (dict): dict of operands width

    Returns:
        bit Enum: Bit representation of "op" pattern constraint.
                  None if operand's constraint is not convertible to bit.
    """
    if all_ops_widths[op] == 1: # One bit width operand
        if op not in constraints:
            # No operand constrains means don't-care
            return bit.DCARE
        
        constr : dict[int, bool] = constraints[op]
        if constr == {1:True}:
                return bit.ONE
        elif constr == {0:True}:
                return bit.ZERO
        elif constr == {0:True, 1:True}:
                # Explicitly don't-care
                return bit.DCARE
    
    return None 

def _has_VEXDEST_equals_1F_restriction(cnames : set, ptrn_list : 'list[ild.pattern_t]',
                                       all_ops_widths : dict):
    """Return true if all patterns includes VVVVV=1F or VVVVV=any restriction.
       In this case, we can replace all VEXDEST210, VEXDEST3, VEXDEST4 restrictions with one 
       check since there are no other kinds of VVVVV restrictions.
       
       Assumption - This check is executed only after a completed VEXDEST210_7 optimization
       """
    if not set([_vd_token_7_ones, _vd_token3, _vd_token4]).issubset(cnames):
        return False
    
    for ptrn in ptrn_list:
        if _vd_token_1f_ones in ptrn.constraints:
            genutil.die(f"XXX {_vd_token_1f_ones} already exists in the patterns.")
        
        # Treat VEXDEST[0-2] a one bit, see VEXDEST210_7 assumption above
        bit210 = get_constraint_bit(ptrn.constraints, _vd_token_7_ones, all_ops_widths)
        bit3 = get_constraint_bit(ptrn.constraints, _vd_token3, all_ops_widths)
        bit4 = get_constraint_bit(ptrn.constraints, _vd_token4, all_ops_widths)
        # xed stores the inverted VEXDEST[4] bit value. store the encoding bit value:
        if bit4 == bit.ONE: bit4 = bit.ZERO
        if bit4 == bit.ZERO: bit4 = bit.ONE
        vd_bits = [bit210, bit3, bit4]

        if all(b == bit.ONE for b in vd_bits):
            # Trivial VVVVV=11111 constraint
            continue
        elif all(b == bit.DCARE for b in vd_bits):
            # Trivial VVVVV=any (Don't-Care) constraint
            continue
        else:
            # Found non-trivial constraint (VVVVV not in [0x1F, don't-care]) 
            return False

    # At this point, all patterns restrictions are VVVVV trivial (all_ones or don't-care)
    return True

def _replace_VEXDEST_with_VD1F(cnames : set, ptrn_list : 'list[ild.pattern_t]'):
    """ Replace VEXDEST210, VEXDEST3, VEXDEST4 constrains with  VEXDEST_1F """    
    cnames.remove(_vd_token_7_ones)
    cnames.remove(_vd_token3)
    cnames.remove(_vd_token4)
    cnames.add(_vd_token_1f_ones)
    
    for ptrn in ptrn_list:
        found =  dict.fromkeys([_vd_token4, _vd_token3, _vd_token_7_ones], False)
        
        if ptrn.constraints[_vd_token_7_ones] == {1:True}:
            found[_vd_token_7_ones] = True
        for bt in ptrn.ii.ipattern.bits:
            if bt.token == _vd_token3:
                if bt.test == 'eq':
                    found[_vd_token3] = True
            if bt.token == _vd_token3:
                if bt.test == 'eq':
                    found[_vd_token4] = True

        if all(found.values()):
            # VVVVV=11111
            ptrn.constraints[_vd_token_1f_ones] = {1:True}
        elif any(found.values()):
            # non-trivial VVVV restriction
            error = f'XXX VEXDEST210_1F Found unexpected VVVVV restriction, should not reach here:\n'
            error += f'VEXDEST210_1F={found}'
            genutil.die(error)
        else:
            # VVVVV=any (don't-care)
            ptrn.constraints[_vd_token_1f_ones] = {1:True, 0:True}


_rm_token = 'RM'
_rm_token_4 = 'RM4'
def _is_binary_RM_4(cnames, ptrn_list):
    # ptrn_list is a list of ild.pattern_t.  Returns True if all
    # patterns have just RM=4 as a constraint.
    if _rm_token not in cnames:
        return False
    for ptrn in ptrn_list:
        # not all patterns have the _rm_token and querying the
        # default-dictionary can add it. so we check first...
        if _rm_token in ptrn.constraints:
            cvals = ptrn.constraints[_rm_token]
            if len(cvals) != 1:
                # more than one constraint value
                return False
            elif 4 not in cvals: 
                # one constraint value but it is not 4.
                return False
        else: # some pattern does not have and RM constraint
            return False
    # all have one constraint of RM=4.                
    return True

def _replace_RM_with_RM4(cnames, ptrn_list):
    # When we call this we know that all the patterns in the pattern
    # list have RM=4 either from (a) RM[0b100] or (b) RM=4
    # constraints.  The RM[0b100] is captured in prebindings (and the
    # constraints, which is how we got here) and 3 raw 1, 0, 0 bits
    # are present in the pattern.  This function does remove the RM
    # from the cnames, but it doesn't really do anything to the
    # ipattern.  So there is no need to search ipattern again
    
    # ptrn_list is a list of ild.pattern_t
    cnames.remove(_rm_token)
    cnames.add(_rm_token_4)
    for ptrn in ptrn_list:
        #print("B-ICLASS: {}".format(ptrn.ii.iclass))
        ptrn.constraints[_rm_token_4] = {1:True}

_mask_token = 'MASK'
_mask_token_n0 = 'MASK_NOT0'
_mask_token_zero = 'MASK_ZERO'
def _is_binary_MASK_NOT0(cnames, ptrn_list):
    if _mask_token not in cnames:
        return False
    for ptrn in ptrn_list:
        # check before indexing to avoid creating entry in
        # default-dict.
        if _mask_token in ptrn.constraints:
            cvals = ptrn.constraints[_mask_token]
            if len(cvals)!=7:  
                return False
            elif 0 in cvals: # have 7 values but 0 is there so no good
                return False
        else: # some pattern does not have mask constraint
            return False
    return True

def _has_MASK_ZERO_restriction(cnames, ptrn_list):
    """Return true if all pattern_t in the list has MASK=000 or MASK=any restriction."""
    if _mask_token not in cnames:
        return False
    for ptrn in ptrn_list:
        if _mask_token in ptrn.constraints:
            cvals : dict[int, bool] = ptrn.constraints[_mask_token]
            if cvals == {0:True}:
                for bt in ptrn.ii.ipattern.bits:
                    if bt.token == _mask_token:
                        if bt.test != 'eq':
                            return False # MASK!=000. Optimization is only for MASK=000
            elif len(cvals.keys())==8 and all(cvals.values()):
                continue # MASK=Any
            else:
                return False
    return True


def _replace_MASK_with_MASK_NOT0(cnames, ptrn_list):
    cnames.remove(_mask_token)
    cnames.add(_mask_token_n0)
    for ptrn in ptrn_list:
        found = False
        for bt in ptrn.ii.ipattern.bits:
            if bt.token == _mask_token:
                if bt.test == 'ne':
                    found = True
                    ptrn.constraints[_mask_token_n0] = {1:True}
                    break
        if not found:
            #mask is not in the pattern, all values of MASK_NOT0 are valid 
            ptrn.constraints[_mask_token_n0] = {0:True, 1:True}



def _replace_MASK_with_MASK_ZERO(cnames, ptrn_list):
    cnames.remove(_mask_token)
    cnames.add(_mask_token_zero)
    for ptrn in ptrn_list:
        if _mask_token in ptrn.constraints and ptrn.constraints[_mask_token] == {0:True}:
            ptrn.constraints[_mask_token_zero] = {1:True}
        else:
            # all values of MASK_ZERO are valid 
            ptrn.constraints[_mask_token_zero] = {0:True, 1:True}
            

def get_compressed_op_getter_fn(opname):
    """
    Compressed operands are special - we do not capture them
    in ILD and do not derive them in NTs. (though we could..
    FIXME: is it worthy?), hence in order to get their value we can not
    use regular xed3_operand_get_* function - we use special getters
    for them.
    get_compressed_op_getter_fn(opname) returns a name of the special getter
    for a given compressed operand name.
    FIXME: right now we just use the same operand naming scheme as for
    regular operands. Do we need this function?
    """
    return operand_storage.get_op_getter_fn(opname)

mod3_repl=0
vd7_repl=0
vd1f_repl=0
rm4_repl=0
masknot0_repl=0
mask0_repl=0

def replacement_stats():
    s = []
    for x,y in [('MOD3', mod3_repl),
                ('VD7', vd7_repl),
                ('VD1F', vd1f_repl),
                ('RM4', rm4_repl),
                ('MASK!=0', masknot0_repl),
                ('MASK=0',mask0_repl)]:
        s.append('{} {}'.format(x,y))
    return ', '.join(s)

def _get_united_cdict(ptrn_list : list, state_space : dict[str, dict[int,bool]], 
                      vexvalid : str, all_ops_widths : dict):
    """@param ptrn_list: list of ild.pattern_t
    @param state_space: all legal values for xed operands:
                        state_space['REXW'][1] = True,
                        state_space['REXW'][0]=True
    @param vexvalid: VEXVALID value we want to filter by. vevxavlid=='0'
                    will include only patterns with vexvalid=='0' constraint
                    value.
    @param all_ops_widths: dict of operands to their bit widths. 

    @return ild_cdict.constrant_dict_t which unites patterns constraint dicts

    This gets called with all the patterns for a specific map &
    opcode, but for all encoding spaces. So first we filter based on
    encoding space (vexvalid).    """
    global mod3_repl, vd7_repl, vd1f_repl, rm4_repl, masknot0_repl, mask0_repl
    cnames = []

    # FIXME: 2019-10-30: patterns now know their vexvalid value and
    # encspace, and the maps are split by encspace as well, so we can
    # avoid the following filtering by vexvalid.
    
    #filter by encoding space (vexvalid)
    ptrns : list[ild.pattern_t] = []
    ivv = int(vexvalid)
    for ptrn in ptrn_list:
        #FIXME: 2019-10-30: if vexvalid in list(ptrn.special_constraints['VEXVALID'].keys()):
        if ivv == ptrn.vv:
            ptrns.append(ptrn)

    if len(ptrns) == 0:
        return None

    for ptrn in ptrns:
        cnames.extend(list(ptrn.constraints.keys()))
    cnames = set(cnames)

    if _is_binary_MOD3(ptrns):
        mod3_repl += 1
        _replace_MOD_with_MOD3(cnames, ptrns)

    if _has_VEXDEST210_equals_7_restriction(cnames, ptrns): 
        vd7_repl += 1
        _replace_VEXDEST210_with_VD2107(cnames, ptrns)         
        if _has_VEXDEST_equals_1F_restriction(cnames, ptrns, all_ops_widths):
            vd7_repl -= 1
            vd1f_repl += 1
            _replace_VEXDEST_with_VD1F(cnames, ptrns)

    if _is_binary_RM_4(cnames, ptrns):
        rm4_repl += 1
        _replace_RM_with_RM4(cnames, ptrns)
    # Hint for disabled optimization (Replaced with MASKNOT0())
    # if _is_binary_MASK_NOT0(cnames, ptrns):
    #     masknot0_repl += 1
    #     _replace_MASK_with_MASK_NOT0(cnames, ptrns)

    if _has_MASK_ZERO_restriction(cnames, ptrns): 
        mask0_repl += 1
        _replace_MASK_with_MASK_ZERO(cnames, ptrns)

    # For each pattern we have a list of constraints. ptrn.constraints
    # is the legal values for those constraints. In each map opcode
    # bin, we have several patterns with different constraints. We
    # want to make one hash table for these different patterns. Thats
    # why we want to take the union of all the constraints and make
    # one dictionary (and ultimately a hash table). Need to add all
    # legal variations of all constraints, cross product. (dangerous)
    #For example if we have two patterns:
    #PATTERN1: MOD=1
    #PATTERN2: REG=2
    #then for PATTERN1 we will create a constraint dictionary with all
    #combinations (MOD=1 REG=0), (MOD=1, REG=1) ,..., (MOD=1, REG=7)
    #and for PATTERN2 we will have (MOD=0 REG=2), (MOD=1 REG=2), ...
    cdicts = []
    for ptrn in ptrns:
        cdict = constraint_dict_t(cnames, ptrn.constraints, state_space, ptrn)
        cdicts.append(cdict)
    insn_map = ptrns[0].insn_map
    opcode = ptrns[0].opcode
    msg = []
    msg.append("cdict conflict in pattern")
    msg.append('MAP:%s OPCODE:%s\n' % (insn_map, opcode))
    msg = "\n".join(msg)
    # now we unite (cross-product) after exploding/back-filling all the
    # constraints. All patterns now have same constraints.
    united_dict = constraint_dict_t.unite_dicts(cdicts, msg, cnames)
    
    #generate the int value for each tuple
    united_dict.create_tuple2int(all_ops_widths)

    #print "UNITED DICT: VV {} OPCODE {} MAP {}:  tuples {}".format(
    #    vexvalid, opcode, insn_map, len(united_dict.tuple2rule) )
    
    #creating the default action that will be taken when we did not hit 
    #a valid hash entry
    default_action = [actions.gen_return_action('0')]
    united_dict.action_codegen = actions_codegen.actions_codegen_t(
        united_dict.tuple2rule,
        default_action,
        united_dict.strings_dict)
    return united_dict



#FIXME: maybe it should contain tuple2int function?
#Now tuple2int is a part of phash object.
class constraint_dict_t(object):
    def __init__(self, cnames=None, state_space=None, all_state_space=None,
                 rule=None):
         """cnames is sorted list of constraint names.
        
           state_space is the constraints from the pattern_t.

           all_state_space is a dict w/legal values for all constraints in grammar.

           rule is the ild.py pattern_t object (essentially the instruction). """
         #cnames is sorted list of strings - constraints' names that we want
         #this cdict to have.
         if cnames:
             self.cnames = sorted(list(cnames))
         else:
             self.cnames = []

         self.strings_dict = ild_codegen._dec_strings

         #state_space is a dict with constraints' values we want
         #this cdict to represent.
         #For example if we want cdict to allow only MODE=0 we will
         #have state_space['MODE'][0] = True
         if state_space:
             self.state_space = state_space
         else:
             self.state_space = {}

         #all_state_space is a dict with all legal values that constraints
         #have in grammar.
         #For example:
         #all_state_space['REXW'][0]=True, all_state_space['REXW'][1]=True
         #It is used when state_space doesn't have a constraint from cnames.
         #We need this when we build united constraint dict for a set of
         #patterns:
         #first we build a separate constraint dict for each pattern, but
         #it includes all the cnames that set has, and then we unite those
         #cdicts. See _get_united_cdict() function
         if all_state_space:
             self.all_state_space = all_state_space
         else:
             self.all_state_space = {}

         # this is the ild.py:pattern_t
         self.rule = rule
         
         #tuple2int maps the same tuples as tuple2int to hash key values.
         self.tuple2int = {}
         
         #reverse mapping from hash key to list of constraint value tuples.
         self.int2tuple = {}
         
         #dict of all operands -> bit width.
         self.op_widths = {}

         self.action_codegen = None
         
         #dict mapping tuples to rules. 
         #tuples are the constraint values (without the constraint names).
         self.tuple2rule = {}  # ild.pattern_t
         if self.state_space:
             self.tuple2rule = self._initialize_tuple2rule(self.cnames, {})

    @staticmethod
    def unite_dicts(dict_list, err_msg, cnstr_names):
        """ dict_list is a list of constraint dictionaries.  The keys
        in the dictionary are the values of the constraints as tuples.
        If we see the same values in more than one pattern, we have a
        decoding conflict in the grammar. The dictionaries have been
        expanded so that they all have the same constraint names upon
        entry.
        """

        dlen = len(dict_list)
        if dlen == 0:
            return None
        if dlen == 1:
            return dict_list[0]
        
        res = constraint_dict_t(cnames=cnstr_names)
        for cdict in dict_list:
            for key in cdict.tuple2rule.keys():
                if key in res.tuple2rule:  # keys are tuples of constraint values
                    msg = []
                    msg.append("key: %s" % (key,))
                    msg.append("cdict:%s" % cdict)
                    msg.append("res:%s" % res)
                    msg = "\n".join(msg)
                    ildutil.ild_err(err_msg + msg)
                    return None
                else:
                    res.tuple2rule[key] = cdict.tuple2rule[key]
                    
        return res


    def _initialize_tuple2rule(self, cnames, tuple2rule): # recursive
        """look @ first cnames, get the possible values for it.  Add an entry
        to the current tuple2rule dictionary with each possible value
        and the current rule (which is the ild.py pattern_t, pointed
        to by the set of constraints.).  Each time we recursively
        call, we take the next constraint and add its values to the
        key tuple for the dictionary.

        """
        if len(cnames) == 0:
            # when we are out of constraints, we return the fully
            # constructed tuple.
            return tuple2rule
        # pick off the cnames one at a time
        name = cnames[0]
        if name in self.state_space:
            vals = sorted(self.state_space[name].keys())
        else:
            vals = sorted(self.all_state_space[name].keys())
        if len(tuple2rule) == 0:
            #initialize tuple2rule with singleton tuples
            for val in vals:
                tuple2rule[(val,)] = self.rule
            return self._initialize_tuple2rule(cnames[1:], tuple2rule)

        new_tuple2rule = {}
        for key_tuple in tuple2rule.keys():
            for val in vals:
                new_key = key_tuple + (val,)
                new_tuple2rule[new_key] = self.rule
        return self._initialize_tuple2rule(cnames[1:], new_tuple2rule)

    def get_all_keys_by_val(self, val):
        return [k for k,v in self.tuple2rule.items() if v == val]
    
    def create_tuple2int(self, all_ops_widths):
        '''create the mapping of tuple to its int value by CONCATENTATING all
        the input constraint values to make an integer that is
        ultimately the input to the hash function. '''
        tuple2int = {}
        int2tuple = {}
        for t in self.tuple2rule.keys():
            res = tup2int.tuple2int(t, self.cnames, all_ops_widths)
            if res in int2tuple:
                err = "the tuple % and the tuple %s generate the same value:%d"
                genutil.die(err % (t,str(int2tuple[res]),res))    
            else:
                tuple2int[t] = res
                int2tuple[res] = t
        
        #later using the op_widths for the code generation             
        self.op_widths = all_ops_widths
        self.tuple2int = tuple2int
        self.int2tuple = int2tuple    
    
    def get_ptrn(self, tup):
        ''' return the pattern that represents the given tuple '''
        return self.tuple2rule[tup].ptrn

    def filter_tuples(self,tuples):
        '''from all the dictionaries in self, remove the tuples that are not
        in the input tuples list.  return new instance of cdict. This
        is used for re-grouping tuples when making the 2nd level of
        2-level hash tables. '''
        
        new_cdict = copy.copy(self)
        new_cdict.tuple2int = {}
        new_cdict.tuple2rule = {}
        for t in tuples:
            new_cdict.tuple2int[t] = self.tuple2int[t] 
            new_cdict.tuple2rule[t] = self.tuple2rule[t] 
            
        
        new_cdict.int2tuple = dict((i,t) for t,i in 
                                   new_cdict.tuple2int.items())
        
        return new_cdict
          
    def get_operand_accessor(self, cname):
        ''' return a tuple of the operand accessor function and the constraint 
        names that it represents '''
        
        ptrn_list = list(self.tuple2rule.values())
        if cname in list(_token_2_module.keys()):
            nt_module = _token_2_module[cname] # name of python module!
            getter_fn = nt_module.get_getter_fn(ptrn_list) # indirect module refs!
            if not getter_fn: # -> error
                    msg = 'Failed to resolve %s getter fn for '
                    msg += 'MAP:%s OPCODE:%s'
                    insn_map = ptrn_list[0].insn_map
                    opcode = ptrn_list[0].opcode
                    ildutil.ild_err(msg % (cname, insn_map, opcode))
            access_str = '%s(%s)' % (getter_fn, self.strings_dict['obj_str'])
            nt = ild_nt.get_nt_from_lufname(getter_fn)
            return access_str, nt
        else:
            access_str = ild_codegen.emit_ild_access_call(cname, 
                                                      self.strings_dict['obj_str'])
            return access_str, cname

    def __str__(self):
        rows = []
        size = len(self.tuple2rule)
        rows.append("cdict_size=%d" % size)
        if size >= 100:
            rows.append('HUGE!')
        elif size >= 50:
            rows.append('BIG!')
        legend = "{} -> VALUE".format(" ".join(self.cnames))
        rows.append(legend)
        if len(self.tuple2rule) == 0:
            rows.append("_ \t-> %s" % self.rule)

        # print all the decision values first with iclass, if any
        for key in sorted(self.tuple2rule.keys()):
            val = self.tuple2rule[key] # ild.pattern_t
            s = []
            for cname, tval in zip(self.cnames,key):
                s.append("{}:{}".format(cname,tval))
            iclass = 'n/a'
            if hasattr(val,'iclass'):
                iclass = val.iclass
            rows.append("{} -> {}".format(", ".join(s), iclass))
            
        rows.append("\n\n")
        
        # now print them again with their detailed information
        for key in sorted(self.tuple2rule.keys()):
            val = self.tuple2rule[key]  # ild.pattern_t
            s = []
            for cname, tval in zip(self.cnames,key):
                s.append("{}:{}".format(cname,tval))
            rows.append("{} \t-> {}".format(", ".join(s), str(val)))
        return "\n".join(rows)
    


def get_constraints_lu_table(agi,
                             ptrns_by_map_opcode,
                             state_space,
                             vexvalid,
                             all_ops_widths):
    """
    returns a tuple (cdict_by_map_opcode,cnames)
    cnames is a set of all constraint names used in patterns.
    cdict_by_map_opcode is  a traditional 2D lookup dict from map,opcode to
    constraint_dict_t objects that represent the mapping from constraints
    values to different patterns of the corresponding (map,opcode,vexvalid)
    bin. These cdict objects can later be used for generating hash functions
    from constraint values to patterns (inums).
    """
    maps = ild_info.get_maps(agi)
    cdict_by_map_opcode = collections.defaultdict(dict)
    cnames = set()
    for insn_map in maps:
        for opcode in range(0, 256):
            opcode = hex(opcode)
            ptrns = ptrns_by_map_opcode[insn_map][opcode]
            cdict = _get_united_cdict(ptrns, state_space, vexvalid,
                                      all_ops_widths)
            cdict_by_map_opcode[insn_map][opcode] = cdict
            if cdict:
                cnames = cnames.union(set(cdict.cnames))
    return cdict_by_map_opcode,cnames

def gen_ph_fos(agi,
               cdict_by_map_opcode,
               log_fn,
               ptrn_dict,
               vv):
    """
    Returns a tuple (phash_lu, phash_fo_list, op_lu_list)
    * phash_lu:  is a traditional 2D dict by (map, opcode) to a
      hash function name.
    * phash_fo_list: is a list of all phash function objects created
      (we might have fos that are not in lookup table - when we have
      2-level hash functions).
    * op_lu_list:  is a list for all the operands lookup functions

    Also writes log file for debugging.
    """
    maps = ild_info.get_maps(agi)
    log_f = open(log_fn, 'w')
    cnames = set() # only for logging
    stats = {
             '0. #map-opcodes': 0,
             '1. #entries': 0,
             '2. #hentries': 0,
             '3. #hashes': 0,
             '4. #min_hashes': 0,
             '5. #cdict_size_1_to_10': 0,
             '6. #cdict_size_10_to_20': 0,
             '7. #cdict_size_20_to_100': 0,
             '8. #cdict_size_at_least_100': 0
             }
    lu_fo_list = []  
    op_lu_map = {} # fn name -> fn obj
    phash_lu = {}  # map, opcode -> fn name
    for insn_map in maps:
        phash_lu[insn_map] = {}
        zeros = 0
        for opcode in range(0, 256):
            opcode = hex(opcode)
            cdict = cdict_by_map_opcode[insn_map][opcode]
            if cdict:
                stats['0. #map-opcodes'] += 1
                stats['1. #entries'] += len(cdict.tuple2rule)
                cnames = cnames.union(set(cdict.cnames))
                _log(log_f,'XYZ VV: {} MAP:{} OPCODE:{}:\n{}\n'.format(
                    vv, insn_map, opcode, cdict))

                phash = ild_phash.gen_hash(cdict)
                if phash:
                    _log(log_f,"%s" % phash)
                    phash_id = 'map%s_opcode%s_vv%d' % (insn_map, opcode,
                                                        vv)
                    fname = "%s_%s" % (_find_fn_pfx,phash_id)
                    (fo_list, op_lu_fo) = phash.gen_find_fos(fname)
                    lu_fo_list.extend(fo_list)

                    #hold only one instance of each function
                    if op_lu_fo:
                        if op_lu_fo.function_name not in op_lu_map:
                            op_lu_map[op_lu_fo.function_name] = op_lu_fo
                    for fo in fo_list:
                        _log(log_f,'//find function:\n')
                        _log(log_f,fo.emit())
                        _log(log_f,'-----------------------------\n')
                    #FIXME: assumption: L2 function is last in the list
                    #maybe return dict or tuple to make a distinction between
                    #L2 and L1 functions?
                    phlu_fn = lu_fo_list[-1]
                    phash_lu[insn_map][opcode] = phlu_fn.function_name
                    phash.update_stats(stats)
                else:
                    _log(log_f,'---NOPHASH-----\n')
                    msg = "Failed to gen phash for map %s opcode %s"
                    ildutil.ild_err(msg % (insn_map, opcode))
            else:
                phash_lu[insn_map][opcode] = '(xed3_find_func_t)0'
                zeros = zeros + 1
        if zeros == 256: # all zero... shortcut to avoid scanning maps for "all-zeros"
            _log(log_f, "ZEROING phash_lu for map {} vv {}\n".format(insn_map, vv))
            phash_lu[insn_map] = None
    _log(log_f,"cnames: %s\n" %cnames)
    for key in sorted(stats.keys()):
        _log(log_f,"%s %s\n" % (key,stats[key]))
    _log(log_f, f'Restriction replacements stats:\n {replacement_stats()}')
    log_f.close()
    return phash_lu, lu_fo_list, list(op_lu_map.values())

