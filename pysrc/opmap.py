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
import sys
import re

class opmap_field_t(object):
    """This describes one field that makes up a concatenated sequence of bits. It has a width and can be inverted"""
    def __init__(self, name, width, invert=False):
        self.name = name
        self.width = width
        self.invert = invert
        # Updated when used with other fields
        self.global_bit_offset = 0 # of the rightmost bit

class opmap_t(object):
    """This generates two strings: one for decoding and one for
    encoding. For decoding, I pack the bit fields in to one larger
    value that can be used for register indexing. For encoding, I take
    the larger value and scatter it to the various component fields"""
    
    def __init__(self, name):
        self.index_name = name
        self.fields = [] # of opmap_field_t's. MSB is on the left when created! Reversed when used.
        self.total_width = 0
        self.decode_output = ''
        self.encode_output = ''

    def add(self,o):
        self.fields.append(o)
    def activate(self):
        self.number_fields()
        self.emit_decoder_code()
        self.emit_encoder_code()
    def dump(self):
        print(self.index_name, " DECODER OUTPUT: ", self.decode_output)
        print(self.index_name, " ENCODER OUTPUT: ", self.encode_output)
        
    def number_fields(self):
        self.fields.reverse()
        total = 0
        for f in self.fields:
            f.global_bit_offset = total
            total = total + f.width
        self.total_width = total
        
    def emit_decoder_code(self):
        """Assemble the fields in to an index. The index will be used
        to compute a register of some type."""
        self.decode_preamble()
        for f in self.fields:
            self.decode_emit_one_field(f)
        self.decode_epilogue()
        
    def emit_encoder_code(self):
        """convert a given index in to settings of the various
        constituent fields for subsequent encoding."""
        self.encode_preamble()
        for f in self.fields:
            self.encode_emit_one_field(f)
        self.encode_epilogue()

    

    def decode_preamble(self):
        self.decode_output = "xed_uint32_t c="
        self.decode_first_term = True
    def decode_emit_one_field(self,f):
        d = {}
        d['shift'] = str(f.global_bit_offset)
        d['name'] = f.name
        if f.invert:
            c = '%(conditional_or)s (((~ov[XED_OPERAND_%(name)s]) & %(mask)s) << %(shift)s)'
            d['mask'] = str((1<<f.width)-1)
        else:
            c = '%(conditional_or)s (ov[XED_OPERAND_%(name)s] << %(shift)s)'

        if self.decode_first_term:
            self.decode_first_term = False
            d['conditional_or'] = ''
        else:
            d['conditional_or'] = '|'

        self.decode_output +=  (c%d)
        
    def decode_epilogue(self):
        self.decode_output += ";"


    def encode_preamble(self):
        pass
    def encode_emit_one_field(self,f):
        """Extract field from the named index"""
        d = {}
        if f.invert:
            c = 'ov[XED_OPERAND_%(field_name)s]  = ((~ov[XED_OPERAND_%(index_name)s]) >> %(shift)s) & %(mask)s;\n'
        else:
            c = 'ov[XED_OPERAND_%(field_name)s]  = (ov[XED_OPERAND_%(index_name)s] >> %(shift)s) & %(mask)s;\n'
        d['index_name'] = self.index_name
        d['field_name'] = f.name
        d['shift'] = str(f.global_bit_offset)
        d['mask'] =  str((1<<f.width)-1)
        self.encode_output += (c%d)
    def encode_epilogue(self):
        pass


def die(s):
    sys.stderr.write(s+"\n")
    sys.exit(1)
    
class parse_opmap_t(object):
    """Read a list of lines and generate a a dictionary containing
    opmap_t's indexed by group name. To operate, this object needs a
    dictionary mapping field names to widths"""
    
    opmap_pattern = re.compile(r'(?P<grp>[A-Za-z0-9_]+)[(](?P<indx>[A-Za-z0-9_]+)[)]')
    
    def __init__(self, field_to_bits):
        """Fields to bits is a dictionary that maps field names to bit
        widths as is required to manufacture opmpa_field_t objects"""
        
        self.groups = {}
        self.field_to_bits = field_to_bits

        
    def read_line(self,line):
        a = line.split()
        if len(a) <= 1:
            die("Not enough fields on line " + line)
        m=parse_opmap_t.opmap_pattern.match(a[0])
        if not m:
            die("Could not parse " + line)
        (group,index) = m.group("grp","indx")
        fields = a[1:]
        opmap = opmap_t(index)

        for f in fields:
            if ":" in f:
                (name,suffix) = f.split(':')
            else:
                name = f
                suffix = None

            invert = False
            if suffix:
                if suffix == 'invert':
                    invert=True
                else:
                    die("Unknown suffix: " + suffix)
                
            try:
                width = self.field_to_bits[name]
            except:
                die("Could not find width for field [" + name + "]")
            ofield = opmap_field_t(name, width, invert=invert)
            opmap.add(ofield)
        opmap.activate()
        if group in self.groups:
            die("Overwrite attempt for group: " + group)
        self.groups[group] = opmap
            
    def read_lines(self,lines):
        for line in lines:
            line = re.sub(r'#.*','',line)
            line = line.strip()
            if line:
                self.read_line(line)
                
    def dump(self):
        for g,v in self.groups.items():
            print(g, ":  ")
            v.dump()
            print("\n\n")

if __name__ == "__main__":
    o = opmap_t('regidx1')
    o.add(opmap_field_t('bb',1)) # leftmost field first!
    o.add(opmap_field_t('b',1))
    o.add(opmap_field_t('a',3))
    o.activate()
    o.dump()
    
    o = opmap_t('regidx2')
    o.add(opmap_field_t('bb',1)) # leftmost field first!
    o.add(opmap_field_t('b',1, invert=True))
    o.add(opmap_field_t('a',3))
    o.activate()
    o.dump()

    d = { 'a':3, 'b':1, 'bb':1}
    p = parse_opmap_t(d)
    lines = [ 'FOO(indx1)  a b bb',
              'BAR(indx2)  bb b a',
              'ZIP(indx3)   b bb:invert a' ]
    p.read_lines(lines)
    p.dump()
