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

import actions

class actions_codegen_t(object):
    ''' This file is about:
    (a) examining the actions that we'll do after hashing. 
    Some actions may be conditional and this creates valid indicators for the 
    conditional bindings.
    (b) printing the values of the actions for the hash table initialization. 
    (c) printing the conditional initialization of the xed fields after 
    successful hashing. Including calling other functions and returning values.
    '''
    def __init__(self, tuple2rule, default_actions, strings_dict):
        ''' params: tuple2rule: is a mapping from tuple to a rule
                    default_actions is a list action when we do not hit 
                        a valid hash entry
                    strings_dict a is mapping of (generic) strings 
                        to specific string (type refinement, etc) for codegen'''
        self.all_fbs = None
        self.common_fbs = None
        self.max_nt_number = 0
        self.tuple2rule = tuple2rule
        self.default_actions = default_actions    
        self.strings_dict = strings_dict
        
        #this is a mapping from a tuple to a lost of action_t objects
        self.tuple2actions = self._preprocess(tuple2rule)
        
    def _gather_all_fb(self, rules):
        ''' returns a tuple of:
        (1) the super set of all the field binding
        (2) the intersection of all the fb 
        '''
        if len(rules) == 0:
            return ([], [])
        
        #create a bin of fbs, one entry per rule 
        fbs_bin = []
        for rule in rules:
            rule_fbs = set()
            for action in rule.actions:
                if action.is_field_binding():
                    rule_fbs.add(action.field_name.lower())
            fbs_bin.append(rule_fbs)
            
        
        all_fbs = set()
        common_fbs = fbs_bin[0]
        for xbin in fbs_bin:
            all_fbs.update(xbin)
            common_fbs.intersection_update(xbin)
        
        return sorted(all_fbs), common_fbs
    
    def _get_max_nt_number(self, rules):
        ''' find the maximal number of nt and ntlus among all the rules'''
        nts_per_rule = []
        ntlufs_per_rule = []
        for rule in rules:
            nts = 0
            ntlufs = 0
            for action in rule.actions:
                if action.is_nonterminal():
                    nts += 1
                if action.is_ntluf():
                    ntlufs += 1    
            nts_per_rule.append(nts)
            ntlufs_per_rule.append(ntlufs)
        
        if nts_per_rule:
            return max(nts_per_rule), max(ntlufs_per_rule)
        return 0,0
    
    def _create_ntluf_actions(self, action_list):
        '''  return a list of all the ntluf actions  '''
        i = 0
        ntluf_list = []
        for action in action_list:
            if action.is_ntluf():
                if i < self.max_ntluf_number:
                    ntluf_list.append(action)
                else:
                    genutil.die('currently do not support unequal \
                                number of ntluf among all the rules')
                i += 1    
        #adding null pointer values to the actions list so all the rules will 
        #have the same number of actions 
        while i < self.max_ntluf_number:
            nt_list.append(actions.gen_null_fb())
            i += 1

        return ntluf_list
    def _create_nt_actions(self, action_list):
        '''  return a list of all the nt actions  '''
        i = 0
        nt_list = []
        for action in action_list:
            if action.is_nonterminal():
                if i < self.max_nt_number:
                    nt_list.append(action)
                else:
                    genutil.die('currently do not support unequal number of \
                                nt among all the rules')
                i += 1    
        #adding null pointer values to the actions list so all the rules will 
        #have the same number of actions 
        while i < self.max_nt_number:
            nt_list.append(actions.gen_null_fb())
            i += 1
                    
        return nt_list
                

    def _create_fb_actions(self, all_fbs, common_fbs, rule):
        ''' creates a list fb actions for the given rule.
        in case the given rule does not have an action for some fb in the  
        all_fbs list, we add a dummy action node '''
        
        fbs = all_fbs
        fb_list = []
        for fb_name in fbs:
            fb_found = False
            for action in rule.actions:
                if action.is_field_binding() and \
                    action.field_name.lower() == fb_name:
                    fb_found = True
                    fb_list.append(action)
            
            if not fb_found:
                #the rule does not have action for this fb, creating a dummy 
                #node for it
                fb_list.append(actions.gen_dummy_fb(fb_name))
                        
        return fb_list
                        
    def _get_return_action(self, actions):
        ''' find a return action and return it '''
        for action in actions:
            if action.is_return():
                return [action]
        return []
    
    def _has_emit(self, rules):
        ''' returns True if one of the rules has emit action'''

        for rule in rules:
            if rule.has_emit_action():
                return True
        return False
    
    def _preprocess(self, tuple2rule):
        ''' generates the following information:
        (1) the super set of all the field bindings among the rules
        (2) the intersection of the fb.
        (3) the max number of nonterminal functions
        (4) if we have a 'return' action
        (5) a mapping from tuple to a list of all the actions that were 
        captured '''
        tuple2actions = {}
         
        rules = list(tuple2rule.values())
        self.rules = rules
        self.all_fbs, self.common_fbs = self._gather_all_fb(rules)
        self.max_nt_number, self.max_ntluf_number = self._get_max_nt_number(rules)
        self.ret_action = False
        self.has_emit = self._has_emit(rules)
        
        for tupl, rule in tuple2rule.items():
            actions = self._create_fb_actions(self.all_fbs, self.common_fbs, rule)
            nts = self._create_nt_actions(rule.actions)
            ntlufs = self._create_ntluf_actions(rule.actions)
            ret_action = self._get_return_action(rule.actions)
            if ret_action:
                self.ret_action = True
            tuple2actions[tupl] = actions + nts + ntlufs + ret_action
         
            
        return tuple2actions
    
    def get_actions_desc(self):
        ''' returns the description of the action types '''
        desc = []
        for fb in self.all_fbs:
            desc.append("%s %s" % (self.strings_dict['fb_type'], fb))
        for i in range(self.max_nt_number):
            desc.append("%s ntptr%d" % (self.strings_dict['nt_fptr'], i))  
        for i in range(self.max_ntluf_number):
            desc.append("%s ntlufptr%d" % (self.strings_dict['ntluf_fptr'], i))    
        if self.ret_action:
            desc.append("%s value" % self.strings_dict['return_type'])
        if self.has_emit:
            desc.append("%s emit" % self.strings_dict['return_type'])    
        
        if desc:    
            return " ;".join(desc) + ";"
        return ""
    
    def no_actions(self):
        ''' returns True if there is no actions, of any kind.
            returns False if there is at least one action '''
        if self.all_fbs or self.common_fbs or self.max_nt_number or \
           self.max_ntluf_number or self.ret_action or self.has_emit:
            return False
        return True

    def get_values(self, tuple):
        ''' return the values of the actions for the specific given tuple'''
        action_vals = [] 
        
        actions_list = self.tuple2actions[tuple]
        for action in actions_list:
            val = action.get_str_value()
            if action.is_nonterminal():
                val = "%s_%s_BIND" % (self.strings_dict['nt_prefix'],val)
            if action.is_ntluf():
                val = "%s_%s" % (self.strings_dict['ntluf_prefix'],val)    
            action_vals.append(val)
        
        if self.has_emit:
            if self.tuple2rule[tuple].has_emit_action():
                hash_index = self.tuple2rule[tuple].index
                action_vals.append(str(hash_index))
            else:    
                action_vals.append('0')
        values = ",".join(action_vals)
        return values      

    def emit_actions(self):
        ''' dump the code that executes the actions '''
        
        actions_list = []
        fb_template = "%s_set_%s(%s,%s)"
        hash_entry = "%s[%s].%s" 
        
        #dump the code for the fb
        for fb in self.all_fbs:
            hash_val = hash_entry % (self.strings_dict['table_name'],
                                     self.strings_dict['hidx_str'], fb)
            action = fb_template % (self.strings_dict['op_accessor'],
                                    fb, self.strings_dict['obj_str'], hash_val)
            
            if fb not in self.common_fbs:
                #we need to add fb validation
                validation = "if(%s >= 0) " % hash_val
                action = validation + action
            actions_list.append(action)
        
        #dump the code for the nonterminal
        for i in range(self.max_nt_number):
            fptri = "ntptr%d" % i
            hash_val = hash_entry % (self.strings_dict['table_name'],
                                  self.strings_dict['hidx_str'], fptri)
            validation = "if(%s != 0) " % hash_val
            f_call = "res=(*%s)(%s)" % (hash_val, self.strings_dict['obj_str'])
            actions_list.append(validation + f_call)
            
            nt = list(self.tuple2rule.values())[0].nt
            obj_str = self.strings_dict['obj_str']
            emit_call = "xed_encoder_request_iforms(%s)->x_%s=hidx+1"
            actions_list.append(emit_call % (obj_str,nt))
               
        #dump the code for the ntluf
        for i in range(self.max_ntluf_number):
               fptri = "ntlufptr%d" % i
               hash_val = hash_entry % (self.strings_dict['table_name'],
                                     self.strings_dict['hidx_str'], fptri)
               validation = "if(%s != 0) " % hash_val
               f_call = "res=(*%s)(%s,%s)" % (hash_val, self.strings_dict['obj_str'], 'arg_reg')
               actions_list.append(validation + f_call)
        #dump the return code
        if self.ret_action:
            ret_str = "return %s[%s].value" % (self.strings_dict['table_name'],
                                                self.strings_dict['hidx_str'])
            actions_list.append(ret_str)    
        
        #dump the emit action
        if self.has_emit:
            nt = list(self.tuple2rule.values())[0].nt
            obj_str = self.strings_dict['obj_str']
            emit_call = "xed_encoder_request_iforms(%s)->x_%s=%s"
            hash_entry =  "%s[%s].emit" % (self.strings_dict['table_name'],
                                           self.strings_dict['hidx_str'])
            actions_list.append(emit_call % (obj_str,nt,hash_entry))
        return actions_list
    
    def _has_return_stmt(self):
        ''' we assume it is enough to check only the first rule, since if 
        on rule has return stmt than all the rules will have one ''' 
        for action in self.rules[0].actions:
            if action.is_return():
                return True
        return False
    
    def get_return_type(self):
        ''' get the c type of the return action ''' 
        if self._has_return_stmt():
            return self.strings_dict['return_type'] 
        return 'void' 
        
    def emit_default(self):
        ''' emit the action taken when we did not hit a valid hash table entry
        '''
        actions = []
        for action in self.default_actions:
           if action.is_return():
               s =  "return %s" % action.get_str_value()
               actions.append(s)
           if action.is_field_binding():
               val = action.get_str_value()
               fb = action.field_name.lower()
               s = "%s_set_%s(%s,%s)" % (self.strings_dict['op_accessor'], fb,
                                         self.strings_dict['obj_str'], val)
               actions.append(s)
                
        return actions
            
    def get_empty_slots(self):
        ''' return a list of the empty slots that will be used in the lu table 
        whenever we do not have a valid hash entry '''
        slots_num = 0
        slots_num += len(self.all_fbs)
        slots_num += self.max_nt_number
        slots_num += self.max_ntluf_number
        # FIXME: the ret_action seems like the only thing that matters
        # for the decoder
        if self.ret_action:
            slots_num += 1
        if self.has_emit:
            slots_num += 1
        return ['0'] * slots_num
        
    def has_fcall(self):
        return self.max_nt_number > 0 or self.max_ntluf_number > 0    


    
