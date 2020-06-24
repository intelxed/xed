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

import re
from verbosity import *
import genutil


class operand_info_t(object):
   """This is one of the major classes of the program. It describes
   the captured fields and lookup functions that are required for
   decoding."""

   decimal_number_pattern = re.compile(r'[0-9]+')
   
   operand_types = [ 'reg', 'imm', 'imm_const', 'error',
                     'relbr', 'ptr', 'nt_lookup_fn', 'mem', 'xed_reset',
                     'flag', 'agen' ]
   
   def __init__(self,
                name,
                type,
                bits='', # typically the right hand side of an operand or '1'
                rw='r',
                invert=False,
                lookupfn_name=None,
                vis='DEFAULT',
                oc2=None,
                cvt=None,
                xtype=None,
                internal=False,
                multireg=0):

      self.name  = name.upper()
      self.type = type # See operand_info_t.operand_types
      self.xtype = xtype # the user specified type for the operand

      self.internal = internal 
      self.multireg = multireg
      
      # some operands are captured during operand processing. Those
      # are called inline operands
      self.inline = False
      
      if self.type not in operand_info_t.operand_types:
         genutil.die("Unexpected type when building operand: %s" %
                     (str(self.type)))
      
      # constant or varible bits, Register names. could be empty for
      # lookup functions that do not take arguments.
      self.bits = bits 

      # for lookup-functions this is the name of that function
      self.lookupfn_name = lookupfn_name
      self.lookupfn_name_base = self._strip_ntluf_name()

      self.rw = rw # r,w,rw, cw (conditional write, may write)

      # ascii conversion function
      if cvt:
          self.cvt = cvt
      else:
          self.cvt = []

      # accept some shorthand.
      if vis == 'SUPP':
         self.visibility = 'SUPPRESSED'
      elif vis == 'IMPL':
         self.visibility = 'IMPLICIT'
      elif vis == 'EXPL':
         self.visibility = 'EXPLICIT'
      else:
         # The default visibililty comes from the field definitions
         if vis in ['DEFAULT', 'EXPLICIT', 'IMPLICIT', 'SUPPRESSED', 'ECOND']:
            self.visibility = vis
         else:
            genutil.die("Bad visibility qualifier: " + vis)

      # size code for partial reg writes.
      self.oc2 = oc2
      
      # Sometimes we want the actual operand to be the logical
      # inversion of the captured bit.
      self.invert=invert
      
      # names of functions for extracting or packing these bits
      # These become function pointers in the instruction table.
      self.bit_extractor = None
      self.bit_packer = None

      # actual index of each variable bit in the operand.
      # The values point to bits in the ipattern.
      self.bit_positions = []

      # Captures require finding the rightmost bit of any group of
      # letter-bits of the same name. Sometimes though, the bits captured
      # are constant (as in MOD[11_]).
      
      # sometimes the rightmost bit is not the last in the
      # bit_positions list when the bits are discontinuous. So we
      # stash it here to avoid searching for the maximum value in the
      # bit_positions list.
      self.rightmost_bitpos = 0

   def is_ntluf(self):
      if self.type == 'nt_lookup_fn':
         return True
      return False

   def _strip_ntluf_name(self):
       if self.is_ntluf():
           s = self.lookupfn_name
           s = re.sub(r'[()]*','',s)
           s = re.sub(r'_S[RBE]','',s)
           s = re.sub(r'_[RBNEI].*','',s)
           s = re.sub(r'FINAL_.*','',s)
           return s
       return None


   def get_cvt(self, i):
       cvt = None
       try:
           cvt = self.cvt[i]
       except:
           pass
       if cvt == None:
           cvt = 'INVALID'
       return cvt.upper()
   
   def get_type_for_emit(self):
       if self.type == 'nt_lookup_fn' and self.multireg >= 2:
           return self.type.upper() + str(self.multireg)
       return self.type.upper()
      
   def non_binary_fixed_number(self):
      "Returns True if this operand is a decimal number"
      if type(self.bits) == list:
         if ( len(self.bits) == 1 and
              operand_info_t.decimal_number_pattern.match(self.bits[0]) ):
               return True
      elif genutil.is_stringish(self.bits):
         if operand_info_t.decimal_number_pattern.match(self.bits):
            return True
      return False
   
   def all_bits_fixed(self):
      "Return True if all bits in the operand are 1s/0s (could be mixed)"
      if self.bits == None:
         return False

      for b in self.bits:
         #genutil.msge("\ttesting bit " + b)
         if b != '1' and b != '0':
            # found a non 1/0 bit--> all bits are not fixed.
            #genutil.msge("\t\tall not fixed! " + b)
            return False
         
      # all bits are 1s or 0s.
      return True
      
   def set_implicit(self):
      self.visibility = 'IMPLICIT'
   def set_suppressed(self):
      self.visibility = 'SUPPRESSED'
      
   def dump_str(self, pad=''):
      s = []
      s.append(pad)
      s.append("{:6}".format(self.name))
      s.append("{:9}".format(self.type))
      if self.bits:
         if type(self.bits) == list:
            s.append(''.join(self.bits) + " (L)")
         else:
            s.append('[' + self.bits + ']')
      s.extend([self.rw, self.visibility])
      if self.lookupfn_name:
         s.append( self.lookupfn_name)
      if self.oc2:
         s.append( self.oc2)
      if self.xtype:
         s.append( self.xtype)
      for c in self.cvt:
          if c and c != 'INVALID':
              s.append( "TXT=%s" % (c))
      if self.multireg >= 2:
          s.append("MULTIREG{}".format(self.multireg))
          
      if self.bit_positions:
          s.append(' bitpos:  ' + ', '.join( [str(x) for x in self.bit_positions] ))
      
      if self.invert:
         s.append('invert')
      return " ".join(s)
   
   def dump(self, pad=''):
      genutil.msge( self.dump_str(pad))
   def __str__(self):
      return self.dump_str()
   def __eq__(self,other):
      if self.name != other.name:
         return False
      if self.type != other.type:
         return False
      if self.xtype != other.xtype:
         return False
      if self.lookupfn_name != other.lookupfn_name:
         return False
      if self.invert != other.invert:
         return False
      if self.rw != other.rw:
         return False
      if self.visibility != other.visibility:
         return False
      if self.oc2 != other.oc2:
         return False
      if self.cvt != other.cvt:
         return False
      if self.multireg != other.multireg:
         return False
      if self.bits != other.bits: # FIXME: check this
         return False
      return True
   def __hash__(self):
      h = 0
      if self.name:
         h = h ^ self.name.__hash__()
      if self.type:
         h = h ^ self.type.__hash__()
      if self.xtype:
         h = h ^ self.xtype.__hash__()
      if self.lookupfn_name:
         h = h ^ self.lookupfn_name.__hash__()
      # skipping invert boolean, cvt list and bits list
      h = h ^ self.multireg.__hash__()
      if self.rw:
         h = h ^ self.rw.__hash__()
      if self.visibility:
         h = h ^ self.visibility.__hash__()
      if self.oc2:
         h = h ^ self.oc2.__hash__()
      return h

##############################################################
colon_pattern= re.compile(r'[:]')
slash_pattern= re.compile(r'/')
error_pattern = re.compile(r'^XED_ERROR_')
oc2_pattern = re.compile(r'^[a-z][a-z0-9]*$')

# b = longbcd
# e = longdouble
# f = float
# s = struct
# v = variable
# i = signed integer
# u = unsigned integer

decimal_number_pattern = re.compile(r'[0-9]+')
letters_underscore_pattern = re.compile(r'^[a-z_]+$')
mem_pattern = re.compile(r'MEM[01]')
imm_token_pattern = re.compile(r'IMM[0123]')
agen_pattern = re.compile(r'AGEN')
relative_branch_pattern = re.compile(r'RELBR')
pointer_pattern = re.compile(r'PTR')
xed_reset_pattern = re.compile(r'XED_RESET')
double_parens_pattern = re.compile(r'[(][)]')
equals_pattern = re.compile(r'(?P<lhs>[^!]+)=(?P<rhs>.+)')
not_equals_pattern = re.compile(r'(?P<lhs>[^!]+)!=(?P<rhs>.+)')
az_cap_pattern = re.compile(r'[A-Z]')
enum_pattern = re.compile(r'^XED_')
reg_pattern = re.compile(r'^XED_REG_')
error_pattern = re.compile(r'^XED_ERROR_')
hex_pattern = re.compile(r'0[xX][0-9A-Fa-f]+')
multireg_pattern = re.compile(r'MULTI(?P<sd>(SOURCE|DEST|SOURCEDEST))(?P<nreg>[0-9]+)')
convert_pattern = re.compile(r'TXT=(?P<rhs>[0-9A-Za-z_]+)')


def parse_one_operand(w, 
                      default_vis='DEFAULT', 
                      xtypes=None, 
                      default_xtypes=None,
                      internal=False,
                      skip_encoder_conditions=True):
   """Format examples:
   name=xxxxxy:{r,w,crw,rw,rcw}[:{EXPL,IMPL,SUPP,ECOND}][:{some oc2 code}][:{some xtype code}]
   name=NTLUR():{r,w,crw,rw,rcw}[:{EXPL,IMPL,SUPP,ECOND}][:{some oc2 code}][:{some xtype code}]
          oc2 can be before EXPL/IMPL/SUPP. oc2 is the width code.
          MEM{0,1}, PTR, RELBR, AGEN, IMM{0,1,2,3}

          xtype describes the number of data type and width of each element.
          If the xtype is omitted, xed will attempt to infer it from the oc2 code.

          ECOND is for encoder-only conditions. Completely ignored by the decoder.
          
   Default is read-only

   @param w: string
   @param w: an operand specification string
   
   @rtype operand_info_t
   @return a parsed operand
   """
   
   if vopnd():
      genutil.msge("PARSE-OPND: " + w)

   # get the r/w/rw info, if any
   vis = default_vis
   oc2 = None
   rw = 'r'
   cvt = []
   invert = False
   lookupfn_name=None
   xtype = None
   multireg = 0
   if colon_pattern.search(w):
      chunks = w.split(':')
      if vopnd():
         genutil.msge("CHUNKS [%s]" % (",".join(chunks)))
      for i,c in enumerate(chunks):
         if vopnd():
            genutil.msge("\tCHUNK %d %s" %( i,c))
         if i == 0:
            a = c
         elif i == 1:
            rw = c
            if vopnd():
               genutil.msge("\t\tSET rw to  %s" % (rw))
         elif (i == 2 or i == 3) and (c in ['IMPL', 'SUPP',  'EXPL', 'ECOND']):
            vis = c
            if vopnd():
               genutil.msge("\t\tSET VIS to %s" % (vis))
         else: # FIXME: somewhat sloppy error checking on input
                      
            multi_reg_p=multireg_pattern.match(c)
            cp=convert_pattern.match(c)
            
            if multi_reg_p:
                multireg = int(multi_reg_p.group('nreg')) 
            elif cp:
                cvt.append(cp.group('rhs'))
            elif oc2 == None and oc2_pattern.match(c):
               oc2 = c
               if vopnd():
                  genutil.msge("\t\tSET OC2 to  %s" % (oc2))
            elif oc2 and c in xtypes:
               xtype = c
               if vopnd():
                  genutil.msge("\t\tSET xtype to  %s" % (xtype))
            elif decimal_number_pattern.match(c):
               genutil.die("Bad number in %s" % (w))
            else:
               genutil.die(
                   "Bad oc2 pattern in %s when looking at %d chunk: %s " %
                   (w,i,c) )

   else:
      a = w
      
   if skip_encoder_conditions and vis == 'ECOND':
      return None
   
      
   # From now on, use a, not w.

   if slash_pattern.search(a):
      genutil.die("Bad slash in operand")

   if xtype == None:
      # need to use the default xtype based on the oc2 width code
      if oc2:
         try:
            xtype = default_xtypes[oc2.upper()]
         except:
            s = ''
            for i,v in default_xtypes.items():
               s += "\t%10s -> %10s\n" % (i,v)
            genutil.die("Parsing operand [%s]. Could not find default type for %s. xtypes=%s\nTypes=%s" % (w, oc2, str(xtypes), s))
      else:
         # there was no oc2 type and no xtype. probably a nonterminal
         # lookup function
         xtype = 'INVALID'

   # look for X=y and X!=y and bare operands like MEM0.

   eqp = equals_pattern.search(a)
   neqp = not_equals_pattern.search(a)
   if eqp:
      (name,rhs)  = eqp.group('lhs','rhs')
      if vopnd():
         genutil.msge("PARSE-OPND:\t" + name + " + " + rhs)
      
      if double_parens_pattern.search(rhs): # NTLUF
         if vopnd():
            genutil.msge("PARSE-OPND:\t nonterminal lookup function "
                 + name + " <- " + rhs)
         # remove the parens
         nt_lookup_fn = double_parens_pattern.sub('',rhs)         
         optype ='nt_lookup_fn'
         rhs = None
         lookupfn_name=nt_lookup_fn
     
      elif reg_pattern.match(rhs):
         optype = 'reg'
      elif error_pattern.match(rhs):
         optype = 'error'
      elif enum_pattern.match(rhs): 
         # for storing XED_* enum values as RHS's of operand bindings
         optype = 'imm_const'
      elif (not genutil.numeric(rhs)) and az_cap_pattern.search(rhs): 
         genutil.die("THIS SHOULD NOT HAPPEN: %s" % (rhs))
      elif letters_underscore_pattern.match(rhs):   
         rhs = list(rhs.replace('_',''))
         optype = 'imm'
      else:
         rhs = hex(genutil.make_numeric(rhs))
         optype = 'imm_const'
   elif neqp:
      (name,rhs)  = neqp.group('lhs','rhs')
      if vopnd():
         genutil.msge("PARSE-OPND: (NOT EQUALS)\t" + name + " + " + rhs)
      invert = True
      if reg_pattern.match(rhs):
         optype = 'reg'
      elif az_cap_pattern.search(rhs): 
          genutil.die("THIS SHOULD NOT HAPPEN")
      elif letters_underscore_pattern.match(rhs): 
          genutil.die("Cannot have a != pattern with don't-care letters")
      else:
          rhs = hex(genutil.make_numeric(rhs))
          optype = 'imm_const'
   elif mem_pattern.search(a):        # memop
      name = a
      optype ='imm_const'
      rhs = '1'
   elif imm_token_pattern.search(a):        # immediate placeholder
      name = a
      optype ='imm_const'
      rhs = '1'
   elif agen_pattern.search(a):        # agen
      name = a
      optype ='imm_const'
      rhs = '1'
   elif relative_branch_pattern.search(a):
      name = a
      optype ='imm_const'
      rhs = '1'
   elif pointer_pattern.search(a): 
      name = a
      optype ='imm_const'
      rhs = '1'
   elif xed_reset_pattern.search(a):
      # special marker that tells the traverser to restart this
      # nonterminal from the current position
      name = a
      optype ='xed_reset'
      rhs = ''
      vis = 'SUPP'
   elif double_parens_pattern.search(a):
      if vopnd():
         genutil.msge("PARSE-OPND:\t unbound nonterminal lookup function " +
                      a)
      # 2007-07-23 this code is not used
      genutil.die("UNBOUND NTLUF!: %s" % (a)) 
               
   else:
      # macros -- these get rewritten later
      if vopnd():
         genutil.msge("PARSE-OPND:\t flag-ish: " + a)
      name = a
      optype = 'flag'
      rhs = ''

   
   xop =  operand_info_t(name, optype, rhs, rw=rw, invert=invert,
                         vis=vis, oc2=oc2, cvt=cvt, xtype=xtype,
                         lookupfn_name=lookupfn_name, internal=internal,
                         multireg=multireg)

   return xop
