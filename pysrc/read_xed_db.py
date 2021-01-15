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
import collections
import patterns
import slash_expand
import genutil
import opnd_types
import opnds
import cpuid_rdr
import map_info_rdr

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)
def msgb(b,s=''):
    sys.stderr.write("[{0}] {1}\n".format(b,s))

class inst_t(object):
    def __init__(self):
        pass
    def __str__(self):
        s = []
        for fld in sorted(self.__dict__.keys()):
            s.append("{}: {}".format(fld,getattr(self,fld)))
        return "\n".join(s) + '\n'


    def get_eosz_list(self):
        if self.space == 'legacy':
            if hasattr(self,'attributes'):
                if 'BYTEOP' in self.attributes:
                    return [8]
            if hasattr(self,'eosz'):
                if self.eosz == 'oszall':
                    return [16,32,64]
                if self.eosz == 'osznot16':
                    return [32,64]
                if self.eosz == 'osznot64':
                    return [16,32]
                if self.eosz == 'o16':
                    return [16]
                if self.eosz == 'o32':
                    return [32]
                if self.eosz == 'o64':
                    return [64]
                die("Could not handle eosz {}".format(self.eosz))
            die("Did not find eosz for {}".format(self.iclass))
        else: #  vex, evex, xop
            return None
            

class width_info_t(object):
    def __init__(self, name, dtype, widths):
        """ a name and a dict of widths indexed by osz 8, 16,32, and 64b"""
        self.name = name.upper()
        self.dtype = dtype
        self.widths = widths  # dict indexed by 8,16,32,64
    def __str__(self):
        s = []
        s.append("name {}".format(self.name))
        s.append("datatype: {}".format(self.dtype))
        s.append("widths: {}".format(",".join(self.widths.values())))
        return " ".join(s)
    

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

def _op_immd(op):
    if op.name == 'IMM0':
        if op.oc2 == 'd':
            return True
def _op_immw(op):
    if op.name == 'IMM0':
        if op.oc2 == 'w':
            return True
def _op_immz(op):
    if op.name == 'IMM0':
        if op.oc2 == 'z':
            return True
def _op_immv(op):
    if op.name == 'IMM0':
        if op.oc2 == 'v':
            return True
    return False
def _op_imm8(op):
    if op.name == 'IMM0':
        if op.oc2 == 'b':
            return True
    return False

def _get_mempop_width_code(v):
    for op in v.parsed_operands:
        if op.name == 'MEM0':
            return op.oc2
    die("Could not find evex memop for {}".format(v.iclass))

def _set_eosz(v):
    eosz = 'oszall'
    if v.space == 'legacy':
        if 'EOSZ=1' in v.pattern:
            eosz = 'o16'
        elif 'EOSZ=2' in v.pattern:
            eosz = 'o32'
        elif 'EOSZ=3' in v.pattern:
            eosz =  'o64'
        elif 'EOSZ!=1' in v.pattern:
            eosz = 'osznot16'
        elif 'EOSZ!=3' in v.pattern:
            eosz = 'osznot64'
            
        if v.mode_restriction != 'unspecified':
            
            if v.mode_restriction == 0:  # 16b
                if v.osz_required and 'IMMUNE66' not in v.pattern:
                    eosz = 'o32'
                else:
                    eosz = 'o16'
                    
            elif v.mode_restriction == 1: # 32b
                if v.osz_required and 'IMMUNE66' not in v.pattern:
                    eosz = 'o16'
                else:
                    eosz = 'o32'
                    
            elif v.mode_restriction == 2: # 64b
                if v.default_64b:
                    eosz = 'o64'
                elif v.rexw_prefix == '1':
                    eosz = 'o64'
                elif 'FORCE64' in v.pattern:
                    eosz = 'o64'
                elif v.osz_required and 'IMMUNE66' not in v.pattern:
                    eosz = 'o16'
                else:
                    eosz = 'o32'
    v.eosz = eosz

def is_positive_integer(s):
    if re.match(r'^[0-9]+$',s):
        return True
    return False
    
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
                 element_types_filename,
                 cpuid_filename='',
                 map_descriptions_filename=''):

        self.xtypes = self._gen_xtypes(element_types_filename) 
        self.width_type_dict, self.width_info_dict = self._gen_widths(widths_filename)
        
        self.state_bits = self._parse_state_bits(state_bits_filename)
        
        self.map_info = []
        if map_descriptions_filename:
            self.map_info = map_info_rdr.read_file(map_descriptions_filename)
        
        self.deleted_unames = {}
        self.deleted_instructions = {}
        self.recs = self._process_lines(instructions_filename)
        self._find_opcodes()
        self._fix_real_opcode()

        self._parse_operands()
        self._generate_operands()
        self._generate_memop_rw_field()
        self._generate_missing_iforms()
        self._summarize_operands()
        self._summarize_vsib()
        self._summarize_sibmem()
        
        self.cpuid_map = {}
        if cpuid_filename:
            self.cpuid_map = cpuid_rdr.read_file(cpuid_filename)
            self._add_cpuid()
            
            
        self._add_vl()
        self._add_broadcasting()
        self._evex_disp8_scaling()

    def get_width_info_dict(self):
        return self.width_info_dict
        
    def _refine_widths_input(self,lines):
       """Return  a dict of width_info_t. Skip comments and blank lines"""
       comment_pattern = re.compile(r'#.*$')
       width_info_dict = {}
       for line in lines:
          pline = comment_pattern.sub('',line).strip()
          if pline == '':
             continue
          wrds = pline.split()
          ntokens = len(wrds)
          # dtype is the assumed datatype for that width code
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
          bit_widths = {}
          for osz,val in zip([8,16,32,64], [width8, width16, width32, width64]):
             number_string = _is_bits(val)
             if number_string:
                bit_widths[osz] = number_string
             else:
                bit_widths[osz] = str(int(val)*8)
          width_info_dict[name] = width_info_t(name, dtype, bit_widths)
       return width_info_dict
        
    def _gen_widths(self, fn):
        lines = open(fn,'r').readlines()
        width_info_dict = self._refine_widths_input(lines)

        # sets the default data type for each width
        width_type_dict = {}
        for w in width_info_dict.values():
            width_type_dict[w.name] = w.dtype
        return width_type_dict, width_info_dict

    def _gen_xtypes(self, fn):
        lines = open(fn,'r').readlines()
        xtypes_dict = opnd_types.read_operand_types(lines)
        return set(xtypes_dict.keys())
            
    def _compute_memop_rw(self,v):
        read=False
        write=False
        
        for opnd in v.parsed_operands:
            if opnd.name.startswith('MEM'):
                if 'r' in opnd.rw:
                    read = True
                if 'w' in opnd.rw:
                    write = True
            elif opnd.bits:
                if 'STACKPUSH' in opnd.bits:  # mem write
                    write = True
                if 'STACKPOP' in opnd.bits:   # mem read
                    read = True
                    
        if read and write:
            return 'mem-rw'
        elif write:
            return 'mem-w'
        elif read:
            return 'mem-r'
        return 'none'
            

    def _compute_operands(self,v):
        expl_operand_list = []
        impl_operand_list = []
        for op in v.parsed_operands:
            s = None
            if op.name in ['MEM0','MEM1']:
                s = 'MEM'
            elif op.name in ['IMM0','IMM1']:
                s = 'IMM'
            elif op.type == 'nt_lookup_fn':
                s = op.lookupfn_name_base
            elif op.type == 'reg':
                s = op.bits
                s = re.sub(r'XED_REG_','',s)
            elif op.type == 'imm_const':
                if op.name in ['BCAST','SCALE']:
                    continue
                s = op.name
            else:
                msbg("UNHANDLED","{}".format(op))
                
            if s:
                if op.visibility in ['IMPLICIT','SUPPRESSED']:
                    impl_operand_list.append(s)
                if op.visibility in ['EXPLICIT', 'DEFAULT']:
                    expl_operand_list.append(s)

        return expl_operand_list, impl_operand_list
    
    def _generate_operands(self):
        for v in self.recs:
            if not hasattr(v,'iform'):
                v.iform=''
            v.explicit_operands, v.implicit_operands = self._compute_operands(v)
            
            if not v.explicit_operands:
                v.explicit_operands = ['none']
            if not v.implicit_operands:
                v.implicit_operands = ['none']

    def _generate_one_iform(self,v):
        # This must match the logic from generator.py's compute_iform()
        tokens = []
        for op in v.parsed_operands:
            if op.visibility in ['IMPLICIT', 'EXPLICIT', 'DEFAULT']:
                s = None
                if op.name in ['MEM0','MEM1']:
                    s = 'MEM'
                    if op.oc2:
                        s += op.oc2
                elif op.name in ['IMM0','IMM1']:
                    s = 'IMM'
                    if op.oc2:
                        s += op.oc2
                    
                elif op.type == 'nt_lookup_fn':
                    #msgb("NTLUF: {}".format(op.lookupfn_name))
                    s = op.lookupfn_name_base
                    if op.oc2 and s not in ['X87']:
                        if op.oc2 == 'v' and s[-1] == 'v': 
                            pass # avoid duplicate v's
                        else:
                            s += op.oc2
                            
                elif op.type == 'reg':
                    s = op.bits.upper()
                    #msgb("REG: {}".format(s))
                    s = re.sub(r'XED_REG_','',s)
                    if op.oc2 and op.oc2 not in ['f80']:
                        s += op.oc2
                                
                elif op.type == 'imm_const':
                    if op.name in ['BCAST','SCALE']:
                        continue
                    s = op.name
                    if op.oc2:
                        s += op.oc2
                else:
                    msgb("IFORM SKIPPING ","{} for {}".format(op, v.iclass))
                if s:
                    tokens.append(s)
                    
        iform = v.iclass
        if tokens:
            iform += '_' + "_".join(tokens)
        return iform

        
    def _generate_missing_iforms(self):
        for v in self.recs:
            if v.iform == '' or  not hasattr(v,'iform'):
                v.iform = self._generate_one_iform(v)
                
    def _generate_memop_rw_field(self):
        for v in self.recs:
            v.memop_rw = self._compute_memop_rw(v) 
            
    def _add_cpuid(self):
        '''set v.cpuid with list of cpuid bits for this instr'''
        for v in self.recs:
            v.cpuid = []
            ky = 'XED_ISA_SET_{}'.format(v.isa_set.upper())
            if ky in self.cpuid_map:
                v.cpuid = self.cpuid_map[ky]
                
    def _add_broadcasting(self):
        broadcast_attr  = re.compile(r'BROADCAST_ENABLED')
        for v in self.recs:
            v.broadcast_allowed = False
            if v.space == 'evex':
                if broadcast_attr.search(v.attributes):
                    v.broadcast_allowed = True


    def _evex_disp8_scaling(self):
        disp8_pattern  = re.compile(r'DISP8_(?P<tupletype>[A-Z0-9_]+)')
        esize_pattern  = re.compile(r'ESIZE_(?P<esize>[0-9]+)_BITS')
        for v in self.recs:
            v.avx512_tuple = None
            v.element_size = None
            if v.space == 'evex':
                t = disp8_pattern.search(v.attributes)
                if t:
                    v.avx512_tuple = t.group('tupletype')
                    if v.avx512_tuple != 'NO_SCALE':
                        e = esize_pattern.search(v.pattern)
                        if e:
                            v.element_size = int(e.group('esize'))
                        else:
                            die("Need an element size")
                        v.memop_width_code = _get_mempop_width_code(v)

                        # if the oc2=vv), we get two widths depend on
                        # broadcasting. Either the width is (a) vl(full),
                        # vl/2(half), vl/4 (quarter) OR (b) the element
                        # size for broadcasting.
                        if v.memop_width_code == 'vv':
                            divisor = { 'FULL':1, 'HALF':2,'QUARTER':4}
                            # we might override this value if using broadcasting
                            v.memop_width = int(v.vl) // divisor[v.avx512_tuple]
                        else:
                            wi = self.width_info_dict[v.memop_width_code]
                            # we can use any width for these since they are not OSZ scalable.
                            v.memop_width = int(wi.widths[32])
    
    def _add_vl(self):
        def _get_vl(iclass,space,pattern):
            if 'VL=0' in pattern:
                return '128'
            elif 'VL=1' in pattern:
                return '256'
            elif 'VL=2' in pattern:
                return '512'
            # VLX is for things that use VL as an Encoder Output.
            # VLX is offset by +1 from typical VL values.
            elif 'VLX=1' in pattern:
                return '128'
            elif 'VLX=2' in pattern:
                return '256'
            elif 'VLX=3' in pattern:
                return '512'
            
            elif 'FIX_ROUND_LEN512' in pattern:
                return '512'
            elif space == 'vex':
                return 'LIG'
            elif space == 'evex':
                return 'LLIG'
            die("Not reached")

        for v in self.recs:
            if v.space in ['vex','evex']:
                v.vl  = _get_vl(v.iclass, v.space, v.pattern)
            else:
                v.vl = 'n/a'
                
    def _summarize_operands(self):
        for v in self.recs:
            v.has_imm8 = False
            v.has_immz = False #  16/32b imm. (32b in 64b EOSZ)
            v.has_imm8_2 = False
            v.imm_sz = '0'
            for op in v.parsed_operands:
                if _op_imm8(op):
                    v.has_imm8 = True
                    v.imm_sz = '1'                    
                elif _op_immz(op):
                    v.has_immz = True
                    v.imm_sz = 'z'                    
                elif _op_immv(op):
                    v.imm_sz = 'v'                    
                elif _op_immd(op):
                    v.imm_sz = '4'
                elif _op_immw(op):
                    v.imm_sz = '2'
                elif op.name == 'IMM1':
                    v.has_imm8_2 = True
                    
    def _summarize_vsib(self):
        for v in self.recs:
            v.avx_vsib = None
            v.avx512_vsib = None
            if 'UISA_VMODRM_XMM()' in v.pattern:
                v.avx512_vsib = 'xmm'
            elif 'UISA_VMODRM_YMM()' in v.pattern:
                v.avx512_vsib = 'ymm'
            elif 'UISA_VMODRM_ZMM()' in v.pattern:
                v.avx512_vsib = 'zmm'
            elif 'VMODRM_XMM()' in v.pattern:
                v.avx_vsib = 'xmm'
            elif 'VMODRM_YMM()' in v.pattern:
                v.avx_vsib = 'ymm'

    def _summarize_sibmem(self):
        for v in self.recs:
            v.sibmem = False
            for op in v.parsed_operands:
                if op.name == 'MEM0' and op.oc2 == 'ptr':
                    v.sibmem=True
                    break

    def _parse_operands(self):
        '''set v.parsed_operands with list of operand_info_t objects (see opnds.py).'''
        for v in self.recs:
            v.operand_list = v.operands.split()
            v.parsed_operands = []
            for op_str in v.operand_list:
                #op is an operand_info_t  object
                op =  opnds.parse_one_operand(op_str,
                                              'DEFAULT',
                                              self.xtypes,
                                              self.width_type_dict,
                                              skip_encoder_conditions=False)
                v.parsed_operands.append(op)
            
    def _fix_real_opcode(self):
        for v in self.recs:
            if not hasattr(v,'real_opcode'):
                v.real_opcode='Y'


    def _find_legacy_map_opcode(self, pattern):
        """return (map, opcode:str). map is either an integer or the string AMD for 3dNow"""
        opcode, mapno = pattern[0], 0 # assume legacy map 0 behavior
        # records are ordered so that shortest legacy map is last
        # otherwise this won't work.
        for mi in self.map_info:
            if mi.is_legacy():
                if pattern[0] == mi.legacy_escape:
                    if mi.legacy_opcode == 'N/A':
                        mapno = int(mi.map_id)
                        opcode = pattern[mi.opcpos]
                        break
                    elif mi.legacy_opcode == pattern[1]:
                        if mi.map_name == 'amd-3dnow':
                            mapno = 'AMD3DNOW'
                        #elif mi.map_id == 'AMD3DNOW':
                        #    mapno = mi.map_id
                        else:
                            mapno = int(mi.map_id)
                        opcode = pattern[mi.opcpos] 
                        break
        
        return mapno,opcode
                
    def _find_opcodes(self):
        '''augment the records with information found by parsing the pattern'''

        map_pattern = re.compile(r'MAP=(?P<map>[0-9]+)')
        vex_prefix  = re.compile(r'VEX_PREFIX=(?P<prefix>[0-9])')
        rep_prefix  = re.compile(r'REP=(?P<prefix>[0-3])')
        osz_prefix  = re.compile(r' OSZ=(?P<prefix>[01])')
        no_prefix   = re.compile(r'REP=0 OSZ=0')
        rexw_prefix = re.compile(r'REXW=(?P<rexw>[01])')
        reg_required = re.compile(r'REG[\[](?P<reg>[b01]+)]')
        mod_required = re.compile(r'MOD[\[](?P<mod>[b01]+)]')
        mod_mem_required = re.compile(r'MOD!=3')
        mod_reg_required = re.compile(r'MOD=3')
        rm_val_required = re.compile(r'RM=(?P<rm>[0-9]+)')
        rm_required  = re.compile(r'RM[\[](?P<rm>[b01]+)]')  # RM[...] or SRM[...]
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
            if p0 == 'VEXVALID=1':
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
            else: # legacy maps and AMD 3dNow (if enabled)
                v.map, opcode = self._find_legacy_map_opcode(pattern)

            v.opcode = opcode
            v.partial_opcode = False
            
            v.amd_3dnow_opcode = None
            # conditional test avoids prefetches and FEMMS.
            if v.extension == '3DNOW' and v.category == '3DNOW':
                v.amd_3dnow_opcode = pattern[-1]

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
            rm = rm_required.search(v.pattern) # bit capture
            if rm:
                v.rm_required = genutil.make_numeric(rm.group('rm'))
            rm = rm_val_required.search(v.pattern)  # equality
            if rm:
                v.rm_required = genutil.make_numeric(rm.group('rm'))
            

            v.mod_required = 'unspecified'
            mod = mod_required.search(v.pattern)
            if mod:
                v.mod_required = genutil.make_numeric(mod.group('mod'))
            mod = mod_mem_required.search(v.pattern)
            if mod:
                v.mod_required = '00/01/10'
            mod = mod_reg_required.search(v.pattern)
            if mod:
                v.mod_required = 3

            v.has_modrm = False
            if 'MODRM' in v.pattern: # accounts for normal MODRM and various VSIB types
                v.has_modrm=True
            elif (v.reg_required != 'unspecified' or
                  v.mod_required != 'unspecified'):
                v.has_modrm=True
            elif v.rm_required != 'unspecified':
                # avoid the partial opcode bytes which do not have MODRM
                if 'SRM[' not in v.pattern: 
                    v.has_modrm=True
                

            # 16/32/64b mode restrictions
            v.mode_restriction = 'unspecified'
            if not64_pattern.search(v.pattern):
                v.mode_restriction = 'not64'
            else:
                mode = mode_pattern.search(v.pattern)
                if mode:
                    v.mode_restriction = int(mode.group('mode'))

            easz = 'aszall'
            if 'EASZ=1' in v.pattern:
                easz = 'a16'
            elif 'EASZ=2' in v.pattern:
                easz = 'a32'
            elif 'EASZ=3' in v.pattern:
                easz =  'a64'
                v.mode_restriction = 2
            elif 'EASZ!=1' in v.pattern:
                easz = 'asznot16'
            v.easz = easz



            v.default_64b = False
            if 'DF64()' in v.pattern or 'CR_WIDTH()' in v.pattern:
                v.default_64b = True
                
            _set_eosz(v)
            
            v.scalar = False
            if hasattr(v,'attributes'):
                v.attributes = v.attributes.upper()
                if 'SCALAR' in v.attributes:
                    v.scalar = True
            else:
                v.attributes = ''


            if opcode.startswith('0x'):
                v.opcode_base10 = int(opcode,16)
            elif opcode.startswith('0b'):
                # partial opcode.. 5 bits, shifted 
                v.opcode_base10 = genutil.make_numeric(opcode) << 3
                v.partial_opcode = True
            
            v.upper_nibble = int(v.opcode_base10/16)
            v.lower_nibble = v.opcode_base10 & 0xF


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
        r = self._process_udeletes(r)
        r = self._remove_replaced_versions(r)
        return r
    def _remove_replaced_versions(self,recs):
        # versions are based on iclasses
        dropped = 0
        iclass_version = collections.defaultdict(int)
        iclass_dct = collections.defaultdict(list) 
        n = [] # new list of records we build here
        for r in recs:
            if not hasattr(r,'version'):
                # "not versioned" is version 0, most stuff...
                iclass_dct[r.iclass].append(r)
            else:
                version = int(r.version)
                if iclass_version[r.iclass] < version:
                    dropped += len(iclass_dct[r.iclass])
                    iclass_dct[r.iclass] = [r]   # replace older versions of stuff
                    iclass_version[r.iclass] = version # set new version
                elif iclass_version[r.iclass] == version:
                    iclass_dct[r.iclass].append(r) # more of same
                elif iclass_version[r.iclass] > version:
                    # drop this record, version number too low
                    dropped += 1  

        msgb("VERSION DELETES", "dropped {} versioned records".format(dropped))
        # add the versioned ones to the list of records
        for iclass in iclass_dct.keys():
            for r in iclass_dct[iclass]:
                n.append(r)
        return n

    def _process_udeletes(self,recs):
        dropped = 0
        n = []
        for r in recs:
            if hasattr(r,'uname'):
                if r.uname in self.deleted_unames:
                    dropped += 1
                    continue
            n.append(r)
        msgb("UDELETES", "dropped {} udelete records".format(dropped))
        return n
    
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
        lines = open(fn).readlines()
        lines = genutil.process_continuations(lines)
    
        started = False
        recs = []
        nt_name = "Unknown"
        i = 0

        for line in lines:
            i = i + 1
            if i > 500:
                sys.stderr.write(".")
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
                m = patterns.delete_iclass_full_pattern.search(line)
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
                if value.startswith(':'):
                    die("Double colon error {}".format(line))
                if key == 'PATTERN':
                    # Since some patterns/operand sequences have
                    # iforms and others do not, we can avoid tripping
                    # ourselves up by always adding an iform when we
                    # see the PATTERN token. And if do we see an IFORM
                    # token, we can replace the last one in the list.
                    d['IFORM'].append('')
                if key == 'IFORM':
                    # Replace the last one in the list which was added
                    # when we encountered the PATTERN token.
                    d[key][-1] = value
                else:
                    # for normal tokens we just append them
                    d[key].append(value)
            else:
                die("Unexpected: [{0}]".format(line))
        sys.stderr.write("\n")
        return recs

