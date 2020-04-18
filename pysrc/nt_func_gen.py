#!/usr/bin/env python
# -*- python -*-
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
#  distrtibuted under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL

# encoder generator support

import os
import copy

import refine_regs
import genutil
import constraint_vec_gen
import func_gen
import actions

_xed_reg_invalid = 'XED_REG_INVALID'
# those operand are very wide but the real values they may have are few
# specifying here the valid values for the operands and the number bits
# needed to represent each one  
_valid_width = {'BRDISP_WIDTH' :[8, 16, 32],
                'DISP_WIDTH'   :[0, 8, 16, 32, 64],
                'IMM_WIDTH'    :[8, 16, 32, 64],
                }
_width_bits = {'BRDISP_WIDTH' :6,
                'DISP_WIDTH'  :7,
                'IMM_WIDTH'   :7,
               }

#FIXME:2020-04-18 (not used, see below variable references)
_vexpfx_vals = [0xc4, 0xc5, 0x62]
_vexpfx_bits = 8

'''
the tables for this nt are too complex to be generated using hash functions
and look up tables.
they are generated in the old style (if statement)
'''
_complicated_nt = ['SIB_REQUIRED_ENCODE','VMODRM_MOD_ENCODE', 'REX_PREFIX_ENC',
                   'PREFIX_ENC','VEX_TYPE_ENC']
                   
def get_complicated_nt():
    return _complicated_nt                    

class nt_function_gen_t(object):
    def __init__ (self,enc_config, storage_fields):
        self.nonterminals = enc_config.nonterminals
        self.decoder_ntlufs = enc_config.decoder_ntlufs
        self.decoder_nonterminals = enc_config.decoder_nonterminals
        self.storage_fields = storage_fields
        self.functions = []
        self.operand_lu_fos = []
        
        self.vec_gen_log = open(
            os.path.join(enc_config.gendir,'nt_function_log.txt'),
            'w')
        
        regs_file = enc_config.files.regs_input_file
        self.reg2int, max_gprs_bits = self._gen_regs_dict(regs_file)
        self.state_space,self.ops_width = self._gen_state_space(max_gprs_bits)
    
    def _is_reg_type(self,field_name):
        ''' check if the field name represents a reg type '''
        
        if field_name not in self.storage_fields:
            return False 
        ctype = self.storage_fields[field_name].ctype
        return ctype == 'xed_reg_enum_t'

    def _cond_is_UIMM0_1(self,cond):
        ''' check whether the condition is UIMM0=1.
            die if the operand is UIMM0 but the value is different than 1'''
        if cond.field_name == 'UIMM0':
            if cond.rvalue.value == '1':
                return True
            else:
                #the operand is UIMM0 but the value is not 1
                err= ('not expecting UIMM0 will have any other constraint '+ 
                      'other than UIMM0=1')
                genutil.die(err)
        return False
    
    def _replace_UIMM0_1_cond(self):
        ''' if the condition is UIMM0=1 we replace it with UIMM0_1=1
            UIMM0_1 represent the accessor that compares the value 
            of UIMM0 to 1.'''
        return 'UIMM0_1'
             
    def _build_constraint(self, nonterminal):
        '''
        build a dict that represents the values that the operands can have.
        e.g.
        for the constraint EASZ=3 MODE!=3
        the cdict is {EASZ:[3],MODE:[0,1,2]}
        '''
        
        for rule in nonterminal.rules:
            constraints = {}
            for cond in rule.conditions.and_conditions:
                key = cond.field_name
                if cond.equals:
                    if cond.rvalue.null():
                        constraints[key] = [self.reg2int[_xed_reg_invalid]]
                    elif cond.rvalue.any_valid():     
                        #will be gathered later
                        continue
                    else:
                        if self._cond_is_UIMM0_1(cond):
                            key = self._replace_UIMM0_1_cond()
                        val = cond.rvalue.value
                        if self._is_reg_type(key):
                            constraints[key] = [self.reg2int[val]]
                        else:
                            constraints[key] = [genutil.make_numeric(val)]
                else:
                    #we have != condition, we need to calculate all the 
                    #possible values based on the width of the field and remove 
                    #the the unwanted value.
                    #need to deep copy since we modify the list, and we want 
                    #to preserve the original 
                    all_vals = list(copy.deepcopy(self.state_space[key]))
                    val = genutil.make_numeric(cond.rvalue.value)
                    all_vals.remove(val)
                    constraints[key] = all_vals
            rule.cdict = constraints 
        
    def _encoder_preferred(self, rules):
        ''' returns the rule that has the attribute enc_prefered '''
               
        for rule in rules:
            if rule.enc_preferred:
                return rule
        return []
    
    def _unite_rules(self,nonterminal):
        ''' removing rules with identical constraints.
        if more than one rule has that same constraint then one of them must 
        be marked as encoder preferred.
        
        bucketing the rules, each bin represents unique constraint. 
        we go over each bin, if it has more than one rule, 
        we look for the attribute enc_preferred   '''
        
        rules_bin = []
        for rule in nonterminal.rules:
            found = False
            for bin in rules_bin:
                if bin[0].cdict == rule.cdict:
                    bin.append(rule)
                    found = True
                    break
            if not found:        
                rules_bin.append([rule])
        
        rules = []
        for bin in rules_bin:
            if len(bin) > 1:
                preferred_rule = self._encoder_preferred(bin)
                if preferred_rule:
                    rules.append(preferred_rule)
                else:
                    err = "in nt %s several rules has the constraint: %s\n"
                    err += "one of them must be marked as encoder preferred\n"
                    genutil.die(err % (nonterminal.name,bin[0].conditions))
            else:
                rules.extend(bin)
        return rules

    def _gen_ntluf(self,nonterminal):
        '''create the constraint dictionary and call the function generator''' 

        self._build_constraint(nonterminal)
        rules = self._unite_rules(nonterminal)
        cvg = constraint_vec_gen.constraint_vec_gen_t(self.state_space, 
                                                     self.ops_width, rules, 
                                                     nonterminal.name,
                                                     nonterminal.otherwise,
                                                     self.vec_gen_log)
        
        
        #FIXME: temporary hack, the ild_phash is generic and does not aware 
        #whether it handles decoder or encoder.
        #currently we need to know this, need it till we finish the iform 
        #encoding   
        if nonterminal.is_ntluf():
            cvg.ntluf = True
        else:
            cvg.nt = True    
        cvg.work()
        
        raw_name = nonterminal.name
        
        if nonterminal.is_ntluf():
            func_name = "%s_%s" % ("xed_encode_ntluf",raw_name)     
        else:
            func_name = "%s_%s_%s" % ("xed_encode_nonterminal",raw_name,"BIND")
                
        function_gen = func_gen.func_gen_t(cvg,func_name)
        #this builds the hash tables
        fos, operand_lu_fo = function_gen.gen_function()
        return fos, operand_lu_fo
        
    def _add_op_lu_fo(self,operand_lu_fo):
        ''' check if the function already exists in the functions list.
        if exists do nothing
        if not add it to the list of all the functions '''
        if operand_lu_fo == None:
            return 
        fname = operand_lu_fo.function_name
        for fo in self.operand_lu_fos:
            if fname == fo.function_name:
                return
        self.operand_lu_fos.append(operand_lu_fo)
    
    def _gen_default_action(self,nts):
        ''' add to to each nonterminal the default action that should be taken
        in case the no rule was satisfied '''
        
        for nt in nts:
            if nt.otherwise == 'error':
                err_fb = 'ERROR=XED_ERROR_GENERAL_ERROR'
                nt.default_action = actions.action_t(err_fb)
            else:
                #creating return action which return nothing
                nt.default_action = actions.gen_return_action('')

    def gen_nt_functions(self):
        nonterminals = (list(self.nonterminals.values()) + 
                       list(self.decoder_nonterminals.values()) +  
                       list(self.decoder_ntlufs.values()))
        
        for nt in nonterminals:
            if nt.name in _complicated_nt:
                continue

            fos, operand_lu_fo = self._gen_ntluf(nt)
            self.functions.extend(fos)
            if operand_lu_fo:
                self._add_op_lu_fo(operand_lu_fo)
        
        self.vec_gen_log.close()
        return self.functions, self.operand_lu_fos
            
    def _check_duplications(self,regs):
        ''' n^2 loop which verifies that each reg exists only once.  '''
        
        for reg in regs:
            count = 0
            for r in regs:
                if reg == r:
                    count += 1
            if count > 1:
                genutil.die("reg %s defined more than once" % reg)        
   
    
    def _gen_regs_dict(self,regs_file):
        ''' creates a dictionary of reg->int_value
            this imitates the reg_enum_t that is created in the generator  '''
        
        f = genutil.base_open_file(regs_file,"r","registers input")
        lines = f.readlines()
        # remove comments and blank lines
        # regs_list is a list of reg_info_t's
        regs_list = refine_regs.refine_regs_input(lines)

        #sort the regs by their groups
        reg_list_enumer_vals = refine_regs.rearrange_regs(regs_list)
        
        #we do not need to the PSEUDO regs since 
        #they are not in use by the encoder
        tmp = list(filter(lambda x: not x.in_comment('PSEUDO'), reg_list_enumer_vals))
        regs = [  x.name for x in  tmp]

        
        #put XED_REG_INVLAID in the beginning
        regs.remove('INVALID')
        ordered_regs = ['INVALID']
        ordered_regs.extend(regs)
        
        #add XEG_REG_ prefix
        full_reg_name = [  'XED_REG_' + x for x in  ordered_regs]
        
        self._check_duplications(full_reg_name)
        reg2int = {}
        for i,reg in enumerate(full_reg_name):
            reg2int[reg] = i
        
        max_reg = len(regs_list) - 1
        import math
        
        #calculate how many bits we need to represent 
        #the max int value of the regs
        bits_width = int(math.floor(math.log(max_reg,2))) + 1 
        return reg2int, bits_width  
         
    def _gen_state_space(self, max_gprs_bits):
        ''' max_gprs_bits is the number of bits needed to represent 
        all the registers that are generated by xed (xed_reg_enum_t), 
        calculated in _gen_regs_dict
        
        generating two dictionaries
        op_space: mapping from operand to its possible values
        op_width: mapping from operand to the number of bits needed 
                  to represent it '''
        op_space = {}
        op_width = {}
        for field in self.storage_fields:
            if self.storage_fields[field].ctype == 'xed_reg_enum_t':
                #do not specifying the space of the regs since it is enormous
                #do not want any one to use it  
                op_width[field] = max_gprs_bits
            else:
                if 'WIDTH' in field:
                    if field in _valid_width:
                        op_space[field] = _valid_width[field]
                        op_width[field] = _width_bits[field]
                    else:
                        #this field is in use by the encoder
                        continue    
                elif 'VEXPFX_OP' == field:
                    # FIXME: 2020-04-18 NOT USED -- remove...
                    op_space[field] = _vexpfx_vals
                    op_width[field] = _vexpfx_bits
                elif field in ['DISP','BRDISP','UIMM0']:
                    # those operands are not used by the encoders nonterminals
                    # they are very wide and specifying the range of valid 
                    # values for them is not needed and chokes python
                    # FIXME: could add a column to the filed data file for this 
                    pass
                else:
                    bits = self.storage_fields[field].bitwidth
                    op_space[field] = range(2**bits)
                    op_width[field] = bits 
        
        # adding artificial operands 
        op_space['UIMM0_1'] = [0,1]
        op_width['UIMM0_1'] = 1
        return op_space,op_width
    
                
               
