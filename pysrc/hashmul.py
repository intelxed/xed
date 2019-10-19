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
import sys
import math

import xedhash

class hashmul_t(xedhash.hash_fun_interface_t):
    """Implement multiplicative hashing."""

    def __init__(self,  table_size):
        # golden ratio phi is (1+sqrt(5))/2. From Knuth, volume 3, page 516
        # 1/phi = (sqrt(5)-1)/2 (after some arithmetic)
        # We are using 1/phi * 2**n
        # where n is the number of bits in the data type (32)

        
        self.golden_ratio_recip2to32 = 2654435769
        self.table_size = table_size

        # pow2 is True if the table is a power of 2.
        # ilog2_table_size is only valid if pow2 is True
        self.pow2, self.ilog2_table_size = self.power_of_2()

    def kind(self):
        return "mult"

    def power_of_2(self):
        ilog2_table_size = int(math.log(self.table_size,2))
        if pow(2,ilog2_table_size) == self.table_size:
            return (True, ilog2_table_size)
        return (False, -1)

    def get_table_size(self):
        return self.table_size

    def __str__(self):
        return "h(x) = hashmul({})".format(self.table_size)
    
    def apply(self, k):
        """Apply the hash function to the key k"""
        #sys.stderr.write("Apply {} --> ".format(k))
        q = self.golden_ratio_recip2to32 * k
        fraction = q & ((1<<32)-1)
        r = fraction * self.table_size
        v = r >> 32
        #sys.stderr.write(" {}\n".format(v))
        return v

    def apply_pow2(self, k):
        """Apply the hash function to the key k, for power of 2 table sizes"""
        q = self.golden_ratio_recip2to32 * k
        fraction = q & ((1<<32)-1)
        v = fraction >> (32-self.ilog2_table_size)
        return v

    def is_perfect(self, key_list):
        values = set()
        for k in key_list:
            #sys.stderr.write("Checking {}\n".format(k))
            v = self.apply(k)
            if v in values:
                # collision - not perfect
                return False
            values.add(v)

        # no collisions in the output of the hash: perfect
        return True

    def need_hash_index_validation(self):
        """Need to validate that we landed on live bucket"""
        return True

    def add_key_validation(self, strings_dict):
        key_str = strings_dict['key_str']
        hentry_str ='%s[%s]' % (strings_dict['table_name'], 
                                strings_dict['hidx_str'])
        
        return 'if(%s.key == %s)' % (hentry_str, key_str)


    def emit_cvar_decl(self):
        if self.pow2:
            return "xed_union64_t t"
        return "xed_union64_t t, u"


    def emit_cexpr(self, key_str="key"):
        """Emit a C expression for the hash function given a C variable
           key_str."""
        if self.pow2:
            # power of 2 table size can replace the 2nd multiply with a shift
            c_hash_expr = """(t.u64 = {0}  * {1},  t.s.lo32 >> (32-{2}))""".format(
                str(self.golden_ratio_recip2to32), 
                key_str, 
                self.ilog2_table_size)
        else:
            # the ULL cast on the constant is important to get 64b math.
            c_hash_expr = """(t.u64 = {0}  * {1}, u.u64 = t.s.lo32 * {2}ULL, u.s.hi32)""".format(
                str(self.golden_ratio_recip2to32), 
                key_str, 
                str(self.table_size))

        return c_hash_expr

def find_perfect(keylist):
    n = len(keylist)
    for m in range(n,2*n):
        f = hashmul_t(n)
        if f.is_perfect(keylist):
            return f
    return None

def test1():
    f = hashmul_t(128)
    
    for k in range(0,128):
        v = f.apply(k)
        print("{} -> {}".format(k,v))
    
    if f.is_perfect(range(0,128)):
        print("Hash function is perfect")
    else:
        print("Hash function has collisions")

    print(f.emit_cexpr())
    return 0
def test2():
    f = hashmul_t(9)
    inputs = [225,2273,737,2785,241,2289,753,2801]
    for k in inputs:
        v = f.apply(k)
        print("{} -> {}".format(k,v))
    
    if f.is_perfect(inputs):
        print("Hash function is perfect")
    else:
        print("Hash function has collisions")

    print(f.emit_cexpr())
    return 0
def test3():
    f = hashmul_t(16)
    inputs = [225,2273,737,2785,241,2289,753,2801]
    for k in inputs:
        v1 = f.apply(k)
        v2 = f.apply_pow2(k)
        if v1 != v2:
            print("ERROR {} -> {} {}".format(k,v1,v2))
        else:
            print("OK    {} -> {} {}".format(k,v1,v2))
    
    if f.is_perfect(inputs):
        print("Hash function is perfect")
    else:
        print("Hash function has collisions")

    print(f.emit_cexpr())
    return 0

def test4():
    f = hashmul_t(1)
    inputs = [68002]
    for k in inputs:
        v1 = f.apply(k)
        v2 = f.apply_pow2(k)
        if v1 != v2:
            print("ERROR {} -> {} {}".format(k,v1,v2))
        else:
            print("OK    {} -> {} {}".format(k,v1,v2))
    
    if f.is_perfect(inputs):
        print("Hash function is perfect")
    else:
        print("Hash function has collisions")

    print(f.emit_cexpr())
    return 0

def test():
    fail = 0
    for f in [test1, test2, test3, test4]:
        r = f()
        if r:
            print("FAIL: {}".format(f.__name__))
            fail = 1
        else:
            print("PASS: {}".format(f.__name__))
    return fail

if __name__ == "__main__":
    r = test()
    sys.exit(r)
        
