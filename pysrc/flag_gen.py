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

# FIXME: could cut table sizes by rusing identical entries in the
# simple flags table. 2007-05-02
from __future__ import print_function
import re
import sys
from genutil import *

def _convert_to_list_of_string(x):
    return [ str(a) for a in x]
def _curly_list(x):
    return '{' + ','.join(x) + '},'
def _curly_string(x):
    return '{' + x +  '}'

class flag_set_t(object):
    field_pairs = [('cf',1), ('must_be_1',1),
                   ('pf',1), ('must_be_0a',1),
                   ('af',1), ('must_be_0b',1),
                   ('zf',1), ('sf',1),
                   ('tf',1), ('_if',1),
                   ('df',1), ('of',1),
                   ('iopl',2),  # 2b wide field
                   ('nt',1), ('must_be_0c',1),
                   ('rf',1), ('vm',1),
                   ('ac',1), ('vif',1),
                   ('vip',1), ('id',1),
                   ('must_be_0d',2),
                   ('must_be_0e',4),
                   
                   # not part of [er]flags, just stored that way for convenience.
                   ('fc0',1),
                   ('fc1',1),
                   ('fc2',1),
                   ('fc3',1) ] 
    field_names = [ x[0] for x in field_pairs]

    def __init__(self, very_technically_accurate=False):
        for (f,w) in flag_set_t.field_pairs:
            if very_technically_accurate and f.startswith('must_be_1'):
                setattr(self,f,1)
            else:
                setattr(self,f,0)

    def set(self,fld,val=1):
        if fld == 'if':
            fld = '_if' # recode this one to avoid keyword clash
        if fld == 'iopl':
            val = 3 # turn on both bits for IOPL. Just a convention
            
        if fld in flag_set_t.field_names:
            setattr(self,fld,val)
        else:
            die("Bad flags field name: {}".format(fld) )

    def as_integer(self):
        s = 0
        n = 0
        for (f,w) in flag_set_t.field_pairs:
            mask = (1<<w)-1
            s = s | (getattr(self,f) & mask) << n
            n = n + w
        return s

    def as_hex(self): 
        return hex(self.as_integer())

class flag_action_t(object):
   """Simple flag/actions pairs. If the input is 'nothing' we do not have any flag action"""
   valid_flag_actions = ['mod','tst','u','0','1','ah', 'pop'] # FIXME: x86 specific
   def __init__(self, s):
      self.flag = None
      self.action = None # Could be mod,tst,u,0,1, ah, pop
      if s != 'nothing':
         (self.flag,self.action) = s.split('-')
         if self.action not in flag_action_t.valid_flag_actions:
            die("Invalid flag_action_t in %s" % s)
   def __str__(self):
      if self.flag == None:
         return 'nothing'
      return "%s-%s" % (self.flag , self.action)
   def is_nothing(self):
      if self.flag == None:
         return True
      return False
   def reads_flag(self):
      if self.action == 'tst':
         return True
      return False
   def writes_flag(self):
      if self.action != 'tst':
         return True
      return False
   def makes_flag_undefined(self):
      return self.action == 'u'

      
         
class flags_rec_t(object):
   """Collection of flag_action_t records with an optional qualifier
   for things conditioned on immediates, and may/must/readonly field"""
   
   valid_flags_semantics_specifiers = ['MAY', 'MUST', 'READONLY' ]
   valid_flags_qualifiers = ['REP', 'NOREP', 'IMM0', 'IMM1', 'IMMx' ]

   _flag_pattern = re.compile(r'\s*(?P<qualifiers>.*)\s+[\[](?P<flags>.*)[\]]')
   def __init__(self,input_chunk):
      self.qualifier = None
      self.may_must = None # Could be READONLY, MAY or MUST, REP_MAY
      self.flag_actions = [] # [ flag_action_t ]
      m = flags_rec_t._flag_pattern.search(input_chunk)
      if m:
         flags_input = m.group('flags').strip().split()
         qualifiers = m.group('qualifiers').strip().split()
      else:
         die("Could not find flags in %s" % input_chunk)
      
      first = qualifiers[0]
      if first in flags_rec_t.valid_flags_qualifiers:
         self.qualifier = first
         qualifiers.pop(0)
      self.may_must = qualifiers[0]
      if self.may_must not in flags_rec_t.valid_flags_semantics_specifiers:
         die("Invalid flags specification: %s" % input_chunk)

      self.read_set = flag_set_t()
      self.write_set = flag_set_t()
      self.undefined_set = flag_set_t()

      self.flag_action_index = -1
      self.simple_id = -1

      for flag_action_str in flags_input:
         fa = flag_action_t(flag_action_str)
         self.flag_actions.append(fa)
         if fa.flag:
             if fa.reads_flag():
                 self.read_set.set(fa.flag)
             if fa.writes_flag():
                 self.write_set.set(fa.flag)
             if fa.makes_flag_undefined():
                 self.undefined_set.set(fa.flag)
         else:
             sys.stderr.write("Bogus flag: {}\n".format(flag_action_str))

   def get_number_of_flag_actions(self):
       return len(self.flag_actions)

   def get_flag_action_index(self):
       return self.flag_action_index
   def set_flag_action_index(self,n):
       self.flag_action_index = n
   def get_simple_id(self):
       return self.simple_id
   def set_simple_id(self,n):
       self.simple_id = n

   def x86_flags(self):
      """Return True if any of the flags are x86 flags. False otherwise"""
      for flag_action in self.flag_actions:
         s = flag_action.flag
         if s != 'fc0' and s != 'fc1' and s != 'fc2' and s != 'fc3':
            return True
      return False
      
   def reads_flags(self):
      for fa in self.flag_actions:
         if fa.reads_flag():
            return True
      return False
   def writes_flags(self):
      for fa in self.flag_actions:
         if fa.writes_flag():
            return True
      return False
   def conditional_writes_flags(self):
      if self.writes_flags() and (self.may_must == 'MAY' or  self.may_must == 'REP_MAY'):
         return True
      return False
   
   def is_simple(self):
       if self.qualifier == None:
           return True
       return False
   def is_complex(self):
       if self.qualifier != None:
           return True
       return False
   def is_rep(self):
      if self.qualifier == 'REP' or self.qualifier == 'NOREP':
         return True
      return False
   def is_imm(self):
      if self.qualifier == 'IMM0' or \
             self.qualifier == 'IMM1' or \
             self.qualifier == 'IMMx':
         return True
      return False
            
   def __str__(self):
      s = []
      if self.qualifier != None:
         s.append(self.qualifier)
      s.append(self.may_must)
      s.append('[')
      s.extend([str(x) for x in self.flag_actions])
      s.append(']')
      return ' '.join(s)

   def is_nothing(self):
      if len(self.flag_actions) == 1:
         fa = self.flag_actions[0]
         if fa.is_nothing():
            return True
      return False

   def emit_code(self, prefix,fo):
      for fa in self.flag_actions:
         if fa.flag:
            s = "xed_simple_flag_set_flag_action(%s,XED_FLAG_%s,XED_FLAG_ACTION_%s)" % \
                (prefix, fa.flag, fa.action)
            fo.add_code_eol(s)
            
   def identifier(self,limit=99):
      s = []
      for i,fa in enumerate(self.flag_actions):
         if not fa.flag:
             die("Bogus flag!")
         s.append("{}-{}".format(fa.flag, fa.action))
         if i >= limit:
             break
      return ":".join(s)

   def emit_data_record(self, fo):
      for i,fa in enumerate(self.flag_actions):
         if not fa.flag:
             die("Bogus flag!")
         s = "/* {} */ {{ XED_FLAG_{},XED_FLAG_ACTION_{} }},".format(
             self.get_flag_action_index() + i, fa.flag, fa.action)
         fo.add_code(s)
            
# Need to emit 3 tables:
#   xed_flag_action_t array   
#   xed_simple_flag_t array
#   xed_complex_flag_t array
#
# constraint: need hand out indices to the simple and complex table as
# instructions are encountered during code gen so that I can give the
# instruction record the index to the complex or simple flags table.
# 
# most instructions are simple flags and have one simple record per
# instruction some are complex and have multiple simple flags records
# per instruction. 
#



class flags_info_t(object):
    """Collection of flags_rec_t records"""

    _flag_simple_rec = 1
    _flag_complex_rec = 1
    _max_actions_per_simple_flag = 0
    _max_flag_actions = 0
    # for unique-ifying the flag-actions array.
    _fa_table = {} 
    _fr_table = {} 

    def __init__(self,input_line):
       # flags_recs is a list of flag_rec_t's. Usually 0 or 1. Sometimes 3
       if input_line != '':
          lst  = input_line.split(',')
          self.flags_recs = [  flags_rec_t(x.strip()) for x in lst]
       else:
          self.flags_recs = []

       self.complex_id = -1
    def set_complex_id(self,n):
       self.complex_id = n
    def get_complex_id(self,n):
       return self.complex_id
        
    def __str__(self):
       s = ', '.join( [str(x) for x in self.flags_recs] )
       return s

    def x87_flags(self):
       """Return True if all the flags are x87 flags. And False if any are x86 flags"""
       for fr in self.flags_recs:
          if fr.x86_flags():
             return False
       return True
    
    def x86_flags(self):
       """Return True if any flags are x86 flags"""
       for fr in self.flags_recs:
          if fr.x86_flags():
             return True
       return False
             

    def rw_action(self):
       """Return one of: r, w, cw, rcw or rw. This is the r/w action
       for a rFLAGS() NTLUF."""
       r = ''
       w = ''
       c= ''
       has_nothing_record = False
       for fr in self.flags_recs:
          if fr.is_nothing():
             has_nothing_record=True
          if fr.reads_flags():
             r = 'r'
          if fr.writes_flags():
             w = 'w'
             if fr.conditional_writes_flags():
                # things that are conditional writes are also writes
                c = 'c'

       if has_nothing_record:
          c = 'c'
       retval =  "%s%s%s" % (r,c,w)
       return retval
    
    def make_case_name(self,qualifier):
       if qualifier == 'IMMx':
          return 'IMMED_OTHER'
       elif qualifier == 'IMM0':
          return 'IMMED_ZERO'
       elif qualifier == 'IMM1':
          return 'IMMED_ONE'
       elif qualifier == 'REP':
          return 'HAS_REP'
       elif qualifier == 'NOREP':
          return 'NO_REP'
       else:
          die("Unhandled flags qualifier: %s" % qualifier)
             
    def is_complex(self):
       for x in self.flags_recs:
          if x.is_complex():
             return True
       return False

    def is_rep(self):
       for x in self.flags_recs:
          if x.is_rep():
             return True
       return False

    def is_imm(self):
       for x in self.flags_recs:
          if x.is_imm():
             return True
       return False
    

    def _compute_assign_flag_action_id(self, fr, fo_flag_actions):

        # compute an identifying string as an identifier of the (flag, action)+ sequence
        id = fr.identifier()

        try:
            t = flags_info_t._fa_table[id]
            is_new = False
        except:
            is_new = True
            t = flags_info_t._max_flag_actions
            # skip ahead by # of (flag,actions) entries
            flags_info_t._max_flag_actions += fr.get_number_of_flag_actions()

            # install all the prefixes of the current flag-action group that
            # share the same starting point for extra compression
            
            # FIXME: could do all possible singletons and subranges.
            for i in range(0,fr.get_number_of_flag_actions()):
                id = fr.identifier(i)
                flags_info_t._fa_table[id] = t

        # set the flag_action index
        fr.set_flag_action_index( t )

        if is_new:
            # emit the flag actions (using the indices assigned above)
            fr.emit_data_record(fo_flag_actions)

        return t

    def emit_data_record(self, fo_simple, fo_complex, fo_flag_actions):
        
        # emit the simple flag records 
        # (a) remember and id/number for the flags records; complex flags need it later
        # as do the instructions. 
        # (b) number the flag actions so that we can refer to them from the simple flag recs.

        flag_id = -1
        for fr in self.flags_recs:

            may  = '1' if fr.may_must == 'MAY'  else '0'
            must = '1' if fr.may_must == 'MUST' else '0'

            s = []
            s.append( str( fr.get_number_of_flag_actions() ))
            s.append(may)
            s.append(must)
            s.append(_curly_string(fr.read_set.as_hex()))
            s.append(_curly_string(fr.write_set.as_hex()))
            s.append(_curly_string(fr.undefined_set.as_hex()))
            
            flag_action_id  = self._compute_assign_flag_action_id(fr, fo_flag_actions)
            s.append(str(fr.get_flag_action_index()))

            t = _curly_list(s)
            try:
                # Attempt to reuse an identical flag record
                flag_id = flags_info_t._fr_table[t]
                is_new = False
            except:
                is_new = True
                # Assign an id/number to the simple flag records.
                # This gets used by the xed_inst_t to find the flags rec
                # and by the complex flags to find the right simple flags.
                flag_id = flags_info_t._flag_simple_rec
                flags_info_t._flag_simple_rec += 1
                # remember pattern for later use
                flags_info_t._fr_table[t] = flag_id

            fr.set_simple_id( flag_id  )
            if is_new:
                comment = '/* {} */ '.format(flag_id)
                fo_simple.add_code( comment + t )

        # emit the complex flag table
        if self.is_complex():
            flag_id = flags_info_t._flag_complex_rec
            self.set_complex_id( flag_id )
            flags_info_t._flag_complex_rec += 1

            s = []
            s.append('1' if self.is_rep() else '0')
            s.append('1' if self.is_imm() else '0')
            
            cases = []
            ordered_cases = ['IMMED_ZERO', # FIXME: IMMED_ZERO is unused
                             'IMMED_ONE',
                             'IMMED_OTHER',
                             'HAS_REP', 
                             'NO_REP' ]

            # go through ordered cases, find a flag rec that matches
            # and add it if found.

            for c in ordered_cases:
                found = None
                for fr in self.flags_recs:
                    cname = self.make_case_name(fr.qualifier)
                    if c == cname:
                        found = fr
                        break
                if found:
                    cases.append( found.get_simple_id())
                else:
                    cases.append( 0 )
            if not cases:
                die("Complex flag with no cases")

            cases = _convert_to_list_of_string(cases)
            s.append(_curly_list(cases))
            comment = '/* {} */ '.format(flag_id)
            fo_complex.add_code(comment + _curly_list(s))


        if flag_id == -1:
            die("flag_id was not set")
        if self.is_complex():
            return (flag_id, True)  # True for complex
        return (flag_id, False)     # False for simple


    def code_gen(self, itable_prefix_string, fo): # FIXME: DEAD: DELETE THIS
       """
       - set xed_inst_t::_flag_info_index in to the index of one of the next 2 tables
       - initialize the xed_flags_simple_table
       - initialize the xed_flags_complex_table

       @type  itable_prefix_string: string
       @param itable_prefix_string:
       @type  fo: function_object_t
       @param fo: the function object for the instruction we are initializing.        
       """

       complex = self.is_complex()
       if complex:
          flags_info_t._flag_complex_rec += 1
          retval = (flags_info_t._flag_complex_rec, True)
          
          complex_prefix = "xed_flags_complex_table[%d]" % \
                           (flags_info_t._flag_complex_rec)
          if self.is_rep():
             fo.add_code_eol("%s.check_rep=1" % (complex_prefix))
          elif self.is_imm():
             fo.add_code_eol("%s.check_imm=1" % (complex_prefix))
          else:
             die("Unhandled complex flags condition: %s" % str(self))
       else: # SIMPLE 
          retval = (flags_info_t._flag_simple_rec, False)

       for fr in self.flags_recs:

          if complex:
             # emit the complex decider information for this record FIXME
             case_name = self.make_case_name(fr.qualifier)
             if fr.is_nothing():
                srec = 0
             else:
                srec = flags_info_t._flag_simple_rec

             s="%s.cases[XED_FLAG_CASE_%s]=%d" % ( complex_prefix,
                                                   case_name,
                                                   srec)
             fo.add_code_eol(s)


          simple_prefix = "xed_flags_simple_table+%d" % \
                            (flags_info_t._flag_simple_rec)
          flags_info_t._flag_simple_rec += 1
          
          may_must = None
          if fr.may_must == 'MUST':
             may_must = "xed_simple_flag_set_must_write"
          elif fr.may_must == 'MAY':
             may_must = "xed_simple_flag_set_may_write"
          if may_must:
             fo.add_code_eol("%s(%s)" % (may_must,simple_prefix))
          
          # emit the individual bits
          fr.emit_code(simple_prefix, fo)
          
          x = len(fr.flag_actions)
          if x > flags_info_t._max_actions_per_simple_flag:
             flags_info_t._max_actions_per_simple_flag = x
          # track the max # of flag actions
          flags_info_t._max_flag_actions += x
       return retval

def _testflags():
    """Test function for flag_set_t objects"""
    a = flag_set_t()
    a.set('cf')
    a.set('zf')
    a.set('of')
    print(a.as_integer())
    print(a.as_hex())

if __name__ == '__main__':
    _testflags()
