#!/usr/bin/env python
# -*- python -*-
########################################################
# THIS IS NOT DONE YET... IGNORE FOR NOW
########################################################
# Mark Charney
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

# This is a front-end for the enumer program. It writes the config
# file used by the enumer. It currently generates operands, or
# iclasses enumerations, but could be generalized to do anything.

# input:
#   list of string s (iclasses, operands, field tokns) from the graph builder

# output:
#   file for use with the enumer

import os
import sys


############################################################################
# Messages
def msge(s):
   sys.stderr.write(s  + '\n')
def msg(s):
   sys.stdout.write(s  + '\n')
def msgn(s):
   sys.stdout.write(s)

def cond_die(v, cmd, msg):
   if v != 0:
      s = msg + '\n  [CMD] ' + cmd
      die(s)

def die(m):
   msge('[ERROR] ' + m)
   sys.exit(1)
def warn(m):
   msg('[WARNING] ' + m)

############################################################################

# Require python 2.4 (or later) for this script
def check_python_version():
   tup = sys.version_info
   major = tup[0]
   minor = tup[1]
   if (major > 2 ) or \
      (major == 2 and minor >= 4):
       return 
   die('Need Python version 2.4 or later.')
   
check_python_version()

from optparse import OptionParser # requires python 2.3

parser = OptionParser()

# Most useful switches

parser.add_option('--iclasses',
                  action='store_true', dest='iclasses', default=False,
                  help='Enum for iclasses')
parser.add_option('--operands',
                  action='store_true', dest='operands', default=False,
                  help='Enum for operands')
parser.add_option('--operand-types',
                  action='store_true', dest='operand_types', default=False,
                  help='Enum for operands')
parser.add_option('--extensions',
                  action='store_true', dest='extensions', default=False,
                  help='Enum for extensions')
parser.add_option('--categories',
                  action='store_true', dest='categories', default=False,
                  help='Enum for categories')
parser.add_option('--input',
                  action='store', dest='input', default='',
                  help='Input file')
parser.add_option('--output',
                  action='store', dest='output', default='',
                  help='Output file')
parser.add_option('--gendir',
                  action='store', dest='gendir', default='gen',
                  help='Output directory')
parser.add_option('--verbosity', '-v',
                  action='store', dest='verbosity', default=0,
                  help='Level of verbosity')

############################################################################

def print_enum_header(f, type, prefix,cfn,hfn):
   f.write('namespace ' + 'XED' + '\n')  
   f.write('cfn ' + cfn + '\n')
   f.write('hfn ' + hfn + '\n')
   f.write('typename ' + type + '\n')
   f.write('prefix ' + prefix + '\n')
   f.write('stream_ifdef ' + 'XED_PRINT' + '\n')

def print_lines(lines, f):
   'print the lines, in upper case'
   for line in lines:
      f.write(line.upper())
   
def print_enum(lines,gendir, base_name, type_name, prefix,output):
   #f = open(os.path.join(gendir,base_name +'-enum.txt'),'w')
   f = open(output,'w')
   base_fn = base_name + '-enum'
   cfn = os.path.join(gendir,base_fn + '.cpp')
   hfn = os.path.join(gendir,base_fn + '.H')
   print_enum_header(f, type_name, prefix, cfn, hfn)
   print_lines(lines,f)


def print_iclass_enum(lines,gendir, output):
   print_enum(lines,gendir, 'xed-iclass', 'xed_iclass_enum_t', 'XED_ICLASS_',output)
def print_operand_enum(lines,gendir, output):
   print_enum(lines,gendir, 'xed-operand', 'xed_operand_enum_t', 'XED_OPERAND_',output)
def print_operand_type_enum(lines,gendir, output):
   print_enum(lines,gendir, 'xed-operand-type', 'xed_operand_type_enum_t', 'XED_OPERAND_TYPE_',output)
def print_category_enum(lines,gendir, output):
   print_enum(lines,gendir, 'xed-category', 'xed_category_enum_t', 'XED_CATEGORY_',output)
def print_extension_enum(lines,gendir, output):
   print_enum(lines,gendir, 'xed-extension', 'xed_extension_enum_t', 'XED_EXTENSION_',output)

if __name__ == '__main__':
   (options, args ) = parser.parse_args()
   if options.input == '':
      die('Need --input filename argument')
   if options.output == '':
      die('Need --output filename argument')

   lines = open(options.input,'r').readlines()
   if options.operands:
      print_operand_enum(lines,options.gendir, options.output)
   elif options.iclasses:
      print_iclass_enum(lines,options.gendir, options.output)
   elif options.operand_types:
      print_operand_type_enum(lines,options.gendir, options.output)
   elif options.categories:
      print_category_enum(lines,options.gendir, options.output)
   elif options.extensions:
      print_extension_enum(lines,options.gendir, options.output)
   else:
      die("Unrecognized option")

############################################################################
