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

import sys
import re
import shlex

import genutil

def _die(s):
    genutil.die(s)
def _msgb(b,s=''):
    genutil.msgerr("[{}] {}".format(b,s))

class map_info_t(object):
    def __init__(self):
        self.map_name = None
        self.space = None  # legacy, vex, evex, xop
        self.legacy_escape = None # N/A or 0f
        self.legacy_opcode = None # N/A or 38, 3a
        self.map_id = None  # N/A or 0,1,2,3,... 8,9,0xA
        # "var" means variable, requires a table generated based on defined instructions
        self.modrm = None  # var,yes,no, has modrm
        self.imm8 = None   # var,yes,no, has imm8
        self.imm32 = None  # var,yes,no, has imm32
        self.opcpos = None  # 0,1,2, ... -1 (last) opcode position in pattern
        self.priority = 10
        # search_pattern is the string that we use to identify this
        # map in the XED decode patterns. The pattern may have spaces
        # in it. (and motivates using shlex to parse the input lines)
        self.search_pattern = None
        
    def is_legacy(self):
        return self.space == 'legacy'
    def is_vex(self):
        return self.space == 'vex'
    def is_evex(self):
        return self.space == 'evex'
    def is_xop(self):
        return self.space == 'xop'


    def map_short_name(self):
        if self.map_name  == 'amd-3dnow':
            return 'AMD'
        h = hex(self.map_id)[-1]
        return str(h)
    def ild_enum(self):
        s = self.map_short_name()
        if self.space == 'XOP':
            s = '_XOP{}'.format(s)
        return 'XED_ILD_MAP{}'.format(s)

    def get_legacy_escapes(self):
        if self.legacy_opcode == 'N/A':
            return (self.legacy_escape, None)
        return (self.legacy_escape, self.legacy_opcode)
        
    def has_variable_modrm(self):
        return self.modrm == 'var'
    def has_regular_modrm(self):
        return self.modrm == 'yes'
    
    def has_variable_imm8(self):
        return self.imm8 == 'var'
    def has_regular_imm8(self):
        return self.imm8 == 'yes'
    
    def has_variable_imm32(self):
        return self.imm32 == 'var'
    def has_regular_imm32(self):
        return self.imm32 == 'yes'
    
    def __str__(self):
        s = []
        s.append("name: {}".format(self.map_name))
        s.append("space: {}".format(self.space))
        s.append("legacyesc: {}".format(self.legacy_escape))
        s.append("legacyopc: {}".format(self.legacy_opcode))
        s.append("mapid: {}".format(self.map_id))
        s.append("modrm: {}".format(self.modrm))
        s.append("imm8: {}".format(self.imm8))
        s.append("imm32: {}".format(self.imm32))
        s.append("opcpos: {}".format(self.opcpos))
        s.append("priority: {}".format(self.priority))
        s.append("search_pattern: {}".format(self.search_pattern))        
        return " ".join(s)


def _parse_map_line(s):
    # shlex allows for quoted substrings containing spaces as
    # individual args.
    t = shlex.split(s.strip())
    if len(t) != 10:
        _die("Bad map description line: [{}]".format(s))
    mi = map_info_t()
    mi.map_name = t[0]
    mi.space = t[1]
    mi.legacy_escape = t[2]
    mi.legacy_opcode = t[3]
    mi.map_id = t[4]
    mi.modrm = t[5]
    mi.imm8 = t[6]
    mi.imm32 = t[7]
    mi.opcpos = t[8]
    mi.search_pattern = t[9]

    if mi.space not in ['legacy','vex','evex', 'xop']:
        _die("Bad map description encoding space [{}]".format(s))
    if mi.space == 'legacy':
        if genutil.is_hex(mi.legacy_escape):
            pass
        elif mi.legacy_escape != 'N/A':
            _die("Bad map description legacy escape [{}]".format(s))
        if  genutil.is_hex(mi.legacy_opcode):
            pass
        elif mi.legacy_opcode != 'N/A':
            _die("Bad map description legacy opcode [{}]".format(s))
            
        if mi.map_id == 'N/A':
            _die("Bad map description map-id [{}]".format(s))
    else:
        if mi.legacy_escape != 'N/A':
            _die("Bad map description legacy escape [{}]".format(s))
        if mi.legacy_opcode != 'N/A':
            _die("Bad map description legacy opcode [{}]".format(s))
        if genutil.numeric(mi.map_id):
            mi.map_id = genutil.make_numeric(mi.map_id)
        else:
            _die("Bad map description map id [{}]".format(s))

    if mi.modrm not in ['var','yes','no']:
        _die("Bad map description modrm specifier [{}]".format(s))
    if mi.imm8 not in ['var','yes','no']:
        _die("Bad map description imm8 specifier [{}]".format(s))
    if mi.imm32 not in ['var','yes','no']:
        _die("Bad map description imm32 specifier [{}]".format(s))
    if genutil.numeric(mi.opcpos):
        mi.opcpos = genutil.make_numeric(mi.opcpos)
    else:
        _die("Bad map description opcode position specifier [{}]".format(s))

    # we want the longer patterns first when we sort the map_info_t.
    mi.priority = 100-len(mi.search_pattern)
    return mi
    
def read_file(fn):
    lines = open(fn,'r').readlines()
    lines = map(genutil.no_comments, lines)
    lines = list(filter(genutil.blank_line, lines))
    maps = [] # list of map_info_t
    for line in lines:
        maps.append( _parse_map_line(line) )
    maps.sort(key=lambda x: x.priority)
    for m in maps:
        _msgb("MAPINFO",m)
    return maps

if __name__ == "__main__":
    read_file(sys.argv[1])
    sys.exit(0)

