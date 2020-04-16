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
import copy
import os
import collections
import shutil

import genutil
import ildutil
import mbuild
import ild_info
import ild_storage
import ild_eosz
import ild_easz
import ild_imm
import ild_disp
import ild_modrm
import codegen
import ild_codegen
import ild_cdict
import dec_dyn
import actions
import verbosity


op_bin_pattern      = re.compile(r'[_10]{2,}$')
op_hex_pattern      = re.compile(r'[0-9a-f]{2}$', flags=re.IGNORECASE)
reg_binding_pattern = re.compile(r'REG[\[](?P<bits>0b[01_]+)]')
mod_eq_pattern      = re.compile(r'MOD=(?P<bits>[0123]{1})')
mod_neq_pattern     = re.compile(r'MOD(!=|=!)(?P<bits>[0123]{1})')


#debugdir is updated in init_debug
#the module.
debugdir = '.'

#the debug file
debug = None

_mode_token = 'MODE'

#just to know how many there are and how hard it is
#42 nested NTs..
#mostly modrm-related
def _get_nested_nts(agi):
    nested_nts = set()
    for nt_name in agi.nonterminal_dict.keys():
        g = agi.generator_dict[nt_name]
        ii = g.parser_output.instructions[0]
        if genutil.field_check(ii,'iclass'):
            continue #only real NTs, not instructions
        for rule in g.parser_output.instructions:
            for bt in rule.ipattern.bits:
                if bt.is_nonterminal():
                    nested_nts.add(nt_name)
            for op in rule.operands:
                if op.type == 'nt_lookup_fn':
                    nested_nts.add(nt_name)
    return nested_nts


###########################################################################
## < Interface for generator >
###########################################################################

#needed to init the debug directory
def init_debug(agi):
    global debug
    global debugdir
    debugdir = agi.common.options.gendir
    debug = open(mbuild.join(debugdir, 'ild_debug.txt'), 'w')

def gen_xed3(agi, ild_info, ild_patterns,
             all_state_space, ild_gendir, all_ops_widths):
    all_cnames = set()
    ptrn_dict = {}  # map,opcode -> pattern
    maps = ild_info.get_maps(agi)
    for insn_map in maps:
        ptrn_dict[insn_map] = collections.defaultdict(list)
    for ptrn in ild_patterns:
        ptrn_dict[ptrn.insn_map][ptrn.opcode].append(ptrn)
    #FIXME:bad name
    vv_lu = {} # vexvalid-space -> ( ph_lu, lu_fo_list)
    #mapping between a operands to their look up function
    op_lu_map = {}  # func name -> function (for unique-ifying)

    for vv in sorted(all_state_space['VEXVALID'].keys()):
        #cdict is a 2D dictionary:
        #cdict[map][opcode] = ild_cdict.constraint_dict_t
        #Each constraint_dict_t describes all the patterns that fall
        #into corresponding map-opcode.
        #cnames is a set of all constraint names from the patterns
        #in the given vv space
        cdict,cnames = ild_cdict.get_constraints_lu_table(agi,
                                                          ptrn_dict,
                                                          all_state_space,
                                                          vv,
                                                          all_ops_widths)
        all_cnames = all_cnames.union(cnames)
        _msg("vv%s cnames: %s" % (vv,cnames))
        
        constraints_log_file = mbuild.join(ild_gendir,
                                           'all_constraints_vv%s.txt' %vv)

        #now generate the C hash functions for the constraint
        #dictionaries.
        #
        # ph_lu            map from map,opcode -> hash fn name
        # lu_fo_list       list of all phash fn objects
        # operands_lu_list list of operands lookup fns
        ph_lu, lu_fo_list, operands_lu_list = ild_cdict.gen_ph_fos(agi, 
                                                                   cdict,
                                                                   constraints_log_file,
                                                                   ptrn_dict, 
                                                                   vv)
        #hold only one instance of each function
        for op in operands_lu_list:
            if op.function_name not in op_lu_map:
                op_lu_map[op.function_name] = op

        vv_lu[str(vv)] = (ph_lu,lu_fo_list)
    _msg("all cnames: %s" % all_cnames)

    #dump the (a) hash functions and (b) lookup tables for obtaining
    #these hash functions (at decode time). ** Static decode **
    ild_codegen.gen_static_decode(agi,
                                  vv_lu,
                                  list(op_lu_map.values()),
                                  h_fn='xed3-phash.h')
    
    #dec_dyn.work(...) generates all the functions and lookup tables for
    # ** Dynamic decode **
    dec_dyn.work(agi, all_state_space, all_ops_widths, ild_patterns)

#Main entry point of the module
def work(agi):
    ild_gendir = agi.common.options.gendir
    init_debug(agi)

    debug.write("state_space:\n %s" % agi.common.state_space)

    # Collect up interesting NT names.
    # We are going to use them when we generate pattern_t objects
    # and also when we build resolution functions.
    eosz_nts   = ild_eosz.get_eosz_binding_nts(agi)
    easz_nts   = ild_easz.get_easz_binding_nts(agi)
    imm_nts    = ild_imm.get_imm_binding_nts(agi)
    disp_nts   = ild_disp.get_disp_binding_nts(agi)
    brdisp_nts = ild_disp.get_brdisp_binding_nts(agi)

    #just for debugging
    _msg("EOSZ NTS:")
    for nt_name in eosz_nts:
        _msg(nt_name)

    _msg("\nEASZ NTS:")
    for nt_name in easz_nts:
        _msg(nt_name)

    _msg("\nIMMNTS:")
    for nt_name in imm_nts:
        _msg(nt_name)

    _msg("\nDISP NTS:")
    for nt_name in disp_nts:
        _msg(nt_name)

    _msg("\nBRDISP NTS:")
    for nt_name in brdisp_nts:
        _msg(nt_name)

    nested_nts = _get_nested_nts(agi)
    _msg("\nNESTED NTS:")
    for nt_name in nested_nts:
        _msg(nt_name)

    #Get dictionary with all legal values for all interesting operands
    all_state_space = ild_cdict.get_all_constraints_state_space(agi)
    _msg("ALL_STATE_SPACE:")
    for k,v in list(all_state_space.items()):
        _msg("%s: %s"% (k,v))

    #Get widths for the operands
    all_ops_widths = ild_cdict.get_state_op_widths(agi, all_state_space)

    _msg("ALL_OPS_WIDTHS:")
    for k,v in list(all_ops_widths.items()):
        _msg("%s: %s"% (k,v))

    #generate a list of pattern_t objects that describes the ISA.
    #This is the main data structure for XED3
    ild_patterns = get_patterns(agi, eosz_nts, easz_nts, imm_nts,
                                disp_nts, brdisp_nts, all_state_space)

    if ild_patterns:

        #get ild_storage_t object - the main data structure for ILD
        #essentially a 2D dictionary:
        #ild_tbl[map][opcode] == [ ild_info_t ]
        #the ild_info_t objects are obtained from the grammar
        priority = 0
        ild_tbl = _get_info_storage(agi, ild_patterns, priority)

        #generate modrm lookup tables
        ild_modrm.work(agi, ild_tbl, debug)

        #dump_patterns is for debugging
        if verbosity.vild():
            dump_patterns(ild_patterns,
                          mbuild.join(ild_gendir, 'all_patterns.txt'))

        eosz_dict = ild_eosz.work(agi, ild_tbl, eosz_nts, ild_gendir, debug)
        easz_dict = ild_easz.work(agi, ild_tbl, easz_nts, ild_gendir, debug)

        #dump operand accessor functions
        agi.operand_storage.dump_operand_accessors(agi)
        
        if eosz_dict and easz_dict:
            ild_imm.work(agi, ild_tbl, imm_nts, ild_gendir,
                         eosz_dict, debug)
            ild_disp.work(agi, ild_tbl, disp_nts, brdisp_nts, ild_gendir,
                          eosz_dict, easz_dict, debug)

        # now handle the actual instructions
        gen_xed3(agi, ild_info, ild_patterns, 
                 all_state_space, ild_gendir, all_ops_widths)


def get_patterns(agi, eosz_nts, easz_nts,
                 imm_nts, disp_nts, brdisp_nts, all_state_space):
    """
    This function generates the pattern_t objects that have all the necessary
    information for the ILD. Returns these objects as a list.
    """
    machine_modes = agi.common.get_state_space_values('MODE')
    patterns = []
    pattern_t.map_info_g = agi.map_info
    for g in agi.generator_list:
        ii = g.parser_output.instructions[0]
        if genutil.field_check(ii,'iclass'):
            for ii in g.parser_output.instructions:
                ptrn = pattern_t(ii, eosz_nts,
                                 easz_nts, imm_nts, disp_nts, brdisp_nts,
                                 machine_modes, all_state_space)
                patterns.append(ptrn)
                if ptrn.incomplete_opcode:
                    expanded_ptrns = ptrn.expand_partial_opcode()
                    patterns.extend(expanded_ptrns)
    return patterns


def _get_info_storage(agi, ptrn_list, priority):
    """convert list of pattern_t objects to ild_storage_t object, store by
       map/opcode"""

    lookup = ild_storage.get_lookup(agi)
    storage = ild_storage.ild_storage_t(lookup)

    for p in ptrn_list:
        info = ild_info.ptrn_to_info(p, priority) # convert to ild_info_t
        if info not in storage.get_info_list(p.insn_map,p.opcode):
            storage.append_info(p.insn_map, p.opcode, info)
    return storage


#this is for debugging mostly. Also a good source of info on instruction set.
def dump_patterns(patterns, fname):
    f = open(fname, 'w')
    for pattern in patterns:
        f.write( '%s\n' % pattern)
    f.close()

###########################################################################
## </ Interface for generator >
###########################################################################



#Maybe pattern_t should inherit from instruction_info_t
#Let it inherit from object for now.
class pattern_t(object):
    map_info_g = None 

    def __init__(self, ii, eosz_nts, easz_nts, imm_nts, disp_nts,
                 brdisp_nts, mode_space, state_space):

        self.ptrn = ii.ipattern_input
        self.ptrn_wrds = self.ptrn.split()
        self.iclass = ii.iclass
        self.legal = True

        self.category = ii.category
        #FIXME: remove all members of ii stored directly as members
        self.ii = ii

        #incomplete_opcode is used for expanding opcodes that have registers
        #embedded in them
        self.incomplete_opcode = False

        #number of missing bits in incomplete opcode. usually 0 or 3
        self.missing_bits = 0

        self.insn_map = None
        self.opcode = None

        self.space = None # LEGACY|VEX|EVEX
        self.has_modrm = False

        self.imm_nt_seq = None

        self.disp_nt_seq = None

        #modrm.reg bits value, set only when it is explicitly
        #e.g. bounded: REG[010]
        self.ext_opcode = None

        #all legal values for MODE operand in this pattern
        self.mode = None


        #an ordered string of EOSZ setting NTs in the pattern
        #we will use it to create the eosz lookup table for the pattern
        self.eosz_nt_seq = None

        #same for EASZ
        self.easz_nt_seq = None

        #operand deciders of the pattern
        self.constraints = None
        self._set_constraints(ii, state_space)
        
        self.vv = None # vexvalid, integer
        self._set_vexvalid()
        
        self.encspace = None
        self._set_encoding_space()

        mi,insn_map,opcode = self._get_map_opcode()
        self.map_info = mi
        self.insn_map = insn_map
        self.opcode = opcode

        self.has_modrm = ild_modrm.get_hasmodrm(self.ptrn)
        self.set_ext_opcode()

        self.set_mode(ii, mode_space)

        self.eosz_nt_seq = ild_eosz.get_eosz_nt_seq(self.ptrn_wrds,
                                                         eosz_nts)

        self.easz_nt_seq = ild_easz.get_easz_nt_seq(self.ptrn_wrds,
                                                         easz_nts)

        self.imm_nt_seq = ild_imm.get_imm_nt_seq(self.ptrn_wrds, imm_nts)

        self.disp_nt_seq = ild_disp.get_disp_nt_seq(self.ptrn_wrds,
                                                    disp_nts.union(brdisp_nts))
        
        self.actions = [actions.gen_return_action(ii.inum)]

        
    def is_legal(self):
        return (self.legal and
                self.opcode != None and
                self.insn_map != None and
                self.space != None)


    def set_ext_opcode(self):
       #inline captures MOD[mm] REG[rrr] RM[nnn]
       #or REG[111] etc. -- can be constant
       for w in self.ptrn_wrds:
           pb = reg_binding_pattern.match(w)
           if pb:
               bits = pb.group('bits')
               self.ext_opcode = genutil.make_numeric(bits)
               return

    def _set_constraints(self, ii, state_space):
        #FIXME: this assumes, that there are no contradictions
        #between constraints on the same operand.
        #If there are, e.g. MOD=3 ... MOD=1, both values will be
        #set as legal.. check such things here?

        #set constraints that come from operands deciders
        self.constraints = dec_dyn.get_ii_constraints(ii, state_space)
        #print "CONSTRAINTS: {}".format(self.constraints)

        #special care for VEXVALID - it makes it easy to dispatch vex
        #and legacy instructions. For legacy we will explicitly set
        #VEXVALID=0.
        if 'VEXVALID' not in self.constraints:
            self.constraints['VEXVALID'] = {0:True}

        # since we dispatch at the high level on MAP and VEXVALID, we
        # should not include them in the standard constraints.
        self.special_constraints = {}
        for od in ['MAP','VEXVALID']:
            if od in self.constraints:
                self.special_constraints[od] = self.constraints[od]
                del self.constraints[od]

    def _set_vexvalid(self):
        # FIXME: could just look at the pattern...
        lst = list(self.special_constraints['VEXVALID'].keys())
        if len(lst) != 1:
            genutil.die("Not one value for VEXVALID in {}: {}".format(self.iclass, self.ptrn))
        self.vv = int(lst[0])
    def _set_encoding_space(self):
        """returns a string"""
        vv = self.get_vexvalid()
        self.encspace = ild_info.vexvalid_to_encoding_space(vv)
        
    def get_vexvalid(self):
        return self.vv
    def get_encoding_space(self):
        return self.encspace
    
    def set_mode(self, ii, mode_space):
        for bit_info in ii.ipattern.bits:
            if bit_info.token == _mode_token:
                if bit_info.test == 'eq':
                    self.mode = [bit_info.requirement]
                else:
                    reduced_mode_space = copy.deepcopy(mode_space)
                    reduced_mode_space.remove(bit_info.requirement)
                    self.mode = reduced_mode_space
                return
        #when MODE is not mentioned, we assume that any value is
        #legal, it should not mess the conflict resolution.
        self.mode = mode_space

    def parse_opcode(self, op_str):
        # has side effects of settting self.missing_bits and self.incomplete
        val = None
        if genutil.numeric(op_str):
            val = genutil.make_numeric(op_str)

            # special check for partial binary numbers as opcodes
            if genutil.is_binary(op_str):
                bin_str = re.sub('^0b', '', op_str)
                bin_str = re.sub('_', '', bin_str)
                #if it is bin string, it might be incomplete, and we
                #assume that given bits are msb. Hence we have to
                #shift left

                if len(bin_str) > 8:
                    ildutil.ild_err("Unexpectedly long binary opcode: %s" %
                             bin_str)

                if len(bin_str) < 8:
                    self.missing_bits = 8-len(bin_str)
                    val = val << (self.missing_bits)
                    self.incomplete_opcode = True
                    _msg('incomplete opcode for iclass %s, pttrn %s' %
                        (self.iclass, self.ptrn))

        return val


    #if opcode is incomplete, than we have 0's in all the missing bits and
    #need to create copies of the pattern_t that have all other possible
    #variations of the opcode. For example PUSH instruction has opcode 0x50
    #and in expand_partial_opcode method we will create a list of pattern_t objects
    #that have opcodes 0x51-0x57
    #We don't need to create the 0x50 variant, because it already exists
    #(it is the current self)
    #That way we will cover all the legal opcodes for the given incomplete
    #opcode.
    def expand_partial_opcode(self):
        expanded = []
        if self.incomplete_opcode:
            if 'RM[rrr]' in self.ptrn or 'REG[rrr]' in self.ptrn:
                _msg('Expanding opcode for %s' % self.iclass)
                #FIXME: MJC: was assuming hex for self.opcode (2012-06-19)
                opcode = genutil.make_numeric(self.opcode)
                #iterating through all legal variations of the incomplete
                #opcode.
                #Since the variant with all missing bits == 0 was already
                #created (it is the current self), we need to iterate through
                #1 to 2 ^ (self.missing_bits)
                for i in range(1, 2**self.missing_bits):
                    new_ptrn = copy.deepcopy(self)
                    new_ptrn.opcode = hex(opcode | i)
                    expanded.append(new_ptrn)
        return expanded

    def get_opcode(self, tokens):
        opcode = None
        for token in tokens:
            opcode = self.parse_opcode(token)
            if opcode != None:
                break
        if opcode == None:
            ildutil.ild_err("Failed to parse op_str with " +
                            "from tokens %s" %( tokens))
        return hex(opcode)
            
    def _get_map_opcode(self):
        encspace = self.get_encoding_space()
        for mi in pattern_t.map_info_g:
            if mi.space == encspace:
                # if no search pattern we are on the last record  for map 0
                if mi.search_pattern == '' or self.ptrn.find(mi.search_pattern) != -1:
                    insn_map = mi.map_name # different than the stuff we use now.
                    try:
                        opcode = self.ptrn.split()[mi.opcpos]
                    except:
                        genutil.die("Did not find any pos {} in [{}] for {}".format(mi.opcpos,
                                                                                    self.ptrn.split(),
                                                                                    mi))
                    parsed_opcode = self.parse_opcode(opcode)
                    # 0x00 is also a value so we must explicitly test vs
                    # None, and not use "not parsed_opcode"
                    if parsed_opcode==None:  
                        genutil.die("Did failed to convert opcode {} from {} for map {}".format(opcode,
                                                                                                self.ptrn,
                                                                                                mi))
                    return mi, insn_map, hex(parsed_opcode)
        genutil.die("Did not find map / opcode for {}".format(self.ptrn))
                
    def has_emit_action(self):
        ''' This function is needed in order to match the interface of rule_t
            it has no real meaning for the docoder '''
        return False

    def __str__(self):
        printed_members = []
        printed_members.append('ICLASS\t: %s' % self.iclass)
        printed_members.append('PATTERN\t: %s' % self.ptrn)
        #putting map and opcode in one line for easier grepping
        #of the pattern list dump - very handy for different kinds of analysis
        printed_members.append('MAP:%s OPCODE:%s' %
                               (self.insn_map, self.opcode))
        printed_members.append('EXT_OPCODE\t: %s' % self.ext_opcode)
        printed_members.append('MODE\t: %s' % self.mode)
        printed_members.append('INCOMPLETE_OPCODE\t: %s' %
                                self.incomplete_opcode)
        printed_members.append('HAS_MODRM\t: %s' % self.has_modrm)
        printed_members.append('EOSZ_SEQ:\t %s' % self.eosz_nt_seq)
        printed_members.append('EASZ_SEQ:\t %s' % self.easz_nt_seq)
        printed_members.append('IMM_SEQ\t: %s' % self.imm_nt_seq)
        printed_members.append('DISP_SEQ\t: %s' % self.disp_nt_seq)
        
        printed_members.append('CONSTRAINTS\t: {}'.format(self.emit_constraints()))
        printed_members.append('INUM\t: %s' % self.ii.inum)

        return "{\n"+ ",\n".join(printed_members) + "\n}"
    
    def emit_constraints(self):
        sl = []
        for k in self.constraints.keys():
            v = self.constraints[k] # dict with always true-valued items.
            # Only keys of v are relevant.
            s = "{}:{} ".format(k,str(v.keys()))
            sl.append(s)
        return "".join(sl)
        
    def __eq__(self, other):
        return (other != None and
                self.ptrn == other.ptrn and
                self.iclass == other.iclass)

    def __ne__(self, other):
        return (other == None or
                self.ptrn != other.ptrn or
                self.iclass != other.iclass)

def _msg(s):
    debug.write("%s\n" % (s))

