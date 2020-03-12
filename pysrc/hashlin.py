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

import xedhash
   
class linear_func_t(xedhash.hash_fun_interface_t):
    ''' This function is used when the keys are sequential '''
    def __init__(self,k,max_key):
        ''' @param k: the lowest key in the range
            @param max_key: the highest key in range 
        '''
    
        self.k = k
        self.max_key = max_key - k     #used for range validation
        #total number of keys, used for lu table creation
        self.m = self.max_key + 1   
    def kind(self):
        return "linear"
    def get_table_size(self):
        return self.m

    def apply(self, x):
        return x - self.k
    def emit_cexpr(self, key_str='key'):
        return "%s - %d" % (key_str,self.k) 
    def need_hash_index_validation(self):
        ''' the linear function does not need to do hash index validation since 
            it does not do hashing'''
        return False
    def add_key_validation(self,strings_dict):
        hidx_str = strings_dict['hidx_str']
        if self.max_key == 0:
            # 2016-07-28 Added an equality test to remove bogus
            # warnings from klocwork (KW) about negative numbers after
            # subtraction on 1-entry hash tables. Many of the linear
            # hashes have one entry and this removes a bunch of
            # completely inappropriate warnings from the frequently
            # stupid klockwork tool.
            return 'if(%s == %d)' % (hidx_str, self.max_key)
        
        # 2016-07-28 klockwork complains about unsigned hidx with
        # hidx < 0. I considered adding adding "&& hidx >= 0" to
        # the test to quiet KW warnings. But that extra clause
        # causes the clang compiler to complain that I did
        # something stupid (with -Wall) since that that expression
        # is always true for unsigned numbers. Stupid KW just does
        # not understand unsigned arithmetic. Someone should make
        # KW smarter...
        return 'if(%s <= %d)' % (hidx_str, self.max_key)
    def __str__(self):
        
        return 'h(x) = linear(x - %d)' % self.k



def get_linear_hash_function(keylist, tolerable_sparsity=0.2):
    ''' returns phash_t object with a linear_funct_t as the hash function'''
    min_key = min(keylist)
    max_key = max(keylist)
    nelem =  len(keylist)
    nslots = max_key - min_key + 1

    # if the array is more than 20% empty (or overridden value), bail.
    if nslots > nelem:
        if (nelem * (1.0 + tolerable_sparsity)) < nslots:
            return None
    hash_f = linear_func_t(min_key,max_key)
    return hash_f
