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
"""
CPUID record parser and data structures.

This module provides classes for parsing and representing CPUID feature records.
CPUID records specify processor feature detection through leaf/subleaf/register/bit
patterns. Used to associate instructions with their required CPUID features.
"""
from enum import Enum
import genutil
from genutil import die
import re

### Data types ###
class cpuid_record_t:
    """ load and report CPUID record """

    ### CPUID optional string patterns ###
    # CPUID common prefix:  <feature_name>.<leaf>.<subleaf>.<reg>
    cpuid_prefix = r"(?P<fname>\w+)[.](?P<leaf>[0-9A-F]+)[.](?P<s_leaf>[0-9A-F]+)[.](?P<reg>[a-zA-Z]+)"
    # CPUID pattern:        <feature_name>.<leaf>.<subleaf>.<reg>.<bit>
    old_cpuid_pattern = re.compile(cpuid_prefix + r"[.](?P<bit_start>\d+)$")
    # CPUID pattern:        <feature_name>.<leaf>.<subleaf>.<reg>[<bit>]
    cpuid_bit_pattern = re.compile(cpuid_prefix + r"\[(?P<bit_start>\d+)\]$")
    # CPUID pattern:        <feature_name>.<leaf>.<subleaf>.<reg>[<bit>:<bit>]=<value>
    cpuid_range_pattern = re.compile(cpuid_prefix + r"\[(?P<bit_start>\d+)\:(?P<bit_end>\d+)\]=(?P<value>\d+)$")

    def __init__(self, rec_str:str = ''):
        """ init and load from sting if rec_str is not empty """
        self.fname   : str = '' # Feature name
        self.leaf    : str = ''
        self.s_leaf  : str = ''
        self.reg     : str = ''
        self.bit_start : str = ''
        self.bit_end : str = ''
        self.value   : str = '' # Dec number, Not a bit
        if rec_str: self.load_from_str(rec_str)
    
    def valid_self_members(self) -> bool:
        """ Return True if all self.members contains a legal value """
        try:
            if all(len(member) for member in vars(self).values()):
                valid : bool = True
                # Check Leaf/Sub-Leaf (Hexa number >= 0)
                inputs = [int(self.leaf, 16), int(self.s_leaf, 16)]
                valid &= all(i >= 0 for i in inputs)
                # Check reg
                valid &= (len(self.reg) == 3)
                # Check bit indexes (Dec number in range(0, 32))
                b_start, b_end = int(self.bit_start, 10), int(self.bit_end, 10)
                bits           = [b_start, b_end]
                valid &= all(b in range(0, 32) for b in bits)
                valid &= (b_start <= b_end)
                # Check value (Dec number with limited bits width)
                max_bits = b_end - b_start + 1
                bits_len = int(self.value, 10).bit_length()
                valid &= (bits_len <= max_bits)

                return valid
        except: 
            # Main catches are failed string to int(10/16 base) conversion
            return False
        return False

    def load_from_str(self, rec_str : str) -> bool:
        """
        Parse a given cpuid rec_str string and fully load the CPUID information into all self.members.
        The function asserts if any self.member was not set as expected.

        Args:
            rec_str (str): CPUID string representation in a form of XED config file
        
        Returns:
            bool: True  - The loaded record is not empty.
                  False - The loaded record is empty.
        """
        rec_str = rec_str.strip()
        if rec_str == 'N/A':
            self.fname = self.reg = 'INVALID'
            self.leaf = self.s_leaf = self.bit_start = self.bit_end = self.value = '0'
            return False
        
        cpuid_range_def = self.cpuid_range_pattern.match(rec_str)
        if cpuid_range_def:
            # One value bounded by bits indexes, new syntax
            record = cpuid_range_def.groupdict()
            for k in record:
                setattr(self, k, record[k])

        cpuid_bit_def = self.cpuid_bit_pattern.match(rec_str)
        if cpuid_bit_def:
            # One bit, new syntax
            record = cpuid_bit_def.groupdict()
            for k in record:
                setattr(self, k, record[k])
            self.bit_end = self.bit_start
            self.value   = '1'

        old_cpuid_def = self.old_cpuid_pattern.match(rec_str)
        if old_cpuid_def:
            # One bit, old syntax
            record = old_cpuid_def.groupdict()
            for k in record:
                setattr(self, k, record[k])
            self.bit_end = self.bit_start
            self.value   = '1'
        
        assert self.valid_self_members(), f'[ERROR] load CPUID from "{rec_str}" failed. Record: {self.emit()}'
        return True
    
    def emit(self) -> str:
        """emit record's members and values """
        s = '{ '
        for member, val in vars(self).items():
            s += f'{member}={val}, '
        return s.strip(' ,') + ' }'
    
    def __str__(self):
        """Overrides the default implementation"""
        # Return non-compacted generic XED format
        if not self.valid_self_members() or self.fname == 'INVALID':
            return 'N/A'
        if (int(self.bit_start,10) == int(self.bit_end,10)):
            bit_string = f'{self.bit_start}'
        else:
            bit_string = f'{self.bit_start}:{self.bit_end}'
        s = f'{self.fname}.{self.leaf}.{self.s_leaf}.{self.reg}[{bit_string}]'
        s += f'={self.value}'
        return s
   
    def __repr__(self):
        """Overrides the default implementation"""
        # Return non-compacted generic XED format
        if not self.valid_self_members() or self.fname == 'INVALID':
            return 'N/A'
        if (int(self.bit_start,10) == int(self.bit_end,10)):
            bit_string = f'{self.bit_start}'
        else:
            bit_string = f'{self.bit_start}:{self.bit_end}'
        s = f'{self.fname}.{self.leaf}.{self.s_leaf}.{self.reg}[{bit_string}]'
        s += f'={self.value}'
        return '"'+s+'"'

    def __eq__(self, other):
        """Overrides the default implementation"""
        if not isinstance(other, cpuid_record_t):
            return False
        for member in vars(self):
            if getattr(self, member) != getattr(other, member):
                return False
        return True

class group_kind_t(Enum):
    """ 
    Enum for XED CPUID group kind
    The Enum's value is a sorting key and implies the groups indexing order of 
    each ISA-SET's CPUID group
    """
    AVX10 = 0  # AVX10 (EVEX) CPUID model
    FBIT  = 1  # Feature bit CPUID model

    @staticmethod
    def names():
        return list(map(lambda c: c.name, group_kind_t))

DEFAULT_CPUID_GROUP: group_kind_t = group_kind_t.FBIT


class group_record_t:
    """ 
    XED CPUID group class
    XED ISA-SET can be mapped to several CPUID groups.
    CPUID group includes several cpuid records.
    CPUID satisfaction of a given isa-set requires that all group's records are set.
    If one group was satisfied, the isa-set is supported 
    (OR relationship between groups, AND relationship between records)
    """
    def __init__(self, kind: group_kind_t, isa_set: str):
        self.kind: group_kind_t = kind
        self.isa_set: str = re.sub(r'^XED_ISA_SET_', '', isa_set) # isa-set's group
        self.name: str = self.isa_set
        if self.kind != DEFAULT_CPUID_GROUP:
            self.name = f'{self.name}_{self.get_kind_name()}'
        self.records: list[cpuid_record_t] = []
    
    def get_name(self) -> str:
        """ Return the group name """
        return self.name

    def get_kind_name(self) -> str:
        """ Return the group's kind (group_kind_t) name """
        return self.kind.name

    def get_sort_key(self) -> int:
        """ Returns a sorting key for isa-set's group list """
        return self.kind.value

    def get_records(self) -> list[cpuid_record_t]:
        """ Return a list of the group's cpuid records """
        return self.records

    def records_len(self) -> int:
        """ Returns the number of cpuid records """
        return len(self.get_records())

    def add_records_from_str(self, records: list[str]) -> int:
        """
        Convert a string of cpuid records to cpuid_record_t and store as a
        group record.

        Args:
            records (list[str]): cpuid records in a XED config format

        Returns:
            int: Returns the total number of group's records
        """
        for rec_str in records:
            rec = cpuid_record_t()
            loaded = rec.load_from_str(rec_str)
            if not loaded:
                continue  # Do not append an empty record (Usually "n/a" records)
            if (self.kind != group_kind_t.AVX10) and ('AVX10_ENABLED' in rec.fname):
                die(f'Found illegal AVX10 CPUID record ({rec.emit()}) in {self.get_kind_name()} group')
            self.records.append(rec)
        return self.records_len()
    
    def __eg__(self, other):
        """ Overrides the default implementation """
        if not isinstance(other, group_record_t):
            return False
        if self.kind != other.kind:
            return False
        return len(set(self.get_records()).symmetric_difference(other.get_records())) == 0
    
    def __str__(self) -> str:
        """ Overrides the default implementation """
        s = f'Name={self.get_name}, Kind={self.get_kind_name}, ISA-SET={self.isa_set}\n'
        s += 'CPUID records:\n\t'
        s += ', '.join([str(rec) for rec in self.get_records()])
        return s

    def __repr__(self) -> str:
        """ Overrides the default implementation """
        p = ', '.join(['"'+str(rec)+'"' for rec in self.records])
        s = '{"' + self.name + '" : ['+p+'] }'
        return s



### Type Hints ###
cpuid_rec_info_map_t = dict[str, cpuid_record_t]     # d[cpuid-name] = cpuid_record_t
cpuid_group_info_map_t = dict[str, group_record_t]   # d[group-name] = group_record_t
isaset_cpuid_map_t = dict[str, list[group_record_t]] # d[isa-set] = Lits[group_record_t]
##################

def make_cpuid_rec_info_map(isaset_cpuid_map : isaset_cpuid_map_t) -> cpuid_rec_info_map_t:
    """
    Create and return a unique CPUID map of {cpuid-name : cpuid_record_t}.
    The map is generated from isaset_cpuid_map_t

    Args:
        isaset_cpuid_map (isaset_cpuid_map_t): isa-set to a list of cpuid groups

    Returns:
        cpuid_rec_info_map_t: CPUID name to CPUID record mapping
    """    
    cpuid_info_map : cpuid_rec_info_map_t = {}
    for groups in isaset_cpuid_map.values():
        for group in groups:
            for rec in group.get_records():
                if rec.fname in cpuid_info_map:
                    if cpuid_info_map[rec.fname] != rec:
                        die("Mismatch on cpuid record specification for rec {}: {} vs {}".format(
                            rec.fname, cpuid_info_map[rec.fname], rec))
                cpuid_info_map[rec.fname] = rec
    
    # Make an INVALID cpuid record for enumeration usage
    cpuid_info_map['INVALID'] = cpuid_record_t('N/A')
    return cpuid_info_map

def make_cpuid_group_info_map(isaset_cpuid_map : isaset_cpuid_map_t) -> cpuid_group_info_map_t:
    """
    Create and return a unique CPUID map of {cpuid-group-name : group_record_t}.
    The map is generated from isaset_cpuid_map_t

    Args:
        isaset_cpuid_map (isaset_cpuid_map_t): isa-set to a list of cpuid groups

    Returns:
        cpuid_group_info_map_t: Group name to CPUID group mapping
    """    
    group_info_map : cpuid_group_info_map_t = {}
    for groups in isaset_cpuid_map.values():
        for grp in groups:
            if grp.name in group_info_map:
                if group_info_map[grp.name] != grp:
                    die("Mismatch on cpuid group specification for {}: \n{} \nVS \n{}".format(
                        grp.name, group_info_map[grp.name], grp))
            group_info_map[grp.name] = grp
    # Make an INVALID empty cpuid group for enumeration usage
    group_info_map['INVALID'] = group_record_t(isa_set='', kind=DEFAULT_CPUID_GROUP)
    return group_info_map

def read_file(fn : str) -> isaset_cpuid_map_t:
    """
    Read XED CPUID input file and return isa-set to list of group_record_t mapping.
    The support CPUID string format for XED's input files 
    is: "<key>:<cpuid_record>, <cpuid_record>, ..."

    Supported formats for <key>:
    1. "<isa-set>, <cpuid-group>:" includes an explicit isa-set and cpuid-group name.
    2. "<isa-set>:" with no cpuid-group kind. in this case, the group will be autogenerated to:
        a. *AVX10* If "AVX10_ENABLED" was specified as a cpuid_record name
        a. *DEFAULT_CPUID_GROUP* otherwise
    For <cpuid_record> supported formats, check cpuid string patterns in cpuid_record_t.

    Args:
        fn (str): XED CPUID input file name

    Returns:
        isaset_cpuid_map_t: isa-set to list of group_record_t mapping.
    """    
    lines = open(fn,'r').readlines()
    lines = map(genutil.no_comments, lines)
    lines = list(filter(genutil.blank_line, lines))
    d: isaset_cpuid_map_t = {}  # d[isa-set] = Lits[group_record_t]
    for line in lines:
        row_key, row_val = line.split(':', 1)
        row_key_list: list[str] = row_key.replace(' ', '').upper().split(',')
        assert len(row_key_list) in [1,2], f'Illegal cpuid key format: {row_key}'
        
        isa_set = row_key_list[0]
        group_kind: group_kind_t = DEFAULT_CPUID_GROUP
        if len(row_key_list) == 2:
            try:  # Group kind is explicitly set as CPUID key token
                group_kind = group_kind_t[row_key_list[1]]
            except:
                die(f'Unsupported CPUID group kind "{row_key_list[1]}". Expected: {group_kind_t.names()}')
        elif 'AVX10_ENABLED' in row_val.upper():
            # CPUID rows that are naturally belong to the AVX10 group
            # "AVX10_ENABLED" is the cpuid name of a fundamental AVX10 cpuid record
            group_kind = group_kind_t.AVX10
            
        if isa_set in d:
            isa_set_groups: list[group_kind_t] = [grp.kind for grp in d[isa_set]]
            if group_kind in isa_set_groups:
                msg = "Duplicate group definition for isa set. isa-set={} \nold={} \nnew={}"
                genutil.die(msg.format(isa_set, d[isa_set], line))
        else:
            d[isa_set] = []
        group_rec = group_record_t(group_kind, isa_set)
        records_len = group_rec.add_records_from_str(row_val.upper().split())
        if records_len:  # append only non-empty CPUID groups
            d[isa_set].append(group_rec)
    
    # Sort the cpuid groups for each ISA-SET
    for isa_set in d:
        d[isa_set] = sorted(d[isa_set], key=lambda x: x.get_sort_key())

    return d
