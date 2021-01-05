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


############################################################################
## this is the main generator and the decoder generator.
## the main data structures are:
##
## class all_generator_info_t(object):
##    the catch-all for all state  -- at least it tries to be.
##
## class generator_common_t(object):
## class generator_info_t(generator_common_t):
##    each generator has a parser
##
## class parser_t(object):
##
## which contains:
##
## class partitionable_info_t(object):
## class instruction_info_t(partitionable_info_t):
##
## class nonterminal_info_t(object):
## class nonterminal_dict_t(object):

## class bits_list_t(object):
##
## contains a list of:
##
## class bit_info_t(object):

## class state_info_t(object):
## class prebinding_t(object):
## class opnds.operand_info_t(object):
## class graph_node(object):

## class code_gen_dec_args_t(object):
## class table_init_object_t(object):
## class bit_group_info_t(object):
## class reg_info_t(object):
## class width_info_t(object):
############################################################################
from __future__ import print_function
import os
import sys
import copy
import glob
import re
import optparse
import collections

def find_dir(d):
    directory = os.getcwd()
    last = ''
    while directory != last:
        target_directory = os.path.join(directory,d)
        if os.path.exists(target_directory):
            return target_directory
        last = directory
        directory = os.path.split(directory)[0]
    return None

mbuild_install_path = os.path.join(os.path.dirname(sys.argv[0]), '..', 'mbuild')
if not os.path.exists(mbuild_install_path):
    mbuild_install_path =  find_dir('mbuild')
sys.path=  [mbuild_install_path]  + sys.path
try:
   import mbuild
except:
   sys.stderr.write("\nERROR(generator.py): Could not find mbuild. " +
                    "Should be a sibling of the xed directory.\n\n")
   sys.exit(1)

xed2_src_path = os.path.join(os.path.dirname(sys.argv[0]))
if not os.path.exists(xed2_src_path):
    xed2_src_path =  find_dir('xed2')
sys.path=  [ xed2_src_path ]  + sys.path
sys.path=  [ os.path.join(xed2_src_path,'pysrc') ]  + sys.path

from genutil import *
import genutil
import operand_storage
import slash_expand
import flag_gen
from verbosity import *
import opnds
import opnd_types
import cpuid_rdr
import map_info_rdr

send_stdout_message_to_file = False
if send_stdout_message_to_file:
   fn = "out"
   set_msgs(open(fn,"w"))
   sys.stderr.write("Writing messages to file: [" + fn + "]\n")

check_python_version(2,4)

from codegen import *
import metaenum
import enum_txt_writer
import chipmodel
import ctables
import ild
import refine_regs
import classifier

#####################################################################
## OPTIONS
#####################################################################
def setup_arg_parser():
    arg_parser = optparse.OptionParser()
    arg_parser.add_option('--debug',
                          action='store_true', 
                          dest='debug', 
                          default=False,
                          help='Start PDB debugger')
    arg_parser.add_option('--limit-enum-strings',
                          action='store_true', 
                          dest='limit_enum_strings', 
                          default=False,
                          help='Save space by limiting the enum strings')
    arg_parser.add_option('--gendir',
                          action='store', 
                          dest='gendir', 
                          default='gen',
                          help='Directory for generated files')
    arg_parser.add_option('--xeddir',
                          action='store',
                          dest='xeddir', 
                          default='',
                          help='Directory for generated files')
    arg_parser.add_option('--input-regs',
                          action='store', 
                          dest='input_regs', 
                          default='',
                          help='Register input file')
    arg_parser.add_option('--input-widths',
                          action='store', 
                          dest='input_widths', 
                          default='',
                          help='Widths input file')
    arg_parser.add_option('--input-extra-widths',
                          action='store', 
                          dest='input_extra_widths',
                          default='',
                          help='Extra widths input file')
    arg_parser.add_option('--input-element-types',
                          action='store', 
                          dest='input_element_types', 
                          default='',
                          help='File with mappings from type names to' + 
                          ' widths and base element types')
    arg_parser.add_option('--input-element-type-base',
                          action='store', 
                          dest='input_element_type_base', 
                          default='',
                          help='new chunk for element type enum')
    arg_parser.add_option('--input-pointer-names',
                          action='store', 
                          dest='input_pointer_names', 
                          default='',
                          help='Pointer names input file for disassembly')
    arg_parser.add_option('--input-fields',
                          action='store', 
                          dest='input_fields', 
                          default='',
                          help='Operand storage description  input file')
    arg_parser.add_option('--input',
                          action='store', 
                          dest='input', 
                          default='',
                          help='Input file')
    arg_parser.add_option('--input-state',
                          action='store', 
                          dest='input_state', 
                          default='xed-state-bits.txt',
                          help='state input file')
    arg_parser.add_option('--inst',
                          action='store', 
                          dest='inst_init_file', 
                          default='xed-init-inst-table.c',
                          help='Instruction table init file')
    arg_parser.add_option('--sout',
                          action='store', 
                          dest='structured_output_fn', 
                          default='xed-sout.txt',
                          help='Emit structured output file')
    arg_parser.add_option('--patterns',
                          action='store',
                          dest='structured_input_fn', 
                          default='',
                          help='Read structured input file')
    arg_parser.add_option('--chip-models',
                          action='store', 
                          dest='chip_models_input_fn', 
                          default='',
                          help='Chip models input file name')
    arg_parser.add_option('--ctables',
                          action='store', 
                          dest='ctables_input_fn', 
                          default='',
                          help='Conversion tables input file name')
    arg_parser.add_option('--isa',
                          action='store', 
                          dest='isa_input_file', 
                          default='',
                          help='Read structured input file containing' + 
                               ' the ISA INSTRUCTIONS() nonterminal')
    arg_parser.add_option('--spine',
                          action='store', 
                          dest='spine', 
                          default='',
                          help='Read the spine file containing the' +
                               ' top-most decoder nonterminal')
    arg_parser.add_option('--print-graph',
                          action='store_true', 
                          dest='print_graph', 
                          default=False,
                          help='Print the graph for each nonterminal (big)')

    arg_parser.add_option('--verbosity', '--verbose', '-v',
                          action='append', 
                          dest='verbosity', 
                          default=[],
                          help='Level of verbosity, repeatable. '  +
                               ' Values=1..7, enc,merge')
    arg_parser.add_option('--no-imm-suffix',
                          action='store_false', 
                          dest='add_suffix_to_imm', 
                          default=True,
                          help='Omit width suffixes from iforms')
    arg_parser.add_option('--cpuid',
                          action='store', 
                          dest='cpuid_input_fn', 
                          default='',
                          help='isa-set to cpuid map input file')
    arg_parser.add_option('--map-descriptions',
                          action='store', 
                          dest='map_descriptions_input_fn', 
                          default='',
                          help='map descriptions input file')
    arg_parser.add_option("--compress-operands", 
                          action="store_true",
                          dest="compress_operands",
                          default=False,
                          help="use bit-fields to compress the "+
                          "operand storage.")
    arg_parser.add_option("--add-orphan-inst-to-future-chip", 
                          action="store_true",
                          dest="add_orphan_inst_to_future_chip",
                          default=False,
                          help="Add orphan isa-sets to future chip definition.")
    return arg_parser

#####################################################################

header_pattern = re.compile(r'[.][Hh]$')
def is_header(fn):
   global header_pattern
   if header_pattern.search(fn):
      return True
   return False

      
############################################################################
# Compiled patterns used in this program
############################################################################
delete_iclass_pattern = re.compile('^DELETE')
delete_iclass_full_pattern = \
    re.compile(r'^DELETE[ ]*[:][ ]*(?P<iclass>[A-Za-z_0-9]+)')

udelete_pattern = re.compile('^UDELETE')
udelete_full_pattern = \
    re.compile(r'^UDELETE[ ]*[:][ ]*(?P<uname>[A-Za-z_0-9]+)')

operand_token_pattern = re.compile('OPERAND')
underscore_pattern = re.compile(r'_')
invert_pattern = re.compile(r'[!]')

instructions_pattern = re.compile(r'INSTRUCTIONS')
equals_pattern = re.compile(r'(?P<lhs>[^!]+)=(?P<rhs>.+)')
not_equals_pattern = re.compile(r'(?P<lhs>[^!]+)!=(?P<rhs>.+)')

quick_equals_pattern= re.compile(r'=')
colon_pattern= re.compile(r'[:]')

bits_and_letters_underscore_pattern = re.compile(r'^[10a-z_]+$')

hex_pattern = re.compile(r'0[xX][0-9A-Fa-f]+')

slash_macro_pattern = re.compile(r'([a-z][/][0-9]{1,2})')
nonterminal_string = r'([A-Z][a-zA-Z0-9_]*)[(][)]'

parens_to_end_of_line = re.compile(r'[(][)].*::.*$') # with double colon
lookupfn_w_args_pattern =  re.compile(r'[\[][a-z]+]')
#nonterminal_start_pattern=re.compile(r'^' + nonterminal_string + r'\s*::')
nonterminal_start_pattern=re.compile(r'::')
nonterminal_pattern=re.compile(nonterminal_string)
nonterminal_parens_pattern = re.compile(r'[(][^)]*[)]')

binary_pattern = re.compile(r'^[01_]+$') # only 1's and 0's
formal_binary_pattern = re.compile(r'^0b[01_]+$') # only 1's and 0's leading 0b
one_zero_pattern = re.compile(r'^[01]') # just a leading 0 or 1
completely_numeric = re.compile(r'^[0-9]+$') # only numbers

# things identified by the restriction_pattern  are the operand deciders:
restriction_pattern = re.compile(r'([A-Z0-9_]+)(!=|=)([bx0-9A-Z_]+)')
all_caps_pattern = re.compile(r'^[A-Z_0-9]+$')

not11_pattern = re.compile(r'NOT11[(]([a-z]{2})[)]')
letter_basis_pattern = re.compile(r'[a-z]')

all_zeros_pattern = re.compile(r'^[0]+$')
type_ending_pattern = re.compile(r'_t$')
uniq_pattern = re.compile(r'_uniq(.*)$')
ntwidth_pattern = re.compile('NTWIDTH')
paren_underscore_pattern = re.compile(r'[(][)][_]+')

all_lower_case_pattern = re.compile(r'^[a-z]+$')


pattern_binding_pattern = re.compile(
               r'(?P<name>[A-Za-z_0-9]+)[\[](?P<bits>[A-Za-z01_]+)]')
uppercase_pattern = re.compile(r'[A-Z]')


reg_operand_name_pattern = re.compile("^REG(?P<regno>[0-9]+)$")
############################################################################

def comment(s):
   return '/* {} */'.format(s)

def all_the_same(lst):
   "return True if all the elements of the list are the same"
   first = lst[0]
   for x in lst:
      if x != first:
         return False
   return True

def pad_to_multiple_of_8bits(x):
   ilen = len(x)
   frac = ilen & 7
   if frac == 0:
      return x
   t = []
   while frac < 8:
      t.append('0')
      frac = frac + 1
   t.extend(x)
   return t

############################################################################
# $$ nonterminal_info_t
class nonterminal_info_t(object):
   def __init__(self,name, type=None):
      self.name = name
      self.type = type
      self.start_node = None
      
   def set_start_node(self,n):
      self.start_node = n
   
   def is_lookup_function(self):
      if self.type != None:
         return True
      return False

# $$ nonterminal_dict_t
class nonterminal_dict_t(object):
   """dictionary holding nonterminal information for code generation"""

   def __init__(self):
      # dictionary of nonterminal_info_t's by short name.
      # nonterminal_info_t has {name, type, start_node}
      self.nonterminal_info = {} 

   def keys(self):
      return list(self.nonterminal_info.keys())
   
   def add_graph_node(self, nt_name, node_id):
      """set the node id in the graph node"""
      if nt_name not in self.nonterminal_info:
         self.add_to_dict(nt_name)
      n = self.nonterminal_info[nt_name]
      n.start_node = node_id

   def get_node(self,nt_name):
      if nt_name in self.nonterminal_info:
         return self.nonterminal_info[nt_name]
      die("Did not find " + nt_name + " in the nonterminal dictionary.")
         
   def add_to_dict(self,short_nt_name, nt_type=None):
      msge("Adding " + short_nt_name + " to nonterminal dict")
      #nonterminal_info_t has {name, type, start_node, encode, decoder}
      new_nt = nonterminal_info_t(short_nt_name, nt_type)
      self.nonterminal_info[short_nt_name] = new_nt

   def record_nonterminal(self,nt_name, nt_type):
      if nt_name:
         if nt_name not in self.nonterminal_info:
            #msge("Adding NT: " + nt_name)
            self.add_to_dict(nt_name, nt_type)
      else:
         die("Bad nonterminal name")


############################################################################
# $$ bit_info_t
class bit_info_t(object):
   """The patterns are built up of bits of various kinds. Normal 1/0
   bits are type bit.  The other kinds of bits are dontcares which are
   letter names, state bits, operand tests and nonterminals.
   """
   
   bit_types = [ 'bit', 'dontcare', 'operand', 'nonterminal'  ]
   def __init__(self, value, btype='bit', pbit=-1):
      self.btype = btype  # See bit_info_t.bit_types
      self.value = value

      # Physical bits are bits that are real. They are offsets from
      # the beginnning of this nonterminal or the last nonterminal.
      
      self.pbit = pbit
      
      self.token = None  # operand decider
      self.test = None   # eq or ne
      self.requirement = None # the value the od must have (or not have)
      
      if btype == 'operand':
         # for operands, we split them in to a token name and a required value.
         #search for FOO=233 or FOO!=233
         m = restriction_pattern.search(value)
         if not m:
            die("bad operand decider: "+  value)
         (token,test,requirement) = m.groups([0,1,2])
         if vod():
            msge("OperandDecider Token= " + token +
                 " Test= " + test + " Requirement= " + requirement)
         self.token = token
         self.requirement = make_numeric(requirement, value)
         if test == '=':
            self.test='eq'
         else:
            self.test='ne'


   def __eq__(self,other):
      if other == None:
         return False
      if self.value == other.value:
         if self.btype == other.btype:
            return True
      return False
   
   def __ne__(self,other):
      if other == None:
         return True
      if self.value != other.value:
         return True
      if self.btype != other.btype:
         return True
      return False
   
   def __str__(self):
      s =  self.btype + '/' + str(self.value)
      if self.pbit != -1:
         s  +=  '/PBIT' + str(self.pbit)
      return s

   def just_bits(self):
      return self.value

   def is_nonterminal(self):
      if self.btype == 'nonterminal':
         return True
      return False

   def is_operand_decider(self):
      if self.btype == 'operand':
         return True
      return False

   def is_dont_care(self):
      if self.btype == 'dontcare':
         return True
      return False
   
   def is_real_bit(self):
      if self.btype == 'dontcare' or self.btype == 'bit':
         return True
      return False
   def is_one_or_zero(self):
      if self.btype == 'bit':
         return True
      return False

   def nonterminal_name(self):
      if self.is_nonterminal():
         g = nonterminal_pattern.search(self.value)
         if g:
            nt_name = g.group(1)
            return nt_name
         else:
            die("Error finding NT name for " + self.value)
      return None

# $$ bits_list_t
class bits_list_t(object):
   """ list of bit_info_t """
   def __init__(self):
      self.bits = []
   def append(self,x):
      self.bits.append(x)
      
   def __str__(self):
      return self.just_bits()

   def just_bits(self):
      """ return a string of just the bits"""
      s = [ x.just_bits() for x in self.bits]
      o  = []
      i = 0
      for b in s:
          o.append(b)
          i = i + 1
          if i == 4:
              i = 0
              o.append('  ')
      return ' '.join(o)

# $$ state_info_t
class state_info_t(object):
   """This is really just a big dictionary for the state (operand
   decider) macro expansion"""
   def __init__(self, name, list_of_str):
      """ takes a name and a string containing our bit strings"""
      self.name = name
      self.list_of_str = []
      # bust up bit strings that come in via the states file.
      # make individual bits and add them to the list of strings.
      for x in list_of_str:
         if formal_binary_pattern.match(x):
            t = re.sub('0b','',x)
            t = re.sub('_','',t)
            self.list_of_str.extend(list(t))
         else:
            self.list_of_str.append(x)


   def dump_str(self):
      s = self.name + ' '
      for w in self.list_of_str:
         s += w + ' '
      return s

############################################################################
      

def pad_pattern(pattern):
   "pad it to a multiple of 8 bits"
   plen = len(pattern)
   if (plen & 7) != 0:
      rem = 8-(plen & 7)
      pattern +=  '-' * rem
   return pattern



def read_state_spec(fn):
   "Return dictionary  of state bits"
   state_bits = {}
   if not os.path.exists(fn):
      die("Could not read file: " + fn)
   lines = open(fn,'r').readlines()
   lines = map(no_comments, lines)
   lines = list(filter(genutil.blank_line, lines))
   for line in lines:
      ## remove comment lines
      #line = no_comments(line)
      #if line == '':
      #   continue
      #msge("STATELINE: [" + line + ']')

      wrds = line.split()
      tag = wrds[0]
      spattern = wrds[1:]

      si = state_info_t(tag,spattern)

      state_bits[tag] = si
      
   return state_bits
      
def compute_state_space(state_dict):
   """Figure out all the values for each token, return a dictionary
   indexed by token name"""

   state_values = collections.defaultdict(set)
   
   for k in state_dict.keys():
      vals = state_dict[k]
      for wrd in vals.list_of_str:
         m = restriction_pattern.search(wrd)
         if m:
            (token,test,requirement) = m.groups([0,1,2])
            if requirement == 'XED_ERROR_GENERAL_ERROR':
                continue
            requirement_base10 = make_numeric(requirement,wrd)
            state_values[token].add(requirement_base10)
         elif formal_binary_pattern.match(wrd):
            pass # ignore these
         elif nonterminal_pattern.match(wrd):
            pass # ignore these
         elif hex_pattern.match(wrd):
            pass # ignore these
         else:
            die("Unhandled state pattern: %s" % wrd)

   output = {}
   for k,v in state_values.items():
       output[k]=list(v)
   return output
         

############################################################################
        
def validate_field_width(agi, field_name, bits):
    b=make_binary(bits)
    n = len(b)
    opnd = agi.operand_storage.get_operand(field_name)
    if n > int(opnd.bitwidth):
        s = ("length of captured field %s[%s] is %d and that exceeds " +
             " operand storage field width %s\n")
        die(s % (field_name, bits, n, opnd.bitwidth))

# $$ prebinding_t
class prebinding_t(object):
   """This is for fields mentioned in the decode pattern. We want to
   bind the bits to the operand storage fields before calling any
   NT/NTLUFs that require these bindings.
   """
   def __init__(self, name):
      self.field_name =  name
      self.bit_info_list = [] # list of bit_info_t's
   def add_bit(self, b):
      self.bit_info_list.append(b)
   
   def is_constant(self):
      for bi in self.bit_info_list:
           if bi.is_dont_care():
               return False #dontcare in prebinding
      return True
   
   def get_value(self):
       value = ''
       for bi in self.bit_info_list:
           value += bi.just_bits()
       return value
   
   def __str__(self):
      s = []
      s.append(self.field_name)
      s.extend( [str(x) for x in self.bit_info_list ] )
      return ', '.join(s)

def get_btype(b):
   if b == '1' or b == '0':
      return 'bit'
   return 'dontcare'

def parse_opcode_spec(agi, line, state_dict):
    """Given a string of bits, spaces and hex codes, canonicalize it
    to useful binary, return a list of single char bits or letters, or
    nonterminals.

    @rtype:  tuple
    @return: (list of bits, -- everything is raw bits at this level
              list of operand binding tuples,--  same info as the prebindings
              list bit_info_t, -- interpreted bits with types and positions
              dict of prebinding_t,  -- dictionary of the captured fields 
                                        pointing to bits
              xed_bool_t otherwise_ok)
    """
    # if there are any trailing underscores after a nonterminal paren,
    # convert them to spaces.
    b = paren_underscore_pattern.sub('() ', line)
    # if there are any leading underscores before, convert them to spaces

    extra_bindings = [] # the inline captures become "extra" operands later
    if vparse():
        msgb("PARSE OPCODE SPEC " + line)
    # expand things from the state dictionary
    wrds = []
    for w in b.split():
       if w in state_dict:
          wrds.extend(copy.deepcopy(state_dict[w].list_of_str))
       else:
          wrds.append(w)
    all_bits = []
    #
    # 1. hex byte
    # 2. immediate capture IMM(a-z,0-9) ??? IS THIS USED???  
    #                      IMM(a,9) -- old form of slash
    # 3. slash pattern (just more letter bits)
    # 4. pattern binding eg: MOD[mm] or MOD[11_]
    # 5. nonterminal
    # Then EXPAND
    all_bit_infos = []
    all_prebindings = {}
    bcount = 0 # bit count
    for w in wrds:
       if w == 'otherwise':
          return (None,None,None,None,True)
          
       if hex_pattern.match(w):
          bits = pad_to_multiple_of_8bits(hex_to_binary(w))
          for b in bits:
             all_bit_infos.append(bit_info_t(b,'bit',bcount))
             bcount += 1
          all_bits.extend(bits)
          continue

       # inline captures MOD[mm] REG[rrr] RM[nnn] or REG[111] etc. --
       # can be constant
       pb = pattern_binding_pattern.match(w)
       if pb:
          #msgb("PATTERN BINDING", w)
          (field_name,bits) = pb.group('name','bits')
          if uppercase_pattern.search(bits):
              die("\n\nUpper case letters in capture pattern" +
                  ": %s in line\n\n %s\n\n" % ( w, line))

          validate_field_width(agi, field_name, bits)
          extra_bindings.append( (field_name,bits) )
          prebinding = prebinding_t(field_name)
          bits_str = make_binary(bits)
          bits_list = list(bits_str)
          #print "BITS %s -> %s" % ( bits, bits_str)
          for b in bits_list:
             #btype is either bit or dontcare
             btype = get_btype(b)
             bi = bit_info_t(b,btype,bcount)
             bcount += 1
             prebinding.add_bit(bi)
             all_bit_infos.append(bi)
          all_prebindings[field_name] = prebinding
          all_bits.extend(bits_list)
          continue
       if nonterminal_pattern.search(w):
          # got a nonterminal 
          bits = [ w ]
          all_bit_infos.append(bit_info_t(w,'nonterminal', bcount))
          bcount += 1
          all_bits.extend(bits)
          continue


       m  = restriction_pattern.search(w)
       if m:
          (token,test,requirement) = m.groups([0,1,2])
          # got an operand-decider (requirement)
          #msge("RESTRICTION PATTERN " +  str(w))
          # we skip some field bindings that are only for the encoder.
          # They are denoted DS in the fields data-files.
          if agi.operand_storage.decoder_skip(token):
              #msge("SKIPPING RESTRICTION PATTERN " +  str(w))
              continue
          
          # avoid adding redundant restriction patterns
          if w not in all_bits:
              # bit_info_t constructor reparses restriction pattern
              all_bit_infos.append(bit_info_t(w,'operand', bcount))
              bcount += 1
              all_bits.extend([ w ])
          continue
       
       if formal_binary_pattern.search(w):
           bits = make_binary(w)
           all_bits.extend(bits)
           for b in list(bits):
               btype = get_btype(b)
               all_bit_infos.append(bit_info_t(b,btype,bcount))
               bcount += 1
           continue

       # remove the underscores now that we know it is a pattern
       w = w.replace('_','')
       # some binary value or letter
       bits = [ str(x) for x in list(w) ]
       all_bits.extend(bits)
       for b in list(bits):
          btype = get_btype(b)
          all_bit_infos.append(bit_info_t(b,btype,bcount))
          bcount += 1


    # We now also have a a list of bit_info_t's in all_bit_infos and a
    # dictionary of prebinding_t's in all_prebindings.
       
    return (all_bits, extra_bindings, all_bit_infos, all_prebindings, False)

def add_str(s, name, value):
   t =  s + '%-15s' % (name) + ': '
   if type(value) == list:
      for q in value:
         t += q + ' ' 
   else:
       t += value
   t += '\n'
   return t

def add_str_list(s, name, values):
   s = s + '%-15s' % (name) + ': '
   for v in values:
      s = s + v + ' '
   s = s + '\n'
   return s

      
#for the first not commented, non-empty line from lines, 
#return if regexp.search succeeds
def accept(regexp, lines):
   #msge("In accept!")
   line = ''
   while line == '':
      if lines == []:
         return None
      line = no_comments(lines[0])
      line = line.strip()
      lines.pop(0)
   #msge("Testing line :" + line)
   if re.search(regexp,line):
      return True
   return False
   

def read_str(lines,name):
   "Read a line emitted by add_str() above. Split on 1st colon"
   line = ''
   while line == '':
      if lines == []:
         return None
      line = no_comments(lines[0])
      line = line.strip()
      lines.pop(0)
   #msge("Reading line: " + line)
   (iname, rest) = line.split(':',1)
   iname = iname.strip()
   rest = rest.strip()
   if iname != name:
      die('Misparsed structured input file. Expecting: [' 
          + name + '] Observed: [' + iname + ']')
   return rest

def read_str_simple(lines):
   "Read a line emitted by add_str() above. Split on 1st colon"
   line = ''
   while line == '':
      if lines == []:
         return None
      line = no_comments(lines[0])
      line = line.strip()
      lines.pop(0)
   return line

############################################################################
def parse_extra_operand_bindings(agi, extra_bindings):
   """Add the captures as operands"""
   operands = []
   operand_storage_dict = agi.operand_storage.get_operands()
   for (name,bits) in extra_bindings:
      # FIXME handle something other than bits
      bits_str = make_binary(bits)
      # FIXME: add "i#" width codes for the captured operands!
      try:
         bits = operand_storage_dict[name].bitwidth
         oc2= "i%s" % (bits)
      except:
         die("Could not find field width for %s" % (name))

      new_operand = opnds.operand_info_t(name,
                                         'imm',
                                         list(bits_str),
                                         vis='SUPP', 
                                         oc2=oc2)
      # DENOTE THESE AS INLINE TO ALLOW EARLY CAPTURING
      if vbind():
         msge("INLINE OPERAND %s" % (name))
      new_operand.inline = True
      operands.append(new_operand)
   return operands

#NOTE: class attributes are not like static member data in C++. They
#are per object type. So if you derive a new class bar from class foo,
#then the instance (attribute) variables of class foo and class bar
#are disjoint.
global_inum = 0  

# $$ partitionable
class partitionable_info_t(object):
   def new_inum(self):
      global global_inum
      self.inum = global_inum
      global_inum += 1
   
   def __init__(self, name='', ipattern_input='', operands_input=None):

      self.new_inum()
      self.name = name
      self.input_str = ''

      self.ipattern_input = ipattern_input
      self.ipattern =  None # bits_list_t()
      self.prebindings = None # dictionary 

      if operands_input:
          self.operands_input = operands_input
      else:
          self.operands_input = []

      self.operands = [] # list of opnds.operand_info_t's 

      # FOR HIERARCHICAL RECORDS -- THESE GET SPLIT OFF AFTER RECORD-READ
      self.extra_ipatterns = []
      self.extra_operands  = []
      self.extra_iforms_input  = []

      # When we consume a prefix, we must apply state modifications
      # and that might cause us to jump to a different part of the
      # graph, so we must retraverse the state-portion of the graph,
      # but remember what byte we were processing and pick up at the
      # next byte which may or may not be a prefix.
      self.reset_for_prefix = False


      self.encoder_func_obj = None # an instance of a class function_object_t
      
      self.encoder_operands = None

      self.otherwise_ok = False

      # simple nonterminals: either all nonterminals or all operand deciders.
      self.all_nonterminals = None
      self.all_operand_deciders = None

   def get_iclass(self):
       if field_check(self,'iclass'):
           return self.iclass
       return '*NO-ICLASS*'
      
   def refine_parsed_line(self, agi, state_dict):
      """Refine the ipattern_input to ipattern, parse up operands"""
      (simple_pattern,
       extra_bindings,
       all_bit_infos,
       all_prebindings,
       otherwise_ok) = parse_opcode_spec(agi,self.ipattern_input, state_dict)
      
      if otherwise_ok: # FIXME: 2008-09-25 - need to remove this for more
                       #                     general "otherwise" handling
         self.otherwise_ok = True
         return 
      
      self.ipattern = bits_list_t()
      self.ipattern.bits = all_bit_infos
      self.prebindings = all_prebindings

      (self.operands, self.reset_for_prefix) = \
                       parse_operand_spec(agi, self.operands_input)
      if extra_bindings:
         extra_operands = parse_extra_operand_bindings(agi,extra_bindings)
         self.operands.extend(extra_operands)

      self.check_for_simple_nts()
      
   def check_for_simple_nts(self):
      """Check for NTs that do not accept bits. We'll make them in to
      fast functions"""
      all_operand_deciders = True
      all_nonterminals = True
      for bi in self.ipattern.bits:
         if not bi.is_operand_decider():
            all_operand_deciders = False
         if not bi.is_nonterminal():
            all_nonterminals = False

      self.all_nonterminals = all_nonterminals
      self.all_operand_deciders = all_operand_deciders

      
   def __str__(self):
      return self.dump_str()
   
   def dump_str(self, pad='',brief=None):
      return self.input_str 

   def dump_structured(self,pad=''):
      lst = []
      s = pad
      s += self.ipattern_input + ' | '
      s += ' '.join(self.operands_input)
      lst.append( s )
      return lst
   
   def dump(self, pad=''):
      for s in self.dump_structured(pad):
         msge(s)

      s = ' ipatternbits:' + str(len(self.ipattern.bits))
      msge("BITLENGTHS: " + s)
      s = ''
      for b in self.ipattern.bits:
            s += ' ' + b.value 

      msge("GRAPHBITS: " + s)

############################################################################
    
# indicates which fields are required in the input parsing
structured_input_tags = {'ICLASS':          True,  
                         'UNAME':           False, 
                         'CATEGORY':        True,  
                         'EXTENSION':       True,  
                         'ISA_SET':         False, 
                         'STATE':           False, 
                         'PATTERN':         True,  
                         'ATTRIBUTES':      False, 
                         'OPERANDS':        False, 
                         'UCODE':           False, 
                         'FLAGS':           False, 
                         'VERSION':         False, 
                         'CPL':             False, 
                         'COMMENT':         False, 
                         'EXCEPTIONS':      False, 
                         'DISASM':          False, 
                         'DISASM_INTEL':    False, 
                         'DISASM_ATTSV':    False, 
                         'IFORM':           False  
                         }


# $$ instruction_info_t
class instruction_info_t(partitionable_info_t):
   def __init__(self,
                iclass='',
                ipattern_input='',
                operands_input=None,
                category='DEFAULT',
                extension='DEFAULT',
                version = 0,
                isa_set = None):
      partitionable_info_t.__init__(self, iclass,ipattern_input, operands_input)
      self.iclass = iclass
      self.uname = None
      self.ucode = None
      self.comment = None
      self.exceptions = None      

      # Default version. Newer versions replace older versions
      self.version = version 

      self.category = category
      self.extension = extension
      self.isa_set = isa_set
      self.cpl = None
      self.attributes = None
      self.flags_input = None
      self.flags_info = None  # flag_gen.flags_info_t class
      
      self.iform = None
      self.iform_input = None
      self.iform_num = None
      self.iform_enum = None

   def add_attribute(self,s):
      if self.attributes:
         self.attributes.append(s)
      else:
         self.attributes = [s]

   def add_stack_attribute(self, memop_index):
      for op in self.operands:
         if op.bits == 'XED_REG_STACKPUSH':
            self.add_attribute('STACKPUSH%d' % (memop_index))
            return
         elif op.bits == 'XED_REG_STACKPOP':
            self.add_attribute('STACKPOP%d' % (memop_index))
            return
      die("Did not find stack push/pop operand")

   def is_vex(self):
       for bit in self.ipattern.bits: # bit_info_t
           #print("XXR: {} {}  {} {} {}".format(self.iclass, bit.btype, bit.token, bit.test, bit.requirement))
           if bit.btype == 'operand' and  bit.token == 'VEXVALID' and bit.requirement == 1 and bit.test == 'eq':
               return True
       return False
   def is_evex(self):
       for bit in self.ipattern.bits: # bit_info_t
           if bit.btype == 'operand' and bit.token == 'VEXVALID' and bit.requirement == 2 and bit.test == 'eq':
               return True
       return False
   def get_map(self):
       for bit in self.ipattern.bits: # bit_info_t
           if bit.token == 'MAP' and bit.test == 'eq':
               return bit.requirement
       return 0


   def dump_structured(self):
       """Return a list of strings representing the instruction in a
       structured way"""

       slist = []

       slist.append('{\n')

       s = add_str('', 'ICLASS', self.iclass)
       slist.append(s)

       if self.uname:
           s = add_str('', 'UNAME', self.uname)
           slist.append(s)
 
       if self.version != 0:
          s = add_str('','VERSION', str(self.version))
          slist.append(s)
  
          s = add_str('','CATEGORY', self.category)
          slist.append(s)
  
          s = add_str('','EXTENSION', self.extension)
          slist.append(s)
          s = add_str('','ISA_SET', self.isa_set)
          slist.append(s)
          s = add_str('','PATTERN', self.ipattern_input)
          slist.append(s)
          if self.cpl:
              s = add_str('','CPL', self.cpl)
              slist.append(s)
  
  
          if self.attributes:
              s = add_str('','ATTRIBUTES', self.attributes)
              slist.append(s)
          if self.ucode:
              s = add_str('','UCODE', self.ucode)
              slist.append(s)
          if self.comment:
              s = add_str('','COMMENT', self.comment)
              slist.append(s)
          if self.exceptions:
              s = add_str('','EXCEPTIONS', self.exceptions)
              slist.append(s)
          if self.exceptions:
              s = add_str('','DISASM_INTEL', self.disasm_intel)
              slist.append(s)
          if self.exceptions:
              s = add_str('','DISASM_ATTSV', self.disasm_att)
              slist.append(s)
          if self.iform_input:
              s = add_str('','IFORM_INPUT', self.iform_input)
              slist.append(s)
          if self.iform:
              s = add_str('','IFORM', self.iform)
              slist.append(s)
  
          if self.flags_input:
              s = add_str('','FLAGS', self.flags_input)
              slist.append(s)
 
       t = ''
       for op in self.operands_input:
           t = t + op + ' '
       s = add_str('','OPERANDS', t)
       slist.append(s)
         
       slist.append('}\n')
       return slist

   def read_structured_flexible(self,lines):
      debug = False
      accept(r'[{]', lines)
      reached_closing_bracket = False
      # FIXME add more error checking
      structured_input_dict = dict(zip(list(structured_input_tags.keys()),
                                       len(structured_input_tags)*[False]))
      found_operands = False
      filling_extra = False # when there is more than one pattern/operand/iform per {...} definition
      while 1:
         line = read_str_simple(lines)
         if debug:
            msge("Reading: " + line)
         if not line:
            if debug:
               msge("Dead line - ending")
            break
         if line == '}':
            if debug:
               msge("Hit bracket")
            reached_closing_bracket = True
            break
         #print "READING [%s]" % (line)
         if colon_pattern.search(line):
            (token, rest ) = line.split(':',1)
            token = token.strip()
            rest = rest.strip()
            if rest.startswith(':'):
                die("Double colon error {}".format(line))

            # Certain tokens can be duplicated. We allow for triples
            # of (pattern,operands,iform). The iform is optional.  If
            # we see "pattern, operand, pattern" without an
            # intervening iform, the iform is assumed to be
            # auto-generated. But we must have an operand line for
            # each pattern line.
            #msge("LINE: %s" % (line))
            if token in structured_input_dict:
               if structured_input_dict[token] == True:
                  if token in [ 'PATTERN', 'OPERANDS', 'IFORM']:
                     filling_extra = True
                  else:
                     die("Duplicate token %s in entry:\n\t%s\n" % (token, line))
            structured_input_dict[token] =True
            #msge("FILLING EXTRA = %s" %( str(filling_extra)))
                  
            if token == 'ICLASS':
               self.iclass = rest
               if viclass():
                  msgb("ICLASS", rest)

            elif token == 'CATEGORY':
               self.category = rest
            elif token == 'CPL':
               self.cpl = rest
            elif token == 'EXTENSION':
               self.extension = rest

               # the isa set defaults to the extension. We can override
               # the isa set with the ISA_SET token.
               if self.isa_set == None:
                   self.isa_set = self.extension

            elif token == 'ISA_SET':
               self.isa_set = rest
            elif token == 'ATTRIBUTES':
               self.attributes = rest.upper().split()
            elif token == 'VERSION':
               self.version = int(rest)
            elif token == 'FLAGS':
               self.flags_input = rest
               self.flags_info = flag_gen.flags_info_t(self.flags_input)
               if vflag():
                  msge("FLAGS parsed = %s" % str(self.flags_info))
            elif token == 'PATTERN':
               if filling_extra:
                  self.extra_ipatterns.append(rest)
                  #msge("APPENDING None TO IFORMS INPUT")
                  self.extra_iforms_input.append(None)
                  self.extra_operands.append(None)
               else:
                  self.ipattern_input = rest
               found_operands=False
            elif token == 'OPERANDS':
               if filling_extra:
                  # overwrite the one that was added when we had an
                  # extra pattern.
                  if len(self.extra_operands) == 0:
                     die("Need to have a PATTERN line before the " + 
                         "OPERANDS line for " + self.iclass)
                  self.extra_operands[-1] = rest.split()
               else:
                  self.operands_input = rest.split()
               found_operands=True
            elif token == 'UCODE':
               self.ucode = rest
            elif token == 'COMMENT':
               self.comment = rest
            elif token == 'EXCEPTIONS':
               self.exceptions = rest
            elif token == 'DISASM':
               self.disasm_intel = rest
               self.disasm_att = rest
            elif token == 'DISASM_INTEL':
               self.disasm_intel = rest
            elif token == 'DISASM_ATTSV':  # AT&T System V
               self.disasm_att = rest
            elif token == 'UNAME':
               self.uname = rest
               if viclass():
                  msgb("UNAME", rest)

            elif token == 'IFORM':
               if filling_extra:
                  if len(self.extra_iforms_input) == 0:
                     die("Need to have a PATTERN line before " +
                         "the IFORM line for " + self.iclass)
                  self.extra_iforms_input[-1] = rest
               else:
                  self.iform_input = rest
            else:
               setattr(self,token,rest.strip())
               # die("Unhandled token in line: " + line)
         else:
            print("NEXT FEW LINES: ")
            for x in lines[0:20]:
               print("INPUT LINE: %s" % (x.strip()))
            die("Missing colon in line: " + line)

      if reached_closing_bracket:
         if found_operands == False:
            die("Did not find operands for " + self.iclass)
         for k in  structured_input_dict.keys():
            if structured_input_dict[k] == False:
               if structured_input_tags[k]:
                  die("Required token missing: "+ k)

         if debug:
            msge("\tReturning...")
         return True
      return False
   
   def add_scalable_attribute(self, scalable_widths, agi):
      """Look for operations that have width codes that are scalable
      width codes (z,v,a,p,p2,s,spw8,spw,spw3,spw2,
      etc. (auto-derived) , and add an attribute SCALABLE"""
      
      scalable = False

      for op in self.operands:
         if op.oc2:
            s= op.oc2.upper()
            #msge("RRR Checking for %s in %s" % (s, str(scalable_widths)))
            if s in scalable_widths:
               scalable=True
               break

         if op.lookupfn_name:
            #msge("OPNAME: " + op.lookupfn_name)
            scalable =  look_for_scalable_nt(agi, op.lookupfn_name)
            if scalable:
               break

      if scalable:
         s  = "SCALABLE"
         self.add_attribute(s)


   
   def add_fixed_base_attribute(self):
      """Look for STACKPUSH/STACKPOP operands and then add an
      attribute that says fixed_base0 or fixed_base1 depending on
      which base reg has the SrSP operand."""
      stack_memop_indx = -1
      if vattr():
         msgb("ATTRIBUTE-FOR-STACKOP: CHECKING", self.iclass)
      for op in self.operands:
         if op.is_ntluf():
            if vattr():
               msgb("ATTRIBUTE-NTLUF",  "%s = %s" % (op.name,op.lookupfn_name))
            if op.lookupfn_name == 'SrSP':
               if op.name == 'BASE0':
                  stack_memop_indx = 0
               elif op.name == 'BASE1':
                  stack_memop_indx = 1
               else:
                  pass # skip other fields
      if stack_memop_indx != -1:
         if vattr():
            msgb("ATTRIBUTE-FOR-STACKOP", 
                 "%s memop index %s" % (self.iclass, stack_memop_indx))
         s  = "FIXED_BASE%d" % stack_memop_indx
         self.add_attribute(s)
         self.add_stack_attribute(stack_memop_indx)


   def __str__(self):
      return self.dump_str()
   
   def dump_str(self, pad='', brief=False):
      s = []
      s.append(pad)
      s.append(self.iclass)
      if self.uname:
          s.append(" uname=%s" % str(self.uname))
      s.append(" inum=%s " % str(self.inum))
      if field_check(self,'iform') and self.iform:
          s.append(" iform=%s " % str(self.iform))
      if field_check(self,'iform_input') and self.iform_input:
          s.append(" iform_input=%s " % str(self.iform_input))
      if field_check(self,'isa_set') and self.isa_set:
          s.append(" isa_set=%s " % str(self.isa_set))
      s.append("pattern len=%d\n" % len(self.ipattern.bits))
      s.append(" %s ipattern: %s\n" % (pad,self.ipattern.just_bits()) )
      
      if brief:
          return ''.join(s)
      if self.prebindings:
         s.append('prebindings: \n\t' + 
                  '\n\t'.join( [str(x) for x in list(self.prebindings.values())]) + '\n')
      for op in self.operands:
         s.append(pad)
         s.append("   ")
         s.append(op.dump_str(pad))
         s.append("\n")
      return ''.join(s)
        

def look_for_scalable_nt(agi, nt_name):
   """Look for a nonterminal that is sensitive to EOSZ. It looks
   recursively at NTs in the patterns, but that does not occur in x86."""
   try:
      gi = agi.generator_dict[nt_name]
   except:
      die("Generator not found for nt_name: %s" % (nt_name))
      
   for rule in gi.parser_output.instructions:
      for b in rule.ipattern.bits:
         if b.token == 'EOSZ':
            return True
         elif b.is_nonterminal():
            r_nt_name = b.nonterminal_name()
            if look_for_scalable_nt(agi, r_nt_name):  # RECUR
               return True
   return False



def mk_opnd(agi, s, default_vis='DEFAULT'):
    op = opnds.parse_one_operand(s,
                                 default_vis,
                                 agi.xtypes,
                                 agi.widths_dict)
    return op

def add_flags_register_operand(agi,ii):
   """If the instruction has flags, then add a flag register operand."""
   if field_check(ii,'flags_info') and \
           ii.flags_info and ii.flags_info.x86_flags():
      rw = ii.flags_info.rw_action()
      (memidx_dummy,regidx) = find_max_memidx_and_regidx(ii.operands)
      s = "REG%d=rFLAGS():%s:SUPP" % ( regidx, rw )
      if vflag():
         msgb("RFLAGS-APPEND", "%s <-- %s" % ( ii.iclass, s))
      op = mk_opnd(agi,s)
      if op:
          ii.operands.append(op)

def add_flags_register_operand_all(agi,parser):
    for ii in parser.instructions:
        add_flags_register_operand(agi,ii)


def rewrite_stack_push(op,memidx,regidx):
   s = []
   #s.append("REG%d=SrSP():rw:SUPP" % (regidx))
   s.append("MEM%d:w:%s:SUPP" % (memidx, op.oc2))
   s.append("BASE%d=SrSP():rw:SUPP" % (memidx))
   if memidx == 0:
      s.append("SEG0=FINAL_SSEG0():r:SUPP") # note FINAL_SSEG0()
   else:
      s.append("SEG1=FINAL_SSEG1():r:SUPP") # note FINAL_SSEG1() ***
   return s
   
def rewrite_stack_pop(op,memidx,regidx):
   s = []
   #s.append("REG%d=SrSP():rw:SUPP" % (regidx))
   s.append("MEM%d:r:%s:SUPP" % (memidx, op.oc2))
   s.append("BASE%d=SrSP():rw:SUPP" % (memidx))
   if memidx == 0:
      s.append("SEG0=FINAL_SSEG0():r:SUPP") # note FINAL_SSEG()
   else:
      s.append("SEG1=FINAL_SSEG1():r:SUPP") # note FINAL_SSEG1() ***
   return s
   


def expand_stack_operand(op, memidx, regidx):
   """Replace the STACKPUSH and STACKPOP operands by a sequence of operands
    @type  op: opnds.operand_info_t
    @param op: input operand that is a stack push or pop

    @type  memidx: integer
    @param memidx: index of the memop we should use, either 0 or 1.

    @type  regidx: integer
    @param regidx: index of the first register we should use for 
                   the rSP() operand

    @rtype: [ strings ]
    @return: additional text of operands (to be processed) for the
                           stack pointer access, memop, base, & seg.
   """
   if vstack():
      msgb("EXPANDING STACK OP", "%s memidx %d regidx %d"
           % (op.bits, memidx, regidx))
   if op.bits == 'XED_REG_STACKPUSH':
      out = rewrite_stack_push(op,memidx,regidx)
   elif op.bits == 'XED_REG_STACKPOP':
      out = rewrite_stack_pop(op,memidx,regidx)
   else:
      out = None
   if vstack():
      msgb("STACKOPS", str(out))
   return out
   

    

def find_max_memidx_and_regidx(operands):
   "find the maximum memidx and regidx"
   memidx = 0
   regidx = 0
   verbose = False
   for op in operands:
      if verbose:
         msgb("OPNAME", op.name)
      if op.name == 'MEM0':
         memidx = 1
      elif op.name == 'MEM1':
         memidx = 2 # this should cause an error if it is ever used
      rnm = reg_operand_name_pattern.match(op.name)
      if rnm:
         current_regidx = int(rnm.group('regno'))
         if verbose:
            msgb("COMPARE REGS", "current %d max %d" % 
                 ( current_regidx, regidx))
         if current_regidx >= regidx:
            if verbose:
               msgb("BUMPING regidx")
            regidx = current_regidx+1
   return (memidx, regidx)

def parse_operand_spec(agi,operand_spec):
    """build a list classes holding operand info"""
    #print str(operand_spec)
    operands = []
    reset_any = False
    for w in operand_spec:
        op = mk_opnd(agi,w)
        if op:
            if op.type == 'xed_reset':
               reset_any = True
            else:
               operands.append(op)
    ##############################################################
    # expand stack operands
    #
    found_stackop = None
    for op in operands:
       # msgb("BITS", str(op.bits))
       if op.bits == 'XED_REG_STACKPUSH' or op.bits == 'XED_REG_STACKPOP':
          found_stackop = op
          break
    if found_stackop:
       (memidx, regidx) = find_max_memidx_and_regidx(operands)
       new_strings = expand_stack_operand(found_stackop, memidx, regidx)
       # make new operands based on these strings.
       if new_strings:
          for s in new_strings:
             new_op = mk_opnd(agi,s) 
             if new_op:
                 operands.append(new_op)
    #
    ##############################################################
    return (operands, reset_any)

    
##################################################################
# Structured input / output of  instructions
##################################################################


def is_nonterminal_line(s):
   g = nonterminal_start_pattern.search(s)
   if g:
      # remove everything from the parens to the end of the line
      # including two colons
      t = parens_to_end_of_line.sub('', s)
      wrds = t.split()
      short_nt_name = wrds[-1]
      if len(wrds) == 1:
         type = None
         msge("NONTERMINAL: " + short_nt_name + " notype")
      else:
         type = wrds[0]
         msge("NONTERMINAL: " + short_nt_name + " type= " + type)
      return (short_nt_name, type)
   return (None,None)

def remove_instructions(agi):
    for g in agi.generator_list:
        ii = g.parser_output.instructions[0]
        if field_check(ii,'iclass'):
            g.parser_output = remove_overridden_versions(g.parser_output)

def remove_overridden_versions(parser):
   """Remove instructions that have newer versions using a dictionary
   of lists."""
   d = {} 
   for ii in parser.instructions:
      if ii.iclass in parser.deleted_instructions:
         continue # drop this record
      if ii.uname  in parser.deleted_unames:
         msge("DROPPING UNAME %s" % (ii.uname))
         continue # drop this record
      if ii.iclass in d:
         if ii.version == d[ii.iclass][0].version:
            d[ii.iclass].append(ii)
         elif ii.version > d[ii.iclass][0].version:
            # we have an updated version. drop the old stuff and start over
            del d[ii.iclass]
            d[ii.iclass] = [ii] 
         else:
            pass # drop this record
      else:
         # add first element of this iclass
         d[ii.iclass] = [ii]

   iis = []
   for ilist in list(d.values()):
      iis.extend(ilist)
   parser.instructions = iis
   return parser

def read_input(agi, lines):
   """Read the input from a flat token-per-line file or a structured
   ISA input file"""
   msge("read_input " + str(global_inum))
   # first line must be a nonterminal
   (nt_name, nt_type) = is_nonterminal_line(lines[0])
   if not nt_name:
      die("Did not find a nonterminal: " + lines[0])

   parser = None
   # see if we  have encountered this nonterminal before
   try:
      gi = agi.generator_dict[nt_name]
      # we have a re-occurrence of an earlier nonterminal. We extend it now.
      msge("FOUND OLD PARSER FOR " + nt_name)
      parser = gi.parser_output
   except:
      # need to make a new generator & parser
      parser = parser_t()
      parser.nonterminal_line = lines[0].strip()
      parser.nonterminal_name = nt_name
      parser.nonterminal_type = nt_type
      gi = agi.make_generator(nt_name)
      gi.parser_output = parser
      agi.nonterminal_dict.record_nonterminal(nt_name, nt_type)
      
   msge("Nonterminal " + parser.nonterminal_line)
   msge("Nonterminal name " + parser.nonterminal_name)
   lines.pop(0)

   # The {...} defined "instruction" patterns must have the substring
   # "INSTRUCTIONS" in their name.
   
   if instructions_pattern.search(parser.nonterminal_name):
       nlines = read_structured_input(agi,
                                      agi.common.options,
                                      parser,
                                      lines,
                                      agi.common.state_bits)
   else:
       nlines = read_flat_input(agi, 
                                agi.common.options,
                                parser,
                                lines,
                                agi.common.state_bits)
   return nlines
   

def read_structured_input(agi, options, parser, lines, state_dict):
   msge("read_structured_input")
   while len(lines) != 0:
      if verb4():
         msge("NEXTLINE " + lines[0])
      first_line = no_comments(lines[0])
      if first_line == '':
         lines.pop(0)
         continue
      first_line  = slash_expand.expand_all_slashes(first_line)
              
      if udelete_pattern.search(first_line):
         m = udelete_full_pattern.search(first_line)
         uname = m.group('uname')
         msge("REGISTERING UDELETE %s" % (uname))
         parser.deleted_unames[uname] = True
         lines.pop(0)
      elif delete_iclass_pattern.search(first_line):
         m = delete_iclass_full_pattern.search(first_line)
         iclass = m.group('iclass')
         parser.deleted_instructions[iclass] = True
         lines.pop(0)
      
      
      elif nonterminal_start_pattern.search(first_line):
         msge("Hit a nonterminal, returning at: " + first_line )
         break
      else:
         ii = instruction_info_t()
         okay = ii.read_structured_flexible(lines)
         if okay:
            #mbuild.msgb("PATTERN:", ii.ipattern_input)
            # when there are multiple patterns/operands in the
            # structured input, we flatten them out here, making
            # multiple complete records, one per
            # pattern/set-of-operands.
            flat_ii_recs = expand_hierarchical_records(ii)

            # finalize initialization of instruction records
            for flat_ii in flat_ii_recs:
               flat_ii.refine_parsed_line(agi,state_dict)
               flat_ii.add_fixed_base_attribute()
               flat_ii.add_scalable_attribute(agi.scalable_widths, agi)
               if flat_ii.otherwise_ok:
                  parser.otherwise_ok = True # FIXME 2008-09-25: is this used?
               else:

                  parser.instructions.append(flat_ii)
                  
   
   msge("parser returning with " + str(len(lines)) + ' lines remaining.')
   return lines
   
##################################################################

def junk_line(line):
    if len(line) == 0:
        return True
    if line[0]  == '#':
        return True
    return False

# $$ parse_t
class parser_t(object):
   def __init__(self):
      self.nonterminal_line = ''
      self.nonterminal_name = ''
      # the actual nonterminal_type is NOW IGNORED 2008-07-22 I take
      # the value from the operand storage fields type spec.  I still
      # use the existence of the nonterminal return type to indicate
      # that an NT is a NTLUF.. FIXME!!
      self.nonterminal_type = None # for lookup functions only

      # list of partitionable_info_t or instruction_info_t, which is a
      # subclass of partitionable_info_t.
      self.instructions = []

      self.deleted_instructions = {}
      self.deleted_unames = {}      
      
      # if epsilon actions result in errors, otherwise_ok is False. If
      # epsilon actions result in no-error, then otherwise_ok should
      # be set to true.
      self.otherwise_ok = False


   def is_lookup_function(self):
      if self.nonterminal_type != None:
         return True
      return False
   
   def dump_structured(self,fp):
      "Print out the expanded records."
      for ii in self.instructions:
         slist  = ii.dump_structured()
         for s in slist:
            fp.write(s)
         fp.write('\n')


   def print_structured_output(self,fp):
      "Print the input in a structuctured token-per-line fashion"
      fp.write(self.nonterminal_line + "\n")
      fp.write("\n")
      self.dump_structured(fp)

         

def read_flat_input(agi, options, parser, lines,state_dict):
   """These are the simple format records, one per line. Used for
   non-instruction things to make partitionable objects"""
   msge("read_flat_input " + str(global_inum))
   while len(lines) > 0:
      if verb4():
         msge("NEXTLINE " + lines[0])
      first_line = no_comments(lines[0])
      if first_line == '':
         lines.pop(0)
         continue
      first_line  = slash_expand.expand_all_slashes(first_line)
      if nonterminal_start_pattern.search(first_line):
         msge("Hit a nonterminal, returning at: " + first_line )
         break

      try:
         (new_bits, bindings) = first_line.split('|')
      except ValueError:
         die('Could not split line in to 2 pieces based on vertical bar: [' +
             first_line + ']')
      
      (opcode_spec,
       extra_bindings,
       all_bit_infos,
       all_prebindings,
       otherwise_ok) = parse_opcode_spec( agi, new_bits, state_dict)

      if otherwise_ok:
         parser.otherwise_ok = True # FIXME 2008-09-25 need to change this
                                    #  if 'otherwise' node have RHS support.
         lines.pop(0)
         continue 
      
      operands_input = bindings.split()
      (operands, reset_for_prefix) = parse_operand_spec(agi, operands_input)
      if extra_bindings:
         extra_operands = parse_extra_operand_bindings(agi, extra_bindings)
         operands.extend(extra_operands)

      # now put  opcode_spec, and operands in to a data structure

      ## FIXME add a table and line number for the name?
      pi = partitionable_info_t('',new_bits, operands_input)
      pi.input_str = first_line

      pi.ipattern = bits_list_t()
      pi.ipattern.bits = all_bit_infos

      pi.prebindings  = all_prebindings

      pi.operands = operands # list of opnds.operand_info_t
      pi.reset_for_prefix = reset_for_prefix

      parser.instructions.append(pi) # FIXME: instruction is a misnomer here
      
      lines.pop(0)
      
   return lines


############################################################################
## $$ Graph build
############################################################################

# $$ graph_node_t
class graph_node(object):
   
   global_node_num = 0
   
   def __init__(self, token,bitpos):
      self.id =  self.__class__.global_node_num
      #msge("CREATE NODE %d" % (self.id))
      self.__class__.global_node_num += 1
      self.token = token
      self.instructions = [] # a list of instruction_info_t class items

      # the relative bit position, mod 8, assuming nonterminals return bytes
      self.bitpos_mod8 = bitpos & 7
      
      # number of bits we use to decide on the next node. 
      self.decider_bits = 0
      
      # number of bits we accept and skip over to get to the next
      # decider-group-of-bits
      self.skipped_bits = 0

      # a nonterminal  that follows this node
      self.nonterminal = None
      
      # an operand decision point
      self.operand_decider = None

      # When we have to go back and pick up a bit that was ignored
      # earlier, we list it here.
      self.back_split_pos = None

      # Usually we want the epsilon actions to result in decode
      # errors. When we want to permit epsilon action for prefix-type
      # nonterminals, then we set self.otherwise_ok to True.
      self.otherwise_ok = False
      
      self.next = {}

      # The capture function_object_t for the operands we need to
      # capture at this node.
      self.capture_function = None
      
      self.trimmed_values = None
      
   def is_nonterminal(self):
      if self.nonterminal != None:
         return True
      return False
   
   def is_operand_decider(self):
      if self.operand_decider != None:
         return True
      return False
   def value_test_node(self):
      """returns (value_test, value_to_test) """
      if self.is_operand_decider():
         if len(self.next) == 2:
            found_value = False
            found_other = False
            value = None
            for k,nxt in self.next.items():
               if k == 'other' and found_other==False:
                  found_other = True
               elif found_value == False:
                  found_value = True
                  value = k
               else:
                  # multiple values
                  return (False, None)
            if found_value and found_other:
               return (True, value)
      return (False, None)
     
   def leaf(self):
      if len(self.next) == 0:
         return True
      return False
     
   def dump_str(self,pad=''):
      eol = "\n"
      s =  pad + 'id: ' + str(self.id)
      s += ' token: ' + str(self.token)
      s += ' next nodes: %d' % (len(self.next))
      s += ' insts: %d' % (len(self.instructions))
      s += eol
      s += pad + 'skipped_bits: ' + str(self.skipped_bits)
      s += ' decider_bits: ' + str(self.decider_bits)
      if self.otherwise_ok:
         s += ' otherwise_ok: ' + str(self.otherwise_ok)
      if self.back_split_pos:
         s += ' back_split_pos: ' + str(self.back_split_pos)
      if self.nonterminal != None:
         s += " NONTERMINAL:" + str(self.nonterminal)
      if self.operand_decider:
         s += ' OPERAND-DECIDER:' + str(self.operand_decider)
      s += eol
      # only print instructions for leaf nodes
      if len(self.next) == 0:
         s += pad + 'insts: ' + eol
         for ii in self.instructions:
            s += ii.dump_str(pad + '    ') + eol
      return s
   def dump(self,pad=''):
      msge(self.dump_str(pad))

        
        

def new_node(graphnode, token, bitpos):
   node =  graph_node(token,bitpos)
   graphnode.next[token] = node
   return  node
   
def get_bit(ii,bitpos):
   if bitpos >= len(ii.ipattern.bits):
      return 'badbit'
   return ii.ipattern.bits[bitpos]


def collect_required_values(instructions, bitpos):
   """Return a list of the required values for a list of operand
   deciders."""
   d = []
   for ii in instructions:
      if not ii.ipattern.bits[bitpos].is_operand_decider():
         die("Died looking for an operand decider")
      operand_decider = ii.ipattern.bits[bitpos]
      if operand_decider.test == 'eq':
         if operand_decider.requirement not in d:
            d.append(operand_decider.requirement)
   return d
   

def partition_by_required_values(options, instructions, bitpos, token,
                                 required_values, state_space, splatter=True, 
                                 operand_storage_dict=None):
   """Return a dictionary of lists of instructions, split by the
   elements of the required_values list"""
   #msge("\n\n\nNEW PARTITION:" )
   d = {}
   all_values = {}
   for ii in instructions:
      if not ii.ipattern.bits[bitpos].is_operand_decider():
         die("THIS DOES NOT HAPPEN")
      # we have an operand decider
      operand_decider = ii.ipattern.bits[bitpos]
      if vod():
         msge("PARTITIONING OPERAND DECIDER  TOKEN: " +
              str(operand_decider.token))
      if operand_decider.token != token:
         die("Mixed partitionings of operand_deciders: splitting on " + token +
             " but encountered " + operand_decider.token)
      if operand_decider.test == 'eq':
         # just one instruction  needs to be placed
         if vod():
            msge("Setting EQ OD %s" % operand_decider.requirement)
         if operand_decider.requirement not in d:
            d[ operand_decider.requirement ] = [ ii ]
         else:
            d[ operand_decider.requirement ].append(ii)
         all_values[operand_decider.requirement]=True
      elif operand_decider.test == 'ne':
         # add to trimmed list of req'd vals ( excluding this value)
         # THIS DUPLICATES (references to) NODES if there is more than
         # one choice.
         if operand_decider.token in state_space:
            all_values_for_this_od = state_space[operand_decider.token]
            if vod():
               msge("NE OD: all values from state space %s" % 
                    (str(all_values_for_this_od)))
         else:
            try:
               osf = operand_storage_dict[operand_decider.token]
               if osf.ctype.find('enum') == -1:
                  nvalues = 1 << int(osf.bitwidth)
                  #all_values_for_this_od = [ str(x) for x in range(0,nvalues) ]
                  all_values_for_this_od = range(0,nvalues)
                  if vod():
                     msge("Synthesized values for %s: %s" % 
                          ( operand_decider.token,
                            ", ".join( [ str(x) for x in all_values_for_this_od])))
            except:
               die("could not find %s in state space dictionary" %  
                   (operand_decider.token))

         if vod():
            msge("All values for OD: %s" % 
                 ", ".join( [ str(x) for x in all_values_for_this_od] ))
         for a in all_values_for_this_od:
            all_values[a]=True
         trimmed_vals = list(filter(lambda x: x != operand_decider.requirement, 
                               all_values_for_this_od))
         if len(trimmed_vals) == 0:
            die("We had a not-equals requirement but did" +
                " not have any other values to bin against.")

         # DO NOT MAKE ONE NODE PER trimmed_vals element - that
         # explodes the graph size.
         #msge("\tAdding other with  values " + str(trimmed_vals))
         other = 'other'
         if other not in d:
            d[ other ] = [ (trimmed_vals,ii) ]
         else:
            d[ other ].append((trimmed_vals,ii) )

   #msge("RETURNING FROM PARTITION: %s" % ( str(d.keys())))
   return (d, list(all_values.keys()) )
      

def all_same_operand_decider(ilist,bitpos):
   """Return false if not all of the next bits are the same
   operand-decider, also return operand decider if True"""
   last = None
   for i in ilist:
      plen = len(i.ipattern.bits)
      if bitpos >= plen:
         #msge("Fell off end of bits")
         return (False,None)

      # They can have different required values, but they must be the
      # same deciding token.
      
      if i.ipattern.bits[bitpos].is_operand_decider():
         if last == None:
            last = i.ipattern.bits[bitpos]
         elif last.token  != i.ipattern.bits[bitpos].token:
            return (False, None)
      else:
         return (False, None) # not an operand decider
   if last:
      return (True, last)
   return (False, None)
         
         

def all_same_nonterminal(ilist,bitpos):
   """Return false if not all of the next bits are the same
   nonterminal, also return nonterminal if True"""
   last_nonterminal = None
   for i in ilist:
      
      plen = len(i.ipattern.bits)
      if bitpos >= plen:
         #msge("Fell off end of bits")
         return (False,None)
      if i.ipattern.bits[bitpos].is_nonterminal():
         if last_nonterminal == None:
            last_nonterminal = i.ipattern.bits[bitpos]
         elif last_nonterminal != i.ipattern.bits[bitpos]:
            #msge("Differing NTs: [" + str(last_nonterminal)+ "] vs ["
            #+ str(i.ipattern.bits[bitpos]) + ']')
            return (False, None)
      else:
         #msge("Not a nonterminal")
         return (False, None) # not a nonterminal
   if last_nonterminal:
      return (True, last_nonterminal)
   return (False, None)


def move_candidate_od_to_front(bitpos, candidate_od, bit_info_t_list):
   """Move a speicific od names candidate_od from wherever it is in
   the list (after bitpos) to the location bitpos"""
   
   found = False
   for i,b in enumerate(bit_info_t_list[bitpos+1:]):
      if b.is_operand_decider():
         if b.token == candidate_od:
            found = True
            badpos = i + bitpos + 1
   if found:
      # move bit_info_t_list[badpos] to just before bitpos
      if vrearrange():
         msge("BEFORE REARRANGE: bitpos = %d  and badpos = %d" %
              (bitpos, badpos))
         for b in bit_info_t_list:
            msge( "\t" + str(b) )
      z = bit_info_t_list[badpos]
      del bit_info_t_list[badpos]
      bit_info_t_list.insert(bitpos,z)
      if vrearrange():
         msge("AFTER REARRANGE:")
         for b in bit_info_t_list:
            msge( "\t" +str(b) )

   return found

def renumber_one_ipattern(i):
    bitpos = 0 
    for p in i.ipattern.bits:
        p.pbit = bitpos
        bitpos = bitpos + 1

def renumber_bitpos(ilist):
    for i in ilist:
        renumber_one_ipattern(i)

def rearrange_at_conflict(ilist,bitpos):
   """Try to rearrange ODs at a conflict"""

   # build up a list of candidate ods

   # FIXME 2008-11-12 Mark Charney: could search for all sequential
   # ODs rather than just one neighboring OD.
   
   candidate_ods = []
   for i in ilist:
      if bitpos >= len(i.ipattern.bits):
         return False
      if i.ipattern.bits[bitpos].is_operand_decider():
         t = i.ipattern.bits[bitpos].token
         if t not in candidate_ods:
            candidate_ods.append(t)
            
         # look ahead one spot too...
         nbitpos = bitpos+1
         if nbitpos < len(i.ipattern.bits):
            if i.ipattern.bits[nbitpos].is_operand_decider():
               t = i.ipattern.bits[nbitpos].token
               if t not in candidate_ods:
                  candidate_ods.append(t)

   if len(candidate_ods) == 0:
      msge("REARRANGE: NO CANDIDATE OD")
      return False

   retry = True
   for candidate_od in candidate_ods:
      if retry == False:
         break
      msge("REARRANGE ATTEMPT  using %s" % (candidate_od))
      retry = False
      for i in ilist:
         if i.ipattern.bits[bitpos].is_operand_decider():
            if candidate_od == i.ipattern.bits[bitpos].token:
               msge("\tSKIPPING %s inum %d -- already fine" %
                    ( i.get_iclass(), i.inum))
            else:
               msge("\tREARRANGE needs to juggle: %s inum %d" % 
                    ( i.get_iclass(), i.inum))
               # attempt to juggle ODs in i.ipattern.bits to get
               # candidate_od in to bitpos
               if move_candidate_od_to_front(bitpos, 
                                             candidate_od, 
                                             i.ipattern.bits):
                  msge("\tREARRANGE one pattern worked for %s inum %d" % 
                       ( i.get_iclass(), i.inum))
               else:
                  retry = True
                  msge("\tREARRANGE FAILED for %s. Trying again..." % 
                       (candidate_od))
                  break # hit the outer loop

   if retry == True:
      msge("REARRANGE FAILED for all ODs")
      return False

   # make sure they are all the same OD at this bitpos now
   candidate_od = None
   for i in ilist: 
      if i.ipattern.bits[bitpos].is_operand_decider():
         if candidate_od == None:
            candidate_od = i.ipattern.bits[bitpos].token
         elif candidate_od != i.ipattern.bits[bitpos].token:
            msge("REARRANGE FAILED AT END(1)! bitpos = %d" % (bitpos))
            msge( i.dump_str() )
            return False
      else:
         print_node(ilist)
         msge("REARRANGE FAILED AT END(2)!")
         return False
   msge("REARRANGE: FIXED OD CONFLICT!")

   # since we rearranged, we need to renumber the pbits or the
   # extraction will not work properly.
   renumber_bitpos(ilist)
   return True


def some_funky_spot(ilist,bitpos):
   """Return true if some pattern has a nonterminal or operand decider"""
   for i in ilist:
      if bitpos < len(i.ipattern.bits):
         if i.ipattern.bits[bitpos].is_nonterminal():
            return True
         if i.ipattern.bits[bitpos].is_operand_decider():
            return True
   return False

def print_split(others,ones,zeros,brief=False):
      for s,lst in [('Others',others),
                    ('Ones', ones),
                    ('Zeros', zeros)]:
          msge(s +': ')
          for ii in lst:
              try:
                  msge( ii.dump_str(brief=brief))
              except:
                  msge( "XUNKNOWN: " + str(ii) )
         

def partition_nodes(ilist,bitpos):
   """return a tuple of lists of nodes whose next bit is zero, one or
   a letter (others)"""
   zeros = []
   ones = []
   others = []
   zero = '0'
   one= '1'
   for inst in ilist:
      bit = inst.ipattern.bits[bitpos]
      if bit.value == zero:
         zeros.append(inst)
      elif bit.value == one:
         ones.append(inst)
      else:
         others.append(inst)
   return (ones,zeros,others)

def print_node(ilist):
   for ii in ilist:
      msge("\t" + ii.dump_str(brief=True))

def at_end_of_instructions(ilist, bitpos):
   """If all instructions are done with their bits, return 1
   None). Check for length problems too.  If not done, return 0.
   If there is an error, return -1"""
   done = False
   notdone = False
   for ii in ilist:
      if isinstance(ii,tuple):
         die("Bad tuple where instruction expected: "+ str(ii))
      if bitpos >= len(ii.ipattern.bits):
         done = True
      else:
         notdone = True
   if done:
      if notdone:
         msge("Length error: some instructions done and some" + 
              " are not done simultaneously")
         msge("ilist len = " + str(len(ilist)))
         msge("\n\nILIST:")
         for ii in ilist:
            msge( 'bitpos:' + str(bitpos) + 
                  '  len-pattern:' + str( len(ii.ipattern.bits)))
            if (len(ii.ipattern.bits)) == 0:
                msge("BAD INST: %s" % ( str(ii)))
         msge("\n\nNODE:")
         print_node(ilist)
         #die("Dying")
         return -1 # problem: some done, some not done
      return 1 # all is well, all done
   return 0 # not done yet

def no_dont_cares(instructions, bitpos):
   "Return True if there are no don't cares"
   for i in instructions:
      if i.ipattern.bits[bitpos].is_dont_care():
         return False
   return True
   
def some_different(instructions,bitpos):
   """Return True if there are ones and zeros and no don't cares,
   nonterminals or operand deciders"""
   zero = '0'
   one= '1'

   zeros = 0
   ones = 0
   for i in instructions:
      if i.ipattern.bits[bitpos].value == zero:
         zeros += 1
      elif i.ipattern.bits[bitpos].value == one:
         ones += 1
   if zeros > 0 and ones > 0:
      return True
   return False

def scan_backwards_for_distinguishing_bit(instructions,bitpos):
   """Return a tuple (t/f, bitpos) that says where we can partition
   this node further (when possible)."""
   
   b = bitpos - 1
   while b >= 0:
      if no_dont_cares(instructions,b):
         if some_different(instructions,b):
            msge("FALLBACK: we can parition on the 1s and 0s at bitpos " + 
                 str(b))
            return (True, b)
      b = b - 1
   msge("FALLBACK: No bits left to examine: at bit %d" % (bitpos))
   return (False, None)

def convert_splitpos_to_bit_index(graph,splitpos):
   """Convert the fake bitposition in splitpos in to a real bit
   position by skipping leading operand deciders. Intervening
   nonterminals might mess this up??? FIXME
   """
   i = graph.instructions[0]
   real_bits = 0
   for b in i.ipattern.bits[0:splitpos]:
      if not b.is_operand_decider():
         real_bits += 1
   msge("BACKSPLIT  fake bitpos: %d real bitpos: %d\n" % (splitpos, real_bits))
   return real_bits
         

      

def back_split_graph(common, graph, bitpos, skipped_bits, splitpos):
   """Partition based on splitpos and then recur in to build_sub_graph
   for the partitions."""

   options = common.options
   msge("back_split_graph: based on " + str(splitpos))
   (ones,zeros,others) = partition_nodes(graph.instructions,splitpos)
   if vbuild():
      s =  "ones %d zeros %d others %d" % (len(ones), len(zeros), len(others))
      msge('back_split_graph: ' + s )
   if len(others) > 0:
      die("We encountered some junk on a back-split")

   if len(zeros) == 0:
      die("We didn't have any zeros in the back-split partition")
   if len(ones) == 0:
      die("We didn't have any ones in the back-split partition")
      
   graph.skipped_bits = skipped_bits
   graph.decider_bits = 1
   graph.back_split_pos = convert_splitpos_to_bit_index(graph,splitpos) 
   
   # zero child node
   znode = new_node(graph,'0',bitpos)
   znode.instructions.extend(zeros)
   build_sub_graph(common,znode,bitpos, 0)  # RECUR

   # one child node
   onode = new_node(graph,'1',bitpos)
   onode.instructions.extend(ones)
   build_sub_graph(common,onode,bitpos, 0)  # RECUR



# global hack -- FIXME: 2007-07-10 to get the operand storage
#                                  dictionary in to
#                                  partition_by_required_values.
g_operand_storage_dict = None

def build_sub_graph(common, graph, bitpos, skipped_bits):
   """Recursively partition instructions based on 1s, 0s and
   placeholder letters"""
   global g_operand_storage_dict
   options = common.options

   # expand_dont_cares is an important control for the graph
   # building. If expand_dont_cares is false, whenever we see a
   # don't-care in some thing at the next bit position, then we skip
   # that bit in the graph formation. This leads to problems when
   # skipped 1s and 0s are required to disambiguate the tree
   # downstream. When expand_dont_cares is true, then whenever we have
   # some 1s or 0s that happen to collide with a don't-care in some
   # thing at the next bit positiona, then we copy all the don't-care
   # ("others") on both zero and one successor nodes. Something down
   # stream will disambiguate them necessarily. The nice thing about
   # expand_dont_cares being true is that (a) one does not have the
   # problem alluded to above (which I've only seen when processing
   # the SIB BASE table, and hacked around by swapping the nonterminal
   # argument order). And (b), we don't have to confirm that bits we
   # skipped have required values when we get down to just one
   # decoding option.
   #
   # I only expand the don't cares if they happen to line up with some
   # nodes that have 1s or 0s in them. This attempts to prevent the
   # immediates from exploding the graph. But if immediates line up
   # with some 1s and 0s, they'll get expanded. The 1B PUSH does not
   # get expanded because the 0101_0xxx is unique once you get to the
   # 0101_0 part. So that would have to be coalesced in graph merging
   # later on.
   #
   #
   # WARNING: When expand_dont_cares is true the graph currently
   # explodes in size.
   expand_dont_cares = False

   # skip_constants is an important control for the graph building. If
   # skip_constants is false, then when the next bit for all
   # instructions is 1 or the next bit for all instructions is 0, then
   # we pretend it is decider bit and make a new node.  This node is
   # trivial because it only has one out-edge, but it enabls the graph
   # merger to merge it in to the parent node when merging is
   # done. This results in a smaller graph.  When skip_constants is
   # True, then we "skip" bits where the next bit is always 1 or 0 for
   # all instructions. In this case, we still need to confirm that we
   # have a 1 or 0 at decode time, but it doesn't contribute new
   # information. After node merging, the graph is smaller when
   # skip_constants is False at graph build time, so that is the
   # preferred setting.
   skip_constants = False

   # stop_early is another important control. If stop_early is True,
   # then we do not continue building the graph when we are down to
   # one instruction. When stop_early is False, we keep going even
   # when there is only one instruction. Setting stop_early to False
   # is required to get the nonterminals that may be down stream built
   # in to the graph.
   stop_early = False
   
   if vbuild():
      msge("[SUBGRAPH BUILD] Token %s ninst %d" % 
           (str(graph.token), len(graph.instructions)))
      for ii in graph.instructions:
         msge(ii.dump_str('   '))

   if stop_early and len(graph.instructions) == 1:
      # we are down to one option. We must verify when decoding, but
      # the path is now determined fully.
      return

   # Go to the next bit. Note: we initialize the bitpos to -1 so that
   # when we advance it here the first time, we start with bit zero.

   bitpos += 1
   if vbuild():
      msge("Token " + str(graph.token) + "   Reached bit " + str(bitpos))

   at_end = at_end_of_instructions(graph.instructions,bitpos)
   if at_end == 1:
      if vbuild():
         msge("Hit end of instructions -- skipped bits " + str(skipped_bits))
      if len(graph.instructions) > 1:
         msge("\nBUILD ERROR: more than one leaf when ran out of bits:")
         for ii in graph.instructions:
            msge(ii.dump_str('   ', brief=True))
         msge("\n\n")
         (okay, splitpos) = scan_backwards_for_distinguishing_bit(
                                                     graph.instructions,bitpos)
         if okay:
            msge("NEED TO BACKSPLIT AT POSITION %d" % (splitpos))
            # redo this bit (hence bitpos-1) once we split based on splitpos
            back_split_graph(common, graph, bitpos-1, skipped_bits, splitpos)
            return
         else:
            msge("Back-split failed to solve the problem")
         die("BUILD ERROR: more than one leaf when ran out of bits." + 
             " See stdout.")
      graph.skipped_bits = skipped_bits
      return
   elif at_end == -1:
      if vbuild():
         msge("Hit end of SOME instructions -- try back_split")
      (okay, splitpos) = \
          scan_backwards_for_distinguishing_bit(graph.instructions,bitpos)
      if not okay:
         die("Back-split failed to solve ending problem")
      else:
         # redo this bit (hence bitpos-1) once we split based on splitpos
         back_split_graph(common, graph, bitpos-1, skipped_bits, splitpos)
         return

   if vpart():
      msge("Here is what we are considering, bitpos" + str(bitpos) + ":")
      for ii in graph.instructions:
         msge(ii.dump_str('   ')  + '\n')
         
   #####################################################################


   iterations = 0
   splitting = True
   while splitting:
      #msge("SPLIT ITERATION: %d" % (iterations))
      if iterations > 1:
         die("We should not be trying to resplit things more than once")
      iterations += 1
         
      # Check for identical operand deciders
      (all_same_decider, operand_decider) = \
          all_same_operand_decider(graph.instructions,bitpos)
      if all_same_decider:
         if vbuild():
            msge("All same operand decider: %s" % operand_decider)
         # hit an operand decider

         # tell current node that it is an operand decider
         graph.operand_decider = operand_decider  # a special kind of bit_info_t
         graph.skipped_bits = skipped_bits

         # Collect up the required values...
         required_values = collect_required_values(graph.instructions, bitpos)
         if vpart():
            msge("Required values for operand decider " + str(required_values))

         # When we have things that ignore a particular decider we need
         # to copy everything else to all the options. NOTE: this must be
         # false because when set to true, it messes up the subsequent bitpos
         # ordering for things that were skipped.
         splatter_dont_cares = False

         # split up the nodes based on the different values observed.
         (node_partition,values) = \
             partition_by_required_values(options, graph.instructions, bitpos,
                                          operand_decider.token,
                                          required_values, common.state_space,
                                          splatter_dont_cares,
                                          g_operand_storage_dict)

         graph.child_od_key_values = values


         # check to see if all the 'other' conditions are the same.
         # if not, we must splatter them.
         need_to_splatter = False
         previous_trimmed_values = None
         scalar_values = set()
         for k,partition in node_partition.items():
            if vpart():
               msge("SPATTER SCAN: Operand decider partition key= " + str(k))
            if isinstance(partition[0],tuple):
               for trimmed_values, ii in  partition:
                  s = set(trimmed_values)
                  if previous_trimmed_values == None:
                     previous_trimmed_values = s
                  if s != previous_trimmed_values:
                     # need to splatter!
                     msge("X9 need to splatter based on differing " + 
                          "other conditions")
                     need_to_splatter = True
                     break
            else:
               scalar_values.add(k)

         # if there is an overlap between the 'other' values and
         # values referenced by non "other" nodes (scalar ODs), then
         # we need to splatter. MOD=3 and MOD!=3 will not get splattered.
         # But X=0, X=1, X!=2 will get splattered since X!=2 -> X= 0 or 1.
         # and that overlaps with existing scalar values.

         if not need_to_splatter and previous_trimmed_values:
            if scalar_values.intersection(previous_trimmed_values):
               msge("X9 need to splatter based on cases overlapping " + 
                    "with scalar dispatch")
               need_to_splatter = True

         # fix up the 'other' conditions so that they are partitionable.
         if need_to_splatter:
            msge("Splattering because of conflicting 'other' conditions")
            new_node_partition = {}
            for k,partition in node_partition.items():
               if isinstance(partition[0],tuple):
                  for trimmed_values, ii in  partition:
                     for tv in trimmed_values:
                        try:
                           new_node_partition[tv].append(ii)
                        except:
                           new_node_partition[tv]=[ii]
               else:
                  try:
                     new_node_partition[k].extend(partition)
                  except:
                     new_node_partition[k]=partition
            # replace old partition with splattered partition
            node_partition = new_node_partition

         
         # set up the next nodes and give them their instructions.

         for k,partition in node_partition.items():
            if vpart():
               msge("PARTITIION: Operand decider partition key= " + str(k))
            next_node = new_node(graph,k,bitpos)

            if isinstance(partition[0],tuple):
               # store the key choices in the node for later graph building
               for trimmed_values, ii in  partition:
                  next_node.trimmed_values = trimmed_values
                  next_node.instructions.append(ii)
            else:
               if k == 'XED': # FIXME: why is this test here? / 2009-02-06
                  die("Bad operand decider: " + k )
               next_node.instructions.extend(partition)

         # build the subgraphs for the children
         for child in graph.next.values():
            # RECUR for operand-decider
            build_sub_graph(common, child, bitpos, 0) 
         return

      ####################################################################
      # Check for identical nonterminals
      # nt is the bit_info_t for the nonterminal
      (all_same_nt, nt) = all_same_nonterminal(graph.instructions,bitpos)
      if all_same_nt:
         if vbuild():
            msge("All same nt")
         # hit a nonterminal.

         # tell current node that it is a nonterminal
         graph.nonterminal = nt
         graph.skipped_bits = skipped_bits
         if vbuild():
            msge("GRAPHBLD: Nonterminal: " + 
                 str(nt) + " skipped_bits: " + str(skipped_bits))
         # build a new node that follows the nonterminal and give it
         # all the instructions.  The '-' denotes we go there when the
         # nonterminal is done parsing.
         nt_next_node = new_node(graph,'-',bitpos)

         nt_next_node.instructions.extend(graph.instructions)

         # carry on build the graph from the nt_next_node
         build_sub_graph(common, nt_next_node, bitpos, 0)
         return
      else:
         if vbuild():
            msge("Not all the same nonterminal.")

      #####################################################################
      # *AFTER* we advance the bit, we partition the nodes based on
      # *the current bit

      (ones,zeros,others) = partition_nodes(graph.instructions,bitpos)
      if vbuild():
         s =  "ones %d zeros %d others %d" % (len(ones), 
                                              len(zeros), len(others))
         msge('build_sub_graph ' + s )

      # make sure we do not have some things that hit the Nonterminal
      # and some that do not
      if some_funky_spot(graph.instructions,bitpos):
         msge('FUNKY SPOT: bitpos %d' % (bitpos))
         print_split(others,ones,zeros,brief=True)
         if rearrange_at_conflict(graph.instructions, bitpos):
            msge("REARRANGED ODs TO BYPASS PROBLEM at bitpos %d" % bitpos )
            # try resplitting the nodes now that we've juggled stuff
            continue 

         else:
            (okay, splitpos) = \
                scan_backwards_for_distinguishing_bit(graph.instructions,
                                                      bitpos)
            if not okay:
               die("Look-ahead error - only some are nonterminal " +
                   "at next bit position")
            else:
               # redo this bit (hence bitpos-1) once we split based on
               # splitpos.
               back_split_graph(common, graph, 
                                bitpos-1, skipped_bits, splitpos)
               return
      else:
         splitting = False # we are good to exit

   if verb7():
      print_split(others,ones,zeros)


   # FIXME: enabling either of these lines causes a python error at
   # this point we never need this nodes instructions again.  (Turns
   # out we need them anyway for generating args for the nonterminals,
   # so all is not lost, just confused.)
   #del graph.instructions
   #graph.instructions = []
         
   # if there are any others in then, we cannot split on this bit, so
   # just keep going. Similarly, if there are all 1s or all 0s then we
   # just keep going (when skip_constants is True). Only split the
   # node if it is a mix of 1s and 0s.
   if len(others) > 0:

      ####OLD STUFF build_sub_graph(common,graph, skipped_bits+1)  # RECUR

      if expand_dont_cares and (len(ones)>0 or len(zeros)>0):
         # we only do the expansion if ones/zeros are floating around
         # at this point. Build two nodes. Put all the ones in the
         # "one" node, all hte zeros in the "zero" node and the others
         # in both nodes! Then recur on both nodes
         if vbuild():
            msge("Duplicating dontcares")
         graph.skipped_bits = skipped_bits
         graph.decider_bits = 1
         
         # zero child node
         znode = new_node(graph,'0',bitpos)
         if len(zeros) > 0:
            znode.instructions.extend(zeros)
         # Add the "don't-care others" to the zeros
         znode.instructions.extend(others) 
         build_sub_graph(common,znode,bitpos, 0)  # RECUR

         # one child node
         onode = new_node(graph,'1',bitpos)
         if len(ones) > 0:
            onode.instructions.extend(ones)
         # Add the "don't-care others" to the ones
         onode.instructions.extend(others) 
         build_sub_graph(common,onode,bitpos, 0)  # RECUR

      else:
         build_sub_graph(common,graph,bitpos, skipped_bits+1)  # RECUR
      
   elif len(ones) > 0 and len(zeros) == 0:
      # Some one's but no zeros, no others
      if vbuild():
         msge("some ones, no zeros no others")
      if skip_constants:
         build_sub_graph(common,graph, bitpos, skipped_bits+1)  # RECUR
      else:
         graph.skipped_bits = skipped_bits
         graph.decider_bits = 1
      
         onode = new_node(graph,'1',bitpos)
         onode.instructions.extend(ones)
         build_sub_graph(common,onode,bitpos, 0)   # RECUR
   elif len(ones) == 0 and len(zeros) > 0:
      # Some zeros's but no ones, no others
      if vbuild():
         msge("some zeros, no ones  no others")
      if skip_constants:
         build_sub_graph(common,graph,bitpos, skipped_bits+1)
      else:
         graph.skipped_bits = skipped_bits
         graph.decider_bits = 1
      
         znode = new_node(graph,'0',bitpos)
         znode.instructions.extend(zeros)
         build_sub_graph(common,znode, bitpos, 0)  # RECUR
   else:
      # some zeros, some ones -> split it      
      if vbuild():
         msge("Just 0s and 1s, splitting, building a subgraph")
      graph.skipped_bits = skipped_bits
      graph.decider_bits = 1

      # zero child node
      znode = new_node(graph,'0',bitpos)
      znode.instructions.extend(zeros)
      build_sub_graph(common,znode, bitpos, 0)  # RECUR

      # one child node
      onode = new_node(graph,'1',bitpos)
      onode.instructions.extend(ones)
      build_sub_graph(common,onode,bitpos, 0)  # RECUR

      
         
def build_graph(common, parser_output, operand_storage_dict):
   """Build a graph of the parsed instructions. Return the root"""
   if vgraph_res():
      print_resource_usage('build_graph.0')
   global g_operand_storage_dict
   g_operand_storage_dict = operand_storage_dict
   if verb4():
      msge("Building graph:")
      print_node(parser_output.instructions)
      if parser_output.otherwise_ok:
         msge("Otherwise-ok is set to true for this nonterminal")
   nt_name = parser_output.nonterminal_name
   graph  = graph_node(nt_name,0)
   #msge("Building new graph: %d" % (graph.id))

   #THIS LINE IS THE HUGE BIG MEMORY HOG. IS IT REALLY NEEDED??? NO!!
   # Removing it cut the memory usage in half and the execution time in half!
   #ilist =  copy.deepcopy(parser_output.instructions)
   ilist =  parser_output.instructions
   if vgraph_res():
      print_resource_usage('build_graph.1')
   graph.instructions.extend(ilist)
   if vgraph_res():
      print_resource_usage('build_graph.2')
   bitpos = -1
   skipped_bits = 0
   build_sub_graph(common,graph, bitpos, skipped_bits)
   if vgraph_res():
      print_resource_usage('build_graph.3')
   return graph

         
def print_graph(options, node, pad =''):
   s = node.dump_str(pad)
   msge(s)
   for k,nxt in node.next.items():  # PRINTING
      s = pad + ' key: ' + str(k)
      msge(s)
      print_graph(options, nxt, pad + '        ')
   
############################################################################
## $$ OPCAP capturing operands
############################################################################

def collect_immediate_operand_bit_positions(options, opnd, ii):
   """Fill in the opnd.bit_positions list with index of each bit in
   the immediate operand."""
   limit = len(ii.ipattern.bits)
   last_bit_pos = {} # record the next starting point for each letter
                     # we encounter
   for b in opnd.bits:   # try to find each bit.
      if b in last_bit_pos:
         start_at = last_bit_pos[b]
      else:
         start_at = 0
      found = False
      # look at the bits in the ipattern
      for p in range(start_at,limit):
         if ii.ipattern.bits[p].value == b:
            opnd.bit_positions.append( p )
            # bump our new starting point to after the position we just found
            last_bit_pos[b] = p+1
            found = True
            break
         
      if not found:
         die("Did not find bit %s of operand %s in instruction %s " % 
             (str(b), str(opnd), ii.dump_str()))

################################
         
uninteresting_operand_types_list = ['imm_const', 'reg', 'relbr', 'ptr', 'error',
                                    'nt_lookup_fn', 'mem', 'xed_reset', 
                                    'flag', 'agen']

uninteresting_operand_types_dict = \
    dict(zip(uninteresting_operand_types_list,
             [True]*len(uninteresting_operand_types_list)))


def decorate_operand(options,opnd,ii):
   """Set opnd.bit_positions list and opnd.rightmost_bitpos for this
   operand in this instruction"""

   global uninteresting_operand_types_dict
   
   if opnd.type in uninteresting_operand_types_dict:
      pass
   elif opnd.type == 'imm':
      if ii.prebindings and opnd.name in ii.prebindings:
         opnd.bit_positions = [ x.pbit for x in
                                ii.prebindings[opnd.name].bit_info_list ]
      else:
         collect_immediate_operand_bit_positions(options,opnd, ii)
      opnd.rightmost_bitpos = max(opnd.bit_positions)
   else:
      die("Unhandled operand type: " + str(opnd))
         


def decorate_operands(options,agi):
   for gi in agi.generator_list:
      for ii in gi.parser_output.instructions:
         for opnd in ii.operands:
            decorate_operand(options,opnd,ii)


def find_all_operands(options, node):
   """Return a set of operand names for this graph node. Just look at
   all the instructions."""
   operands = set()

   if vcapture():
      for ii in node.instructions:
         for opnd in ii.operands:
            msge("FINDALL: " + opnd.name + " type= [" + opnd.type + ']')

   # Get the operands from the first instruction
   # Only look at the imm-type operands
   ii = node.instructions[0]
   for opnd in ii.operands:
      if vcapture():
         msge("FINDALL Operand " + opnd.name + " type= [" + opnd.type + ']')
      # at leaves, include all operands. at internal nodes, just the
      # reg, imm and imm_const operands.
      if node.leaf():
         operands.add(opnd.name)
      elif opnd.type == 'imm' or opnd.type == 'imm_const' or opnd.type == 'reg':
         operands.add(opnd.name)

   # Remove any operands that are not in every instruction.
   # (We do not reprocess the first element.)
   for ii in node.instructions[1:]:
      op2set = set()
      for opnd in ii.operands:
         if node.leaf():
            # FIXME: this *was* operands.add(opnd.name)
            # 2007-06-26. Not sure if it was wrong or equivalent.
            op2set.add(opnd.name) 
         elif opnd.type == 'imm' or opnd.type == 'imm_const' or \
                 opnd.type == 'reg':
            op2set.add(opnd.name)
      operands = operands.intersection(op2set)
   return operands


def collect_instruction_types(agi, master_list):
   """Collect the iclass / category /extension"""
   need_to_die = False
   for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if field_check(ii, 'iclass'):
            plist = [] 
            if field_check(ii, 'attributes'):
                plist = ii.attributes

            if field_check(ii, 'iclass_string_index'):
                iclass_string_index = ii.iclass_string_index
            else:
                iclass_string_index = 0

            t = (ii.iclass, ii.extension, ii.category, ii.isa_set, 
                 plist, 
                 iclass_string_index)
            if ii.iform_enum  in master_list:
               # duplicate iform - check extension and isa-set
               (oldi, olde, oldc, 
                olds, oldp, oldisi) = master_list[ii.iform_enum]
               if olde != ii.extension:
                  need_to_die = True
                  msgb("ERROR:EXTENSION ALIASING IN IFORM TABLE", ii.iform_enum)
               if olds != ii.isa_set:
                  msgb("ERROR: ISA_SET ALIASING IN IFORM TABLE", ii.iform_enum)
                  need_to_die = True
               msgb("DUPLICATE IFORM", ii.iform_enum)
            master_list[ii.iform_enum] = t                  
   if need_to_die:
      mbuild.die("Dieing due to iform aliasing")

def collect_isa_sets(agi):
   """Collect the isaset info"""
   s = set()
   for generator in agi.generator_list:
      for ii in generator.parser_output.instructions:
         if field_check(ii, 'iclass'):
             s.add(ii.isa_set.upper())
   return s



def collect_tree_depth(node, depths, depth=0):
   """Collect instruction field data for enumerations"""

   cdepth = depth + 1
   if len(node.next) == 0:
      try:
         depths[cdepth] += 1
      except:
         depths[cdepth] = 1
   else:
      for child in node.next.values():
         collect_tree_depth(child, depths, cdepth) 
   return depths

def collect_ifield(options, node, field, master_list):
   """Collect instruction field data for enumerations"""
   for ii in node.instructions:
      if field_check(ii, field):
         s = getattr(ii,field)
         if s not in master_list:
            master_list.append(s)
   for child in node.next.values():
      # FIXME: sloppy return value handling???
      collect_ifield(options,child, field,master_list) 
   return master_list
         
            
def collect_ofield(options, node, field, master_list):
   """Collect operand field data for enumerations"""
   for ii in node.instructions:
      for opnd in ii.operands:
         if field_check(opnd, field):
            s = getattr(opnd,field)
            if s != None and s not in master_list:
               master_list[s] = True
   for child in node.next.values():
      collect_ofield(options,child, field,master_list) 

def collect_ofield_operand_type(options, node, field, master_list):
   """Collect operand type enumeration data"""
   for ii in node.instructions:
       for opnd in ii.operands:
           if field_check(opnd, field):
               s = opnd.get_type_for_emit()
               #s = getattr(opnd,field)
               if s != None and s not in master_list:
                   master_list[s] = True
   for child in node.next.values():
       collect_ofield_operand_type(options,child, field,master_list) 

      
def collect_ofield_name_type(options, node, field, master_list):
   """Collect operand field data for enumerations"""
   for ii in node.instructions:
      for opnd in ii.operands:
         if field_check(opnd, field):
            s = getattr(opnd,field)
            type = getattr(opnd,'type')
            if s not in master_list:
               master_list[s]=type
   for child in node.next.values():
      collect_ofield_name_type(options,child, field,master_list) 

         

def collect_attributes_pre(options, node,  master_list):
    collect_attributes(options, node,  master_list)
    # add always-available attributes. These facilitate writing
    # unconditional property-checking code in XED.
    for attr in [ 'MASKOP_EVEX', 'MASK_AS_CONTROL' ]:
        if attr not in master_list:
            master_list.append(attr)
    
    
def collect_attributes(options, node,  master_list):
   """Collect all attributes"""
   for ii in node.instructions:
         if field_check(ii, 'attributes'):
            s = getattr(ii,'attributes')
            if isinstance(s, list):
               for x in s:
                  if x not in master_list:
                     master_list.append(x)
            elif s != None and s not in master_list:
               master_list.append(s)
   for nxt in node.next.values():
      collect_attributes(options,nxt, master_list) 


idata_files = 0
def write_instruction_data(agi, idata_dict):
   """Write a file containing the content of the idata_dict. The keys
   are iclass:extension the values are (iclass, extension, category). This
   appends to the file if we've already opened this."""
   global idata_files
   idata_files += 1
   if idata_files > 1:
       die("Not handled: appending ot idata.txt file")
           
   fe = xed_file_emitter_t(agi.common.options.xeddir, 
                           agi.common.options.gendir, 
                           'idata.txt', 
                           shell_file=True)
   fe.start(full_header=False)
   
   kys = list(idata_dict.keys())
   kys.sort()
   s = "#%-19s %-15s %-15s %-30s %-20s %s\n" % ("iclass", 
                                                "extension", 
                                                "category", 
                                                "iform", 
                                                "isa_set",
                                                'attributes')
   fe.write(s)
   for iform in kys:
      (iclass,extension,category,isa_set, plist, 
                              iclass_string_index) = idata_dict[iform]
      if plist:
          attributes = ":".join(plist)
      else:
          attributes = 'INVALID'
      s = "%-19s %-15s %-15s %-30s %-20s %s\n" % (iclass, 
                                                  extension, 
                                                  category, 
                                                  iform, 
                                                  isa_set,
                                                  attributes)
      fe.write(s)
   fe.close()
   
def attr_dict_keyfn(a):
    return a[0]

def write_attributes_table(agi, odir): 
   fn = 'xed-attributes-init.c' 
   if vattr():
       msgb("Writing attributes file", fn)
   f = agi.common.open_file(fn, start=False)
   f.add_misc_header("#include \"xed-attributes.h\"")
   f.add_misc_header("#include \"xed-gen-table-defs.h\"")
   f.start()
   f.write("\nconst xed_attributes_t ")
   f.write("xed_attributes[XED_MAX_REQUIRED_ATTRIBUTES] = {\n")

   if vattr():
       msgb("Unique attributes", len(agi.attributes_dict))
   t = []
   for s,v in agi.attributes_dict.items():
       t.append((v,s))
   t.sort(key=attr_dict_keyfn)
   if vattr():
       msgb("Sorted Unique attributes", len(t))
   agi.attributes_ordered =  t

   #  agi.attributes_ordered has tuple (i,s) where s is a comma
   #  separated list of attributes that we'll use to manufacture the
   #  initialization equations.
   if len(agi.attributes_ordered) >= 65536:
       die("Too many attributes combinations for the 16b index used" + 
           " in the xed_inst_t data structure." +
           " Please report this to the SDE/XED team.")

   for i,s in agi.attributes_ordered:
       if s:
           v = s.split(',')
           struct_init = make_attributes_structure_init(agi,v)
       else:
           struct_init = make_attributes_structure_init(agi,None)
       f.write("/* %5d */ %s,\n" % (i,struct_init))
   f.write("\n};\n")
   f.close()

def write_quick_iform_map(agi,odir,idata_dict):
   fn = 'xed-iform-map-init.c' 
   f = agi.common.open_file(fn, start=False)
   f.add_misc_header("#include \"xed-iform-map.h\"")
   f.start()

   # FIXME: declare this type
   f.write("\nconst xed_iform_info_t xed_iform_db[XED_IFORM_LAST] = {\n") 
   first = True
   for (iclass,iform_num,iform) in agi.iform_tuples:
      try:
         (x_iclass,extension,category,isa_set,
          plist, 
          iclass_string_index) = idata_dict[iform]
      except:
          (x_iclass,extension,category,isa_set, 
           plist, 
           iclass_string_index) = ('INVALID', 
                                   'INVALID',
                                   'INVALID', 
                                   'INVALID', 
                                   None, 
                                   0) # FIXME BADNESS
         
      if first:
         first = False
      else:
         f.write(",\n")
      qual_iclass = "XED_ICLASS_%s" % (iclass.upper())
      qual_category = "XED_CATEGORY_%s" % (category.upper())
      qual_extension = "XED_EXTENSION_%s" % (extension.upper())
      qual_isa_set = "XED_ISA_SET_%s" % (isa_set.upper())
      t = '/* %29s */ {  (xed_uint16_t) %25s, (xed_uint8_t) %22s, (xed_uint8_t)%20s, (xed_uint16_t)%25s, (xed_uint16_t)%4d }' % \
            (iform, 
             qual_iclass, 
             qual_category, 
             qual_extension, 
             qual_isa_set, 
             iclass_string_index)
      f.write(t)
   f.write("\n};\n")

   f.close()
   
def collect_graph_enum_info(agi,graph):
   # we ignore the return values because we don't need them. The agi
   # fields get written by the collect*() functions.

   # operand fields
   collect_ofield_operand_type(agi.common.options,
                               graph,
                               'type',
                               agi.operand_types)
   collect_ofield(agi.common.options,graph, 'oc2', agi.operand_widths)
   collect_ofield_name_type(agi.common.options,graph, 'name',
                            agi.operand_names)

   collect_ifield(agi.common.options,graph, 'iclass',agi.iclasses)
   collect_ifield(agi.common.options,graph, 'category', agi.categories)
   collect_ifield(agi.common.options,graph, 'extension', agi.extensions)

   collect_attributes_pre(agi.common.options,graph,  agi.attributes)

def add_invalid(lst):
   if 'INVALID' not in lst:
      lst[0:0] = ['INVALID']

############################################################################
def key_invalid_first(x):
    # make 'INVALID' sort to be first.
    if x == 'INVALID':
        # space is first printable character in ascii table and should
        # not show up in our usage.
        return ' ' 
    return x


def key_invalid_tuple_element_0(x):
    return key_invalid_first(x[0])
def key_tuple_element_1(x):
    return x[1]

class rep_obj_t(object):
    def __init__(self, iclass, indx, repkind):
        self.iclass = iclass
        self.indx = indx
        self.repkind = repkind
        self.no_rep_iclass = None
        self.no_rep_indx = None

        
def repmap_emit_code(agi, plist, kind, hash_fn):
    """Emit table that implements the required mapping of iclasses. plist
    is an array of (key,value) pairs. kind is one of repe, repne, rep
    or norep. The hash function maps from the keys to a unique
    value. """

    fo = function_object_t(name='xed_' + kind + '_map',
                           return_type='xed_iclass_enum_t',
                           dll_export=True)
    fo.add_arg('xed_iclass_enum_t iclass')
    t = {}
    mx = 0
    for (k,v) in plist:
        h = hash_fn.apply(k)
        t[h] = (k,v)
        mx = max(mx, h)

    # For nonlinear hashes, add hash key input validation so that we
    # check if the input matches the thing we expect to get on the
    # output of the hash. Then the functions won't return undefined
    # results for unexpected inputs.

    if hash_fn.kind() == 'linear':
        array_limit = mx+1  # no extra room required for validation.
    else:
        array_limit = 2*(mx+1)  # make room for input key validation
    fo.add_code('const xed_uint16_t lu_table[{}] = {{'.format(array_limit))
    
    hashes = list(t.keys())
    hashes.sort()

    # fill in the rows of the array
    for h in range(0,mx+1):
        if h in t:
            (k,v) = t[h]
        else:
            k = "0xFFFF"
            v = 0  # XED_ICLASS_INVALID
        if hash_fn.kind() == 'linear':
            fo.add_code( '/* {} -> {} */ {},'.format(k,h,v))
        else:
            fo.add_code( '/* {} -> {} */ {}, {},'.format(k,h, k,v))
            
    fo.add_code_eol('}')
    fo.add_code_eol('const xed_uint_t key = (xed_uint_t)iclass')
    fo.add_code_eol('const xed_uint_t hash = {}'.format(hash_fn.emit_cexpr()))
    fo.add_code(    'if (hash <= {}) {{'.format(mx))
    if hash_fn.kind() == 'linear':
        fo.add_code_eol('   const xed_uint_t v = lu_table[hash]')
        fo.add_code_eol('   return (xed_iclass_enum_t) v')
    else:
        # validate the correct input mapped to the output
        fo.add_code_eol('   const xed_uint_t ek = lu_table[2*hash]')
        fo.add_code(    '   if (ek == key) {')
        fo.add_code_eol('      const xed_uint_t v = lu_table[2*hash+1]')
        fo.add_code_eol('      return (xed_iclass_enum_t) v')
        fo.add_code(    '   }')
    fo.add_code(    '}')
    fo.add_code_eol('return XED_ICLASS_INVALID')
    return fo

def emit_iclass_rep_ops(agi):

    """We want to make several functions that map (1) norep -> rep, (2)
    norep -> repe, (3) norep ->repne, and (4) rep/repe/repne -> norep.
    To do that, we need 2 hash functions. One hash function maps from
    rep/repe/repne keys and and another one mapping from norep keys.
    """
    import hashfks
    import hashmul
    import hashlin

    # collect the iclasses of interest by name.
    keys = []
    repobjs = []
    for i,iclass in enumerate(agi.iclasses_enum_order):
        #msge("TTX-ICLASS: {}".format(str(iclass)))
        if 'REPE_' in iclass:
            keys.append(i)
            repobjs.append(rep_obj_t(iclass,i,'repe'))
        if 'REPNE_' in iclass:
            keys.append(i)
            repobjs.append(rep_obj_t(iclass,i,'repne'))
        if 'REP_' in iclass:
            keys.append(i)
            repobjs.append(rep_obj_t(iclass,i,'rep'))

    # fill in the no-rep info for each object
    for o in repobjs:
        o.no_rep_iclass = re.sub(r'REP(E|NE)?_', '', o.iclass)
        if o.no_rep_iclass in agi.iclasses_enum_order:
            o.no_rep_indx  = agi.iclasses_enum_order.index(o.no_rep_iclass)
        else:
            o.no_rep_indx  = 0  # invalid

    # make a list of keys for the norep-to-whatever hash functions
    no_rep_keys = uniqueify( [x.no_rep_indx for x in repobjs])
    no_rep_keys.sort()
        
    msge("NOREP KEYS: {}".format(str(no_rep_keys)))
    msge("REP KEYS: {}".format(str(keys)))

    # find the two required  hash functions
    all_fn = { 'repinst':None, 'norepinst':None }
    for kind, kl in [('repinst',keys), ('norepinst',no_rep_keys)]:
        hashfn = hashlin.get_linear_hash_function(kl)
        if not hashfn:
            hashfn = hashmul.find_perfect(kl)
        if not hashfn:
            hashfn = hashfks.find_fks_perfect(kl)

        if hashfn:
            msge('{}'.format(hashfn.emit_cexpr()))
            msge('{}'.format(str(hashfn)))
            msge('FOUND PERFECT HASH FUNCTION FOR {}'.format(kind))
            all_fn[kind]=hashfn
        else:
            # If this ever happens, it is seriously bad news. We'll
            # have to upgrade the perfect hash function generation so
            # that this succeeds or make a fallback code path that either
            # large or slow. Or one could generate a 2-level perfect hash
            # but that seems like overkill for this.
            die('DID NOT FIND PERFECT HASH FUNCTION FOR {}'.format(kind))

    functions = []
    # emit the 3 functions that map from norep -> various kinds of
    # rep/repe/repne prefixes
    for kind in ['repe', 'repne', 'rep']:
        plist = []
        for r in repobjs:
            if r.repkind == kind:
                plist.append((r.no_rep_indx, r.indx))
        fo = repmap_emit_code(agi, plist, kind, all_fn['norepinst'])
        functions.append(fo)
        
    # emit the 1 function that maps from rep/repe/repne -> norep version
    plist = []
    for r in repobjs:
        plist.append((r.indx, r.no_rep_indx))
    fo = repmap_emit_code(agi, plist, "norep", all_fn['repinst'])
    functions.append(fo)

    cfp = agi.open_file('xed-rep-map.c')
    for fn in functions:
        cfp.write(fn.emit())
    cfp.close()
            
##############################################################################

def emit_iclass_enum_info(agi):
   """Emit major enumerations based on stuff we collected from the
   graph."""
   msge('emit_iclass_enum_info')
   iclasses = [s.upper() for s in agi.iclasses]
   add_invalid(iclasses)

   # 2...9  # omitting NOP1
   iclasses.extend( [ "NOP%s" % (str(x)) for x in  range(2,10)]) 

   iclasses = uniqueify(iclasses)
   # sort each to make sure INVALID is first
   iclasses.sort(key=key_invalid_first)
   gendir = agi.common.options.gendir
   xeddir = agi.common.options.xeddir
   agi.iclasses_enum_order = iclasses
   i_enum =  enum_txt_writer.enum_info_t(iclasses, xeddir, gendir,
                                         'xed-iclass',
                                         'xed_iclass_enum_t', 
                                         'XED_ICLASS_',
                                         cplusplus=False)
   
   i_enum.print_enum()
   i_enum.run_enumer()
   agi.add_file_name(i_enum.src_full_file_name)
   agi.add_file_name(i_enum.hdr_full_file_name, header=True)
   agi.all_enums['xed_iclass_enum_t'] = iclasses
   
def power2(x):
   """Return a list of the powers of 2 from 2^0... 2^x"""
   if x == 0:
      return None
   ret = []
   for p in range(0,x):
      ret.append(2**p)
   return ret
      
max_attributes=0

def emit_attributes_table(agi, attributes):
   """Print a global initializer list of attributes to the
   xed_attributes_table[XED_MAX_ATTRIBUTE_COUNT]"""
   cfp = agi.open_file('xed-attributes-list.c')
   cfp.write('const xed_attribute_enum_t ' +
             'xed_attributes_table[XED_MAX_ATTRIBUTE_COUNT] = {\n')
   first = True
   for attr  in attributes:
      if first:
         first = False
      else:
         cfp.write(',\n')
      cfp.write('  XED_ATTRIBUTE_%s' % (attr))
   cfp.write('\n};\n')
   cfp.close()

   
def emit_enum_info(agi):
   """Emit major enumerations based on stuff we collected from the
   graph."""
   msge('emit_enum_info')
   # make everything uppercase
   nonterminals = [  s.upper() for s in agi.nonterminal_dict.keys()]
   operand_types = [ s.upper() for s in agi.operand_types.keys()]
   operand_widths = [ s.upper() for s in agi.operand_widths.keys()]

   operand_names = [ s.upper() for s in 
                     list(agi.operand_storage.get_operands().keys()) ]
   msge("OPERAND-NAMES " + " ".join(operand_names))

   
   extensions = [ s.upper() for s in agi.extensions]
   categories = [ s.upper() for s in agi.categories]
   attributes = [ s.upper() for s in agi.attributes]
   # remove the things with equals signs
   attributes = list(filter(lambda s: s.find('=') == -1 ,attributes))
   

   # add an invalid entry to each in the first spot if it is not
   # already in the list. Sometimes it is there already, so we must
   # sort to make INVALID the 0th entry.
   add_invalid(nonterminals)
   add_invalid(operand_types)
   add_invalid(operand_widths)
   add_invalid(extensions)
   add_invalid(categories)
   gendir = agi.common.options.gendir
   xeddir = agi.common.options.xeddir


   nonterminals.sort(key=key_invalid_first)
   nt_enum =  enum_txt_writer.enum_info_t(nonterminals, xeddir, gendir,
                                          'xed-nonterminal', 
                                          'xed_nonterminal_enum_t',
                                          'XED_NONTERMINAL_',
                                          cplusplus=False)
   
   #For xed3 we want to dump a C mapping nt_enum -> nt_capture_function
   #for that matter we want a mapping:
   #nt_enum_numeric_value -> nt_name
   xed3_nt_enum_val_map = {}
   upper_dict = {}
   for nt_name in agi.nonterminal_dict.keys():
       nt_name_upper = nt_name.upper()
       upper_dict[nt_name_upper] = nt_name 
   for i,upper_nt in enumerate(nonterminals):
       if i == 0:
           continue #no nt_name for invalid guy
       xed3_nt_enum_val_map[i] = upper_dict[upper_nt]
   agi.xed3_nt_enum_val_map = xed3_nt_enum_val_map

   operand_names.sort()
   add_invalid(operand_names)
   on_enum = enum_txt_writer.enum_info_t(operand_names, xeddir, gendir,
                                         'xed-operand', 
                                         'xed_operand_enum_t', 
                                         'XED_OPERAND_',
                                         cplusplus=False)
   #for xed3 we want to create xed3_operand_struct_t
   #and it would be nice to order struct members in the
   #operand_enum order
   agi.xed3_operand_names = operand_names
   
   operand_types.sort(key=key_invalid_first)
   ot_enum = enum_txt_writer.enum_info_t(operand_types, xeddir, gendir,
                                         'xed-operand-type', 
                                         'xed_operand_type_enum_t',
                                         'XED_OPERAND_TYPE_',
                                         cplusplus=False)
   
   attributes.sort(key=key_invalid_first)
   lena = len(attributes)
   attributes_list = ['INVALID']
   if lena > 0:
      attributes_list.extend(attributes)
   if lena > 128:
      die("Exceeded 128 attributes. " +
          " The XED dev team needs to add support for more." +
          " Please report this error.")
   global max_attributes
   max_attributes= lena

   emit_attributes_table(agi, attributes)

   for i,a in enumerate(attributes_list):
       agi.sorted_attributes_dict[a] = i

   at_enum = enum_txt_writer.enum_info_t(attributes_list, xeddir, gendir,
                                         'xed-attribute', 
                                         'xed_attribute_enum_t',
                                         'XED_ATTRIBUTE_',
                                         cplusplus=False)
   

   categories.sort(key=key_invalid_first)
   c_enum = enum_txt_writer.enum_info_t(categories, xeddir, gendir,
                                        'xed-category',
                                        'xed_category_enum_t', 
                                        'XED_CATEGORY_',
                                        cplusplus=False)
   
   extensions.sort(key=key_invalid_first)
   e_enum = enum_txt_writer.enum_info_t(extensions, xeddir, gendir,
                                        'xed-extension',
                                        'xed_extension_enum_t', 
                                        'XED_EXTENSION_',
                                        cplusplus=False)
   
   enums = [ nt_enum, on_enum, ot_enum, at_enum,
             # ow_enum,
             c_enum, e_enum ]


   for e in enums:
      e.print_enum()
      e.run_enumer()
      agi.add_file_name(e.src_full_file_name)
      agi.add_file_name(e.hdr_full_file_name,header=True)

   
############################################################################

def emit_code(f,s):
   'A simple function that tacks on a semicolon and a newline'
   f.write(s + ';\n')

def pick_arg_type(arg):
   """Arg is a bit string whose name length determines what type we
   should use for passing it"""
   return 'xed_uint32_t'
   #if arg == None or len(arg) <= 32:
   #   utype = "xed_uint32_t"
   #else:
   #   utype = "xed_uint64_t"
   #return utype

def create_basis(arg):
   "return an bit string with the values of the 1s in arg, and zeros elsewhere"
   basis = letter_basis_pattern.sub('0',arg)
   # squish strings of all zeros down to just a single zero.
   if all_zeros_pattern.match(basis):
      return '0'
   return basis

def get_inst_from_node(node):
   if len(node.instructions) == 0:
      die("no instructions when doing cg for nonterminal. graph build error.")
   # grab the first instruction since they are all the same when the
   # get to a nonterminal
   ii = node.instructions[0]

   #FIXME: confirm that the arg bits are in the same positions for all
   #the instructions of this node. Otherwise erroneous bits will be
   #extracted.

   return ii
   
############################################################################
def compute_iform(options,ii, operand_storage_dict):
   """These are really the iforms."""
   iform = []
   if viform():
      msge("IFORM ICLASS: %s" % (ii.iclass))
   iform.append(ii.iclass)
   for operand in ii.operands:
      if operand.internal:
         if viform():
            msge("IFORM SKIPPING INTERNAL %s" % (operand.name))
      elif operand.visibility == 'SUPPRESSED':
         if viform():
            msge("IFORM SKIPPING SUPPRESSED %s" % (operand.name))

      elif operand.type == 'nt_lookup_fn':
         s = operand.lookupfn_name_base 
         if operand.oc2 and s not in ['X87'] :
            if operand.oc2 == 'v' and s[-1] == 'v': 
               pass # avoid duplicate v's
            else:
               s += operand.oc2
         iform.append( s )
      elif operand.type == 'reg':
         s = operand.bits.upper()
         s= re.sub('XED_REG_','',s)
         if operand.oc2 and operand.oc2 not in ['f80']:
            s += operand.oc2
         iform.append( s )
      elif operand.type == 'imm_const':
         s = operand.name.upper()
         s=re.sub('IMM[01]','IMM',s)
         s=re.sub('MEM[01]','MEM',s)
         add_suffix = True
         if s == 'IMM':
            add_suffix = options.add_suffix_to_imm
         if add_suffix:
            if operand.oc2:
               s += operand.oc2
         iform.append( s )
      else: # this skips MOD/REG/RMp
         if viform():
            msge("IFORM SKIPPING %s" % (operand.name))
   if len(iform) == 0:
      iform = ['default']
   ii.iform = iform
   if viform():
      msgb("IFORMX", "%s: %s" % (ii.iclass, "_".join(iform)))
   return tuple(iform)
      

def compute_iforms(options, gi, operand_storage_dict):
   """Classify the operand patterns"""

   # look at the first parser record to see if it contains actual
   # instructions.
   ii = gi.parser_output.instructions[0]
   if not field_check(ii,'iclass'):
    return None

   iforms = {} # dict by iform pointing instructions recs
   ii_iforms = {} # dict by iclass of iform names
   for ii in gi.parser_output.instructions:
      iform  = compute_iform(options,ii,operand_storage_dict)
      if viform():
         msge("IFORM %s %s" % (ii.iclass, str(iform)))
      s = "_".join(iform)
      if ii.iform_input: # override from grammar input
         s = ii.iform_input
      ii.iform_enum = s

      if viform():
          try:
             iforms[s].append(ii)
          except:
             iforms[s]=[ii]
          try:
             ii_iforms[ii.iclass].append(s)
          except:
             ii_iforms[ii.iclass]=[s]

   # printing various ways
   if viform():
      for iform,iilist in iforms.items():
         msge("IFORM %s: %s" % (iform,
                                " ".join([x.iclass for x in iilist] )))

      for iclass,iformlist in ii_iforms.items():
         str_iforms = {}
         dups = []
         for iform in iformlist:
            if iform in str_iforms:
               dups.append(iform)            
            else:
               str_iforms[iform]=True


         msge("II_IFORM %s: %s" % (iclass, " ".join(list(str_iforms.keys()))))
         if len(dups)!=0:
            msge("\tDUPS: %s: %s" % (iclass," ".join(dups)))

############################################################################
## CG code generation
############################################################################

# $$ code_gen_dec_arg_t
class code_gen_dec_args_t(object):
   """Empty class that I fill in as I pass arguments"""
   pass


operand_max=0

def code_gen_itable_operand(agi, 
                            data_table_file,
                            operand):
   """Emit code for one opnds.operand_info_t operand"""

   global operand_max

   if operand.type == 'error':
      return False
   if operand.internal:
       return False

   this_operand = operand_max
   oprefix =  'xed_operand+%s' % str(operand_max)
   operand_max += 1

   x_name = None
   x_vis = None
   x_rw = None
   x_oc2 = None
   x_type = None
   x_xtype = None  
   x_imm_nt_reg = '0'

   x_name = 'XED_OPERAND_%s' % operand.name.upper() 

   if operand.type == 'nt_lookup_fn':
      x_imm_nt_reg = 'XED_NONTERMINAL_' + operand.lookupfn_name.upper()
   elif operand.type == 'imm_const':
      x_imm_nt_reg = operand.bits
   elif operand.type == 'reg':
      x_imm_nt_reg = operand.bits
   elif operand.type == 'flag': # FIXME: not used
      x_imm_nt_reg = operand.bits

   try:   
       x_vis  = 'XED_OPVIS_%s' % operand.visibility.upper() 
       x_type = 'XED_OPERAND_TYPE_%s' % operand.get_type_for_emit()

       #
       # Some "PUBLIC" operands captured in the pattern do not have
       # xtypes specified. I just make them int types.
       #
       if operand.xtype == None:
           operand.xtype = 'int'
       x_xtype ='XED_OPERAND_XTYPE_%s' % operand.xtype.upper()
       
       x_rw   = 'XED_OPERAND_ACTION_%s' % operand.rw.upper()
       x_cvt_index = str(operand.cvt_index)
   except:
       mbuild.die("ERROR processing operand %s" % (str(operand)))

   if operand.oc2:
      x_oc2 ='XED_OPERAND_WIDTH_%s' % (operand.oc2.upper())
   else:
      try:
          if operand.type == 'nt_lookup_fn':
              x_oc2 ='XED_OPERAND_WIDTH_%s' % ( 
                  agi.extra_widths_nt[operand.lookupfn_name].upper() )
          elif operand.type == 'reg':
              tname = re.sub('XED_REG_', '', operand.bits)
              x_oc2 ='XED_OPERAND_WIDTH_%s' % ( 
                  agi.extra_widths_reg[tname].upper() )
          elif operand.type == 'imm_const':
              x_oc2 ='XED_OPERAND_WIDTH_%s' % ( 
                  agi.extra_widths_imm_const[operand.name].upper() )
          else:
              mbuild.msgb("INVALID WIDTH CODE", str(operand))
              x_oc2 ='XED_OPERAND_WIDTH_INVALID'
      except:
          mbuild.msgb("INVALID WIDTH CODE", str(operand))
          x_oc2 ='XED_OPERAND_WIDTH_INVALID'
          
   if operand.type == 'nt_lookup_fn':
       nt = '1'
   else:
       nt = '0'
   args = [ x_name, x_vis, x_rw, x_oc2, x_type, x_xtype, 
            x_cvt_index, x_imm_nt_reg, nt ]

   try:
      #msgb("X_NAME", x_name)
      s_args = ",".join(args)
      data_table_file.add_code( '/*%4d*/ XED_DEF_OPND(%s),' % 
                                (this_operand, s_args) )
   except:
      die("Bad token in list: %s" % (str(args)))

   return True

def memorize_attributes_equation(agi, attr_string_or):
    try:
        return agi.attributes_dict[attr_string_or]
    except:
        p = agi.attr_next_pos
        if vattr():
            msgb("Memorizing attribute", 
                 "%d -> %s" % (p, attr_string_or))

        agi.attributes_dict[attr_string_or] = p
        agi.attr_next_pos = p + 1
        return p



def make_one_attribute_equation(attr_grp,basis):                 
    one = '((xed_uint64_t)1)'
    attr_string_or = None
    for a in attr_grp:
        if basis:
            rebase = "(%s<<(XED_ATTRIBUTE_%s-%d))" % (one, a, basis)
        else:
            rebase = "(%s<<XED_ATTRIBUTE_%s)" % (one, a)

        if attr_string_or:
            attr_string_or = "%s|%s" % (attr_string_or, rebase)
        else:
            attr_string_or = rebase

    return attr_string_or
    
def lookup_attr(agi, attr):
    try:
        return agi.sorted_attributes_dict[attr]
    except:
        die("Failed to find attribute [%s] in attributes dictionary" % (attr))

def partition_attributes(agi, attr):
    """Partition the attributes in to groups of 64 by their
    ordinality.  Return a list of groups. 0..63 are in one group,
    64...127 in the next, etc.
    """
    
    d = { 0:[], 1:[] }
    #msgb("PARTITIONING ATTRIBUTES", '[%s]' % (",".join(attr)))
    for a in attr:
        i = lookup_attr(agi,a)
        b = i // 64
        try:
            d[b].append(a)
        except:
            d[b] = [a]
    return d
    

def make_attributes_equation(agi,ii):
   """Make a unique key representing the attributes of this instruction"""
   key = ''
   if field_check(ii,'attributes'):
      if ii.attributes:
         trimmed_attributes = \
             list(filter(lambda s: s.find('=') == -1 ,ii.attributes))

         if len(trimmed_attributes) > 0:
             trimmed_attributes.sort()
             key = ",".join(trimmed_attributes)

   n  = memorize_attributes_equation(agi,key)
   return n

def make_attributes_structure_init(agi,v):
   eqns = {0:'0',1:'0'}

   if v:
       groups = partition_attributes(agi, v)
       n = len(groups)
       for i in range(0,n):
           g = groups[i]
           eqns[i] = make_one_attribute_equation(g,i*64)

   el = []
   n = len(eqns)
   for i in range(0,n):
       if eqns[i]:
           el.append(eqns[i])
       else:
           el.append('0')

   s = '{ %s }' % (",".join(el))
   return s

############################################################################
global_operand_table = {}
global_operand_table_id = 0
global_id_to_operand = {}
global_oid_sequences = {}
global_max_operand_sequences = 0
global_oid_sequence_id_to_oid_list = {}
def remember_operand(xop):
   """Call this from wherever operands are created. It assigns unique
   IDs to each operand."""

   global global_operand_table
   global global_operand_table_id
   global global_id_to_operand

   try:
      xop.unique_id = global_operand_table[xop]
      #msgb("A9: Found existing operand ID {} for {}".format(xop.unique_id, str(xop)))
   except:
      global_operand_table[xop] = global_operand_table_id
      xop.unique_id = global_operand_table_id
      global_id_to_operand[xop.unique_id] = xop
      global_operand_table_id = global_operand_table_id  + 1

import hlist
def find_common_operand_sequences(agi):
    """Label each instruction with an oid_sequence number that
    corresponds to its operand sequence. The operands get their
    unique_ids first. """

    global global_operand_table_id # counter of # of operands
    global global_oid_sequences 
    global global_max_operand_sequences
    global global_oid_sequence_id_to_oid_list
    next_oid_seqeuence = 0
    reused = 0
    n_operands = 0
    for gi in agi.generator_list:
        for ii in gi.parser_output.instructions:
            # build up a list of operand unique indices
            ii.oid_list  = []
            for op in ii.operands:
                # skip the internal operands
                if op.internal:
                    continue
                remember_operand(op)
                ii.oid_list.append(op.unique_id)

            # then find out if other instructions share that operand sequence
            hl = hlist.hlist_t(ii.oid_list)
            try:
                (ii.oid_sequence, ii.oid_sequence_start) = \
                    global_oid_sequences[hl]
                reused = reused + 1
            except:
                ii.oid_sequence = next_oid_seqeuence
                ii.oid_sequence_start = n_operands
                global_oid_sequences[hl] = (next_oid_seqeuence, n_operands)
                global_oid_sequence_id_to_oid_list[next_oid_seqeuence] = hl
                next_oid_seqeuence = next_oid_seqeuence + 1
                n_operands = n_operands + len(ii.oid_list)

    msgb("Unique Operand Sequences", str(next_oid_seqeuence))
    n = 0
    for k in global_oid_sequences.keys():
        n = n + len(k.lst)
    global_max_operand_sequences = n
    msgb("Number of required operand sequence pointers", 
         str(global_max_operand_sequences))
    msgb("Number of reused operand sequence pointers", str(reused))
    msgb("Number of required operands", str(global_operand_table_id))


def code_gen_operand_sequences(agi):
    global global_oid_sequences
    global global_oid_sequence_id_to_oid_list

    m = len(global_oid_sequences)
    k = 0
    for i in range(0, m):
        hl = global_oid_sequence_id_to_oid_list[i]
        for oi,n in enumerate(hl.lst):
            s = '/* %4d %4d.%1d */ %6d,' % (k, i, oi, n)
            agi.operand_sequence_file.add_code(s)
            k = k + 1

def code_gen_unique_operands(agi):
    global global_operand_table_id
    global global_id_to_operand

    for i in range(0,global_operand_table_id):
        operand = global_id_to_operand[i]
        okay = code_gen_itable_operand(agi, agi.data_table_file, operand)
        if not okay:
            die("operand code gen failed")

############################################################################
max_operand_count = 0
global_final_inum = 0
global_emitted_zero_inum = False
def code_gen_instruction(agi, options, ii, state_dict, fo, 
                         nonterminal_dict, operand_storage_dict):
   """Emit code for one instruction entry"""
   global max_operand_count
   fp = agi.inst_fp

   itable = 'xed_inst_table[' + str(ii.inum) + ']'
   global global_final_inum
   if ii.inum > global_final_inum:
      global_final_inum = ii.inum

   global global_emitted_zero_inum
   if ii.inum == 0:
       if global_emitted_zero_inum:
           return
       global_emitted_zero_inum = True

   has_iclass =  field_check(ii,'iclass')
   if verb1():
      s = "code_gen_instruction - inum: " + str(ii.inum) + ' ' 
      if has_iclass:
         s += ii.iclass
      else:
         s += 'no-iclass'
      msge( s) 

   # print the operands - separate table with 'index & count" pointers
   # in this table
   operand_count = 0
   for operand in ii.operands:
      if operand.type == 'error':
          continue
      if operand.internal:
          continue

      operand_count = operand_count + 1
   if operand_count != len(ii.oid_list):
       die("Mismatch on operand list for %s" % (str(ii)))

   # print the flags - separate table with "index & count" pointers in
   # this table
   flgrec=0
   complex =False
   if field_check(ii,'flags_info'):
      if ii.flags_info:
         # emit the rflags info
         #FIXME: OLD (flgrec, complex) = ii.flags_info.code_gen(itable, fo)
         (flgrec, complex) = ii.flags_info.emit_data_record(agi.flag_simple_file,
                                                            agi.flag_complex_file,
                                                            agi.flag_action_file)


   # not using "1ULL" because that does not work with VC6 (!!!)
   one = '((xed_uint64_t)1)'
   # emit attributes
   attributes_index = make_attributes_equation(agi,ii)

   operand_names = [ x.name.upper() for x in ii.operands]

   # THE NEW WAY - DATA INITIALIZATION -- see include/private/xed-inst-defs.h
   cpl = '3'
   if has_iclass:
      args = [ 'XED_ICLASS_%s' % (ii.iclass.upper()),
               'XED_CATEGORY_%s' % (ii.category.upper()),
               'XED_EXTENSION_%s' % (ii.extension.upper()) ]
      if ii.cpl:
         cpl = str(ii.cpl)
      args.append(cpl)
      args.append('XED_IFORM_%s'  %( ii.iform_enum))

   else:
      args = [ 'XED_ICLASS_INVALID',
               'XED_CATEGORY_INVALID',
               'XED_EXTENSION_INVALID']
      args.append(cpl)
      args.append('XED_IFORM_INVALID')

         
   #if field_check(ii,'ucode') and ii.ucode:
   #   args.append(str(ii.ucode))
   #else:
   #   args.append('0')


   args.append(str(ii.oid_sequence_start))
   args.append(str(operand_count))
   if operand_count > max_operand_count:
       max_operand_count = operand_count
   
   args.append(str(flgrec))
   if complex:
      flagtype = '1'
   else:
      flagtype = '0'
   args.append(flagtype)
   
   args.append(str(attributes_index))
   if field_check(ii,'exceptions') and ii.exceptions:
       args.append('XED_EXCEPTION_' + ii.exceptions)
   else:
       args.append('XED_EXCEPTION_INVALID')

   s_args = ",".join(args)
   
   fp.add_code( '/*%4d*/ XED_DEF_INST(%s),' % (ii.inum, s_args) )




#$$ table_init_object
class table_init_object_t(object):
   def __init__(self, file_name, function_name):
      self.file_name_prefix = file_name
      self.function_name_prefix = function_name
      
      self.fp = None # file pointer
      self.fo = None # function_object_t
      self.init_functions = []
      self.max_lines_per_file = 3000

   def get_init_functions(self):
      return self.init_functions
   
   def get_fo(self,gi):
      if not self.fp:
         # make a new output file and new function obj if we don't
         # already have one
         n = str(len(self.init_functions))
         self.fp = gi.common.open_file(self.file_name_prefix + n + '.c', 
                                       start=False)
         self.fp.start()
         
         full_function_name = self.function_name_prefix + n
         self.fo = function_object_t(full_function_name,"void")
         self.init_functions.append(self.fo)
      return self.fo
   
   def check_file(self):
      if self.fo:
         if self.fo.lines() >= self.max_lines_per_file:

            self.fp.write(self.fo.emit())
            self.fp.close()
            del self.fp

            self.fo = None
            self.fp = None
         
   def finish_fp(self):
      # write anything that didn't get emitted already
      if self.fp:
         self.fp.write(self.fo.emit())
         self.fp.close()
         del self.fp

         self.fo = None
         self.fp = None


   
   
   
def code_gen_instruction_table(agi, gi, itable_init, nonterminal_dict,
                               operand_storage_dict):
   """Emit a table of all instructions. itable_init is a
   table_init_object_t with a list of function_object_ts to which we add
   those that we create."""
   if vtrace():
      msge("code_gen_instruction_table")

   for ii in gi.parser_output.instructions:
      fo = itable_init.get_fo(gi)
      code_gen_instruction(agi,
                           gi.common.options,
                           ii,
                           gi.common.state_bits,
                           fo,
                           nonterminal_dict,
                           operand_storage_dict)
      
      itable_init.check_file()
      

def rewrite_default_operand_visibilities(generator,
                                         operand_field_dict):
   """Change the default visibilty of any operand to the visibilty
   indicated by the operand_field_t in the dictionary."""

   if not generator.parser_output.is_lookup_function():
      for ii in generator.parser_output.instructions:
         #if field_check(ii,'iclass'):
         #   mbuild.msgb("Processing", ii.iclass)
         for opnd in ii.operands:
            #mbuild.msgb("Operand", "\t%s" % (str(opnd)))
            if opnd.visibility == 'DEFAULT':
               new_vis = operand_field_dict[opnd.name].default_visibility
               if vopvis():
                  msge("OPVIS-DELTA: " + opnd.name + " to " + new_vis )
               opnd.visibility = new_vis
               
#################################################################
def emit_string_table(agi, iclass_strings):

    f = agi.common.open_file('xed-iclass-string.c', start=False)
    f.add_misc_header('#include "xed-gen-table-defs.h"')
    f.add_misc_header('#include "xed-tables-extern.h"')
    f.start()
    s = 'char const* const xed_iclass_string[XED_ICLASS_NAME_STR_MAX] = {\n'
    f.write(s)
    for i in iclass_strings:        
        f.write('"%s",\n' % (i))
    f.write('};\n')
    f.close()
        

def collect_iclass_strings(agi):
    """We collect the disasm strings in pairs. One for Intel, One for
    ATT SYSV syntax"""
    iclass_strings = ['invalid','invalid']
    
    # string table indexed by intel syntax dotted with the att syntax
    st = { 'invalid.invalid': 0 }
    n = 2
    for generator in agi.generator_list:
        ii = generator.parser_output.instructions[0]
        if not field_check(ii,'iclass'):
            continue
        for ii in generator.parser_output.instructions:
            if field_check(ii,'disasm_intel'):
                if not field_check(ii,'disasm_att'):
                    die("Missing att syntax when intel sytnax" + 
                        " is provided for %s" % (ii.iclass))
            if field_check(ii,'disasm_att'):
                if not field_check(ii,'disasm_intel'):
                    die("Missing intel syntax when att sytnax " +
                        " is provided for %s" % (ii.iclass))
            if field_check(ii,'disasm_att'):
                k = '%s.%s' % (ii.disasm_intel, ii.disasm_att)
                if k in st:
                    ii.iclass_string_index = st[k]
                else:
                    st[k] = n
                    ii.iclass_string_index = n
                    iclass_strings.append(ii.disasm_intel)
                    iclass_strings.append(ii.disasm_att)
                    n = n + 2

    agi.max_iclass_strings = n
    emit_string_table(agi, iclass_strings)

def compress_iform_strings(values):
   # values are a list of 3 tuples (iform string, index, comment) and
   # the comments are generally empty strings.
    bases = {}
    operand_sigs = { '':0 }
    o_indx = 1
    b_indx = 0
    h  = {} # map index to base, operand indices

    # split the bases (iclass name, mostly) and operand sigs.
    # assign ids to the bases and to the operand sigs
    for iform,index,comment in values:
        try:
            s,rest = iform.split("_",1)
            if s not in bases:
                bases[s]=b_indx
                b = b_indx
                b_indx += 1
            if rest not in operand_sigs:
                operand_sigs[rest] = o_indx
                o = o_indx
                o_indx += 1
        except:
            if iform not in bases:
                bases[iform]=b_indx
                b = b_indx
                o = 0
                b_indx += 1
        # store the base,operand_sig pair 
        h[int(index)] = (b,o)
        
    print("XZ: NTUPLES {} BASES {}  OPERAND_SIGS {}".format(len(values),
                                                            len(bases),
                                                            len(operand_sigs)))

    if len(h) != (max( [ int(x) for x in h.keys() ] )+1):
        print("PROBLEM IN h LENGTH")
    # make an numerically indexed version of the bases table
    bi = {}
    for k,v in bases.items():
        bi[v] = k
    # make an numerically indexed version of the operand_sig table
    oi = {}
    for k,v in operand_sigs.items():
        oi[v] = k

    f = sys.stdout

    f.write('static const char* base[] = {\n')
    for i in range(0,len(bases)):
        f.write( '/* {} */ "{}",\n'.format(i,bi[i]) )
    f.write('};\n')

    f.write('static const char* operands[] = {\n')
    for i in range(0,len(operand_sigs)):
        f.write('/* {} */ "{}",\n'.format(i,oi[i]))
    f.write('};\n')

    f.write('static const iform_name_chunks[] = {\n')
    for i in range(0,len(h)):
        a,b = h[i]
        f.write( '/* {} */ {{ {},{} }},\n'.format(i,a,b))
    f.write('};\n')

        
def generate_iform_enum(agi,options,values):
   # values are a list of 3 tuples (iform string, index, comment) and
   # the comments are generally empty strings.
   string_convert = 1
   if options.limit_enum_strings:
       string_convert = 0
   enum =  enum_txt_writer.enum_info_t(values,
                                       options.xeddir, options.gendir,
                                       'xed-iform',
                                       'xed_iform_enum_t', 'XED_IFORM_',
                                       cplusplus=False,
                                       extra_header = ['xed-common-hdrs.h',
                                                       'xed-iclass-enum.h'],
                                       upper_case=False,
                                       string_convert=string_convert)
   enum.print_enum()
   enum.run_enumer()
   agi.add_file_name(enum.src_full_file_name)
   agi.add_file_name(enum.hdr_full_file_name,header=True)

def generate_iform_first_last_enum(agi,options,values):
   enum =  enum_txt_writer.enum_info_t(values,
                                       options.xeddir, options.gendir,
                                       'xed-iformfl', 
                                       'xed_iformfl_enum_t', 
                                       'XED_IFORMFL_',
                                       cplusplus=False,
                                       extra_header = ['xed-common-hdrs.h', 
                                                       'xed-iclass-enum.h'],
                                       upper_case=False,
                                       string_convert=-1)
   enum.print_enum()
   enum.run_enumer()
   agi.add_file_name(enum.src_full_file_name)
   agi.add_file_name(enum.hdr_full_file_name,header=True)



global_max_iforms_per_iclass = 0

def collect_and_emit_iforms(agi,options):
   iform_dict = {} # build dictionary by iclass of [iform,...]
   for generator in agi.generator_list:
      ii = generator.parser_output.instructions[0]
      if not field_check(ii,'iclass'):
         continue
      for ii in generator.parser_output.instructions:
         try:
            iform_dict[ii.iclass].append(ii.iform_enum)
         except:
            iform_dict[ii.iclass] = [ii.iform_enum]

   # number them from zero, per iclass
   vtuples = [('INVALID', 0, 'INVALID') ]
   imax = {} # maximum number of iforms per iclass
   for ic,ol in iform_dict.items():
      ol = uniqueify(ol)
      sz= len(ol)
      vsub = zip([ic.upper()]*sz,   # the iclass
                 range(0,sz),       # number the iforms
                 ol)                # the list of iform names
      imax[ic] = sz
      vtuples.extend(vsub)

   #msge("VTUPLES %s" % (str(vtuples)))
   # Relying on stable sorting. sort first by 2nd field (#1), then
   # sort by iclass, making sure "INVALID" is first.
   vtuples.sort(key=key_tuple_element_1)
   vtuples.sort(key=key_invalid_tuple_element_0)


   agi.iform_tuples = vtuples
   
   # number the tuples from 0
   ntuples = []
   for i,v in enumerate(vtuples):
      lv = list(v)
      lv.extend([str(i),''])
      t = tuple(lv)
      ntuples.append(t)

   #msge("NTUPLES %s" % (str(ntuples)))
   # add a first and last element for each group of iforms (per iclass)
   first_last_tuples = []
   last_tuple = None
   ifirst = {}
   for v in ntuples:
      if last_tuple and last_tuple[0] != v[0]:
         if last_tuple[0] != 'INVALID':
            t = ( 'INVALID', 0, last_tuple[0] + "_LAST", last_tuple[3], '')
            first_last_tuples.append(t)
         t = ( 'INVALID', 0, v[0] + "_FIRST", v[3], '')
         ifirst[v[0]] = int(v[3])
         first_last_tuples.append(t)
      last_tuple = v
   if last_tuple and last_tuple[0] != 'INVALID':
      t = ( 'INVALID', 0, last_tuple[0] + "_LAST", last_tuple[3], '')
      first_last_tuples.append(t)


   #msge("NTUPLES %s" % (str(ntuples)))
   # rip off first two fields of vtuples
   vtuples = [  x[2:] for x in ntuples]

   #for t in vtuples:
   #   msge("TUPLE " + str(t))
   generate_iform_enum(agi,options,vtuples)
   # compress_iform_strings(vtuples)

   # rip off first two fields of vtuples
   first_last_tuples = [ x[2:] for x in  first_last_tuples]
   generate_iform_first_last_enum(agi,options,first_last_tuples)   

   #emit  imax in global iclass order for data-initialization!
   cfp = agi.open_file('xed-iform-max.c')
   cfp.write('const xed_uint32_t ' +
             'xed_iform_max_per_iclass_table[XED_ICLASS_LAST] = {\n')
   first = True
   gmax = 0  # maximum number of iforms for any iclass
   niform = 0 # total number of iforms
   for ic in agi.iclasses_enum_order:
      if first:
         first = False
      else:
         cfp.write(',\n')
      try:
         mx = imax[ic]
      except:
         mx = 0  # for the INVALID entry
      if mx > gmax:
         gmax = mx
      niform = niform + mx
      cfp.write('  /* %25s */  %2d' % (ic,mx))
   cfp.write('\n};\n')


   cfp.write('const xed_uint32_t' + 
             ' xed_iform_first_per_iclass_table[XED_ICLASS_LAST] = {\n')
   first = True
   niform = 0 # total number of iforms
   for ic in agi.iclasses_enum_order:
      if first:
         first = False
      else:
         cfp.write(',\n')
      try:
         firstiform = ifirst[ic]
      except:
         firstiform = 0  # for the INVALID entry

      cfp.write('  /* %25s */  %2d' % (ic,firstiform))
   cfp.write('\n};\n')

   cfp.close()
   
   global global_max_iforms_per_iclass
   global_max_iforms_per_iclass = gmax

   
############################################################################

def relabel_itable(agi):
   """Renumber the itable so that it is sequential."""
   global global_inum
   inum = 1
   for gi in agi.generator_list:
      if not gi.parser_output.is_lookup_function():
         for ii in gi.parser_output.instructions:
            has_iclass =  field_check(ii,'iclass')
            if has_iclass:
                ii.inum = inum
                inum += 1
            else:
                # make all the non-instruction leaves point to node zero
                ii.inum = 0
   global_inum = inum


############################################################################
# The renum_node_id is global because we renumber each graph so that
# we have contiguous numbers for graph code-gen for the distinct subgraphs.
renum_node_id = -1
def renumber_nodes(options,node):
   """renumber the nodes now that we've deleted some"""
   #msge("renumbering graph nodes..")
   renumber_nodes_sub(options,node)
   global renum_node_id
   #msge(" ...last node id = %d" % (renum_node_id))

def renumber_nodes_sub(options,node):
   """renumber the nodes now that we've deleted some"""
   # bump the 'global' node counter
   global renum_node_id
   renum_node_id = renum_node_id + 1
   # update the current node
   #msge("RENUMBER NODE %d becomes %d" % ( node.id, renum_node_id))
   node.id = renum_node_id
   # recur
   for nxt in node.next.values():
      renumber_nodes_sub(options,nxt)


def merge_child_nodes(options,node):
   """Merge the children and grandchildren of this node."""
   candidates = len(node.next)
   if vmerge():
      msge(str(candidates) + " merge candidate")
   # merge tokens??
   # should not need to merge instructions
   # bit_pos* becomes a bigger range
   # more "next" nodes.
   tnode = {}
   for k,child in node.next.items():      # children  # MERGING 
      for j in child.next.keys():  # grandchildren
         bigkey = str(k) + str(j)
         if vmerge():
            msge("Bigkey= %s"  % (bigkey))
         child.next[j].token = bigkey
         tnode[bigkey] = child.next[j]
   # overwrite the current nodes next pointers:
   node.next = tnode
            
   # increment number of decider bits
   node.decider_bits = node.decider_bits + 1
   if vmerge():
      msge("Decider bits after merging = " + str(node.decider_bits))



def merge_nodes(options,node):
   """Merge compatible nodes, deleting some nodes and increasing the
   arity of others"""
   # If nodes are sequential in their bit positions and the next one
   # is not a leaf, consider merging them.

   #FIXME: must not merge across state bits.
   if (not node.is_nonterminal() and 
       not node.leaf() and 
       not node.is_operand_decider()):
      merging = True
      while merging:
         all_match = True
         decider_bits = [ node.next[k].decider_bits for k in 
                          list(node.next.keys()) ]
         if not all_the_same(decider_bits):
            if vmerge():
               msge("Not merging because unequal numbers of decider" +
                    " bits follow:" + str(decider_bits))
               for nxt in node.next.values():
                  msge("\tChildNode:\n" +nxt.dump_str('\t\t'))
            all_match = False
            break


         # stop at byte boundaries. All the children have the same
         # number of decider bits at this point. Look at the first
         # one.
         if decider_bits[0] == 8:
            msge("Stopping child nodes with 8 decider bits")
            break
         if vmerge():
            msge("PREMRG node decider " + 
                 "bits= %d child decider bits= %d bitpos_mod8= %d\n" %
                 ( node.decider_bits, decider_bits[0], node.bitpos_mod8))

         # FIXME: the following is not right. We want the bitpos_mod8
         # of the child because that is what we are merging with the
         # grandchild. We also don't care about the decider its of the parent.
         
         # FIXME: we are not updating the bitpos_mod8 of the children
         # when we merge them.

         # NOTE: IT IS BETTER NOT DO DO THIS TEST AT ALL. THE GRAPH IS
         # MUCH SMALLER.  but more 'next' nodes, which are much
         # smaller. so that is good!
         
         # Do not want to merge across byte boundaries.
         #if node.decider_bits + decider_bits[0] + node.bitpos_mod8 > 8:
         #if node.decider_bits + decider_bits[0] + node.bitpos_mod8 > 8:
         #   msge("Stopping child node merging at a byte boundary")
         #   break
         
            
         # look at all the next nodes
         for child in node.next.values():
            if child.back_split_pos != None:
               if vmerge():
                  msge("Not merging because a child is back-split")
               all_match = False
               break
            if child.is_nonterminal():
               if vmerge():
                  msge("Not merging because a child is a nonterminal")
               all_match = False
               break
            if child.decider_bits == 0: # FIXME: WHY WOULD THIS HAPPEN?
               if vmerge():
                  msge("Not merging because zero decider bits follow: " + 
                       str(child.decider_bits))
                  msge("\tChildNode:\n" + child.dump_str('\t'))
               all_match = False
               break
            if child.skipped_bits != 0: 
               if vmerge():
                  msge("Not merging because skipped bits at child level: " + 
                       str(child.skipped_bits))
               all_match = False
               break
                  

         if all_match:
            merge_child_nodes(options,node)

         else:
            merging = False

   # recur
   for child in node.next.values():
      merge_nodes(options,child)

def optimize_graph(options, node):
   """return an optimized graph. Merge compatible nodes."""
   if vgraph_res():
      print_resource_usage('optimize-graph.0')
   merge_nodes(options,node)
   if vgraph_res():
      print_resource_usage('optimize-graph.1')
   renumber_nodes(options,node)
   if vgraph_res():
      print_resource_usage('optimize-graph.2')
   

def epsilon_label_graph(options, node):
   node.otherwise_ok  = True
   # recur
   for child in node.next.values():
      epsilon_label_graph(options,child)
   
############################################################################
## Packers and extractors
############################################################################
# $$ bit_group_info_t
class bit_group_info_t(object):
   """Tell us where physical bits are symbolically. Each bit_group_info_t has:
   
      a bit name
      a bit instance - the i'th copy of the named bit

      a length - number of bits in this group. So this group is bit i
      though bit i+length-1.

      a position - not counting NONTERMINALS or OPERAND DECIDERS. 

      a nonterminal adder - a string describing all previous
      nonterminals encountered)

      a nonterminal instance - counting any and all kinds of
      nonterminals in this pattern
   """
   def __init__(self, 
                bit_name, 
                instance, 
                position_count, 
                nonterminal_adder, 
                nonterminal_instance=0):
      self.bit_name = bit_name
      # number of the first bit of this run
      self.bit_instance = instance
      # length of this run of bits
      self.length = 1
      self.position_count = position_count
      self.position_nonterminal_adders = nonterminal_adder

      # for nonterminals, the nonterminal_instance says the numeric id
      # of this sub-nonterminal in the current nonterminal. If there
      # are 4 sub-nonterminals in a nonterminal, they are numbered 0
      # to 3. This index is used to index in to the nonterminal storage
      # associated with the current nonterminal.
      self.nonterminal_instance = 0
      
   def emit(self):
      "return a string"
      lst = [self.bit_name ]
      if self.bit_instance != 0:
         lst.append('instnc:'+str(self.bit_instance))
      lst.append( 'len:'+str(self.length) )
      lst.append(  'pos:'+str(self.position_count) )
      if self.position_nonterminal_adders != '':
         lst.append('ntadders:'+self.position_nonterminal_adders)
      s = '/'.join(lst)
      return s

   
def print_bit_groups(bit_groups, s=''):
   q = "BITGRP:"
   for b in bit_groups:
      q = q + b.emit() + ' '
   msge(s + " " + q)

############################################################################

def emit_function_headers(fp, fo_dict):
   """For each function in the fo_dict dictionary, emit the function
   prototype to the fp file emitter object."""
   for fname in fo_dict.keys():
      fo = fo_dict[fname]
      fp.write(fo.emit_header())
      
############################################################################
def mark_operands_internal(agi, parser_output):
    """Go through all the operands in the parser and mark each
    internal or not. They have already been expanded and cleaned
    up."""

    for ii in parser_output.instructions:
        for op in ii.operands: # opnds.operand_info_t list
            ip = agi.operand_storage.get_operand(op.name).internal_or_public
            if ip  == "INTERNAL":
                op.internal = True


def rewrite_state_operands(agi, state_bits, parser_output):
   """For each operand in the parser output, make sure we denote state
   modifcations as operands and not flags"""
   for pi in parser_output.instructions:
      expand_operands(agi, pi, state_bits)

def expand_operands(agi, pi, state_bits):
   """make opnds.operand_info_t's for any un-expanded operands based on the
   strings stored in the state_bits."""
   new_list = []
   for x in pi.operands: # opnds.operand_info_t list
      found = None
      if x.name in state_bits:
         found = x.name
      else:
         lwr = x.name.lower()
         if lwr in state_bits:
            found = lwr

      # the state name we found might expand in to more than one operand.
      if found:
         for v in state_bits[found].list_of_str:
            if vmacro():
               msge("Expanding %s to %s" % (found,v))
            eqp = equals_pattern.match(v)
            if eqp:
               new_operand = mk_opnd(agi, v, default_vis='SUPP')
               if new_operand:
                   new_operand.set_suppressed()
                   new_list.append(new_operand)
            else:
               die("Could not find equals sign in state macro definition of " +
                   x.name)
      elif x.type == 'flag':
         die("THIS SHOULD NOT HAPPEN - FLAG: %s" % (x.name))
      else:
         new_list.append(x)
   pi.operands = new_list



def expand_hierarchical_records(ii):
   """Return a list of new records splitting the extra_ipatterns and
   extra_operands in to new stuff"""
   new_lines = []

   # FIXME: perf: 2007-08-05 mjc could skip this expansion when not
   # needed and save the copying.

   extra_operands = ii.extra_operands
   extra_ipatterns = ii.extra_ipatterns
   extra_iforms_input = ii.extra_iforms_input
   ii.extra_operands = None
   ii.extra_ipatterns = None
   ii.extra_iforms_input = None   
   
   # start with the first instruction, then expand the "extra" ones
   new_lines.append(ii)

   if len(extra_ipatterns) != len(extra_operands) or \
      len(extra_ipatterns) != len(extra_iforms_input):
      die("Missing some patterns, operands or iforms for " + ii.iclass)
      
   for (ipattern, operands, iform) in zip(extra_ipatterns, 
                                          extra_operands, 
                                          extra_iforms_input):
      new_rec = copy.deepcopy(ii)
      new_rec.new_inum()
      new_rec.extra_operands = None
      new_rec.extra_ipatterns = None
      new_rec.extra_iforms_input = None
      new_rec.ipattern_input = ipattern
      new_rec.operands_input = operands
      new_rec.iform_input = iform
      #msge("ISET2: %s -- %s" % (iform, str(operands)))
      new_lines.append(new_rec)

   del extra_ipatterns
   del extra_operands
   return new_lines



# $$ generator_common_t
class generator_common_t(object):
   """This is stuff that is common to every geneator and the
   agi. Basically all the globals that are needed by most generator
   specific processing."""

   def __init__(self):
      self.options = None
      self.state_bits = None # dictionary of state_info_t's
      self.state_space = None # dictionary of all values of each state
                              # restriction (operand_decider)

      self.enc_file = None
      self.inst_file = None
      self.operand_storage_hdr_file = None
      self.operand_storage_src_file = None
      
      self.header_file_names = []
      self.source_file_names = []
      self.file_pointers = []

      self.inst_table_file_names = []

   def get_state_space_values(self,od_token):
       '''return the list of values associated with this token'''
       return self.state_space[od_token]
      
   def open_file(self,fn, arg_shell_file=False, start=True):
      'open and record the file pointers'

      fp = xed_file_emitter_t(self.options.xeddir,
                              self.options.gendir,
                              fn,
                              shell_file=arg_shell_file)
      if is_header(fn):
          self.header_file_names.append(fp.full_file_name)
      else:
          self.source_file_names.append(fp.full_file_name)

      if start:
          fp.start()
      self.file_pointers.append(fp)
      return fp

   def build_fn(self,tail,header=False):
      'build and record the file names'
      if True: # MJC2006-10-10
         fn = tail
      else:
         fn = os.path.join(self.options.gendir,tail)
         if header:
            self.header_file_names.append(fn)
         else:
            self.source_file_names.append(fn)
      return fn
   
   def open_all_files(self):
      "Open the major output files"
      msge("Opening output files")

      header = True


      self.inst_file = self.open_file(self.build_fn(
                                          self.options.inst_init_file))

   def open_new_inst_table_file(self):
      i = len(self.inst_table_file_names)
      base_fn = 'xed-inst-table-init-'
      fn = self.build_fn(base_fn + str(i) + ".c")
      self.inst_table_file_names.append(fn)
      fp = self.open_file(fn)
      return fp

         
   def close_output_files(self):
      "Close the major output files"
      for f in self.file_pointers:
         f.close()

# $$ generator_info_t      
class generator_info_t(generator_common_t):
   """All the information that we collect and generate"""
   def __init__(self, common):
      super(generator_info_t,self).__init__()
      self.common = common
      
      if self.common.options == None:
         die("Bad init")
      #old style generator_common_t.__init__(self,generator_common)
      self.parser_output = None # class parser_t
      self.graph = None
      # unique list of iclasses
      self.iclasses = {}

      # list of tuples of (nonterminal names, max count of how many
      # there are of this one per instruction)
      self.nonterminals = []

      # list of opnds.operand_info_t's
      self.operands = None

      self.storage_class = None

      #For thing that are directly translateable in to tables, we
      #generate a table here.
      self.luf_arrays =  []
      self.marshalling_function = None
      
   def nonterminal_name(self):
      """The name of this subtree"""
      s =  self.parser_output.nonterminal_name
      return nonterminal_parens_pattern.sub('', s)

   def build_unique_iclass_list(self):
      "build a unique list of iclasses"
      self.iclasses = {}
      for ii in self.parser_output.instructions:
         if field_check(ii,'iclass'):
            if ii.iclass not in self.iclasses:
               self.iclasses[ii.iclass] = True


# $$ all_generator_info_t
class all_generator_info_t(object):
   """List of generators, each with its own graph"""
   def __init__(self,options):
      #common has mostly input and output files and names
      self.common = generator_common_t()
      self.common.options = options
      self.common.open_all_files()
      
      self.generator_list = []
      self.generator_dict = {} # access by NT name
      self.nonterminal_dict = nonterminal_dict_t()

      self.src_files=[]
      self.hdr_files=[]

      # list of map_info_rdr.map_info_t describing valid maps for this
      # build.
      self.map_info = None 


      # enum lists
      self.operand_types = {} # typename -> True
      self.operand_widths = {} # width -> True # oc2
      self.operand_names = {} # name -> Type
      self.iclasses  = []
      self.categories = []
      self.extensions = []
      self.attributes = []
      
      # for emitting defines with limits
      self.max_iclass_strings = 0
      self.max_convert_patterns = 0
      self.max_decorations_per_operand = 0

      # this is the iclasses in the order of the enumeration for us in
      # initializing other structures.
      self.iclasses_enum_order = None

      # function_object_ts
      self.itable_init_functions = table_init_object_t('xed-init-inst-table-',
                                                       'xed_init_inst_table_')
      self.encode_init_function_objects = []
      
      # dictionaries of code snippets that map to function names
      self.extractors = {}
      self.packers = {}
      
      self.operand_storage = None # operand_storage_t
      

      # function_object_t 
      self.overall_lookup_init = None

      # functions called during decode traverals to capture required operands.
      self.all_node_capture_functions = []

      # data for instruction table
      self.inst_fp = None

      # list of (index, initializer) tuples for all the entire decode graph
      self.all_decode_graph_nodes=[]
      
      self.data_table_file=None
      self.operand_sequence_file=None

      # set by scan_maps
      self.max_map_vex = 0
      self.max_map_evex = 0
      
      # dict "iclass:extension" -> ( iclass,extension, 
      #                               category, iform_enum, properties-list)
      self.iform_info = {} 

      self.attributes_dict = {}
      self.attr_next_pos  = 0
      self.attributes_ordered  = None
      self.sorted_attributes_dict = {}
      # a dict of all the enum names to their values. 
      # passed to operand storage in order to calculate 
      # the number of required bits
      self.all_enums = {} 

      # these are xed_file_emitter_t objects
      self.flag_simple_file = self.common.open_file("xed-flags-simple.c", start=False)
      self.flag_complex_file = self.common.open_file("xed-flags-complex.c", start=False)
      self.flag_action_file = self.common.open_file("xed-flags-actions.c", start=False)
      self.flag_simple_file.add_header('xed-flags.h')
      self.flag_complex_file.add_header('xed-flags.h')
      self.flag_complex_file.add_header('xed-flags-private.h')
      self.flag_action_file.add_header('xed-flags.h')

      self.flag_simple_file.start()
      self.flag_complex_file.start()
      self.flag_action_file.start()

      self.emit_flag_simple_decl()
      self.emit_flag_complex_decl()
      self.emit_flag_action_decl()

   def close_flags_files(self):
       self.emit_close_array(self.flag_simple_file)
       self.emit_close_array(self.flag_complex_file)
       self.emit_close_array(self.flag_action_file)
       
   def emit_flag_simple_decl(self):
       self.flag_simple_file.add_code("const xed_simple_flag_t xed_flags_simple_table[] = {")
       self.flag_simple_file.add_code("/* 0 */ {0,0,0,{0},{0},{0},0}, /* invalid */")

   def emit_flag_action_decl(self):
       self.flag_action_file.add_code("const xed_flag_action_t xed_flag_action_table[] = {")

   def emit_flag_complex_decl(self):
       self.flag_complex_file.add_code("const xed_complex_flag_t xed_flags_complex_table[] = {")
       self.flag_complex_file.add_code("/* 0 */ {0,0,{0,0,0,0,0},}, /* invalid */")

   def emit_close_array(self,f):
       f.add_code_eol("}")


   def open_operand_data_file(self):
      self.data_table_file=self.open_file('xed-init-operand-data.c', 
                                          start=False)
      self.data_table_file.add_header('xed-inst-defs.h')
      self.data_table_file.start()
      s = ('XED_DLL_EXPORT const xed_operand_t ' + 
          'xed_operand[XED_MAX_OPERAND_TABLE_NODES] = {\n')
      self.data_table_file.write(s)

   def close_operand_data_file(self):
      self.data_table_file.write('};\n')
      self.data_table_file.close()




   def open_operand_sequence_file(self):
      self.operand_sequence_file = \
          self.open_file('xed-init-operand-sequences.c', 
                         start=False)
      self.operand_sequence_file.add_header('xed-inst-defs.h')
      self.operand_sequence_file.start()
      s = ('XED_DLL_EXPORT const xed_uint16_t ' + 
          'xed_operand_sequences[XED_MAX_OPERAND_SEQUENCES] = {\n')
      self.operand_sequence_file.write(s)

   def close_operand_sequence_file(self):
      self.operand_sequence_file.write('};\n')
      self.operand_sequence_file.close()

      
   def add_file_name(self,fn,header=False):
      if type(fn) in [bytes,str]:
          fns = [fn]
      elif type(fn) == list:
          fns = fn
      else:
          die("Need string or list")
      
      for f in fns:
          if header:
             self.hdr_files.append(f)
          else:
             self.src_files.append(f)

   def dump_generated_files(self):
       """For mbuild dependence checking, we need an accurate list of the
          files the generator created. This file is read by xed_mbuild.py"""
       
       output_file_list = mbuild.join(self.common.options.gendir, 
                                      "DECGEN-OUTPUT-FILES.txt")
       f = base_open_file(output_file_list,"w")
       for fn in self.hdr_files + self.src_files:
           f.write(fn+"\n")
       f.close()
   
   def mk_fn(self,fn):
      if True: #MJC2006-10-10
         return fn
      return self.real_mk_fn(fn)

   def real_mk_fn(self,fn):
      return os.path.join(self.common.options.gendir,fn)
      
   def close_output_files(self):
      "Close the major output files"
      self.common.close_output_files()

   def make_generator(self, nt_name):
      g = generator_info_t(self.common)
      self.generator_list.append(g)
      self.generator_dict[nt_name] = g
      return g


   def open_file(self, fn, keeper=True, arg_shell_file=False, start=True, private=True):
      'open and record the file pointers'

      fp = xed_file_emitter_t(self.common.options.xeddir,
                              self.common.options.gendir,
                              fn,
                              shell_file=arg_shell_file,
                              is_private=private)
      if keeper:
          self.add_file_name(fp.full_file_name, is_header(fn))

      if start:
          fp.start()
      return fp


   def scan_maps(self):
       for generator in self.generator_list:
           for ii in generator.parser_output.instructions:
               if genutil.field_check(ii, 'iclass'):
                   if ii.is_vex():
                       self.max_map_vex = max(self.max_map_vex, ii.get_map())
                   elif ii.is_evex():
                       self.max_map_evex = max(self.max_map_evex, ii.get_map())

                        
   def code_gen_table_sizes(self):
      """Write the file that has the declarations of the tables that we
      fill in in the generator"""
      fn = "xed-gen-table-defs.h"
      # we do not put this in a namespace because it is included while
      # in the XED namespace.
      fi = xed_file_emitter_t(self.common.options.xeddir,
                              self.common.options.gendir,
                              fn,
                              namespace=None)

      self.add_file_name(fi.full_file_name,header=True)
      fi.replace_headers([]) # no headers
      fi.start()

      global global_final_inum
      irecs = global_final_inum + 1 # 7000 

      global global_max_iforms_per_iclass
            
      global operand_max
      orecs = operand_max+1

      fi.add_code("#define XED_ICLASS_NAME_STR_MAX %d" % 
                  (self.max_iclass_strings))

      global max_attributes
      fi.add_code("#define XED_MAX_ATTRIBUTE_COUNT %d" % (max_attributes))
      
      fi.add_code("#define XED_MAX_INST_TABLE_NODES %d" % (irecs))

      global global_operand_table_id
      fi.add_code("#define XED_MAX_OPERAND_TABLE_NODES %d" % 
                  (global_operand_table_id))

      global global_max_operand_sequences
      fi.add_code("#define XED_MAX_OPERAND_SEQUENCES %d" % 
                  (global_max_operand_sequences))

      # flags 
      fi.add_code("#define XED_MAX_REQUIRED_SIMPLE_FLAGS_ENTRIES %d" % 
                  (flag_gen.flags_info_t._flag_simple_rec))
      fi.add_code("#define XED_MAX_REQUIRED_COMPLEX_FLAGS_ENTRIES %d" % 
                  (flag_gen.flags_info_t._flag_complex_rec))
      fi.add_code("#define XED_MAX_GLOBAL_FLAG_ACTIONS %d" % 
                  (flag_gen.flags_info_t._max_flag_actions))


      fi.add_code("#define XED_MAX_IFORMS_PER_ICLASS %d" % 
                  (global_max_iforms_per_iclass))

      fi.add_code("#define XED_MAX_REQUIRED_ATTRIBUTES %d" % 
                  (len(self.attributes_dict)))


      fi.add_code("#define XED_MAX_CONVERT_PATTERNS %d" % 
                  (self.max_convert_patterns))
      fi.add_code("#define XED_MAX_DECORATIONS_PER_OPERAND %d" % 
                  (self.max_decorations_per_operand))

      self.scan_maps()
      fi.add_code("#define XED_MAX_MAP_VEX  {}".format(self.max_map_vex))
      fi.add_code("#define XED_MAX_MAP_EVEX {}".format(self.max_map_evex))
      fi.close()

      
   def handle_prefab_enum(self,enum_fn):
      # parse the enum file and get the c and h file names
      gendir = self.common.options.gendir
      m=metaenum.metaenum_t(enum_fn,gendir)
      m.run_enumer()
      # remember the c & h file names
      self.add_file_name(m.src_full_file_name)
      self.add_file_name(m.hdr_full_file_name,header=True)
      all_values = [  x.name for x in m.tuples ]
      return all_values
      
      

      
   def handle_prefab_enums(self):
      """Gather up all the enum.txt files in the datafiles directory"""
      prefab_enum_shell_pattern = os.path.join(self.common.options.xeddir,
                                               "datafiles/*enum.txt")
      prefab_enum_files = glob.glob( prefab_enum_shell_pattern )
      for fn in prefab_enum_files:
         msge("PREFAB-ENUM: " + fn)
         self.handle_prefab_enum( fn )
         
   def extend_operand_names_with_input_states(self):
      type ='xed_uint32_t'
      for operand_decider in self.common.state_space.keys():
         #msge("STATESPACE: considering " + operand_decider)
         if operand_decider not in self.operand_names:
            self.operand_names[operand_decider] = type



def init_functions_for_table(agi, fp, function_name, init_object):
   """emit, to the file pointer fp, headers and calls to each init
   function for the init_object. The function we build is named
   function_name."""
   print_resource_usage('init.0')   
   # emit prototype for each subgraph init function
   for dfo in init_object.get_init_functions():
      #print_resource_usage('init.1')
      fp.write(dfo.emit_header())

   #print_resource_usage('init.2')
   # a function that calls each init function
   init_fo = function_object_t(function_name,'void')
   for dfo in init_object.get_init_functions():
      init_fo.add_code_eol(dfo.function_name + '()')
   fp.write(init_fo.emit())
   fp.close()
   del fp
   #print_resource_usage('init.3')

############################################################################

def generator_emit_function_list(fo_list, file_emitter):
   """Emit the function_object_t-s in the fo_list list via the file_emitter"""
   for fo in fo_list:
      fo.emit_file_emitter(file_emitter)
      
def generator_emit_function_header_list(fo_list, file_emitter):
   """Emit the function headers for the function_object_t-s in the
   fo_list list via the file_emitter"""
   for fo in fo_list:
      file_emitter.add_code(fo.emit_header())

def make_cvt_key(lst):
    return ",".join(lst)
def make_cvt_values(s,n):
    if s == '':
        return ['INVALID']*n
    t = s.split(",")
    len_t = len(t)
    if len_t < n:
        t.extend(['INVALID']*(n-len_t))
    return t
    
def collect_convert_decorations(agi):
    """Find all instruction operands. Each operand has 0...N where N=3
    currently conversion decorations. Number each combination of
    convert decorations. Assign that number to the instruction. Emit a
    initialized array of convert decoration enumeration names, N-wide.
    Element 0 is special: That means no convert decorations.
    """
    cvt_dict = {'0':'INVALID'}
    cvt_list = ['INVALID']
    n = 1
    for gi in agi.generator_list:
        for ii in gi.parser_output.instructions:
            for op in ii.operands:
                if op.cvt:
                    key = make_cvt_key(op.cvt)
                    try:
                        op.cvt_index = cvt_dict[key]
                    except:
                        cvt_dict[key] = n
                        cvt_list.append(key)
                        op.cvt_index = n
                        n = n + 1
                else:
                    op.cvt_index = 0
    if n >= 256:
        die("NOTIFY XED DEVELOPERS: NEED MORE BITS IN operand cvt_idx field")
    msgb("NUMBER OF CONVERT PATTERNS", str(n))
    agi.max_convert_patterns = n
    agi.max_decorations_per_operand = 3
    fn = 'xed-operand-convert-init.c' 
    f = agi.common.open_file(fn, start=False)
    f.add_misc_header("#include \"xed-operand-convert-enum.h\"")
    f.add_misc_header("#include \"xed-gen-table-defs.h\"")
    f.start()
    f.write("\nconst xed_operand_convert_enum_t ")
    f.write("xed_operand_convert[XED_MAX_CONVERT_PATTERNS][%s] = {\n" % 
            ('XED_MAX_DECORATIONS_PER_OPERAND'))

    
    for i,cvt_key in enumerate(cvt_list):
        cvals = make_cvt_values(cvt_key,agi.max_decorations_per_operand)
        s = ("{ XED_OPERAND_CONVERT_%s, " + 
             "XED_OPERAND_CONVERT_%s, " + 
             "XED_OPERAND_CONVERT_%s },  ") % tuple(cvals)
        f.write("/* %d */ %s\n" % (i,s))
    f.write("\n};\n")
    f.close()

                    
                    
############################################################################
# Generate the graph and most tables
############################################################################


def gen_everything_else(agi):
    """This is the major work function of the generator. We read the
    main input files and build the decoder graph and then the decoder"""

    msge("Reading state bits")
    if agi.common.options.input_state != '':
       #parse the xed-state-bits.txt (or something similar) file and return
       #a dictionary from a token_name to an object of 
       #{token_name, [token_expansion]}
       #for example for "no_refining_prefix     REFINING=0 OSZ=0" line we will
       #have an entry no_refining_prefix: 
       #{no_refning_prefix, [REFINING=0, OSZ=0]}
       agi.common.state_bits = read_state_spec(agi.common.options.input_state)
    else:
       die("Could not find state bits file in options")
    msge("Done reading state bits")

    #for each of the requirement statements (eg EOSZ=1), found in the state 
    #file, save for each token (eg EOSZ) all its possible values 
    #(eg [0,1,2,3]), return a dictionary from token to its possible values
    #eg EOSZ: [0,1,2,3]
    agi.common.state_space = compute_state_space(agi.common.state_bits)

    lines = []
    spine  = base_open_file(agi.common.options.spine,"r").readlines()
    lines.extend(spine)

    msge("Reading structured input")
    misc  = base_open_file(
                     agi.common.options.structured_input_fn,"r").readlines()
    lines.extend(misc)

    msge("Reading Instructions (ISA) input")
    isa_lines  = base_open_file(
                     agi.common.options.isa_input_file,"r").readlines()
    lines.extend(isa_lines)
    del isa_lines
    
    lines = process_continuations(lines)

    # Open structured output file
    if agi.common.options.structured_output_fn.startswith(os.path.sep):
       fn = agi.common.options.structured_output_fn
    else:
       fn = os.path.join(agi.common.options.gendir,
                         agi.common.options.structured_output_fn)
    print_structured_output  = False
    if print_structured_output:
       sout = open(fn,"w")
       print_resource_usage('everything.0')

    # read all the input
    while len(lines) != 0:
       msge("=============================================")
       msge("Creating a generator " + str(len(agi.generator_list)))
       msge("=============================================")
       print_resource_usage('everything.1')
       msge("ALines (lines before reading input) = " + str(len(lines)))
       lines = read_input(agi, lines)
       msge("BLines (lines remaining after reading input) = " + str(len(lines)))

    #after this we will have all deleted and udeleted instructions 
    #removed for all parsers, that have instructions.
    #Also all instructions with old versions will be dropped. 
    remove_instructions(agi)
    
    # first pass on the input, build the graph, collect information
    for gi in agi.generator_list:
       # if anything has flags, then add a flags register
       add_flags_register_operand_all(agi,gi.parser_output)
       
       if agi.common.state_bits == None:
          die("Bad agi state bits")
          
       if gi.common.state_bits == None:
          die("Bad state bits")

       rewrite_state_operands(agi, gi.common.state_bits, gi.parser_output)
       mark_operands_internal(agi, gi.parser_output)
       if print_structured_output:
          gi.parser_output.print_structured_output(sout)
       ###############################################
       # BUILD THE GRAPH BY RECURSIVE PARTITIONING
       ###############################################
       gi.graph = build_graph(agi.common, 
                              gi.parser_output, 
                              agi.operand_storage.get_operands())

       if not gi.parser_output.is_lookup_function():
          optimize_graph(agi.common.options, gi.graph)
       nt_name  = gi.graph.token
       #msge("GRAPHROOT: " + nt_name)
       agi.nonterminal_dict.add_graph_node(nt_name, gi.graph.id)

       # For epsilon nodes, where errors are allowed, we label all
       # nodes in the subgraph with "otherwise_ok".
       if gi.parser_output.otherwise_ok:
          epsilon_label_graph(agi.common.options, gi.graph)

       # do not collect operands from nonterminals that are lookup functions:
       if not gi.parser_output.is_lookup_function():
          #msge("Collecting graph enum info")
          collect_graph_enum_info(agi,gi.graph)
          d = {}
          d  =collect_tree_depth(gi.graph, d)
          #msge("DEPTHS: "+ str(d))
       if agi.common.options.print_graph:
          print_graph(agi.common.options,gi.graph)
          
    print_resource_usage('everything.2')
    if print_structured_output:
       sout.close()
       del sout
    
    print_resource_usage('everything.3')
    # Renumber the itable nodes so that they are sequential, skipping
    # over the lookup function itable entries.
    relabel_itable(agi)
    
    print_resource_usage('everything.3a')
    
    # some stuff needs to be created first so that the pass2 stuff can
    # refer to it.
    for generator in agi.generator_list:
       print_resource_usage('everything.4')
       rewrite_default_operand_visibilities(generator,
                                            agi.operand_storage.get_operands())

       compute_iforms(generator.common.options, 
                      generator,
                      agi.operand_storage.get_operands())

    collect_convert_decorations(agi)

    # We emit the iform enum here so that we can use the ordering for
    # initializing other structures.
    emit_iclass_enum_info(agi)
    emit_iclass_rep_ops(agi)
    
    collect_and_emit_iforms(agi,agi.common.options)
    collect_iclass_strings(agi)
    collect_instruction_types(agi, agi.iform_info)
    agi.isa_sets = collect_isa_sets(agi)
    
    # idata.txt file write
    write_instruction_data(agi, agi.iform_info)
    write_quick_iform_map(agi,agi.common.options.gendir,agi.iform_info)
    
    print_resource_usage('everything.4b')
    # mark bit positions in each "instruction"
    decorate_operands(agi.common.options,agi)
    print_resource_usage('everything.4c')

    decorate_instructions_with_exception_types(agi)

    agi.inst_fp = agi.open_file('xed-init-inst-table-data.c', start=False)
    agi.inst_fp.add_header('xed-inst-defs.h')
    agi.inst_fp.start()
    agi.inst_fp.write('const xed_inst_t ' +
                      'xed_inst_table[XED_MAX_INST_TABLE_NODES] = {\n')

    agi.open_operand_data_file()
    agi.open_operand_sequence_file()
    
    cg_args = code_gen_dec_args_t()

    agi.encode_init_function_objects.append(
              function_object_t('xed_encode_init', 'void'))
    print_resource_usage('everything.5')          

    find_common_operand_sequences(agi)

    for generator in agi.generator_list:
       print_resource_usage('everything.6')
       if generator.parser_output.is_lookup_function():
          pass
       else:
          cg_args.gi = generator
          cg_args.options = generator.common.options
          cg_args.node = generator.graph
          cg_args.nonterminal_dict = agi.nonterminal_dict
          cg_args.state_bits = agi.common.state_bits
          cg_args.itable_init_functions = agi.itable_init_functions

          cg_args.encode_init_function_object =  \
                    agi.encode_init_function_objects[0]
          cg_args.operand_storage_dict = agi.operand_storage.get_operands()

          # generate the itable
          code_gen_instruction_table(agi,
                                     cg_args.gi,
                                     cg_args.itable_init_functions,
                                     cg_args.nonterminal_dict,
                                     cg_args.operand_storage_dict)

          print_resource_usage('everything.7')        

    global max_operand_count
    msgb("MAX OPERAND COUNT {}".format(max_operand_count))

    code_gen_unique_operands(agi)
    code_gen_operand_sequences(agi)
    agi.close_operand_data_file()
    agi.close_operand_sequence_file()
    agi.inst_fp.write('};\n')
    agi.inst_fp.close()

    # finish emitting the last function for the itable and the decode graph
    agi.itable_init_functions.finish_fp()

    print_resource_usage('everything.10')
       
    # THIS NEXT FUNCTION IS THE BIGGEST TIME HOG
    init_functions_for_table(agi,
                             agi.common.inst_file,
                             'xed_init_inst_table',
                             agi.itable_init_functions)
    
    print_resource_usage('everything.12')          
    # some states are not assigned to in the graph and we must reserve
    # storage for them anyway. MODE is one example.
    agi.extend_operand_names_with_input_states()

    emit_enum_info(agi)
    agi.handle_prefab_enums()

    agi.add_file_name(agi.common.source_file_names)
    agi.add_file_name(agi.common.header_file_names, header=True)    

    write_attributes_table(agi,agi.common.options.gendir)

    # defines for emitted tables
    agi.code_gen_table_sizes()
    agi.close_flags_files()
    print_resource_usage('everything.16')          

    call_chipmodel(agi)
    call_ctables(agi) 
    emit_operand_storage(agi)

################################################
def emit_operand_storage(agi):
    agi.operand_storage.emit(agi)

def call_ctables(agi):
    """Conversion tables for operands"""
    lines = open(agi.common.options.ctables_input_fn,'r').readlines()
    srcs = ctables.work(lines,
                        xeddir=agi.common.options.xeddir,
                        gendir=agi.common.options.gendir)

def call_chipmodel(agi):
    args = chipmodel.args_t()
    args.input_file_name = agi.common.options.chip_models_input_fn
    args.xeddir = agi.common.options.xeddir
    args.gendir = agi.common.options.gendir
    args.add_orphans_to_future = agi.common.options.add_orphan_inst_to_future_chip

    args.isa_sets_from_instr = agi.isa_sets

    # isaset_ch is a list of the ISA_SETs mentioned in the chip hierarchy.
    # we need to check that all of those are used/mentioned by some chip.
    files_created,chips,isaset_ch = chipmodel.work(args)
    
    agi.all_enums['xed_chip_enum_t'] = chips
    agi.all_enums['xed_isa_set_enum_t'] = isaset_ch
    print("Created files: %s" % (" ".join(files_created)))
    for f in files_created:
        agi.add_file_name(f,is_header(f))

################################################
def read_cpuid_mappings(fn):
    return cpuid_rdr.read_file(fn)

def make_cpuid_mappings(agi,mappings):

    # 'mappings' is a dict of isa_set -> list of cpuid_bit_names 
    
    # collect all unique list of cpuid bit names
    cpuid_bits = {}
    for vlist in mappings.values():
        for bit in vlist:
            if bit == 'N/A':
                data = bitname = 'INVALID'
            else:
                try:
                    bitname,orgdata = bit.split('.',1)
                    data = re.sub('[.]','_',orgdata)
                except:
                    die("splitting problem with {}".format(bit))
                if bitname in cpuid_bits:
                    if cpuid_bits[bitname] != data:
                        die("Mismatch on cpuid bit specification for bit {}: {} vs {}".format(
                            bitname, cpuid_bits[bitname], data))
            cpuid_bits[bitname]=data

    
    cpuid_bit_string_names = sorted(cpuid_bits.keys())

    # move INVALID to 0th element:
    p = cpuid_bit_string_names.index('INVALID')
    del cpuid_bit_string_names[p]
    cpuid_bit_string_names = ['INVALID'] + cpuid_bit_string_names 

    # emit enum for cpuid bit names
    cpuid_bit_enum =  enum_txt_writer.enum_info_t(cpuid_bit_string_names,
                                                  agi.common.options.xeddir,
                                                  agi.common.options.gendir,
                                                  'xed-cpuid-bit',
                                                  'xed_cpuid_bit_enum_t',
                                                  'XED_CPUID_BIT_', 
                                                  cplusplus=False)
    cpuid_bit_enum.print_enum()
    cpuid_bit_enum.run_enumer()
    agi.add_file_name(cpuid_bit_enum.src_full_file_name)
    agi.add_file_name(cpuid_bit_enum.hdr_full_file_name,header=True)

    fp = agi.open_file('xed-cpuid-tables.c')

    fp.add_code('const xed_cpuid_rec_t xed_cpuid_info[] = {')
    # emit initialized structure mapping cpuid enum values to descriptive structures
    for bitname in cpuid_bit_string_names:
        cpuid_bit_data = cpuid_bits[bitname]
        if bitname == 'INVALID':
            leaf = subleaf = bit  = 0
            reg = 'INVALID'
        else:
            (leaf,subleaf,reg,bit) = cpuid_bit_data.split('_')
            
        s = "/* {:18s} */ {{ 0x{}, {}, {}, XED_REG_{} }},".format(
            bitname, leaf,subleaf, bit, reg)
        fp.add_code(s)
    fp.add_code('};')

    # check that each isa set in the cpuid files has a corresponding XED_ISA_SET_ value
    fail = False
    for cisa in mappings.keys():
        t = re.sub('XED_ISA_SET_','',cisa)
        if t not in agi.all_enums['xed_isa_set_enum_t']:
            fail = True
            genutil.warn("bad isa_set referenced cpuid file: {}".format(cisa))
    if fail:
        die("Found bad isa_sets in cpuid input files.")
                    

        
    
    # emit initialized structure of isa-set mapping to array of cpuid bit string enum.
    n = 4
    fp.add_code('const xed_cpuid_bit_enum_t xed_isa_set_to_cpuid_mapping[][XED_MAX_CPUID_BITS_PER_ISA_SET] = {')

    for isaset in agi.all_enums['xed_isa_set_enum_t']:
        print("ISASET: ", isaset)
        x = 'XED_ISA_SET_' + isaset
        raw = n*['XED_CPUID_BIT_INVALID']
        if x in mappings:
            for i,v in enumerate(mappings[x]):
                if v == 'N/A':
                    bit_symbolic_name = 'INVALID'
                else:
                    (bit_symbolic_name,leaf,subleaf,reg,bit) = v.split('.')

                if i >= n:
                    die("Make XED_MAX_CPUID_BITS_PER_ISA_SET bigger")
                raw[i] = 'XED_CPUID_BIT_' + bit_symbolic_name
        bits = ", ".join(raw)
        s = '/* {} */ {{ {}  }} ,'.format(isaset, bits)
        fp.add_code(s)
    fp.add_code('};')
    fp.close()

def gen_cpuid_map(agi):
    fn = agi.common.options.cpuid_input_fn
    if fn:
        if os.path.exists(fn):
            mappings = read_cpuid_mappings(fn)
            make_cpuid_mappings(agi, mappings)
            return
    die("Could not read cpuid input file: {}".format(str(fn)))
    
################################################

def emit_regs_enum(options, regs_list):
    
   #FIXME: sort the register names by their type. Collect all the
   #types-and-widths, sort them by their ordinals. Special handling
   #for the AH/BH/CH/DH registers is required.

   enumvals = refine_regs.rearrange_regs(regs_list)

   reg_enum =  enum_txt_writer.enum_info_t(enumvals,
                                           options.xeddir, options.gendir,
                                           'xed-reg', 'xed_reg_enum_t', 
                                           'XED_REG_', cplusplus=False)
   reg_enum.print_enum()
   reg_enum.run_enumer()
   return (reg_enum.src_full_file_name,reg_enum.hdr_full_file_name)

def emit_reg_class_enum(options, regs_list):
   rclasses = {}
   for ri in regs_list:
      if ri.type not in rclasses:
         rclasses[ri.type]=True

      #Add GPR8,16,32,64 as reg classes
      if ri.type == 'GPR':
         fine_rclass = 'GPR' + ri.width
         if fine_rclass  not in rclasses:
            rclasses[fine_rclass]=True

   del rclasses['INVALID']
   just_rclass_names = list(rclasses.keys())
   # FIXME: would really prefer alphanumeric sort (low priority)
   just_rclass_names.sort() 

   just_rclass_names[0:0] = ['INVALID'] # put INVALID at the start of the list
   reg_enum =  enum_txt_writer.enum_info_t(just_rclass_names,
                                           options.xeddir, 
                                           options.gendir,
                                           'xed-reg-class', 
                                           'xed_reg_class_enum_t',
                                           'XED_REG_CLASS_', 
                                           cplusplus=False)
   reg_enum.print_enum()
   reg_enum.run_enumer()
   return (reg_enum.src_full_file_name,reg_enum.hdr_full_file_name)

def emit_reg_class_mappings(options, regs_list):
   """Emit code to map any reg to its regclass. Also emit code to map
   GPRs to a more specific GPR regclass (GPR8,16,32,64)"""
   
   fo = function_object_t('xed_init_reg_mappings', 'void')
   for ri in regs_list:
      s = 'xed_reg_class_array[XED_REG_%s]= XED_REG_CLASS_%s' % (ri.name, 
                                                                 ri.type)
      fo.add_code_eol(s)

   for ri in regs_list:
      s = 'xed_largest_enclosing_register_array[XED_REG_%s]= XED_REG_%s' % (
          ri.name, ri.max_enclosing_reg)
      fo.add_code_eol(s)

      if ri.max_enclosing_reg_32:
          m32 = ri.max_enclosing_reg_32
      else:
          m32 = 'INVALID' # used for 64b GPRs

      s = 'xed_largest_enclosing_register_array_32[XED_REG_%s]= XED_REG_%s' % (
          ri.name, m32)
      fo.add_code_eol(s)
      
   for ri in regs_list:
      if ri.type == 'GPR':
         s = 'xed_gpr_reg_class_array[XED_REG_%s]= XED_REG_CLASS_%s%s' % (
             ri.name, ri.type, ri.width)
         fo.add_code_eol(s)


   for ri in regs_list:
      if 'NA' == ri.width:
         width   = '0'
         width64 = '0'
      elif '/' in ri.width:
         chunks = ri.width.split('/')
         width   = chunks[0]
         width64 = chunks[1]
      else:
         width   = ri.width
         width64 = ri.width
      
      s = 'xed_reg_width_bits[XED_REG_%s][0] = %s' % (ri.name, width)
      fo.add_code_eol(s)
      s = 'xed_reg_width_bits[XED_REG_%s][1] = %s' % (ri.name, width64)
      fo.add_code_eol(s)

   # write the file in our customized way
   fp = xed_file_emitter_t(options.xeddir,
                           options.gendir,
                           'xed-init-reg-class.c')
   fp.start()
   fp.write(fo.emit())
   fp.close()
   return fp.full_file_name


def gen_regs(options,agi):
   """Generate the register enumeration & reg class mapping functions"""

   lines = base_open_file(options.input_regs,"r","registers input").readlines()

   # remove comments and blank lines
   # regs_list is a list of reg_info_t's
   regs_list = refine_regs.refine_regs_input(lines)
   regs = [  x.name for x in  regs_list]
   agi.all_enums['xed_reg_enum_t'] = regs

   (cfn, hfn) = emit_regs_enum(options, regs_list)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)
   
   (cfn, hfn) = emit_reg_class_enum(options, regs_list)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)
   
   cfn_map = emit_reg_class_mappings(options, regs_list)
   agi.add_file_name(cfn_map)

   agi.regs_info = regs_list


############################################################################
# $$ width_info_t
class width_info_t(object):
   def __init__(self, name, dtype, widths):
      """ a name and a list of widths, 8, 16,32, and 64b"""
      self.name = name.upper()
      self.dtype = dtype
      self.widths = widths

def is_bits(val):
   """Return a number if the value is in explicit bits form:
   [0-9]+bits, or None"""
   length = len(val)
   if length > 4:
      if val[-4:] == "bits":
         number_string =  val[0:-4]
         if completely_numeric.match(number_string):
            return number_string
   return None
   
def refine_widths_input(lines):
   """Return  a list of width_info_t. Skip comments and blank lines"""
   global comment_pattern
   widths_list = []
   for line in lines:
      pline = comment_pattern.sub('',line).strip()
      if pline == '':
         continue
      wrds = pline.split()
      ntokens = len(wrds)
      if ntokens == 3:
         (name, dtype,  all_width) = wrds
         width8 =  all_width
         width16 = all_width
         width32 = all_width
         width64 = all_width
      elif ntokens == 5:
         width8='0'
         (name,  dtype, width16, width32, width64) = wrds
      else:
         die("Bad number of tokens on line: " + line)

      # convert from bytes to bits, unless in explicit bits form "b'[0-9]+"
      bit_widths = []
      for val in [width8, width16, width32, width64]:
         number_string = is_bits(val)
         if number_string:
            bit_widths.append(number_string)
         else:
            bit_widths.append(str(int(val)*8))
      widths_list.append(width_info_t(name, dtype, bit_widths))
   return widths_list

def emit_widths_enum(options, widths_list):
   just_width_names = [ x.name for x in  widths_list]
   width_enum =  enum_txt_writer.enum_info_t(just_width_names,
                                             options.xeddir, options.gendir,
                                             'xed-operand-width',
                                             'xed_operand_width_enum_t',
                                             'XED_OPERAND_WIDTH_', 
                                             cplusplus=False)
   width_enum.print_enum()
   width_enum.run_enumer()
   return (width_enum.src_full_file_name,width_enum.hdr_full_file_name)


def emit_width_lookup(options, widths_list):
   """Emit code to map XED_OPERAND_WIDTH_* and an effective operand size to a
   number of bytes. """

   fo = function_object_t('xed_init_width_mappings', 'void')
   for ri in widths_list:
      for i,w in enumerate(ri.widths):
         s = 'xed_width_bits[XED_OPERAND_WIDTH_%s][%d] = %s' % (ri.name, i, w)
         fo.add_code_eol(s)
         
         if 0: # DISABLED!!!
            if int(w) % 8  == 0:
               multiple = '1'
            else:
               multiple = '0'
            s = 'xed_width_is_bytes[XED_OPERAND_WIDTH_%s][%d] = %s' % (
                ri.name, i, multiple)
            fo.add_code_eol(s)

   # write the file in our customized way
   fp = xed_file_emitter_t(options.xeddir,
                           options.gendir,
                           'xed-init-width.c')
   fp.start()
   fp.write(fo.emit())
   fp.close()
   return fp.full_file_name


def gen_element_types_base(agi):
   """Read in the information about element base types"""
   fn = agi.common.options.input_element_type_base
   msge("MAKING ELEMENT BASE TYPE ENUM")
   all_values = agi.handle_prefab_enum(fn)
   agi.all_enums['xed_operand_element_type_enum_t'] = all_values

def gen_element_types(agi):
   """Read in the information about element types"""
   lines = base_open_file(agi.common.options.input_element_types,
                          "r","element types").readlines()
   agi.xtypes_dict = opnd_types.read_operand_types(lines)
   agi.xtypes = set(agi.xtypes_dict.keys())
   
   (cfn,hfn) = opnd_types.write_enum(agi,agi.xtypes_dict)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)
   cfn = opnd_types.write_table(agi,agi.xtypes_dict)
   agi.add_file_name(cfn)

def gen_extra_widths(agi):
    """Read the extra decorations for NTs and REGs that lack width
    information"""
    lines = base_open_file(agi.common.options.input_extra_widths,
                           "r", "extra widths input").readlines()
    agi.extra_widths_reg = {}
    agi.extra_widths_nt = {}
    agi.extra_widths_imm_const = {}
    for line in lines:
        pline = comment_pattern.sub('',line).strip()
        if pline == '':
            continue
        wrds = pline.split()
        ntokens = len(wrds)
        if ntokens != 3:
            die("Bad number of tokens on line: " + line)
        (nt_or_reg, name, oc2) = wrds
        if nt_or_reg == 'nt':
            agi.extra_widths_nt[name] = oc2
        elif nt_or_reg == 'reg':
            agi.extra_widths_reg[name] = oc2
        elif nt_or_reg == 'imm_const':
            agi.extra_widths_imm_const[name] = oc2
        else:
            die("Bad NT/REG on line: " + line)



def gen_widths(options,agi):
   """Generate the oc2 operand width enumeration & width lookup function"""

   lines = base_open_file(options.input_widths,"r","widths input").readlines()

   # remove comments and blank lines
   # widths_list is a list of width_info_t's
   widths_list = refine_widths_input(lines)

   (cfn, hfn) = emit_widths_enum(options, widths_list)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)
   
   cfn_map = emit_width_lookup(options, widths_list)
   agi.add_file_name(cfn_map)

   agi.widths_list = widths_list
   
   # sets the default data type for each width
   agi.widths_dict = {}
   for w in widths_list:
       agi.widths_dict[w.name] = w.dtype

   # compute the scalable widths
   agi.scalable_widths = set()
   for w in widths_list:
      (w8,w16,w32,w64) = w.widths
      if w16 != w32 or w16  != w64 or w32 != w64:
         msge("Adding scalable width:  " + w.name)
         agi.scalable_widths.add(w.name)
   

############################################################################
def emit_pointer_name_lookup(options, widths_list):
   """Emit code to map integers representing a number of bytes accessed to a 
   pointer name for disassembly."""

   max_width = 0
   for bbytes, name, suffix in widths_list:
      if int(bbytes) > max_width:
         max_width = int(bbytes)+1
   
   hfp = xed_file_emitter_t(options.xeddir,
                           options.gendir,
                           'xed-init-pointer-names.h')
   hfp.start()
   hfp.write("#define XED_MAX_POINTER_NAMES %d\n" % max_width)
   hfp.close()


   fo = function_object_t('xed_init_pointer_names', 'void')
   fo.add_code_eol("memset((void*)xed_pointer_name,0," +
                   "sizeof(const char*)*XED_MAX_POINTER_NAMES)")
   for bbytes, name, suffix in widths_list:
      # add a trailing space to the name for formatting.
      s = 'xed_pointer_name[%s] = \"%s \"' % (bbytes, name)
      fo.add_code_eol(s)

   fo.add_code_eol("memset((void*)xed_pointer_name_suffix,0,"+
                   "sizeof(const char*)*XED_MAX_POINTER_NAMES)")
   for bbytes, name, suffix in widths_list:
      # add a trailing space to the name for formatting.
      s = 'xed_pointer_name_suffix[%s] = \"%s \"' % (bbytes, suffix)
      fo.add_code_eol(s)

   # write the file in our customized way
   fp = xed_file_emitter_t(options.xeddir,
                           options.gendir,
                           'xed-init-pointer-names.c')
   fp.start()
   fp.write("#include \"xed-init-pointer-names.h\"\n")
   fp.write("#include <string.h>\n") # for memset
   fp.write("const char* xed_pointer_name[XED_MAX_POINTER_NAMES];\n")
   fp.write("const char* xed_pointer_name_suffix[XED_MAX_POINTER_NAMES];\n")
   fp.write(fo.emit())
   fp.close()
   return [fp.full_file_name, hfp.full_file_name]

def refine_pointer_names_input(lines):
   """Return  a list of width_info_t. Skip comments and blank lines"""
   global comment_pattern
   widths_list = []
   for line in lines:
      pline = comment_pattern.sub('',line).strip()
      if pline == '':
         continue
      wrds = pline.split()
      ntokens = len(wrds)
      if ntokens == 3:
         (bbytes, name, suffix) = wrds
      else:
         die("Bad number of tokens on line: " + line)
      widths_list.append((bbytes,name,suffix))
   return widths_list
   
def gen_pointer_names(options,agi):
   """Generate the pointer name lookup function"""
   lines = base_open_file(options.input_pointer_names,"r",
                          "pointer names input").readlines()
   widths_list = refine_pointer_names_input(lines)
   (cfn, hfn) = emit_pointer_name_lookup(options, widths_list)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)


def emit_exception_enum(agi):
    if 'INVALID' not in agi.exception_types:
        agi.exception_types.append('INVALID')
    agi.exception_types = uniqueify(agi.exception_types)
    agi.exception_types.sort(key=key_invalid_first)
    enum = enum_txt_writer.enum_info_t( agi.exception_types,
                                        agi.common.options.xeddir,
                                        agi.common.options.gendir,
                                        'xed-exception',
                                        'xed_exception_enum_t',
                                        'XED_EXCEPTION_', 
                                        cplusplus=False)
    enum.print_enum()
    enum.run_enumer()
    agi.add_file_name(enum.src_full_file_name)
    agi.add_file_name(enum.hdr_full_file_name,header=True)


def decorate_instructions_with_exception_types(agi):
    """Put a default exception on instructions that lack a specific
    exception."""
    agi.exception_types = []
    for generator in agi.generator_list:
        ii = generator.parser_output.instructions[0]
        if not field_check(ii,'iclass'):
            continue
        for ii in generator.parser_output.instructions:
            if field_check(ii,'exceptions') and ii.exceptions:
                # clean it up a  little
                ii.exceptions = re.sub('-','_',ii.exceptions)
                ii.exceptions = ii.exceptions.upper()
                agi.exception_types.append(ii.exceptions)
            else:
                ii.exceptions = 'INVALID' 
    # writes agi.exception_types list of exceptions 
    emit_exception_enum(agi)


    
############################################################################

def emit_ctypes_enum(options, ctypes_dict):
   ctypes_dict['INVALID']=True
   type_names = list(ctypes_dict.keys())
   type_names.sort(key=key_invalid_first)
   ctypes_enum =  enum_txt_writer.enum_info_t(type_names,
                                              options.xeddir, options.gendir,
                                              'xed-operand-ctype',
                                              'xed_operand_ctype_enum_t',
                                              'XED_OPERAND_CTYPE_', 
                                              cplusplus=False)
   ctypes_enum.print_enum()
   ctypes_enum.run_enumer()
   return (ctypes_enum.src_full_file_name,ctypes_enum.hdr_full_file_name)

def emit_ctypes_mapping(options, operand_ctype_map, operand_bits_map):
   """Map operand names to ctypes and bits. Return c and h filenames"""
   fn = 'xed-operand-ctype-map'
   cf = xed_file_emitter_t(options.xeddir, options.gendir, fn + '.c')
   hf = xed_file_emitter_t(options.xeddir, options.gendir, fn + '.h')
   cf.start()
   hf.start()
   cf.write("#include \"%s\"\n" % (hf.file_name))

   mfo = function_object_t('xed_operand_get_ctype', 'xed_operand_ctype_enum_t')
   mfo.add_arg("xed_operand_enum_t opname")
   mfo.add_code_eol(" xed_assert(opname <XED_OPERAND_LAST)")
   mfo.add_code_eol(" return xed_operand_ctype[opname]")

   lfo = function_object_t('xed_operand_decider_get_width', 'unsigned int')
   lfo.add_arg("xed_operand_enum_t opname")
   lfo.add_code_eol(" xed_assert(opname <XED_OPERAND_LAST)")
   lfo.add_code_eol(" return xed_operand_bits[opname]")

   ifo = function_object_t('xed_init_operand_ctypes', 'void')

   for o,c in operand_ctype_map.items():
      ifo.add_code_eol(
          "xed_operand_ctype[XED_OPERAND_%s]=XED_OPERAND_CTYPE_%s" % (
              o.upper(),c.upper()))

   for o,c in operand_bits_map.items():
      ifo.add_code_eol("xed_operand_bits[XED_OPERAND_%s]=%s" % (o.upper(), c))
      
   cf.write("static xed_operand_ctype_enum_t"+
            " xed_operand_ctype[XED_OPERAND_LAST];\n")
   cf.write("static unsigned int  xed_operand_bits[XED_OPERAND_LAST];\n")
   cf.write(ifo.emit())
   cf.write(mfo.emit())
   hf.write(mfo.emit_header())
   cf.write(lfo.emit())
   hf.write(lfo.emit_header())
   hf.close()
   cf.close()
   return (cf.full_file_name, hf.full_file_name)


def gen_operand_storage_fields(options,agi):
   """Read the register names and type specifiers. Build some classes, enum"""
   lines = base_open_file(options.input_fields,"r",
                          "operand fields input").readlines()
   
   compress_operands = agi.common.options.compress_operands
   agi.operand_storage = operand_storage.operands_storage_t(lines,
                                                            compress_operands)
   
   operand_fields = agi.operand_storage.get_operands()
   ctypes = {} #  ctypes -> True
   for of in list(operand_fields.values()):
      ctypes[of.ctype]=True


   operand_ctype_map = {}
   operand_bits_map = {}
   for of in operand_fields.values():
      operand_ctype_map[of.name] = of.ctype
      operand_bits_map[of.name] = of.bitwidth


   #msge("OPERAND STORAGE: %s" %(agi.operand_storage.operand_field.keys()))

   # make an enumeration of the ctypes used for passing operands around.
   (cfn, hfn) = emit_ctypes_enum(options, ctypes)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)
   
   (cfn, hfn) = emit_ctypes_mapping(options,
                                    operand_ctype_map, operand_bits_map)
   agi.add_file_name(cfn)
   agi.add_file_name(hfn,header=True)

   
    
############################################################################
# MAIN
############################################################################

def main():
   arg_parser = setup_arg_parser()
   (options, args ) = arg_parser.parse_args()
   
   if options.debug:
       activate_debugger() # genutil
       
   set_verbosity_options(options.verbosity)
   if options.xeddir == '':
      path_to_generator = sys.argv[0]
      (path_to_src, configure) = os.path.split(path_to_generator)
      options.xeddir = path_to_src
      msge("[ASSUMING PATH TO XED SRC] " + options.xeddir)

   agi = all_generator_info_t(options)

   if not os.path.exists(agi.common.options.gendir):
      die("Need a subdirectory called " + agi.common.options.gendir)

   agi.map_info = map_info_rdr.read_file(options.map_descriptions_input_fn)
   gen_operand_storage_fields(options,agi)
   
   gen_regs(options,agi)

   gen_widths(options,agi) # writes agi.widths_list and agi.widths_dict
   gen_extra_widths(agi) # writes agi.extra_widths_nt and agi.exta_widths_reg
   gen_element_types_base(agi) 
   gen_element_types(agi) # write agi.xtypes dict, agi.xtypes
   gen_pointer_names(options,agi)
   
   
   # this reads the pattern input, builds a graph, emits the decoder
   # graph and the itable, emits the extractor functions, computes the
   # iforms, writes map using iforms, computes capture
   # functions, gathers and emits enums. (That part should move out).
   gen_everything_else(agi)
   
   # emit functions to identify AVX and AVX512 instruction groups
   classifier.work(agi) 
   ild.work(agi)
   map_info_rdr.emit_enums(agi)
   
   gen_cpuid_map(agi)
   agi.close_output_files()
   agi.dump_generated_files()

################################################

if __name__ == '__main__':
   _profile = False
   if _profile:
      # profiling takes A REAL LONG TIME
      import profile
      profile.run('main()','profile.out')
   else:
      main()
      sys.exit(0)
#eof
