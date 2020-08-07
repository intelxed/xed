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
from __future__ import print_function
import os
import collections

import codegen
import encutil
import genutil
import actions
import verbosity

max_in_byte = 256 #max unsigned int per byte
emit_function_prefix = 'xed_encode_instruction_emit_pattern'
bind_function_prefix = 'xed_encode_instruction_fb_pattern'
get_field_value      = 'xed_encoder_get_start_field_value'

def key_field_binding_lower(x):
    return x.field_name.lower()
    
def sort_field_bindings(a,b):
    ''' sort action_t of type emit '''
    
    if a.field_name.lower() > b.field_name.lower():
        return 1
    elif a.field_name.lower() < b.field_name.lower():
        return -1
    return 0

def key_iform_by_bind_ptrn(x):
    return x.bind_ptrn

 # priority assigned during initial read (see read_encfile.py)
def key_priority(x): 
    return x.priority

def key_rule_length(x):
    return len(x.rule.get_all_emits() + x.rule.get_all_nts())

class instructions_group_t(object):
    ''' each encoding iform has:
        1. conditions ( e.g.REG1=GPRv_r() )
        2. actions, one type of the actions is a nonterminal (nt)
        
        the conditions and the nt's are called "bind patterns".
          
        if two different iclasses have the same bind patterns
        for all of their iforms,
        we can put those iclasses in the same group.
        
        this is what we are doing in _join_iclasses_to_groups 
        '''
    
    def __init__(self,iarray,log_dir):
        self.iclass2group = {}
        self.log_name = 'groups_log.txt'
        self.groups = self._join_iclasses_to_groups(iarray,log_dir)
        
    def _group_good_for_iclass(self,group,iforms):
        ''' Check if the incoming group represents the list of iforms.
        A group represents a list of iforms if:
        1. it has same number of iforms.
        2. for each iform there is an iform in the group that has the same 
           bind pattern
        
        @param group: ins_group_t object
        @param iforms: a list of iform_t 
        
        @return: True if group represents the the ifoms list '''
        
        if len(group.iforms) != len(iforms):
            return False
        for iform,group_iform in zip(iforms,group.iforms):
            if iform.bind_ptrn != group_iform.bind_ptrn:
                return False
        
        return True
            
    def _put_iclass_in_group(self,groups,iclass,instruction_iforms):
        ''' tries to find a group that represents the incoming iclass.
            'represents' means that all the iforms have exactly the same
            bind patterns.
            if no group was found, then create new group for the iclass. 
            
            @param groups: a list of ins_group_t object 
            @param iclass: the iclass name
            @param instruction_iforms: a list of iform_t, the 
                                       iforms of the iclass 
            
            @return: function_object_t '''
        
        for group in groups:
            # check if group represents the iclass
            if self._group_good_for_iclass(group,instruction_iforms):
                group.add_iclass(iclass,instruction_iforms)
                return
        
        #no matching groups
        #create new one 
        group = ins_group_t()
        group.add_iclass(iclass,instruction_iforms)
        groups.append(group)
        return
                 
    def _join_iclasses_to_groups(self,iarray,log_dir):
        '''           
            1. dividing the iclasses into groups.
            2. creating a mapping from iclass to its group Id.
            3. generating a log

            iarray is a dict[iclass] = [iform_t, ...]
            
            return: a list of ins_group_t objects '''
        
        groups = []
        #1. generate the groups
        for iclass,iforms in list(iarray.items()):
            iforms.sort(key=key_iform_by_bind_ptrn)
            self._put_iclass_in_group(groups,iclass,iforms)
        
        # 2. generate the iclass to group Id mapping
        self.iclass2group = {}
        for i,group in enumerate(groups):
            for iclass in group.get_iclasses():
                self.iclass2group[iclass] = i
        
        # 3. print the log
        if verbosity.vencode():
            log_file = os.path.join(log_dir,self.log_name) 
            df = open(log_file,'w') #debug file
            df.write("number of iclasses: %d\n" % len(iarray))
            df.write("number of groups: %d\n" % len(groups))
            for i,group in enumerate(groups):
                df.write("GROUP Id: %d\n" % i)
                df.write("ICLASSES: %s\n" % str(group.get_iclasses()))
                for iform in group.iforms:
                    df.write("%s: %s\n" % ('BIND PATTERN: ', iform.bind_ptrn ))
                df.write("\n\n")

            df.close()     
        return groups
        
    
    def get_groups(self):
        ''' return the groups list ''' 
        return self.groups
    
    def num_groups(self):
        ''' return the number of groups ''' 
        return len(self.groups)
    
    def get_iclass2group(self):
        ''' return a dict of iclass to it group Id'''
        return self.iclass2group
        
    def get_iclass2index_in_group(self):
        ''' return a dictionary of iclass to its index in the group'''
        d = {}
        for group in self.groups:
            iclasses = sorted(group.get_iclasses())
            for i,iclass in enumerate(iclasses):
                d[iclass] = i
        
        return d

def iforms_sort(lst):
    lst.sort(key=key_iform_by_bind_ptrn)
    lst.sort(key=key_rule_length)
    lst.sort(key=key_priority)

    
class ins_group_t(object):
    ''' This class represents one group.
        it holds the list of iclasses that have the same bind patterns.   
    '''
    
    def __init__(self):
        
        # iclass2iforms is a mapping from iclass string to a list of iform_t
        self.iclass2iforms = {}
        
        #  the iforms field is really the iforms of the first iclass
        #  to be added to the group.
        self.iforms = []
        
        self.iclasses = None # instantiated when we call sort()
        
    def add_iclass(self,iclass,iforms):
        ''' add the iclass and iforms list to the group '''
        
        self.iclass2iforms[iclass] = iforms
        if not self.iforms:
            self.iforms = iforms
        
    def get_iclasses(self):
        ''' return a list of iclasses in the group'''
        return list(self.iclass2iforms.keys())

    def get_ith_iforms(self, i):
        '''return  the ith iform in for each iclass'''
        lst = []
        for ifl in self.iclass2iforms.values():
            lst.append(ifl[i])
        return lst
    
    def get_ith_field(self, i, field):
        '''return a list of the specified field from each iform'''
        lst = []
        for ifl in self.iclass2iforms.values():
            lst.append(getattr(ifl[i],field))
        return lst


    def sort(self):
        '''call this before generating code to make sure all agree on order'''
        self.iclasses = sorted(self.get_iclasses())
        for iclass in self.iclasses:
            iforms_sort( self.iclass2iforms[iclass] )
        # this should be sorted by one of the above since it is just a
        # ref to the first list in group...
        # iforms_sort(self.iforms)
    
    def gen_iform_ids_table(self):
        ''' generate C style table of iform Id's.
            the table is 2D. one row per iclass.
            the columns are the different iform Ids '''
        
        table = []
        for iclass in self.iclasses:
            values = []
            for iform in self.iclass2iforms[iclass]:
                values.append('{:4}'.format(iform.rule.iform_id))
            line = "/*{:14}*/ {{{}}},".format(iclass, ",".join(values))
            table.extend([ line ])
            
        return table
    
    def gen_iform_isa_set_table(self, isa_set_db_for_chip):
        '''generate C style table of isa_set info.  The table is 2D. one row
            per iclass.  the columns are the isa_set for that
            iform. The values all_ones and all_zeros are optimizations
            to reduce the amount of encoder code. '''
        
        table = []
        all_ones =  True
        all_zeros = True
        for iclass in self.iclasses:
            values = []
            for iform in self.iclass2iforms[iclass]:
                #s = 'XED_ISA_SET_{}'.format(iform.isa_set.upper())
                s = '1' if iform.isa_set.upper() in isa_set_db_for_chip else '0'
                if s == '0':
                    all_ones = False
                else:
                    all_zeros = False
                values.append(s)
            line = "/*{:14}*/ {{{}}},".format(iclass, ",".join(values))
            table.extend([ line ])
            
        return table, all_ones, all_zeros

    
class instruction_codegen_t(object):
    def __init__(self,iform_list,iarray,logs_dir, amd_enabled=True):
        self.amd_enabled = amd_enabled
        self.iform_list = iform_list
        self.iarray = iarray # dictionary by iclass of [ iform_t ]
        self.logs_dir = logs_dir #directory for the log file
        
        #list of field binding function_object_t
        self.fb_ptrs_fo_list = None
        #list of emit patterns function_object_t
        self.emit_ptrs_fo_list = None
        
        # number of field binding patterns
        self.max_fb_ptrns = None
        # number of emit patterns
        self.max_emit_ptrns = None
        
        # a list of all values been set to field ordered sequentially 
        self.fb_values_list = None
        # the length of fb_values_list 
        self.fb_values_table_size = None
        
        # list of groups (instructions_group_t) 
        self.instruction_groups = None
        
    def get_values(self,encoder_config):
        ''' copy the necessary fields to encoder_confing object  '''
            
        encoder_config.fb_values_list = self.fb_values_list
        encoder_config.fb_values_table_size = self.fb_values_table_size
        
        encoder_config.emit_ptrs_fo_list = self.emit_ptrs_fo_list
        encoder_config.max_emit_ptrns = self.max_emit_ptrns
      
        encoder_config.fb_ptrs_fo_list = self.fb_ptrs_fo_list
        encoder_config.max_fb_ptrns = self.max_fb_ptrns
        
        encoder_config.ins_groups = self.instruction_groups
        
    def _emit_legacy_map(self, fo, iform):
        # obj_str is the function parameters for the emit function
        def _xemit(bits, v):
            fo.add_code_eol('xed_encoder_request_emit_bytes({},{},0x{:02x})'.format(
                encutil.enc_strings['obj_str'], bits, v))

        if iform.legacy_map.legacy_escape != 'N/A':
            bits = 8
            _xemit(bits, iform.legacy_map.legacy_escape_int)
            if iform.legacy_map.legacy_opcode != 'N/A':
                _xemit(bits, iform.legacy_map.legacy_opcode_int)

                
    def _make_emit_fo(self, iform, i):
        ''' create the function object for this emit pattern
             
            @param iform: iform_t object
            @param i: index of the pattern function
            @return: function_object_t 
        '''
        
        fname = "%s_%d" % (emit_function_prefix,i)
        fo = codegen.function_object_t(fname,
                                       return_type='void')
        
        # obj_str is the function parameters for the emit function
        obj_str = encutil.enc_strings['obj_str']
        enc_arg = "%s* %s" % (encutil.enc_strings['obj_type'],
                              obj_str)
        fo.add_arg(enc_arg)
      
        for action in iform.rule.actions:
            # MASSIVE HACK: we store the legacy_map as MAP0 in
            # xed_encode_iform_db[] (obj/xed-encoder-iforms-init.c)
            # for VEX/EVEX/XOP instr (see
            # _identify_map_and_nominal_opcode() ) to avoid emitting
            # any escape/map bytes at runtime.
            if action.field_name == 'MAP':
                if iform.encspace == 0: # legacy
                    genutil.die("Should not see MAP here: {}".format(iform.iclass))
                pass
            elif action.field_name and action.field_name in ['LEGACY_MAP1',
                                                             'LEGACY_MAP2',
                                                             'LEGACY_MAP3',
                                                             'LEGACY_MAP3DNOW']:
                if iform.encspace != 0: # legacy
                    genutil.die("This should only occur for legacy instr")
                self._emit_legacy_map(fo, iform)
                    
            elif action.field_name and action.field_name == 'NOM_OPCODE':
                code = ''
                get_opcode = 'xed_encoder_get_nominal_opcode(%s)' % obj_str
                if action.nbits == 8:
                    emit_func = 'xed_encoder_request_emit_bytes'
                else:
                    emit_func = 'xed_encoder_request_encode_emit'
                code = ' '*4
                code += '%s(%s,%d,%s)' % (emit_func,obj_str,
                                          action.nbits,get_opcode) 
                fo.add_code_eol(code)     
            else:
                code = action.emit_code('EMIT')
                for c in code:
                    fo.add_code(c)
        
        return fo     
    
    def _make_fb_setter_fo(self, iform, i):
        ''' create the function object for pattern of fields bindings 
             
            @param iform: iform_t object 
            @param i: index of the pattern function
            @return: function_object_t 
        '''
        
        fname = "%s_%d" % (bind_function_prefix,i)
        fo = codegen.function_object_t(fname,
                                       return_type='void')
        
        obj_name = encutil.enc_strings['obj_str']
        enc_arg = "%s* %s" % (encutil.enc_strings['obj_type'],
                              obj_name)
        fo.add_arg(enc_arg)
        
        if not iform.fbs:
            #no field binding we need to set, pacify the compiler
            fo.add_code_eol('(void)%s' % obj_name)
            return fo
        
        fo.add_code_eol('    const xed_uint8_t* val')
        fo.add_code_eol('    val = %s(%s)' % (get_field_value, obj_name))
        for i,fb_action in enumerate(iform.fbs):
            value_from_lu_table = '*(val+%d)' % i
            operand_setter = "%s_set_%s" % (encutil.enc_strings['op_accessor'],
                                                fb_action.field_name.lower())
            code = '    %s(%s,%s);' % (operand_setter,
                                obj_name, value_from_lu_table)
            fo.add_code(code)
    
        return fo
    
    def _study_emit_patterns(self):  # FIXME 2019-10-04 unused. was for learning how to fix code
        bins = collections.defaultdict(list)
        bins_alt = collections.defaultdict(list)
        for iform in self.iform_list:
            bins[iform.emit_actions].append(iform)
            bins_alt[iform.emit_actions_alt].append(iform)
            
        print("emit actions bins conventional {}".format(len(bins)))
        print("emit actions bins alternative  {}".format(len(bins_alt)))
        
        for k in bins.keys():
            bin_content = bins[k]
            if len(bin_content)>1:
                alt_set = set()
                for iform in bin_content:
                    alt_set.add(iform.emit_actions_alt)
                if len(alt_set) > 1:
                    print("EXPANDED {}".format(k))
                    for v in alt_set:
                        print("\t {}".format(v))
    
    def _verify_naked_bits_in_unique_pattern(self):  # FIXME 2019-10-04 unused, no longer relevant
        ''' calculate how many references we have per each full
            instruction emit pattern.
        
            naked bits are bits in the pattern without a field name
            like 0x0F or 0b110.  earlier functions decorated
            opcode/legacy map.  

            If the naked bits just show up once, then we can hardcode
            those bits in the emit function. This is a test for that.

            Current design relies on the naked bits being the same in
            similar instruction patterns. If two patterns differ in
            any naked bits, they cannot share emit functions and we die.
            The workaround would be to capture the bits in some field to
            allow the emit function to be shared & generic.

            The current inputs to XED have no such conflicts.
        '''
        refs_per_ptrn = collections.defaultdict(int)
        for iform in self.iform_list:
            refs_per_ptrn[iform.emit_actions] += 1
            if refs_per_ptrn[iform.emit_actions] >= 2:
                if iform.rule.has_naked_bit_action():
                    # this assumes that the naked bits are going to be different.
                    # if the naked bits were the same, we could share the emit action.
                    genutil.die('emit pattern has more than one reference use of naked bits is not allowed: {}\n{}'.format(iform.emit_actions,iform))
                
    
    def _make_emit_pattern_fos(self):
        ''' collect all the different patterns for emit phase.
            for each pattern create a function representing it.
            adds to each rule in iform_t the index of the pattern function
             
            @return: list of emit pattern function name to function object 
        '''
        emit_patterns = {}
        fo_list = []
        i = 0
        
        for iform in self.iform_list:
            if iform.emit_actions not in emit_patterns: 
                fo = self._make_emit_fo(iform,i)
                emit_patterns[iform.emit_actions] = (fo,i)
                fo_list.append(fo)
                iform.emit_func_index = i
                i += 1 
            
            else:
                fo, index = emit_patterns[iform.emit_actions]
                iform.emit_func_index = index 
    
        return fo_list
    
    
    def _make_fb_pattern_fos(self):
        ''' collect all the different patterns for bind phase.
            for each pattern create a function representing it.
            adds to each rule in iform_t the index of the pattern function
             
            @return: list of emit pattern function name to function object 
        '''
        bind_ptterns = {}
        fo_list = []
        i = 0
        
        for iform in self.iform_list:
            if iform.fb_ptrn not in bind_ptterns: 
                fo = self._make_fb_setter_fo(iform,i)
                bind_ptterns[iform.fb_ptrn] = (fo,i)
                fo_list.append(fo)
                iform.bind_func_index = i
                i += 1 
            
            else:
                fo,index = bind_ptterns[iform.fb_ptrn]
                iform.bind_func_index = index 
    
        return fo_list


    def _identify_map_and_nominal_opcode(self,iform):
        ''' scan the list of actions and identify the nominal opcode and 
            the legacy map.
            replace the actions that describe the bytes of the nom opcode 
            and map with dummy action as place holders. 
        '''
        
        #list of all prefixes for a sanity check
        prefixes = [0x66,0x67,0xf2,0xf3,0xf0,0x64,0x65,0x2e,0x3e,0x26,0x36]
        vv = 0 # vex valid value, or 0 if not vex/evex/xop
        first_naked_bits_index = None
        # i is used as an index further down below
        for i,action in enumerate(iform.rule.actions):
            if action.is_field_binding() and action.field_name == 'VEXVALID':
                vv = action.int_value                 # we are in vex valid 1/2/3
                if vv==0:
                    genutil.die("zero-valued vexvalid. this should not happen.")
            if action.naked_bits():
                if vv == 0 and action.int_value in prefixes:
                    genutil.die("LEGACY SPACE PREFIX BYTE SHOULD NOT BE PRESENT: {}".format(iform))
                    # we are in legacy space and this byte is a
                    # prefix.  prefixes should be encoded with operand
                    # deciders, not explicitly.
                    continue
                else:
                    #this byte represents the nominal opcode or the legacy map
                    first_naked_bits_index = i
                    break
                
        
        if first_naked_bits_index == None:
            err = "did not find nominal opcode for iform: %s" % str(iform)
            genutil.die(err)
    
        last_index = len(iform.rule.actions) - 1
        
        # FIXME: i is the same as first_naked_bits_index and they are both used below
        if i != first_naked_bits_index:
            genutil.die("This should not happen")

        first =  iform.rule.actions[first_naked_bits_index]
        ### FIXME:2020-04-17 rewrite the rest of this to be generic
        ### and use dyanmic map information to guide execution.
        if vv:
            # all VEX/EVEX/XOP instr have an explicit map
            
            #this action represents the opcode
            iform.nominal_opcode = first.int_value
            iform.nom_opcode_bits = first.nbits
            iform.rule.actions[i] = actions.dummy_emit(first,'NOM_OPCODE') # replace opcode
        elif first.int_value != 0x0F:  # map 0
            #this action represents the opcode
            iform.nominal_opcode = first.int_value
            iform.nom_opcode_bits = first.nbits
            iform.rule.actions[i] = actions.dummy_emit(first,'NOM_OPCODE') # replace opcode
        
        else: #first byte == 0x0F and we are legacy space
            #check that we have at least one more byte to read
            if first_naked_bits_index+1 > last_index:
                    genutil.die("not enough actions")
            
            second = iform.rule.actions[first_naked_bits_index+1]
            if not second.naked_bits():
                genutil.die("expecting map/nominal opcode after 0x0F byte")
            
            if self.amd_enabled and second.int_value == 0x0F: #3DNow
                # the nominal opcode in 3DNow is in the last action.
                # FIXME: it is best to not reference directly the last action
                #        but rather add a meaningful field name to the action 
                amd3dnow_opcode_action = iform.rule.actions[-1]
                iform.nominal_opcode = amd3dnow_opcode_action.int_value
                iform.nom_opcode_bits = 8
                iform.rule.actions[-1] = actions.dummy_emit(amd3dnow_opcode_action,
                                                            'NOM_OPCODE')
                iform.rule.actions[i] = actions.dummy_emit(first,'LEGACY_MAP3DNOW')  # replace first 0xF
                # the second 0x0F byte that describes the map is not needed, remove it
                iform.rule.actions.remove(second)
                
            elif second.int_value == 0x38 or second.int_value == 0x3A:
                #check that we have at least one more byte to read
                if first_naked_bits_index+2 > last_index:
                    genutil.die("not enough actions")
                
                third = iform.rule.actions[first_naked_bits_index+2]
                if not third.naked_bits():
                    genutil.die("expecting map/nominal opcode after 0x0F byte")
                
                iform.nominal_opcode = third.int_value
                iform.nom_opcode_bits = third.nbits
                if second.int_value==0x38:
                    xmap  = 'LEGACY_MAP2'
                else:
                    xmap  = 'LEGACY_MAP3'
                iform.rule.actions[i+1] = actions.dummy_emit(second,xmap) # replace the 0x38 or 0x3A
                iform.rule.actions[i+2] = actions.dummy_emit(third,
                                                             'NOM_OPCODE')  # replace opcode
                iform.rule.actions.remove(first) # remove the 0x0F
                
            else: # legacy map1 0f prefix only, 2nd byte is opcode
                iform.nominal_opcode = second.int_value 
                iform.nom_opcode_bits = second.nbits
                iform.rule.actions[i] = actions.dummy_emit(first,'LEGACY_MAP1') # replace 0x0F
                iform.rule.actions[i+1] = actions.dummy_emit(second,    # replace opcode
                                                             'NOM_OPCODE')
        
    def _find_sub_list(self,all_fbs_values, fbs_values):
        ''' find the the sub list: fbs_values
            in the list: all_fbs_values.
            
            if not found return -1
            if found return the fist index of the recurrence '''
            
        elems = len(fbs_values)
        indices_to_scan =  len(all_fbs_values) - elems + 1
        for i in range(indices_to_scan):
            if fbs_values == all_fbs_values[i:i+elems]:
                return i
        return -1
        
    
    def _find_fb_occurrence(self,all_fbs_values, fbs_values):
        ''' find the the sub list: fbs_values
            in the list: all_fbs_values.
            
            if fbs_values is not a sub list to all_fbs_values
            concatenate it.
            
            return: the first index of fbs_values occurrence 
                    in all_fbs_values.  
        '''
        
        if not fbs_values:
            return 0
        
        if not all_fbs_values:
            all_fbs_values.extend(fbs_values)
            return  0
        
        index = self._find_sub_list(all_fbs_values,fbs_values)
        if index >= 0:
            # found sub list
            return index
        
        # did not found sub list concatenate to the end
        last_index = len(all_fbs_values)
        all_fbs_values.extend(fbs_values)
        return last_index 
        
    
    def _make_fb_values_list(self):
        ''' generate a list of the values being set by the FB actions.
            for each iform find the start index of the values list. 

            All the field bindings get put in to a linear array.
            This is finds the index in to that array. 

            This is a quick compression technique for sharing trailing
            subsequences. 
            
            e.g.: iform1 sets the values: 0 1 2  (3 fields)
                  iform2 sets the values: 3 4    (2 fields)
                  iform3 sets the values: 1 2    
                  iform4 sets the values: 2 3
                  
                  the ordered list of unique sequence values across
                  all iforms is: 0 1 2 3 4.
                                           
                  start index of iform1: 0  (which picks up 0, 1 2)       
                  start index of iform2: 3  (which picks up 3, 4)
                  start index of iform3: 1  (which picks up 1, 2)
                  start index of iform4: 2  (which picks up 2, 3)

                  Note: because of ordering, if iform3 happens to show
                  up before iform1, they won't share iform1's
                  subsequence 1,2.
            '''
        
        fbs_list = []
        for iform in self.iform_list:
            # collect all the actions that set fields
            iform.fbs = iform.rule.get_all_fbs() 
            iform.fbs.sort(key=key_field_binding_lower) 
            
            # create a list of int values
            fbs_values = [ x.int_value for x in iform.fbs]
            
            #find the start index of this list of values in the general list
            #and update the general list as needed  
            iform.fb_index = self._find_fb_occurrence(fbs_list, fbs_values)
                
        fbs_list = [ str(x) for x in fbs_list]
        return fbs_list
            
            
    def _make_field_bindings_pattern(self,iform):
        ''' create the string that represents the field bindings pattern. '''
            
        bind_actions = []
        for action in iform.rule.actions:
            if action.type == 'nt':
                pass
            elif action.type == 'FB':
                bind_actions.append(action.field_name)
            elif action.type == 'emit':
                if action.emit_type == 'numeric' and action.field_name:
                    bind_actions.append(action.field_name)
                else:
                    pass
            else:
                genutil.die("unexpected action type: %s" % action.type)    
                                  
        fb_ptrn =  ''
        if bind_actions:
            fb_ptrn = ', '.join(sorted(bind_actions))
        iform.fb_ptrn = fb_ptrn

    def _make_emit_pattern(self,iform):
        '''create the string that represents the action for the emit phase.
           using this string we will classify all the emit actions
           into patterns'''

        iform.emit_actions = self._make_emit_pattern_low(iform)
        
    def _make_emit_pattern_low(self,iform):
        emit_pattern = []
        for action in iform.rule.actions:
            if action.type == 'emit':
                # if no field_name, then we must differentiate the
                # emit patterns using the value to avoid collisions.
                if action.field_name == None:
                    emit_pattern.append("emit {} nbits={} intval={}".format(
                        action.field_name,
                        action.nbits,
                        action.int_value))
                else:
                    emit_pattern.append("emit {} nbits={}".format(
                        action.field_name,
                        action.nbits))

            elif action.type == 'nt':
                emit_pattern.append(str(action))
            elif action.type == 'FB':
                # FB are not used in emit phase so we do not factor them 
                # in to the string that represents the pattern
                pass
            else:
                genutil.die("unexpected action type: %s" % action.type)    
        emit_actions_str = ', '.join(emit_pattern)
        return emit_actions_str
        
    def _make_bind_pattern(self,iform):
        ''' create the string that represents the field bindings pattern. '''
            
        bind_ptrn = [ str(iform.rule.conditions) ]
        for action in iform.rule.actions:
            if action.type == 'nt':
                bind_ptrn.append(str(action))
                                  
        iform.bind_ptrn =  ''
        if bind_ptrn:
            iform.bind_ptrn = ', '.join(bind_ptrn)
              
    def _print_log(self):
        print("---- encoder log ----")
        for i,iform in enumerate(self.iform_list):
            print("%d\n" % i)
            print("IFORM: %s" % str(iform))
            print("iform index: %d" % iform.rule.iform_id)
            bind_index = iform.bind_func_index
            bind_fo = self.fb_ptrs_fo_list[bind_index]
            print("BIND function: %d, %s" % (bind_index,
                                             bind_fo.function_name))
            emit_index = iform.emit_func_index
            emit_fo = self.emit_ptrs_fo_list[emit_index]
            print("EMIT function: %d, %s" % (emit_index,
                                             emit_fo.function_name))
            
            print("NOM_OPCODE: %d" % iform.nominal_opcode)
            fbs_values = [ x.int_value for x in iform.fbs]
            print("FB values: %s" % fbs_values)
            print("\n\n")
            print("-"*20) 
    
    def work(self):  # main entry point
        ''' 
            Each instruction has 
                1) conditions (iclass, user registers, user inputs) and 

                2) actions. 3 types:
                   2a) field bindings, 
                   2b) nonterminals, 
                   2c) bit-emit of operand fields 
                          (hard-coded or from NT output)).

              fos = function output object (plural)

            generate the following:
            1) list of emit patterns fos  (2c)
            2) list of field bindings patterns fos (2a)
            3) list of all field bindings values  (values from prev step)
            4) max number of emit patterns  
            5) max number of field binding patterns
            6) max number of field bindings values
            7) list of groups fos (see explanation in instructions_group_t)
            
        '''
        
        for iform in self.iform_list:
            self._identify_map_and_nominal_opcode(iform)
            self._make_field_bindings_pattern(iform)
            self._make_emit_pattern(iform)
            #see explanation about bind patterns in instructions_group_t
            self._make_bind_pattern(iform)  

        #self._study_emit_patterns()
        #self._verify_naked_bits_in_unique_pattern()
        
        self.fb_values_list = self._make_fb_values_list() # step 3
        self.fb_values_table_size = len(self.fb_values_list)
        
        self.emit_ptrs_fo_list = self._make_emit_pattern_fos()
        self.max_emit_ptrns = len(self.emit_ptrs_fo_list)
        if self.max_emit_ptrns > max_in_byte:
            # we are using uint8 to hold the number of patterns,
            # we need to make sure we don't exceeds 
            error = "total number of emit patterns(%d) exceeds 8 bits"
            genutil.die(error % self.max_emit_ptrns)
            
        self.instruction_groups = instructions_group_t(self.iarray,
                                                       self.logs_dir)
        
        self.fb_ptrs_fo_list = self._make_fb_pattern_fos()
        self.max_fb_ptrns = len(self.fb_ptrs_fo_list)
        if self.max_fb_ptrns > max_in_byte:
            # we are using uint8to hold the number of patterns,
            # we need to make sure we don't exceeds
            error = "total number of field binding patterns(%d) exceeds 8 bits"
            genutil.die(error % self.max_fb_ptrns)

        if verbosity.vencode():
            self._print_log()   
    
    
    

        
        
        
        
        
            
            
        
        
               
