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

import tup2int
import xedhash
#paper of Fredman Komlos and Szemeredi (1984) :
#following hash function family is universal:
# x -> (kx mod p) mod s
# s ~ n^2
# p > s
# k is in 1,3,..., 2k+1
#Implementation of the hash_fun_interface_t
class hash_fun_fks_t(xedhash.hash_fun_interface_t):
    def __init__(self, k, p, m):
        self.k = k
        self.p = p
        if p < m:
            self.m = p
        else:
            self.m = m
    def kind(self):
        return "fks"

    def get_table_size(self):
        return self.m

    def tuple2int(self, tuple_val, cnames, op_widths_dict):#FIXME NOT USED
        return tup2int.tuple2int(tuple_val, cnames, op_widths_dict)

    def apply(self, x):
        return ((self.k*x) % self.p) % self.m

    def emit_cexpr(self, key_str='key'):
        if self.m == 1:
            return '(0)'
        if self.p == self.m:
            #when m==p it is unnecessary to do "mod m"
            expr = '(%d*%s %% %d)' % (self.k, key_str, self.p)
        else:
            expr = '((%d*%s %% %d) %% %d)' % (self.k, key_str, self.p, self.m)
        return expr
    
    def need_hash_index_validation(self):
        return True
    
    def add_key_validation(self, strings_dict):
        key_str = strings_dict['key_str']
        hentry_str ='%s[%s]' % (strings_dict['table_name'], 
                                strings_dict['hidx_str'])
        
        return 'if(%s.key == %s)' % (hentry_str, key_str)
    def __str__(self):
        lines = []
        lines.append('x = Sigma(Ti << bit_shift)')
        lines.append('FKS(x) = (%dx mod %d) mod %d' % (self.k, self.p, self.m))
        return '\n'.join(lines)


_primes = [
  2,      3,      5,      7,     11,     13,     17,     19,     23,     29,
 31,     37,     41,     43,     47,     53,     59,     61,     67,     71,
 73,     79,     83,     89,     97,    101,    103,    107,    109,    113,
127,    131,    137,    139,    149,    151,    157,    163,    167,    173,
179,    181,    191,    193,    197,    199,    211,    223,    227,    229,
233,    239,    241,    251,    257,    263,    269,    271,    277,    281,
283,    293,    307,    311,    313,    317,    331,    337,    347,    349,
353,    359,    367,    373,    379,    383,    389,    397,    401,    409,
419,    421,    431,    433,    439,    443,    449,    457,    461,    463,
467,    479,    487,    491,    499,    503,    509,    521,    523,    541,
547,    557,    563,    569,    571,    577,    587,    593,    599,    601,
607,    613,    617,    619,    631,    641,    643,    647,    653,    659,
661,    673,    677,    683,    691,    701,    709,    719,    727,    733,
739,    743,    751,    757,    761,    769,    773,    787,    797,    809,
811,    821,    823,    827,    829,    839,    853,    857,    859,    863,
877,    881,    883,    887,    907,    911,    919,    929,    937,    941]

#FIXME: BTW the tuple->int computation itself is a good hash function.
#Moreover, when m is a prime, the functions h(t) = (Sigma(AiTi)) mod m
#where Ti and Ai are arbitrary values in Zm Galois field
#are a universal hash function family!
#Hence our tuple2int function might be a good hash function itself, and
#if we parametrize it with Ai, we can get perfect hash functions!
#This can be faster than FKS because we do the tuple2int computation
#for FKS anyway before applying the FKS hash function.
#TODO: check if this approach is better than FKS.
_max_k = 32

_l1_bucket_max = 8 # FIXME: make this a parameter. Also in ild_phash.py


def _get_l1_mlist(n):
    """n is the number of keys in the hash function. Guessing a good size
    for the hash table. Try squaring number of keys but that is too
    much. if we use n, we get minimal perfect hash functions    """
    global _l1_bucket_max
    if n == 1:
        mlist = [1]
    elif n <= _l1_bucket_max:
        mlist = [n, 2*n, n*n]
    else:
        mlist = [n, 2*n] #just to try
    return mlist

def find_fks_perfect(keylist):
    """Return a perfect hash function for a given key list. Or None if no
       perfect hash function could be found."""
    global _max_k
    mlist = _get_l1_mlist(len(keylist))
    for m in mlist: # of buckets
        for p in _primes:
            for k in range(3, _max_k):
                hash_f = hash_fun_fks_t(k,p,m)
                if xedhash.is_perfect(keylist, hash_f):
                    return hash_f
                del hash_f
    return None



def find_fks_well_distributed(keylist):
    """Return a hash well-distributed function (not necessarily perfect!)
       for a given key list"""
    global _max_k
    global _l1_bucket_max
    mlist = _get_l1_mlist(len(keylist)) # number of buckets
    for m in mlist:
        for p in _primes:
            for k in range(3, _max_k):
                hash_f = hash_fun_fks_t(k,p,m)
                if xedhash.is_well_distributed(keylist, hash_f, _l1_bucket_max):
                    return hash_f
                del hash_f
    return None
