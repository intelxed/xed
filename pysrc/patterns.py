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

macro_def_pattern = \
          re.compile(r'^MACRO_DEF[ \t]*[:][ \t]*(?P<name>[_A-Za-z0-9]+)[ \t]*$')
macro_use_pattern = \
          re.compile(r'^MACRO_USE[ \t]*[:][ \t]*(?P<name>[_A-Za-z0-9]+)[(](?P<args>[^)]+)[)][ \t]*$')


xed_reg_pattern = re.compile(r'(?P<regname>XED_REG_[A-Za-z0-9_]+)')

nt_name_pattern  =  re.compile(r'^(?P<ntname>[A-Za-z_0-9]+)[(][)]')
ntluf_name_pattern  =  re.compile(r'^(?P<ntname>[A-Za-z_0-9]+)[(]OUTREG[)]')
nt_pattern       =  re.compile(r'^(?P<ntname>[A-Za-z_0-9]+)[(][)]::')
ntluf_pattern  =  re.compile(r'^(?P<rettype>[A-Za-z0-9_]+)\s+(?P<ntname>[A-Za-z_0-9]+)[(][)]::')

# for the decode rule, the rhs might be empty
decode_rule_pattern = re.compile(r'(?P<action>.+)[|](?P<cond>.*)')

comment_pattern = re.compile(r'#.*$')
leading_whitespace_pattern = re.compile(r'^\s+')
full_line_comment_pattern = re.compile(r'^\s*#')
arrow_pattern = re.compile(r'(?P<cond>.+)->(?P<action>.+)')
curly_pattern = re.compile(r'(?P<curly>[{}])')
left_curly_pattern = re.compile(r'^[{]$') # whole line
right_curly_pattern = re.compile(r'^[}]$') # whole line

delete_iclass_pattern = re.compile('^DELETE')
delete_iclass_full_pattern = \
    re.compile(r'^DELETE[ ]*[:][ ]*(?P<iclass>[A-Za-z_0-9]+)')

udelete_pattern = re.compile('^UDELETE')
udelete_full_pattern = \
    re.compile(r'^UDELETE[ ]*[:][ ]*(?P<uname>[A-Za-z_0-9]+)')

iclass_pattern = re.compile(r'^ICLASS\s*[:]\s*(?P<iclass>[A-Za-z0-9_]+)')
uname_pattern = re.compile(r'^UNAME\s*[:]\s*(?P<uname>[A-Za-z0-9_]+)')
ipattern_pattern = re.compile(r'^PATTERN\s*[:]\s*(?P<ipattern>.+)')
operand_pattern = re.compile(r'^OPERANDS\s*[:]\s*(?P<operands>.+)')
no_operand_pattern = re.compile(r'^OPERANDS\s*[:]\s*$')
real_opcode_pattern = re.compile(r'^REAL_OPCODE\s*[:]\s*(?P<yesno>[A-Za-z0-9_]+)')
extension_pattern = re.compile(r'^EXTENSION\s*[:]\s*(?P<ext>[A-Za-z0-9_]+)')
isa_set_pattern = re.compile(r'^ISA_SET\s*[:]\s*(?P<isaset>[A-Za-z0-9_]+)')


equals_pattern = re.compile(r'(?P<lhs>[^!]+)=(?P<rhs>.+)')
return_pattern = re.compile(r'return[ ]+(?P<retval>[^ ]+)')
not_equals_pattern = re.compile(r'(?P<lhs>[^!]+)!=(?P<rhs>.+)')
bit_expand_pattern = re.compile(r'(?P<bitname>[a-z])/(?P<count>\d{1,2})')
rhs_pattern = re.compile(r'[!]?=.*$')
lhs_capture_pattern = re.compile(r'(?P<name>[A-Za-z_0-9]+)[\[](?P<bits>[a-z]+)]')
lhs_capture_pattern_end = re.compile(r'(?P<name>[A-Za-z_0-9]+)[\[](?P<bits>[a-z01_]+)]$')
lhs_pattern = re.compile(r'(?P<name>[A-Za-z_0-9]+)[!=]')
hex_pattern = re.compile(r'0[xX][0-9a-fA-F]+')
decimal_pattern = re.compile(r'^[0-9]+$')
binary_pattern = re.compile(r"^0b(?P<bits>[01_]+$)") # only 1's and 0's
old_binary_pattern = re.compile(r"B['](?P<bits>[01_]+)") #  Explicit leading "B'" 
bits_pattern = re.compile(r'^[10]+$')
bits_and_underscores_pattern = re.compile(r'^[10_]+$')
bits_and_letters_pattern = re.compile(r'^[10a-z]+$')
bits_and_letters_underscore_pattern = re.compile(r'^[10a-z_]+$')
sequence_pattern = re.compile(r'^SEQUENCE[ \t]+(?P<seqname>[A-Za-z_0-9]+)')
encoding_template_pattern = re.compile(r'[a-z01]+')
letter_pattern = re.compile(r'^[a-z]+$')
letter_and_underscore_pattern = re.compile(r'^[a-z_]+$')
simple_number_pattern = re.compile(r'^[0-9]+$')
