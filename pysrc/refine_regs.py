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
import re
from patterns import *
from genutil import *
import enumer

# $$ reg_info_t

class reg_info_t(object):
   def __init__(self, name, type, width, 
                max_enclosing_reg, 
                ordinal, 
                hreg=False,
                max_enclosing_reg_32=None,
                display_str=None):
      self.name = name.upper()
      if display_str:
          self.display_str = display_str.upper()
      else:
          self.display_str = self.name
      self.type = type.upper()
      self.width = width
      self.max_enclosing_reg = max_enclosing_reg
      self.max_enclosing_reg_32 = max_enclosing_reg_32
      self.ordinal = ordinal
      self.hreg = hreg # the AH,BH,CH,DH registers
      if self.type == 'GPR':
          if self.hreg:
              self.rtype =  self.type + str(self.width) + self.hreg
          else:
              self.rtype =  self.type + str(self.width)
      else:
          self.rtype = self.type

          
def refine_regs_input(lines):
   """Return  a list of reg_info_t. Skip comments and blank lines"""
   global comment_pattern
   all_ri = []
   reg_width_dict = {}
   for line in lines:
       pline = comment_pattern.sub('',line).strip()
       if pline == '':
           continue
       wrds = pline.split()
       n = len(wrds)
       # if there are only 3 fields, duplicate the first field as the 4th field
       if n == 3:
           n = 4
           first = wrds[0]
           wrds.append(first)
       if n == 6 and (wrds[5] not in [ 'h', '-']):
           die("regs-read: Illegal final token on line: " + line)
       if n < 4 or n > 7:
           die("regs-read: Bad number of tokens on line: " + line)
       name = wrds[0]
       rtype = wrds[1]
       width = wrds[2]
       max_enclosing_reg = wrds[3]
       max_enclosing_reg_32 = None
       if '/' in max_enclosing_reg:
           (max_enclosing_reg, max_enclosing_reg_32) = max_enclosing_reg.split('/')

       ordinal = 0
       if n >= 5:
           ordinal = int(wrds[4])
       hreg = None
       if n >= 6:
           hreg = wrds[5]
       if hreg != 'h':
           hreg = None
       # 7th operand is a display string to replace the name in the enumerations
       display_str = None
       if n >= 7:
           display_str = wrds[6]
           
       ri = reg_info_t(name,
                       rtype,
                       width,
                       max_enclosing_reg,
                       ordinal, 
                       hreg,
                       max_enclosing_reg_32,
                       display_str)
       all_ri.append(ri)
       
       # CR/DR regs have slashes in the width for 32/64b mode. They
       # are not relevant for the register enclosing computation that
       # this code is facilitating.
       if width == 'NA':
           # the pseudo registers use NA as their width. We do not
           # care about the enclosing register computation for them.
           short_width = '1' 
       elif '/' in width:
           short_width = re.sub(r'/.*','',width)
       else:
           short_width = width
           
       iw = int(short_width)
       if name in reg_width_dict:
           if reg_width_dict[name] < iw:
               reg_width_dict[name] = iw
       else:
           reg_width_dict[name] = iw

   regs_name_list = []
   regs_dict = {}
              
   for ri in all_ri:
      # add name to list to preserve original order
      if ri.name not in regs_dict:
          regs_dict[ri.name] = ri
          regs_name_list.append(ri.name)
      elif regs_dict[ri.name].width < ri.width: # replace narrower
          regs_dict[ri.name] = ri
      else:
          old_enclosing = regs_dict[ri.name].max_enclosing_reg
          a = reg_width_dict[old_enclosing]
          b = reg_width_dict[ri.max_enclosing_reg]
          print("LER: Comparing {} and {} for {}".format(old_enclosing,
                                                          ri.max_enclosing_reg,
                                                          ri.name))
          if a < b:
              # take the wider enclosing registers
              print("\ttaking new wider version")
              regs_dict[ri.name] = ri

   # return a list resembling the original order
   regs_list = []
   for nm in regs_name_list:
       regs_list.append(regs_dict[nm])
                                  
   return regs_list

def _key_reg_ordinal(x):
    return x.ordinal

def rearrange_regs(regs_list):
    """Return a list of enumer.enumer_values_t objects to be passed to
       enum_txt_writer"""
    groups = uniqueify( [ x.rtype for x in  regs_list])
    msgb("RGROUPS", str(groups))
    enumvals = []
    for g in groups:
        k = list(filter(lambda x: x.rtype == g, regs_list))
        k.sort(key=_key_reg_ordinal)
        first = '%s_FIRST' % (g)
        last = '%s_LAST' % (g)

        # first 
        enumvals.append(enumer.enumer_value_t(k[0].name,
                                              display_str=k[0].display_str))
        enumvals.append(enumer.enumer_value_t(first,
                                              value=k[0].name,
                                              doxygen='//< PSEUDO'))
        
        # everything in the middle
        if len(k) > 1:
            enumvals.extend(
                [  enumer.enumer_value_t(x.name,
                                         display_str=x.display_str) for x in k[1:] ] )  
        #last
        enumvals.append(enumer.enumer_value_t(last,
                                              value=k[-1].name,
                                              doxygen='//<PSEUDO'))
        
    return enumvals
