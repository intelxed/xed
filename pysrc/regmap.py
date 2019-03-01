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
import re
import sys

def die(s):
    sys.stderr.write(s+"\n")
    sys.exit(1)

class regmap_t(object):
    """This converts register indices to register enumerations. And
    vice versa.  This replaces some clunkier register lookup machinery
    in XED2."""
    
    def __init__(self, dst, ntname,base,index):
        self.name = dst
        self.ntname = ntname
        self.base_reg = base
        self.index = index
        self.decode_output = ''
        self.encode_output = ''

    def activate(self):
        self.emit_decoder_code()
        self.emit_encoder_code()
    def dump(self):
        print(" DECODER OUTPUT: ", self.decode_output)
        print(" ENCODER OUTPUT: ", self.encode_output)
        
    def emit_decoder_code(self):
        self.decode_preamble()
        self.decode_emit()
        self.decode_epilogue()
        
    def emit_encoder_code(self):
        self.encode_preamble()
        self.encode_emit()
        self.encode_epilogue()

    

    def decode_preamble(self):
        pass
    def decode_emit(self):
        d = {}
        d['base_reg'] = self.base_reg
        d['index'] = self.index
        d['name'] = self.name # bypass OUTREG!
        c = 'ov[XED_OPERAND_%(name)s]=  %(base_reg)s + %(index)s'
        self.decode_output +=  (c%d)
        
    def decode_epilogue(self):
        self.decode_output += ";"

    def encode_preamble(self):
        pass
    def encode_emit(self):
        d = {}
        d['operand_name'] = self.name
        d['base_reg'] = self.base_reg
        d['index_name'] = self.index
        c =  "ov[XED_OPERAND_%(index_name)s]=  ov[XED_OPERAND_%(operand_name)s] -  %(base_reg)s;"
        self.encode_output += (c%d)
    def encode_epilogue(self):
        pass

class parse_regmap_t(object):
    def __init__(self):
        self.regmaps = {}

        
    def read_line(self,line):
        """ Lines have the following very simple format
        XMM_1  XMM0 REGINDEX1
        """
        a = line.split()
        if len(a) != 3:
            die("Wrong number of fields on line: " + line)
        try:
            (ntname, base, index) = a
        except:
            die("Could not parse " + line)
        regmap = regmap_t('OUTREG', ntname, 'XED_REG_'+base, index)
        regmap.activate()
        if ntname in self.regmaps:
            die("Attempting to duplication regmap " + ntname)
        self.regmaps[ntname] = regmap
            
    def read_lines(self,lines):
        for line in lines:
            line = re.sub(r'#.*','',line)
            line = line.strip()
            if line:
                self.read_line(line)
                
    def dump(self):
        for g,v in self.regmaps.items():
            print(g, ":  ")
            v.dump()
            print("\n\n")

if __name__ == "__main__":
    o = regmap_t('OUTREG', 'XMM_1','XED_REG_XMM0','REGIDX1')
    o.activate()
    o.dump()

    p = parse_regmap_t()
    lines = ['XMM_1 XMM0 REGIDX1',
             'XMM_2 XMM0 REGIDX2',
             'YMM_1 YMM0 REGIDX1',
             'YMM_2 YMM0 REGIDX2' ]
    p.read_lines(lines)
    p.dump()

