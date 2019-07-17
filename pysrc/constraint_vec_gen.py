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
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL
from __future__ import print_function
import copy
import genutil 
import encutil

class constraint_vec_gen_t(object):
    '''this class receives and list of rules and creates:
    (a) tuples that represents each constraint.
    (b) the int value of each tuple.
    (c) log 
    '''
    def __init__(self,state_space,op_widths,rules,nt_name,default_action,log):
        self.state_space = state_space
        self.op_widths = op_widths
        self.rules = rules
        self.nt_name = nt_name
        self.default_action = default_action
        self.log = log
        self.tuple2rule = {}
        self.tuple2int = {}
        self.tuple2conditions = {}
        self.int2tuple = {}
        
    def work(self):
        self.cnames = self._capture_cnames()    
        self._make_tuple2rule()
        self._gen_tuple2int()
        self.strings_dict = encutil.enc_strings
    
    def _capture_cnames(self):
        ''' capture the superset of all constraint names '''  
        
        if not self.rules:
            return []
        
        cnames = set()
        for rule in self.rules:
            cnames.update(set(rule.cdict.keys()))
        cnames = list(cnames)
        cnames.sort()
        if not cnames:
            msg = "XED found rules without any constraints in nt %s"
            genutil.die(msg  % self.nt_name)
        return cnames
    def _make_tuple2rule(self):
        ''' generate the tuple that represents the constraint
            e.g.: for the constraint: MODE=0 EASZ=1
            the tuple is (0,1) 
            if a rule does not have constraint over certain operand then 
            we splatter all the possible values '''
        verbose=False
        if verbose:
            print("_make_tuple2rule")
        for rule in self.rules:
            #print "\t RULE", str(rule)
            # ctup is a list of tuples of all possible value
            # combinations for the constraints.
            ctup = [] 
            first = True
            for cname in self.cnames:
                if verbose:
                    print("CNAME: {}".format(cname))
                new_ctup = []
                if cname in rule.cdict:
                    vals = rule.cdict[cname]
                    if verbose:
                        print("\tTHIS RULE VALS: {}".format(vals))
                else:
                    vals = self.state_space[cname]
                    if verbose:
                        print("\tSTATE SPACE VALS: {}".format(vals))
                if first:
                    first = False    
                    for val in vals:
                        ctup.append((val,))
                    if verbose:
                        print("\tFIRST CTUP: {}".format(ctup))
                    continue    
                else:  
                    # cross product of constraints
                    for val in vals:
                        for c in ctup:
                            new_ctup.append(c+(val,))
                if verbose:
                    print("\tNEW_CTUP: {}".format(new_ctup))
                ctup = new_ctup
            for tupl in ctup:
                if tupl not in self.tuple2rule:
                    if verbose:
                        print("TUPLE: {} RULE: {}".format(tupl, rule))
                    self.tuple2rule[tupl] = rule
                    self.tuple2conditions[tupl] = rule.conditions
                else:
                    err = "in nt {}\n".format(self.nt_name)
                    err += "generated tuple for constraint {} already exists\n"
                    err =  err.format(str(rule.cdict))
                    if verbose:
                        print(err)
                    genutil.die(err)
            
    def _gen_tuple2int(self):
        ''' generate the int value of each tuple. 
            we shift each element by the number of bits that the previous 
            element took '''
        
        for tuple in self.tuple2rule:
            res = 0
            bit_shift = 0
            for i,byte in enumerate(tuple):
                if self.cnames[i] == 'UIMM0':
                    pass
                opwidth = self.op_widths[self.cnames[i]]
                res += byte << bit_shift
                bit_shift += opwidth
             
            if res not in self.int2tuple:
                self.tuple2int[tuple] = res
                self.int2tuple[res] = tuple
            else:
                conflict_tuple = self.int2tuple[res]
                err = "conflict in nt: %s\n" % self.nt_name
                err += "tuple      %s = %s\n" 
                err =err % (str(tuple),self.tuple2conditions[tuple]) 
                err += "and tuple: %s = %s\n" 
                err =err % (str(conflict_tuple),
                            self.tuple2conditions[conflict_tuple])
                err += "generate the same int value: %d" % res
                genutil.die(err)
                 
    def filter_tuples(self,tuples):
        ''' create new cvg that contains only the tuples in the input  '''
        
        new_cdict = copy.copy(self)
        new_cdict.tuple2rule = {}
        new_cdict.tuple2int = {}
        new_cdict.tuple2conditions = {}
        for t in tuples:
            new_cdict.tuple2rule[t] = self.tuple2rule[t]
            new_cdict.tuple2int[t] = self.tuple2int[t]
            new_cdict.tuple2conditions[t] = self.tuple2conditions[t]
        
        
        new_cdict.int2tuple = dict((i,t) for t,i in 
                                   new_cdict.tuple2int.items())
        
        return new_cdict
    
    def dump_log(self):
        log =  "nonterminal: %s\n" % self.nt_name
        log += "cnames: %s\n" % str(self.cnames)
        log += "{0:5} {1:15} {2}\n".format('int','tuple','conditions')
        for val,tuple in sorted(self.int2tuple.items()):
            log += "{0:<5} {1:<15} {2}\n".format(val, tuple, 
                                                 self.tuple2conditions[tuple])
        log += "------------------------------------------------------------\n" 
        self.log.write(log) 
         
    def no_constraints(self):
        ''' return True if there are no constraints '''
        return len(self.tuple2conditions) == 0
    
    def get_operand_accessor(self, cname):
        ''' return the full function in order to access the operand given 
        in cname '''
        str = "%s_get_%s(%s)" % (self.strings_dict['op_accessor'],cname.lower(), 
                                 self.strings_dict['obj_str'])
        return str, cname
    
    def get_ptrn(self, tuple):
        ''' return the pattern for the give tuple '''
        return self.tuple2rule[tuple]

