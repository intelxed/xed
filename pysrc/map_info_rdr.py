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
import collections

import genutil
import enumer
import enum_txt_writer

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
        self.disp = None  # var,yes,no, has disp
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
        if self.map_name  == 'amd_3dnow':
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
    
    def has_variable_disp(self):
        return self.disp == 'var'
    
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
        s.append("disp: {}".format(self.disp))
        s.append("imm8: {}".format(self.imm8))
        s.append("imm32: {}".format(self.imm32))
        s.append("opcpos: {}".format(self.opcpos))
        s.append("priority: {}".format(self.priority))
        s.append("search_pattern: {}".format(self.search_pattern))        
        return " ".join(s)

_map_info_fields = ['map_name',
                    'space',
                    'legacy_escape',
                    'legacy_opcode',
                    
                    'map_id',
                    'modrm',
                    'disp',
                    'imm8',
                    
                    'imm32',
                    'opcpos',
                    'search_pattern' ]

def _parse_map_line(s):
    global _map_info_fields
    # shlex allows for quoted substrings containing spaces as
    # individual args.
    t = shlex.split(s.strip())
    if len(t) != len(_map_info_fields):
        _die("Bad map description line: [{}]".format(s))
    mi = map_info_t()
    for i,fld in enumerate(_map_info_fields):
        setattr(mi,fld,t[i])
    # this gets used in function names so must only be legal characters
    mi.map_name = re.sub('-', '_', mi.map_name)
    mi.map_id_fixup=False
    
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
        elif genutil.numeric(mi.map_id):
            mi.map_id = genutil.make_numeric(mi.map_id)
        else:
            mi.map_id_fixup=True

    else:
        if mi.legacy_escape != 'N/A':
            _die("Bad map description legacy escape [{}]".format(s))
        if mi.legacy_opcode != 'N/A':
            _die("Bad map description legacy opcode [{}]".format(s))
        if genutil.numeric(mi.map_id):
            mi.map_id = genutil.make_numeric(mi.map_id)
        else:
            _die("Bad map description map id [{}]".format(s))

    if mi.disp not in ['var','no']:
        _die("Bad map description disp specifier [{}]".format(s))
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



def emit_ild_enum(agi):
    evalues = []

    sorted_list = sorted(agi.map_info, key=lambda x: x.map_name)
    
    for mi in sorted_list:
        val = None
        if isinstance(mi.map_id,int):
            val = str(mi.map_id)

        e = enumer.enumer_value_t(mi.map_name.upper(), val)
        evalues.append(e)
        
    evalues.append('MAP_INVALID')
        
    enum = enum_txt_writer.enum_info_t(evalues,
                                       agi.common.options.xeddir,
                                       agi.common.options.gendir,
                                       'xed-ild', 
                                       'xed_ild_map_enum_t',
                                       'XED_ILD_',
                                       cplusplus=False)
    
    enum.run_enumer()
    agi.add_file_name(enum.src_full_file_name)
    agi.add_file_name(enum.hdr_full_file_name, header=True)
    agi.all_enums['xed_ild_enum_t'] = evalues


def fix_nonnumeric_maps(maps):
    d = collections.defaultdict(list)
    for mi in maps:
        if not mi.map_id_fixup:
            d[mi.space].append(mi.map_id)
    mx = {} # max per key
    for k in d.keys():
        mx[k] = max(d[k])
    for mi in maps:
        if mi.map_id_fixup:
            maxval = mx[mi.space] + 1
            mi.map_id = maxval
            mx[mi.space] = maxval
            mi.map_id_fixup = False
            
def read_file(fn):
    lines = open(fn,'r').readlines()
    lines = map(genutil.no_comments, lines)
    lines = list(filter(genutil.blank_line, lines))
    maps = [] # list of map_info_t
    for line in lines:
        maps.append( _parse_map_line(line) )
    fix_nonnumeric_maps(maps)
    maps.sort(key=lambda x: x.priority)
    for m in maps:
        _msgb("MAPINFO",m)
    return maps

if __name__ == "__main__":
    read_file(sys.argv[1])
    sys.exit(0)

