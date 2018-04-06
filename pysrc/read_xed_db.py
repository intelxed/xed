#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2018 Intel Corporation
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

import os
import sys
import re
import collections
import patterns
import slash_expand
import genutil
import opnd_types
import opnds

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stdout.write("[{0}] {1}\n".format(b,s))

class inst_t(object):
    def __init__(self):
        pass


class width_info_t(object):
   def __init__(self, name, dtype, widths):
      """ a name and a list of widths, 8, 16,32, and 64b"""
      self.name = name.upper()
      self.dtype = dtype
      self.widths = widths

completely_numeric = re.compile(r'^[0-9]+$') # only numbers

def _is_bits(val):
   """Return a number if the value is in explicit bits form:
   [0-9]+bits, or None"""
   global completely_numeric
   length = len(val)
   if length > 4:
      if val[-4:] == "bits":
         number_string =  val[0:-4]
         if completely_numeric.match(number_string):
            return number_string
   return None



    
class xed_reader_t(object):
    """This class is designed to be used on the partial build materials
    collected up in early part of the build and dumped in to the
    BUILDDIR/dgen directory. Once initialized, the recs attribute 
    is what you'll iterate over to access the instruction records.
    """
    def __init__(self,
                 state_bits_filename,
                 instructions_filename,
                 widths_filename,
                 element_types_filename):

        self.xtypes = self._gen_xtypes(element_types_filename) 
        self.widths_dict = self._gen_widths(widths_filename)
        
        self.state_bits = self._parse_state_bits(state_bits_filename)
        self.deleted_unames = {}
        self.deleted_instructions = {}
        self.recs = self._process_lines(instructions_filename)
        self._find_opcodes()
        self._fix_real_opcode()
        self._generate_explicit_operands()
        self._parse_operands()


    def _refine_widths_input(self,lines):
       """Return  a list of width_info_t. Skip comments and blank lines"""
       comment_pattern = re.compile(r'#.*$')
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
             number_string = _is_bits(val)
             if number_string:
                bit_widths.append(number_string)
             else:
                bit_widths.append(str(int(val)*8))
          widths_list.append(width_info_t(name, dtype, bit_widths))
       return widths_list
        
    def _gen_widths(self, fn):
        lines = open(fn,'r').readlines()
        widths_list = self._refine_widths_input(lines)

        # sets the default data type for each width
        widths_dict = {}
        for w in widths_list:
            widths_dict[w.name] = w.dtype
        return widths_dict

    def _gen_xtypes(self, fn):
        lines = open(fn,'r').readlines()
        xtypes_dict = opnd_types.read_operand_types(lines)
        return set(xtypes_dict.keys())
            
        
    def _compute_explicit_operands(self,v):
        # all operands
        v.operand_list = v.operands.split()
        # just the explicit ones
        expl_operand_list = []


        for opnd in v.operand_list:
            stg = None
            vis = None
            opname = None
            if re.search(r'^[^:]*=',opnd):
                pieces = opnd.split(':')
                for i,p in enumerate(pieces):
                    if i == 0:
                        if '=' in p:
                            stg,opname = p.split('=')
                    elif p in ['IMPL', 'SUPP',  'EXPL', 'ECOND']:
                        vis = p
            elif opnd.startswith('IMM0') or opnd.startswith('MEM0') or opnd.startswith('IMM1'):
                pieces = opnd.split(':')
                opname = pieces[0]
                for i,p in enumerate(pieces):
                    if i>0 and  p in ['IMPL', 'SUPP',  'EXPL', 'ECOND']:
                        vis = p
            if opname and vis not in ['IMPL', 'SUPP', 'ECOND']:
                expl_operand_list.append(re.sub(r'[()]*','',opname))
        return expl_operand_list
                        
    
    def _generate_explicit_operands(self):
        for v in self.recs:
            if not hasattr(v,'iform'):
                v.iform=''
            v.explicit_operands = self._compute_explicit_operands(v)
            
    def _parse_operands(self):
        '''set v.parsed_operands with list of operand_info_t objects (see opnds.py).'''
        for v in self.recs:
            v.parsed_operands = []
            for op_str in v.operand_list:
                #op is an operand_info_t  object
                op =  opnds.parse_one_operand(op_str,
                                              'DEFAULT',
                                              self.xtypes,
                                              self.widths_dict)
                v.parsed_operands.append(op)
                #print "OPERAND: {}".format(op)

            
    def _fix_real_opcode(self):
        for v in self.recs:
            if not hasattr(v,'real_opcode'):
                v.real_opcode='Y'

        
    def _find_opcodes(self):
        '''augment the records with information found by parsing the pattern'''

        map_pattern = re.compile(r'MAP=(?P<map>[0-6])')
        vex_prefix  = re.compile(r'VEX_PREFIX=(?P<prefix>[0-9])')
        rep_prefix  = re.compile(r'REP=(?P<prefix>[0-3])')
        osz_prefix  = re.compile(r'OSZ=(?P<prefix>[01])')
        no_prefix   = re.compile(r'REP=0 OSZ=0')
        rexw_prefix = re.compile(r'REXW=(?P<rexw>[01])')
        reg_required = re.compile(r'REG[[](?P<reg>[b01]+)]')
        mod_required = re.compile(r'MOD[[](?P<mod>[b01]+)]')
        mod_mem_required = re.compile(r'MOD!=3')
        rm_required  = re.compile(r'RM[[](?P<rm>[b01]+)]')
        mode_pattern = re.compile(r' MODE=(?P<mode>[012]+)')
        not64_pattern = re.compile(r' MODE!=2')

        for v in self.recs:

            if not hasattr(v,'isa_set'):
                v.isa_set = v.extension

            v.undocumented = False
            if hasattr(v,'comment'):
                if 'UNDOC' in v.comment:
                    v.undocumented = True

            pattern = v.pattern.split()
            p0 = pattern[0]
            v.map = 0
            v.space = 'legacy'
            if p0 in  ['0x0F']:
                if pattern[1] == '0x38':
                    v.map = 2
                    opcode = pattern[2]
                elif pattern[1] == '0x3A':
                    v.map = 3
                    opcode = pattern[2]
                else:
                    v.map = 1
                    opcode = pattern[1]
            elif p0 == 'VEXVALID=1':
                v.space = 'vex'
                opcode = pattern[1]
            elif p0 == 'VEXVALID=2':
                v.space = 'evex'
                opcode = pattern[1]
            elif p0 == 'VEXVALID=4': #KNC
                v.space = 'evex.u0'
                opcode = pattern[1]
            elif p0 == 'VEXVALID=3':
                v.space = 'xop'
                opcode = pattern[1]
            else:
                opcode = p0
            v.opcode = opcode
            v.partial_opcode = False

            mp = map_pattern.search(v.pattern)
            if mp:
                v.map = int(mp.group('map'))

            v.no_prefixes_allowed = False
            if no_prefix.search(v.pattern):
                v.no_prefixes_allowed = True

            v.osz_required = False
            osz = osz_prefix.search(v.pattern)
            if osz:
                if osz.group('prefix') == '1':
                    v.osz_required = True

            v.f2_required = False
            v.f3_required = False
            rep = rep_prefix.search(v.pattern)
            if rep:
                if rep.group('prefix') == '2':
                    v.f2_required = True
                elif rep.group('prefix') == '3':
                    v.f3_required = True

            if v.space in ['evex','vex', 'xop']: 
                vexp = vex_prefix.search(v.pattern)
                if vexp:
                    if vexp.group('prefix') == '0':
                        v.no_prefixes_allowed = True
                    elif vexp.group('prefix') == '1':
                        v.osz_required = True
                    elif vexp.group('prefix') == '2':
                        v.f2_required = True
                    elif vexp.group('prefix') == '3':
                        v.f3_required = True


            v.rexw_prefix = "unspecified"
            rexw = rexw_prefix.search(v.pattern)
            if rexw:
                v.rexw_prefix = rexw.group('rexw') # 0 or 1

            v.reg_required = 'unspecified'
            reg = reg_required.search(v.pattern)
            if reg:
                v.reg_required = genutil.make_numeric(reg.group('reg'))

            v.rm_required = 'unspecified'
            rm = rm_required.search(v.pattern)
            if rm:
                v.rm_required = genutil.make_numeric(rm.group('rm'))

            v.mod_required = 'unspecified'
            mod = mod_required.search(v.pattern)
            if mod:
                v.mod_required = genutil.make_numeric(mod.group('mod'))
            mod = mod_mem_required.search(v.pattern)
            if mod:
                v.mod_required = '00/01/10'

            # 16/32/64b mode restrictions
            v.mode_restriction = 'unspecified'
            if not64_pattern.search(v.pattern):
                v.mode_restriction = 'not64'
            else:
                mode = mode_pattern.search(v.pattern)
                if mode:
                    v.mode_restriction = int(mode.group('mode'))

            v.scalar = False
            if hasattr(v,'attributes'):
                v.attributes = v.attributes.upper()
                if 'SCALAR' in v.attributes:
                    v.scalar = True


            if opcode.startswith('0x'):
                nopcode = int(opcode,16)
            elif opcode.startswith('0b'):
                # partial opcode.. 5 bits, shifted 
                nopcode = genutil.make_numeric(opcode) << 3
                v.partial_opcode = True

            v.upper_nibble = int(nopcode/16)
            v.lower_nibble = nopcode & 0xF


    def _parse_state_bits(self,f):
        lines = open(f,'r').readlines()
        d = []
        state_input_pattern = re.compile(r'(?P<key>[^\s]+)\s+(?P<value>.*)')
        while len(lines) > 0:
            line = lines.pop(0)
            line = patterns.comment_pattern.sub("",line)
            line = patterns.leading_whitespace_pattern.sub("",line)
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)
            p = state_input_pattern.search(line)
            if p:
                s = r'\b' + p.group('key') + r'\b'
                pattern = re.compile(s) 
                d.append( (pattern, p.group('value')) )
            else:
                die("Bad state line: %s"  % line)
        return d

    def _expand_state_bits_one_line(self,line):
        new_line = line
        for k,v in self.state_bits:
            new_line = k.sub(v,new_line)
        return new_line
    def _process_lines(self,fn):
        r = self._process_input_lines(fn)

        r = self._expand_compound_values(r)
        return r

    def _expand_compound_value(self, in_rec):
        """ v is dictionary of lists. return a list of those with one element per list"""
        if len(in_rec['OPERANDS']) !=  len(in_rec['PATTERN']):
            die("Mismatched number of patterns and operands lines")
        x = len(in_rec['PATTERN']) 
        res = []
        for i in range(0,x):
            d = inst_t()
            for k,v in in_rec.items():
                if len(v) == 1:
                    setattr(d,k.lower(),v[0])
                else:
                    if i >= len(v):
                        die("k = {0} v = {1}".format(k,v))
                    setattr(d,k.lower(),v[i])
            res.append(d)
        
        return res
        
    def _delist(self,in_rec):
        """The valies in the record are lists. Remove the lists since they are
        all now singletons        """
        n  = inst_t()
        for k,v in in_rec.items():
            setattr(n,k.lower(),v[0])
        return n

    def _expand_compound_values(self,r):
        n  = []
        for v in r:
            if len(v['OPERANDS']) > 1 or len(v['PATTERN']) > 1:
                t = self._expand_compound_value(v)
                n.extend(t)
            else:
                n.append(self._delist(v))
        return n

    def _process_input_lines(self,fn):
        """We'll still have multiple pattern/operands/iform lines after reading this.
        Stores each record in a list of dictionaries. Each dictionary has key-value pairs
        and the value is always a list"""

        started = False
        recs = []
        nt_name = "Unknown"
        i = 0
        for line in file(fn):
            i = i + 1
            if i > 500:
                sys.stdout.write(".")
                sys.stdout.flush()
                i = 0
            line = patterns.comment_pattern.sub("",line)
            line=line.strip()
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)

            if patterns.udelete_pattern.search(line):
                m = patterns.udelete_full_pattern.search(line)
                unamed = m.group('uname')
                self.deleted_unames[unamed] = True
                continue

            if patterns.delete_iclass_pattern.search(line):
                m = pattersn.delete_iclass_full_pattern.search(line)
                iclass = m.group('iclass')
                self.deleted_instructions[iclass] = True
                continue

            line = self._expand_state_bits_one_line(line)

            p = patterns.nt_pattern.match(line)
            if p:
                nt_name =  p.group('ntname')
                continue


            if patterns.left_curly_pattern.match(line):
                if started:
                    die("Nested instructions")
                started = True
                d = collections.defaultdict(list)
                d['NTNAME'].append(nt_name)
                continue

            if patterns.right_curly_pattern.match(line):
                if not started:
                    die("Mis-nested instructions")
                started = False
                recs.append(d)
                continue

            if started:
                key, value  = line.split(":",1)
                key = key.strip()
                value = value.strip()
                if key == 'IFORM':
                    # fill in missing iforms with empty strings
                    x = len(d['PATTERN']) - 1
                    y = len(d['IFORM'])
                    # if we have more patterns than iforms, add some
                    # blank iforms
                    while y < x:
                        d['IFORM'].append('')
                        y = y + 1

                d[key].append(value)

            else:
                die("Unexpected: [{0}]".format(line))
        sys.stdout.write("\n")
        return recs

