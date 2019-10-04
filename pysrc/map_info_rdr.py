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
import genutil

def _die(s):
    genutil.die(s)
def _msgb(b,s=''):
    genutil.msgb(b,s)

class map_info_t(object):
    def __init__(self):
        self.map_name = None
        self.space = None  # legacy, vex, evex, xop
        self.legacy_escape = None # N/A or 0f
        self.legacy_opcode = None # N/A or 38, 3a
        self.map_id = None  # 1,2,3,... 8,9,0xA
        # "var" means variable, requires a table generated based on defined instructions
        self.modrm = None  # var,yes,no, has modrm
        self.imm8 = None   # var,yes,no, has imm8
        self.imm32 = None  # var,yes,no, has imm32
        
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
        return " ".join(s)


def _parse_map_line(s):
    t = s.strip().split()
    if len(t) != 8:
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
            
        if mi.map_id != 'N/A':
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
    return mi


def read_file(fn):
    lines = open(fn,'r').readlines()
    lines = map(genutil.no_comments, lines)
    lines = list(filter(genutil.blank_line, lines))
    maps = [] # list of map_info_t
    for line in lines:
        maps.append( _parse_map_line(line) )
    maps.sort(key=lambda x: (x.space,x.map_name))
    for m in maps:
        _msgb("MAPINFO",m)
    return maps
