#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2020 Intel Corporation
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
import os
import re
import shlex
import collections
import math

import genutil
import enumer
import enum_txt_writer
import codegen

# dict space name -> numerical space id
_space_id = {'legacy':0, 'vex':1, 'evex':2, 'xop':3, 'knc':4}
_space_id_to_name = {v: k for k,v in _space_id.items()}

# list ordered by numerical space id
_space_id_sorted  = sorted(_space_id.keys(), key=lambda x: _space_id[x])
def _encoding_space_max():
    return max(_space_id.values())
def _encoding_space_range():
    #Could make this dynamic based on what spaces are enabled
    return range(0, _encoding_space_max()+1)

def vexvalid_to_encoding_space(vv):
    """Input number, output string"""
    return _space_id_sorted[vv]
def encoding_space_to_vexvalid(space):
    """Input string, output number"""
    return _space_id[space]


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
        self.imm = None   # var,0,1,2,4 (bytes) var=7
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
    
    def has_variable_imm(self):
        return self.imm == 'var'
    
    
    def __str__(self):
        s = []
        s.append("name: {}".format(self.map_name))
        s.append("space: {}".format(self.space))
        s.append("legacyesc: {}".format(self.legacy_escape))
        s.append("legacyopc: {}".format(self.legacy_opcode))
        s.append("mapid: {}".format(self.map_id))
        s.append("modrm: {}".format(self.modrm))
        s.append("disp: {}".format(self.disp))
        s.append("imm: {}".format(self.imm))
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
                    'imm',
                    
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
    if mi.space == 'legacy':
        if mi.legacy_escape != 'N/A':
            mi.legacy_escape_int  = int(mi.legacy_escape,16)
            if mi.legacy_opcode != 'N/A':
                mi.legacy_opcode_int = int(mi.legacy_opcode,16)
            else:
                mi.legacy_opcode_int = None
        
    mi.map_id_fixup=False
    
    if mi.space not in ['legacy','vex','evex', 'xop','knc']:
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
    if mi.imm not in ['var','0','1','2','4']:
        _die("Bad map description imm specifier [{}]".format(s))
    if genutil.numeric(mi.opcpos):
        mi.opcpos = genutil.make_numeric(mi.opcpos)
    else:
        _die("Bad map description opcode position specifier [{}]".format(s))

    # we want the longer patterns first when we sort the map_info_t.
    mi.priority = 100-len(mi.search_pattern)
    return mi



def emit_enums(agi):
    emit_ild_enum_dups(agi)    # XED_ILD_*
    emit_ild_enum_unique(agi)  # XED_MAPU_*
    file_list = emit_map_info_tables(agi)
    agi.hdr_files.extend(file_list)

def emit_map_info_tables(agi):
    '''variable modrm,disp,imm tables, per encoding space using natural
       map ids. returns list of files generated'''
    map_features_cfn = 'xed-map-feature-tables.c'
    map_features_hfn = 'xed-map-feature-tables.h'
    private_gendir = os.path.join(agi.common.options.gendir,'include-private')
    hfe = codegen.xed_file_emitter_t(agi.common.options.xeddir,
                                     private_gendir,
                                     map_features_hfn)

    for h in [ 'xed-map-info.h' ]:
        hfe.add_header(h)
    hfe.start()

    sorted_list = sorted(agi.map_info, key=lambda x: x.map_name)

    spaces = list(set([ mi.space for mi in sorted_list ]))
    sorted_spaces = sorted(spaces, key=lambda x: encoding_space_to_vexvalid(x))
    max_space_id = _encoding_space_max() # legacy,vex,evex,xop,knc
    #max_space_id = encoding_space_to_vexvalid(sorted_spaces[-1])
    
    max_map_id = max([mi.map_id for mi in agi.map_info]) #0...31
    
    fields = ['modrm', 'disp', 'imm']

    cvt_yes_no_var = { 'yes':1, 'no':0, 'var':2 }
    cvt_imm        = { '0':0, '1':1, '2':2, '4':4, 'var':7 }

    field_to_cvt = { 'modrm': cvt_yes_no_var,
                     'disp' : cvt_yes_no_var,
                     'imm'  : cvt_imm }

    bits_per_chunk = 64
    
    # The field width in bits must be a power of 2 for current design,
    # otherwise the bits of interest can span the 64b chunks we are
    # using to store the values.
    field_to_bits = { 'modrm': 2,
                      'disp' : 2,
                      'imm'  : 4 }
    
    def collect_codes(field, space_maps):
        '''cvt is dict converting strings to integers. the codes are indexed by map id.'''
        cvt = field_to_cvt[field]
        codes = { key:0 for key in range(0,max_map_id+1) }
        
        for mi in space_maps:
            codes[mi.map_id] = cvt[getattr(mi,field)]
            
        codes_as_list = [ codes[i] for i in range(0,max_map_id+1) ]
        return codes_as_list

    def convert_list_to_integer(lst, bits_per_field):
        '''return an integer or a list of integer if more than 64b'''
        integers = []
        tot = 0
        shift = 0
        for v in lst:
            if shift >= 64:
                integers.append(tot)
                tot = 0
                shift = 0
            tot = tot + (v << shift)
            shift = shift + bits_per_field
        integers.append(tot)

        if len(integers) == 1:
            return integers[0]
        return integers


    for space_id in _encoding_space_range():

        space = _space_id_to_name[space_id]
        space_maps = [ mi for mi in sorted_list if mi.space == space ]

        for field in fields:
            bits_per_field = field_to_bits[field]
            total_bits = max_map_id * bits_per_field
            required_chunks = math.ceil(total_bits / bits_per_chunk)
            values_per_chunk = bits_per_chunk // bits_per_field
            ilog2_values_per_chunk = int(math.log2(values_per_chunk))
            mask = (1<<bits_per_field)-1
            
            f = codegen.function_object_t('xed_ild_has_{}_{}'.format(field,space),
                                          'xed_bool_t',
                                          static=True, inline=True)
            f.add_arg('xed_uint_t m')
            if space_maps:
                codes = collect_codes(field, space_maps)
                constant = convert_list_to_integer(codes,bits_per_field)
            else:
                codes = [0]
                constant = 0
            f.add_code('/* {} */'.format(codes))
            if set(codes) == {0}:  # all zero values...
                f.add_code_eol('return 0')
                f.add_code_eol('(void)m')
            else:
                if required_chunks <= 1:
                    f.add_code_eol('const xed_uint64_t data_const = 0x{:x}ULL'.format(constant))
                    f.add_code_eol('return (xed_bool_t)((data_const >> ({}*m)) & {})'.format(
                        bits_per_field, mask))
                else:
                    f.add_code('const xed_uint64_t data_const[{}] = {{'.format(required_chunks))
                    ln = ['0x{:x}ULL'.format(c) for c in constant]
                    f.add_code_eol(' {} }}'.format(", ".join(ln)))

                    f.add_code_eol('const xed_uint64_t chunkno = m >> {}'.format(ilog2_values_per_chunk))
                    f.add_code_eol('const xed_uint64_t offset = m & ({}-1)'.format(values_per_chunk))
                    f.add_code_eol('return (xed_bool_t)((data_const[chunkno] >> ({}*offset)) & {})'.format(
                        bits_per_field, mask))
                    
            hfe.write(f.emit())  # emit the inline function in the header


    # emit a function that covers all spaces
    for field in fields:
        bits_per_field = field_to_bits[field]
        total_bits = max_map_id * bits_per_field
        required_chunks = math.ceil(total_bits / bits_per_chunk)
        values_per_chunk = bits_per_chunk // bits_per_field
        ilog2_values_per_chunk = int(math.log2(values_per_chunk))
        mask = (1<<bits_per_field)-1

        f = codegen.function_object_t('xed_ild_has_{}'.format(field),
                                      'xed_bool_t',
                                      static=True, inline=True)
        f.add_arg('xed_uint_t vv')
        f.add_arg('xed_uint_t m')
        if required_chunks <= 1:
            f.add_code('const xed_uint64_t data_const[{}] = {{'.format(max_space_id+1))
        else:
            f.add_code('const xed_uint64_t data_const[{}][{}] = {{'.format(max_space_id+1,
                                                                           required_chunks))

        for space_id in _encoding_space_range():
            space = _space_id_to_name[space_id]
            space_maps = [ mi for mi in sorted_list if mi.space == space ]
            if space_maps:
                codes = collect_codes(field, space_maps)
                constant = convert_list_to_integer(codes,bits_per_field)
            else:
                codes = [0]*required_chunks
                if required_chunks <= 1:
                    constant = 0
                else:
                    constant = [0]*required_chunks
                    
            f.add_code('/* {} {} */'.format(codes,space))                
            if required_chunks <= 1:
                f.add_code(' 0x{:x}ULL,'.format(constant))
            else:
                ln = ['0x{:x}ULL'.format(c) for c in constant]
                f.add_code('{{ {} }},'.format(", ".join(ln)))
                
        f.add_code_eol('}')
        f.add_code_eol('xed_assert(vv < {})'.format(max_space_id+1))
        if required_chunks <= 1:
            f.add_code_eol('return (xed_bool_t)((data_const[vv] >> ({}*m)) & {})'.format(bits_per_field,
                                                                                         mask))
        else:
            f.add_code_eol('const xed_uint64_t chunkno = m >> {}'.format(ilog2_values_per_chunk))
            f.add_code_eol('const xed_uint64_t offset = m & ({}-1)'.format(values_per_chunk))
            f.add_code_eol('return (xed_bool_t)((data_const[vv][chunkno] >> ({}*offset)) & {})'.format(
                bits_per_field, mask))
            
        hfe.write(f.emit())  # emit the inline function in the header


            
    # emit a set of functions for determining the valid maps in each encoding space
    if max_map_id > 64:
        genutil.die("Need to make this work with multiple chunks of u64")
    for space_id in _encoding_space_range():
        space = _space_id_to_name[space_id]

        space_maps = [ mi for mi in sorted_list if mi.space == space ]
        f = codegen.function_object_t('xed_ild_map_valid_{}'.format(space),
                                      'xed_bool_t',
                                      static=True, inline=True)
        f.add_arg('xed_uint_t m')
        max_id = _encoding_space_max()
        #max_id = max( [mi.map_id for mi in space_maps ] )
        codes_dict = { key:0 for key in range(0,max_map_id+1) }
        for mi in space_maps:
            codes_dict[mi.map_id] = 1
        codes = [ codes_dict[i] for i in range(0,max_map_id+1) ]
        
        f.add_code('/* {} */'.format(codes))
        constant = convert_list_to_integer(codes,1)
        f.add_code_eol('const xed_uint64_t data_const = 0x{:x}ULL'.format(constant))
        # no need for a max-map test since, the upper bits of the
        # constant will be zero already
        f.add_code_eol('return (xed_bool_t)((data_const >> m) & 1)')
        hfe.write(f.emit())  # emit the inline function in the header

    # emit a table filling in "xed_map_info_t xed_legacy_maps[] = { ... }"

    legacy_maps = [ mi for mi in sorted_list if mi.space == 'legacy' ]
    legacy_maps = sorted(legacy_maps,
                         key=lambda x: -len(x.search_pattern) * 10 + x.map_id)
    
    hfe.add_code('const xed_map_info_t xed_legacy_maps[] = {')
    for mi in legacy_maps:
        if mi.map_id == 0:
            continue
        has_legacy_opcode = 1 if mi.legacy_opcode != 'N/A' else 0
        legacy_opcode = mi.legacy_opcode if mi.legacy_opcode != 'N/A' else 0
        legacy_escape = mi.legacy_escape if mi.legacy_escape != 'N/A' else 0
        
        hfe.add_code('{{ {}, {}, {}, {}, {} }},'.format(legacy_escape,
                                                        has_legacy_opcode,
                                                        legacy_opcode,
                                                        mi.map_id,
                                                        mi.opcpos))
    hfe.add_code_eol('}')
            
    hfe.close()
    return [hfe.full_file_name]

def emit_ild_enum_unique(agi):
    """modify map_info_t values to include mapu enum name so that we can
       build other arrays for the C-code based on that unique enum"""
    sorted_list = sorted(agi.map_info, key=lambda x: x.map_name)
    evalues = ['INVALID']
    for mi in sorted_list:
        s = mi.map_name.upper()
        evalues.append(s)
        mi.mapu_name = 'XED_MAPU_{}'.format(s)

    enum = enum_txt_writer.enum_info_t(evalues,
                                       agi.common.options.xeddir,
                                       agi.common.options.gendir,
                                       'xed-mapu', 
                                       'xed_mapu_enum_t',
                                       'XED_MAPU_',
                                       cplusplus=False)
    
    enum.run_enumer()
    agi.add_file_name(enum.src_full_file_name)
    agi.add_file_name(enum.hdr_full_file_name, header=True)
    agi.all_enums['xed_mapu_enum_t'] = evalues
    
    
def emit_ild_enum_dups(agi):
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
    agi.all_enums['xed_ild_map_enum_t'] = evalues

    

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
    #for m in maps:
    #    _msgb("MAPINFO",m)
    return maps

if __name__ == "__main__":
    read_file(sys.argv[1])
    sys.exit(0)

