#!/usr/bin/env python
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
class hnode_t(object):
    def __init__(self, lst=None, id=None):
        self.lst = lst
        self.token = id
    

class hash_compare_t(object):
    def __init__(self):
        self.bins = {} # indexed by hash values
        self.token = 1

    def hash_list(self, inlist):
        """Return a hash of the content of inlist"""
        h = 0
        i = 1
        for v in inlist:
            h = h + v*i
            i = i + 1
        return h

    def find(self,inlist):
        h = self.hash_list(inlist)
        if h in self.bins:
            bucket = self.bins[h]
            for b in bucket:
                if b.lst == inlist:
                    return b.token
        return None
     
    def insert(self,inlist):
        """Return a identifier for this list upon insertion, creating
        one if necessary."""

        h = self.hash_list(inlist)
        if h in self.bins:
            bucket = self.bins[h]
            for node in bucket:
                if node.lst == inlist:
                    return node.token
            # not found... add it to the bucket
            n = hnode_t(inlist, self.token)
            bucket.append(n)
            self.token = self.token + 1
            return n.token
        else:
            # nothing with this hash value, add a bucket
            n = hnode_t(inlist, self.token)
            self.bins[h] = [ n ]
            self.token = self.token + 1
        return n.token
                


def test_hash():
    h = hash_compare_t()
    a = [1,2,3]
    b = [1,2,4]
    c = [1,2,3]
    d = [1,2,5]
    e = [1,2]
    v = h.insert(a)
    print("A's UID: %d" % ( v )) 
    v = h.insert(b)
    print("B's UID: %d" % ( v )) 
    v = h.insert(c)
    print("C's UID: %d" % ( v )) 
    v = h.insert(d)
    print("D's UID: %d" % ( v )) 
    v = h.insert(e)
    print("E's UID: %d" % ( v )) 

if __name__ == "__main__":
    test_hash()
