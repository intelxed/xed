#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
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
import argparse, sys, json
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, fields
from typing import get_origin
from collections import OrderedDict

sys.path.append(str(Path(__file__).resolve().parent))
import gen_setup
# XED specific type imports (for type hints)
from read_xed_db import inst_t, xed_reader_t, Restriction
from opnds import operand_info_t
from cpuid_rdr import group_record_t


@dataclass
class xed_instruction_record_t:
    """
    xed_instruction_record_t is a user-facing wrapper class for XED's internal inst_t object,
    providing a database-like representation of an instruction's attributes.

    Note:
        The types of the members are especially important, as when converting an inst_t object
        to a xed_instruction_record_t object, the destination type for each field is determined
        by the type annotation in this class. This ensures an implicit automated type conversion
        and data integrity during the transformation process.
    """
    ## XED Attributes
    iclass: str = None
    disasm_intel: str = None
    iform: str  = None
    isa_set: str = None
    extension: str = None
    exceptions: str = None
    category: str = None
    pattern: str = None
    attributes: list[str] = field(default_factory=list)
    cpl: int = None
    encoding_space: str = None
    ## CPUID
    cpuid_groups: list[group_record_t] = field(default_factory=list)
    ## flags
    flags: str = None
    ## effective operand/address size
    default_64b: bool = False
    eosz_list: list[int] = field(default_factory=list)
    easz_list: list[int] = field(default_factory=list)
    ## Operands
    operand_list: list[str] = field(default_factory=list)
    parsed_operands: list[operand_info_t] = field(default_factory=list)
    explicit_operands: list[str] = field(default_factory=list)
    implicit_operands: list[str] = field(default_factory=list)
    sibmem: bool = False
    element_size: int = None
    ## Prefix Restrictions
    f2_required: bool = False
    f3_required: bool = False
    rex2_restriction: Restriction = None
    rexw_prefix: bool = False
    no_prefixes_allowed: bool = False
    osz_66_required: bool = False # == osz_required
    ### Opcode
    map: int = None
    opcode_base02: str = None
    opcode_base16: str = None
    partial_opcode: bool = False
    reg_required: int = None
    rm_required: int = None
    undocumented: bool = False
    # ModRM Restrictions
    has_modrm: bool = False
    mod_required: list[int] = None
    # System Restrictions
    mode_restriction: list[int] = None
    ### EVEX specific attributes
    evex_sub_space: str = None # TBD convert to Enum
    evex_pp: int = None
    u_bit: int = None
    vl: int = None
    broadcast_allowed: bool = None
    # EVEX / APX
    is_apx_scc: bool = False
    nd: int = None
    nf: int = None

    @classmethod
    def from_inst_t(cls, src_inst: inst_t, xed_reader: xed_reader_t = None) -> "xed_instruction_record_t":
        """Create a xed_instruction_record_t from an inst_t object."""
        xedi = cls()
        set_fields: set[str] = set()  # fields names that were set to the xedi object
        for dst_member in fields(xedi):
            if hasattr(src_inst, dst_member.name):
                src_value = getattr(src_inst, dst_member.name)
                # Type conversion from string
                if isinstance(src_value, str):
                    if dst_member.type == bool:      # str -> bool
                        if src_value.lower() in ['true', '1']:
                            value = True
                        elif src_value.lower() in ['false', '0']:
                            value = False
                        else:
                            value = None # 'unspecified' -> None
                    elif dst_member.type == int:     # str -> int
                        try:
                            value = int(src_value, 0)  # Handles hex and decimal
                        except ValueError:
                            value = None
                    elif get_origin(dst_member.type) == list: # str -> list
                        value = [x.strip() for x in re.split(r'[,\s]+', src_value) if x.strip()]
                    else:
                        value = src_value.strip()
                else:
                    value = src_value
                setattr(xedi, dst_member.name, value)
                set_fields.add(dst_member.name)

        ### Fixup inst_t attributes
        empty = 'none'
        if empty in xedi.explicit_operands:
            xedi.explicit_operands.remove(empty)
        if empty in xedi.implicit_operands:
            xedi.implicit_operands.remove(empty)
        # Fixup mod_required
        if src_inst.mod_required in ('unspecified', 'none', None):
            xedi.mod_required = []
        elif src_inst.mod_required == '00/01/10':
            xedi.mod_required = [0, 1, 2]
        elif src_inst.mod_required == 3:
            xedi.mod_required = [3]
        else:
            assert 0, f"Unexpected mod_required value: {xedi.mod_required}"
        # Fixup mode_restriction
        if isinstance(src_inst.mode_restriction, str):
            if src_inst.mode_restriction in ('unspecified', 'none', None):
                xedi.mode_restriction = [16, 32, 64]
            elif src_inst.mode_restriction == 'not64':
                xedi.mode_restriction = [16, 32]
            else:
                assert 0, f"Unexpected mode_restriction string value: {xedi.mode_restriction}"
        elif isinstance(src_inst.mode_restriction, int):
            mode_map = {0 : 16, 1 : 32, 2 : 64}
            xedi.mode_restriction = [mode_map[src_inst.mode_restriction]]
        else:
            assert 0, f"Unexpected mode_restriction type: {type(src_inst.mode_restriction)}"
            
        # Fixup spaces
        xedi.pattern = single_space(xedi.pattern)
        
        # Fixup disasm
        if not xedi.disasm_intel:
            xedi.disasm_intel = xedi.iclass

        ### Extend with new calculated fields ###
        if src_inst.partial_opcode: 
            # src_inst.opcode is binary
            opc_02_cvt = lambda src_inst: src_inst.opcode
            opc_16_cvt = lambda src_inst: hex(int(src_inst.opcode, 2) << 3)
        else: 
            # src_inst.opcode is hex
            opc_02_cvt = lambda src_inst: bin(int(src_inst.opcode, 16))
            opc_16_cvt = lambda src_inst: src_inst.opcode

        calculated_fields = {
            'opcode_base02':      opc_02_cvt,
            'opcode_base16':      opc_16_cvt,
            'evex_pp':            get_evex_pp,
            'eosz_list':          lambda src_inst: src_inst.get_eosz_list(),
            'easz_list':          lambda src_inst: src_inst.get_easz_list(),
            'osz_66_required':    src_inst.osz_required,
            'encoding_space':     src_inst.space,
            'evex_sub_space':     None,  # TBD
        }
        set_fields.update(calculated_fields.keys())
        for key, func in calculated_fields.items():
            setattr(xedi, key, func(src_inst) if callable(func) else func)
        
        ### optional inst_t members - 
        # The inst_t objects include some members only under certain conditions.
        # We need to ensure these are always set in the xed_instruction_record_t to provide a consistent interface.
        set_fields.update(['flags', 'disasm_intel', 'exceptions'])

        ### Check that all fields are set
        all_flds_names: set[str] = {f.name for f in fields(xedi)}
        missing: set[str] = all_flds_names - set_fields
        assert len(missing) == 0, f'xed_instruction_record_t.from_inst() missing fields initialization: {", ".join(missing)}'
        
        return xedi


def gen_xed_inst_db(args, xed_db: xed_reader_t = None) -> list[xed_instruction_record_t]:
    """Generate a list of xed_instruction_record_t from the input XED database."""
    if not xed_db:
        xed_db: xed_reader_t = input_xed_db(args)
    xed_inst_db: list[xed_instruction_record_t] = []
    for rec in xed_db.recs:
        inst_rec = xed_instruction_record_t.from_inst_t(rec, xed_db)
        xed_inst_db.append(inst_rec)
    return xed_inst_db

def convert_to_serializable(obj) -> dict:
    """Convert the object into a serializable dict for json.dump()."""                      
    def is_serializable(o) -> bool:
        try:
            json.dumps(o)
            return True
        except (TypeError, OverflowError):
            return False

    result = {}
    for key, value in obj.__dict__.items():
        if callable(value):
            result[key] = value()
        elif isinstance(value, Enum):
            result[key] = str(value)
        elif isinstance(value, list):
            result[key] = []
            for v in value:
                if isinstance(v, str) and v.isdigit():
                    elem = int(v)
                elif hasattr(v, 'to_serializable'):
                    elem = v.to_serializable()
                elif is_serializable(v):
                    elem = v
                else:
                    elem = str(v)
                result[key].append(elem)
        elif isinstance(value, dict):
            result[key] = { str(k): str(v) for k, v in value.items() }
        elif isinstance(value, str) and value.isdigit():
            result[key] = int(value) # str -> int
        elif is_serializable(value):
            result[key] = value
        else:
            result[key] = str(value)
        
        # empty string -> None
        if result[key] == '':
            result[key] = None

    return result

### Main functions ###

def input_xed_db(args) -> xed_reader_t:
    args.prefix = args.xed_dgen
    gen_setup.make_paths(args)
    xed_db: xed_reader_t = gen_setup.read_db(args)
    return xed_db

def get_evex_pp(rec) -> str:
    if rec.space != 'legacy':    
        if rec.no_prefixes_allowed:
            return 0 # 'NP'
        elif rec.osz_required:
            return 1 # '66'
        elif rec.f2_required:
            return 2 # 'F2'
        elif rec.f3_required:
            return 3 # 'F3'
    return None

def single_space(s: str) -> str:
    if s is None:
        return ''
    return ' '.join(s.split())

def fix_attr(rec: inst_t) -> None:
    rec.operands = single_space(rec.operands)
    rec.pattern = single_space(rec.pattern)

def output_json(args, xed_json_db: list) -> None:
    if args.compact:
        indent = None
        separators = (',', ':')
    else:
        indent = 2
        separators = None
    
    ### Sort fields in desired order ###
    # Define priority fields in desired order
    priority_fields = [
        'iclass', 'disasm_intel', 'isa_set', 'extension', 'category', 'iform', 
        'encoding_space', 'attributes', 'flags', 'operand_list', 'explicit_operands', 
        'implicit_operands', 'parsed_operands',
    ]
    
    sorted_instructions = []
    for inst in xed_json_db:
        ordered_inst = OrderedDict()
        
        # Add priority fields first
        for field in priority_fields:
            if field in inst:
                ordered_inst[field] = inst[field]
        
        # Add remaining fields in alphabetical order
        remaining = sorted(set(inst.keys()) - set(priority_fields))
        for field in remaining:
            ordered_inst[field] = inst[field]
        
        sorted_instructions.append(ordered_inst)
    #################################
    out_data: dict = {'Instructions': sorted_instructions}
    with open(args.out, 'w') as json_fp:
        json.dump(out_data, json_fp, sort_keys=False, indent=indent, separators=separators)

def verify_instruction_record_fields(xed_input_db: xed_reader_t, xed_gen_inst_rec_db: list[xed_instruction_record_t]):
    """Validate that the xed_instruction_record_t members and the inst_t members match expectations."""
    # Get dataclass fields from xed_instruction_record_t - an actual object, not just the class definition
    xed_inst_rec_fields: set[str] = set(vars(xed_gen_inst_rec_db[0]).keys())
    
    # Get actual instance attributes from inst_t object (not class attributes)
    # inst_t is not homogeneous, so we can not use only the first record
    # Get attributes from all records:
    inst_t_fields: set[str] = set()
    for rec in xed_input_db.recs:
        inst_t_fields.update(vars(rec).keys())
    
    only_in_xed_inst_rec = xed_inst_rec_fields - inst_t_fields
    only_in_inst_t = inst_t_fields - xed_inst_rec_fields
    
    print("Fields only in xed_instruction_record_t:")
    for f in sorted(only_in_xed_inst_rec):
        print(f"  {f}")
    print("\nFields only in inst_t:")
    for f in sorted(only_in_inst_t):
        print(f"  {f}")

    expected_only_in_xed_inst_rec: set[str] = {'easz_list', 'encoding_space', 'eosz_list', 'evex_pp', 'evex_sub_space', 
                                               'opcode_base16', 'opcode_base02', 'osz_66_required'}
    assert only_in_xed_inst_rec == expected_only_in_xed_inst_rec, "Unexpected fields in xed_instruction_record_t: " + \
        f"{only_in_xed_inst_rec.symmetric_difference(expected_only_in_xed_inst_rec)}"
    
    expected_only_in_inst_t: set[str] = {
    'amd_3dnow_opcode', 'avx512_tuple', 'avx512_vsib', 'avx_vsib', 
    'comment', 'disasm', 'disasm_attsv', 'easz', 'eosz', 
    'lower_nibble', 'memop_rw', 'memop_width', 'memop_width_code', 
    'ntname', 'opcode', 'operands', 'osz_required', 'real_opcode', 
    'scalar', 'scc_val', 'space', 'uname', 'upper_nibble', 'version',
    'has_imm16', 'has_imm32', 'has_imm8', 'has_imm8_2', 'has_immz', 'imm_sz',
    'opcode_base10',
    }
    assert only_in_inst_t == expected_only_in_inst_t, "Unexpected fields in inst_t: " + \
        f"{only_in_inst_t.symmetric_difference(expected_only_in_inst_t)}"
    
    print("[PASSED] object members validation")
    

def validate_xed_inst_db(xed_input_db: xed_reader_t, xed_gen_inst_rec_db: list[xed_instruction_record_t]) -> None:
    
    verify_instruction_record_fields(xed_input_db, xed_gen_inst_rec_db)
    
    # Ensure xed_instruction_record_t instance members match the dataclass definition
    xed_inst_rec_fields: set[str] = set(vars(xed_gen_inst_rec_db[0]).keys())
    for rec in xed_gen_inst_rec_db:
        rec_fields: set[str] = set(vars(rec).keys())
        missing: set[str] = xed_inst_rec_fields - rec_fields
        added: set[str] = rec_fields - xed_inst_rec_fields
        assert len(added) == 0, f'xed_instruction_record_t instance has extra fields: {", ".join(added)}'
        assert len(missing) == 0, f'xed_instruction_record_t instance missing fields: {", ".join(missing)}'
    print("[PASSED] xed_instruction_record_t instance members validation")

    # Ensure all xed_instruction_record_t members matches dataclass type definition
    for rec in xed_gen_inst_rec_db:
        for f in fields(rec):
            value = getattr(rec, f.name)
            if value is not None:
                expected_type = get_origin(f.type) or f.type
                assert isinstance(value, expected_type), \
                    f'xed_instruction_record_t.{f.name} has incorrect type: expected {f.type}, got {type(value)}'
                # If type is a list, validate all inner elements types
                if expected_type == list:
                    elem_type = f.type.__args__[0]
                    for elem in value:
                        assert isinstance(elem, elem_type), \
                            f'xed_instruction_record_t.{f.name} list element has incorrect type: expected {elem_type}, got {type(elem)}'
    print("[PASSED] xed_instruction_record_t member types validation")


def main():
    parser = argparse.ArgumentParser(description='Parse XED datafiles and export instruction metadata as JSON')
    parser.add_argument('--xed-dgen', type=str, required=True, help='XED build obj/dgen directory')
    parser.add_argument('--out', type=str, default='xed_db.json', help='Output JSON file')
    parser.add_argument('--compact', action='store_true', help='Dump compact JSON format')
    parser.add_argument('--raw', action='store_true', help='Dump raw XED inst_t records')
    parser.add_argument('--validate', action='store_true', help='Dump development statistics and validate correctness')
    args = parser.parse_args()

    xed_input_db: xed_reader_t = input_xed_db(args)
    xed_gen_inst_rec_db: list[xed_instruction_record_t] = None

    if args.validate:
        xed_gen_inst_rec_db = gen_xed_inst_db(args, xed_input_db)
        validate_xed_inst_db(xed_input_db, xed_gen_inst_rec_db)

    xed_json_db = [] # serializable list of instructions objects
    if args.raw:
        for rec in xed_input_db.recs:
            fix_attr(rec) # basic cleanup
            xed_json_db.append(convert_to_serializable(rec))
    else:
        if not xed_gen_inst_rec_db:
            xed_gen_inst_rec_db = gen_xed_inst_db(args, xed_input_db)
            
        for rec in xed_gen_inst_rec_db:
            xed_json_db.append(convert_to_serializable(rec))
    output_json(args, xed_json_db)

if __name__ == '__main__':
    main()
