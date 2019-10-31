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
class hlist_t(object):
    """A hashable integer list"""

    def __init__(self,l):
        self.lst = l
    def __eq__(self,other):
        if self.lst == other.lst:
            return True
        return False
    def __hash__(self):
        h = 0
        for v in self.lst:
            h = h ^ v
            h = h << 1
        return h
    def __str__(self):
        s = ",".join( [ str(x) for x in self.lst])
        return s


def test_hlist():
    a = hlist_t([1,2,3])
    b = hlist_t([1,2,3])
    c = hlist_t([1,3])
    
    if a == b:
        print('a==b')
    if a == c:
        print('a==c')
        
    d = {}

    d[a] = 1
    d[b] = 2
    d[c] = 3
    for k in d.keys():
        print(str(k))

if __name__ == '__main__':
    test_hlist()
