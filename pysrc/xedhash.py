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

import collections

#The idea is to have different algorithms for finding hash
#functions. So far we use only FKS and it seems to work well enough.
class hash_fun_interface_t(object):
    def _raise_error(self):
        raise NotImplementedError("Hash function not implemented.")
    def apply(self, x):
        self._raise_error()
    def emit_cexpr(self, key_str):
        self._raise_error()
    def __str__(self):
        self._raise_error()
    def kind(self):
        self._raise_error()
        
def is_perfect(keylist, hash_f):
    "Does each input map to a different bucket? If so, it is perfect."""
    bucket = set()
    for x in keylist:
        hash_val = hash_f.apply(x)
        if hash_val in bucket:
            # collision! ka-boom
            return None
        else:
            bucket.add(hash_val)
    return bucket

def _measure_bucket_max(table, maxbin):
    """check for buckets that are too large (_l1_bucket_max)"""
    okay = True
    max_bucket = 0
    bad_buckets = 0
    for k, vl in table.items():
        lvl = len(vl)
        if lvl >= maxbin:
            if lvl > max_bucket:
                max_bucket = lvl
            bad_buckets = bad_buckets + 1
            okay = False
    return okay

def is_well_distributed(keylist, hash_f, maxbin):
    """populate the buckets and see if any are too big"""
    table = collections.defaultdict(list) 
    for t,x in keylist.items():
        hash_val = hash_f.apply(x)
        table[hash_val].append(t) 

    okay = _measure_bucket_max(table, maxbin)
    return okay
