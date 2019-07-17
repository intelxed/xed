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
import enum_txt_writer
import codegen

class operand_type_t(object):
   def __init__(self,
                name,
                dtype,
                bits_per_element):
       self.name = name
       self.dtype = dtype
       self.bits_per_element = bits_per_element


def read_operand_types(lines):
    """ Return a dictionary of operand_type_t"""
    ots = {}
    for line in lines:
        line = re.sub(r'#.*','',line)
        line = line.strip()
        if line: 
            (xtype, dtype, bits_per_element) = line.split()
            ots[xtype] = operand_type_t(xtype,dtype,bits_per_element)

    return ots

def write_table(agi,ots):
   """Emit the xtypes enum and write the initialization table"""
   
   fp = codegen.xed_file_emitter_t(agi.common.options.xeddir,
                                   agi.common.options.gendir,
                                   'xed-init-operand-type-mappings.c')
   fp.start()
   fp.add_code("const xed_operand_type_info_t xed_operand_xtype_info[] = {")
   names = list(ots.keys())
   names.sort()
   names = ['INVALID'] + names
   ots['INVALID'] = operand_type_t('INVALID','INVALID','0')
   for n in names:
      v = ots[n]
      s = '/* %s */ { XED_OPERAND_ELEMENT_TYPE_%s, %s },' % (n, v.dtype, v.bits_per_element)
      fp.add_code(s)
   fp.add_code_eol("}")
   fp.close()
   return fp.full_file_name

def write_enum(agi,ots):
   """Emit the xtypes enum"""
   names = list(ots.keys())
   names.sort()
   names = ['INVALID'] + names
   width_enum =  enum_txt_writer.enum_info_t(names,
                                             agi.common.options.xeddir,
                                             agi.common.options.gendir,
                                             'xed-operand-element-xtype',
                                             'xed_operand_element_xtype_enum_t',
                                             'XED_OPERAND_XTYPE_', cplusplus=False)
   width_enum.print_enum()
   width_enum.run_enumer()
   
   return (width_enum.src_full_file_name,width_enum.hdr_full_file_name)
