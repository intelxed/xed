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


import codegen
import ild_phash
import actions_codegen
import verbosity
import genutil


class func_gen_t(object):
    def __init__(self,cvg, fname):
        self.cvg = cvg # constraint vector generator
        self.fname = fname
    
    def _gen_empty_function(self,fname):
        ''' generate a function without constraints  '''
        
        return_type = 'xed_uint32_t'
        fo = codegen.function_object_t(fname,
                                       return_type=return_type,
                                       static=False,
                                       inline=False)

        obj_type = self.cvg.strings_dict['obj_type']
        obj_str =  self.cvg.strings_dict['obj_str']
        arg = "%s* %s" % (obj_type, obj_str)
        fo.add_arg(arg)
        
        lines = self.cvg.action_codegen.emit_default()
        for line in lines:
            if line == 'return ':
                fo.add_code_eol('return 1')
            else:
                fo.add_code_eol(line)
        fo.add_code_eol('(void)%s' % obj_str)
        fo.add_code_eol('return 1')
        return fo

    def gen_function(self):
        ''' returns tuple of:
        1) list functions (we can have several functions in case we 
            need to levels of hashing)
        2) the operands lookup function (generates the key)        
        '''
        action_codegen = actions_codegen.actions_codegen_t(self.cvg.tuple2rule,
                                                       self.cvg.default_action,
                                                       self.cvg.strings_dict)
        self.cvg.action_codegen = action_codegen

        if self.cvg.no_constraints():
            fo = self._gen_empty_function(self.fname)
            return [fo], None
        
        phash = ild_phash.gen_hash(self.cvg)
        if phash == None:
            genutil.die("Failed to find perfect hash for %s" % self.fname)
        if verbosity.vfuncgen():
            self.cvg.log.write("%s" % phash)

        fos, operand_lu_fo = phash.gen_find_fos(self.fname)
        return fos, operand_lu_fo
        
        
        
        
        

        
        
        
    
            
        
        
    
                
        
            
            
        
     
