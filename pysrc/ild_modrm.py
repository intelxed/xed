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

import ild_info
import ild_codegen
import ildutil

_modrm_nt           = 'MODRM()'
_vmodrm             = 'VMODRM'
_modrm_bind         = 'MOD['
_mod3_req           = 'MOD=3'

_modrm_header_fn    = 'xed-ild-modrm.h'

_has_modrm_true     = 'XED_ILD_HASMODRM_TRUE'
_has_modrm_false    = 'XED_ILD_HASMODRM_FALSE'
_has_modrm_undef    = 'XED_ILD_HASMODRM_UNDEF'
#for MOV_DR and MOV_CR that ignore MODRM.MOD bits
_has_modrm_ignore   = 'XED_ILD_HASMODRM_IGNORE_MOD'
_has_modrm_typename = 'xed_uint8_t'

_hasmodrm_defines = {
                     _has_modrm_false  : 0,
                     _has_modrm_true   : 1,
                     _has_modrm_ignore : 2,
                     _has_modrm_undef  : 3,
                    }


#FIXME: do we want to check by NT names or do something similar to
#EOSZ/EASZ - find all NTs that bind interesting operand and look
#for them in the pattern.
#FIXME2: it seems we need to check VMODRM() NT too
def get_hasmodrm(ptrn):
    """
    Return XED_ILD_HASMODRM_[TRUE|FALSE|IGNORE_MOD] string
    """
    if is_ignored_mod(ptrn):
        return _has_modrm_ignore
    has_modrm = (_modrm_nt in ptrn) or (_modrm_bind in ptrn)
    return _bool2has_modrm_str(has_modrm)

def is_ignored_mod(ptrn):
    """
    Return True|False if MODRM.MOD bits are ignored
    e.g. MOV_DR instruction
    """
    #if MODRM.MOD is ignored then MODRM's fields should
    #be bounded, but it should not be a VMODRM (SIMD
    #instructions, there should not be MODRM() that uses
    #MODRM's fields and there should not be a constraint MOD=3
    #which is usage of MODRM.MOD too.
    return (_modrm_bind in ptrn and 
             not _vmodrm in ptrn and
             not _modrm_nt in ptrn and
             not _mod3_req in ptrn)

def _resolve_modrm_conflict(info_list):
    """
    Not trying to dispatch by prefixes, mode or anything else.
    Because modrm doesn't have such conflicts.
    """
    return None

def _is_modrm_conflict(info_list):
    if len(info_list) <= 1:
        return False
    first = info_list[0]
    for info in info_list[1:]:
        if first.has_modrm != info.has_modrm:
            return True
    return False

def _bool2has_modrm_str(val):
    """
    Returns C define string for has_modrm
    """
    if val == None:
        return _has_modrm_undef
    if val:
        return _has_modrm_true
    return _has_modrm_false
    

def gen_modrm_lookup(united_lookup, debug):
    modrm_lookup = {}
    for insn_map in ild_info.get_dump_maps():
        modrm_lookup[insn_map] = {}
        for opcode in range(0, 256):
            info_list = united_lookup.get_info_list(insn_map, hex(opcode))
            info_list = ild_info.get_min_prio_list(info_list)
            if len(info_list) == 0:
                #no infos in map-opcode, illegal opcode
                has_modrm = _has_modrm_undef
            elif _is_modrm_conflict(info_list):
                #conflict in has_modrm value in map-opcode's info_list
                #try to resolve
                info = _resolve_modrm_conflict(info_list)
                if not info:
                    ildutil.ild_err(
                    'UNRESOLVED CONFLICT IN MODRM\n infos:\n%s\n' % 
                        "\n".join([str(info) for info in info_list]))
                has_modrm = info.has_modrm
            else:
                #several infos that agree on has_modrm property, we can choose
                #any of them to get has_modrm
                info = info_list[0]
                has_modrm = info.has_modrm
            modrm_lookup[insn_map][hex(opcode)] = has_modrm
    return modrm_lookup



def work(agi, united_lookup, debug):
    """
    dumps MODRM lookup tables to xed_ild_modrm.h
    """
    modrm_lookup = gen_modrm_lookup(united_lookup, debug)
    ild_codegen.dump_lookup(agi, modrm_lookup, 'has_modrm', _modrm_header_fn,
                            [], _has_modrm_typename,
                            define_dict=_hasmodrm_defines)
    

