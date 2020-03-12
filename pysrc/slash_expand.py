#!/usr/bin/env python
# -*- python -*-
# Mark Charney <mark.charney@intel.com>
# Code generation support: emitting files, emitting functions, etc.
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


import re
import genutil

slash2_macro_pattern  = re.compile(r'(?P<letter>[a-z])[/](?P<number>[0-9]+)')

def expand_all_slashes(s):
   global slash2_macro_pattern
   a = s
   m = slash2_macro_pattern.search(a)
   while m:
      n = int(m.group('number'))
      if n > 99:
         genutil.die("Hit a very large number %d when explanding slash patterns in [%s]" %( n, s))
      new = n * m.group('letter')
      old  = '%s/%s' % ( m.group('letter'),  m.group('number') )
      #print "old %s -> new %s" % (old,new)
      a = a.replace(old,new,1)
      m = slash2_macro_pattern.search(a)
   return a
