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

## The ild.py needs the mapping from decode search patterns to
##   symbolic map names.  It includes V0F, V0F38, V0F3A and it has order
##   requirements V0F and 0x0F must be after the longer patterns.
## 
## The ild_info.py map information is really just the raw map names
##  in order as we all as an indicator for which maps are irregular.

import map_info_rdr    

def get_maps(agi):
    map_names = [ mi.map_name for mi in agi.map_info ]
    return map_names

def get_maps_max_id(agi):
    return  max([mi.map_id for mi in agi.map_info])

def vexvalid_to_encoding_space(vv):
    """Input number, output string"""
    return map_info_rdr.vexvalid_to_encoding_space(vv)
def encoding_space_to_vexvalid(space):
    """Input string, output number"""
    return map_info_rdr.encoding_space_to_vexvalid(space)


def get_maps_for_space(agi,vv):
    encspace = vexvalid_to_encoding_space(vv)
    maps = [ mi for mi in agi.map_info if mi.space == encspace ]
    return maps


def get_dump_maps_modrm(agi):
    maps = []
    for mi in agi.map_info:
        if mi.has_variable_modrm():
            maps.append(mi.map_name)
    return maps

def get_dump_maps_imm(agi):
    maps = []
    for mi in agi.map_info:
        if mi.has_variable_imm():
            maps.append(mi.map_name)
    return maps
        
def get_dump_maps_disp(agi):
    maps = []
    for mi in agi.map_info:
        if mi.has_variable_disp():
            maps.append(mi.map_name)
    return maps

#10 is enough i think
storage_priority = 10
                

class ild_info_t(object):
    def __init__(self, vexvalid=None,
                 insn_map=None, opcode=None, incomplete_opcode=None,
                 missing_bits=None, has_modrm=None, eosz_nt_seq=None,
                 easz_nt_seq=None,
                 imm_nt_seq=None, disp_nt_seq=None,ext_opcode=None, 
                 mode=None,
                 priority=storage_priority):
        self.vexvalid = vexvalid # numeric
        self.insn_map = insn_map
        self.opcode = opcode
        
        #Boolean, indicates if given opcode is incomplete
        #that happens when last 3 bits of the opcode are taken
        #for operand register definition like in 0x40 opcodes for push(or pop)
        self.incomplete_opcode = incomplete_opcode
        
        #Integer, indicates number of bits that incomplete opcode misses.
        #Usually 3, but added that for generality
        self.missing_bits = missing_bits
        
        #Integer. The value of opcode << 3 + MODRM.REG when the MODRM.REG
        #is the extension of the opcode. None if opcode is not extended
        self.ext_opcode = ext_opcode
        
        self.mode = mode
        
        #String. Indicates whether instruction has MODRM byte
        #and whether it is ignored.
        #XED_ILD_HASMODRM_[TRUE|FALSE|IGNORE_MOD]
        self.has_modrm = has_modrm
        
        #[string] - list of EOSZ-binding NT names in pattern
        self.eosz_nt_seq = eosz_nt_seq
        
        #[string] - list of EASZ-binding NT names in pattern
        self.easz_nt_seq = easz_nt_seq
        
        #[string] - list of IMM_WIDTH-binding NT names in pattern
        self.imm_nt_seq = imm_nt_seq
        
        self.disp_nt_seq = disp_nt_seq
        
        #Integer. Indicates the priority of the object in conflict
        #resolution with other objects wit same map-opcode pair.
        #Priority 0 is the highest.
        #For example storage's objects have priority 10 and objects
        #obtained from grammar parsing have priority 0.
        self.priority = priority
        
    #This method is important because it defines which objects conflict
    # NOTE: SKIPPING vexvalid field in comparison
    def __eq__(self, other):
        return (other != None and
                self.insn_map == other.insn_map and
                self.opcode == other.opcode and
                self.has_modrm == other.has_modrm and
                self.ext_opcode == other.ext_opcode and
                self.mode == other.mode and
                self.eosz_nt_seq == other.eosz_nt_seq and
                self.easz_nt_seq == other.easz_nt_seq and
                self.imm_nt_seq == other.imm_nt_seq and
                self.disp_nt_seq == other.disp_nt_seq)
        
    #This method is not less important than __eq__
    # NOTE: SKIPPING vexvalid field in comparison
    def __ne__(self, other):
        return (other == None or
                self.insn_map != other.insn_map or
                self.opcode != other.opcode or
                self.has_modrm != other.has_modrm or
                self.ext_opcode != other.ext_opcode or
                self.mode != other.mode or
                self.eosz_nt_seq != other.eosz_nt_seq or
                self.easz_nt_seq != other.easz_nt_seq or
                self.imm_nt_seq != other.imm_nt_seq or
                self.disp_nt_seq != other.disp_nt_seq)
    
    #not currently used. But helps to conveniently sort
    #objects for pretty printing (by map-opcode values)
    def sort_key(self):
        return (int(self.insn_map,16) << 8) + int(self.opcode, 16)
    
    def __str__(self):
        printed_members = []
        printed_members.append('MAP\t: %s' % self.insn_map)
        printed_members.append('OPCODE\t: %s' % self.opcode)
        printed_members.append('EXT_OPCODE\t: %s' % self.ext_opcode)
        printed_members.append('MODE\t: %s' % self.mode)
        printed_members.append('INCOMPLETE_OPCODE\t: %s' % 
                                self.incomplete_opcode)
        printed_members.append('HAS_MODRM\t: %s' % self.has_modrm)
        printed_members.append('EOSZ_SEQ:\t %s' % self.eosz_nt_seq)
        printed_members.append('IMM_SEQ\t: %s' % self.imm_nt_seq)
        printed_members.append('DISP_SEQ\t: %s' % self.disp_nt_seq)
        
        return "{\n"+ ",\n".join(printed_members) + "\n}"

#convert pattern_t object to ild_info_t object
def ptrn_to_info(pattern, prio=storage_priority):
    return ild_info_t(vexvalid=pattern.get_vexvalid(),
                      insn_map=pattern.insn_map,
                      opcode=pattern.opcode, 
                      incomplete_opcode=pattern.incomplete_opcode, 
                      missing_bits=pattern.missing_bits, 
                      has_modrm=pattern.has_modrm, 
                      eosz_nt_seq=pattern.eosz_nt_seq,
                      easz_nt_seq=pattern.easz_nt_seq,
                      imm_nt_seq=pattern.imm_nt_seq,
                      disp_nt_seq=pattern.disp_nt_seq,
                      ext_opcode=pattern.ext_opcode,
                      mode=pattern.mode,
                      priority=prio)
    
#Get pattern_t object and set of infos , create info_t object and add it
#to the set
def add_ild_info(info_set, pattern):
    info = ptrn_to_info(pattern)
    info_set.add(info)

#info object has property 'priority' and min priority
#will win the conflict resolution.
#For example storage's info objects have priority=10, so that
#info objects obtained from grammar (priority=0) could override them
def get_min_prio_list(info_list):
    if len(info_list) == 0:
        return []
    min_prio = min(info_list, key=lambda x: x.priority).priority
    min_list = []
    for info in info_list:
        if info.priority == min_prio:
            min_list.append(info)
    return min_list


###

class ild_gap_fill_t:
    """Data structure to fill in gaps in ILD info for MODRM/DISP/IMM length decoding."""
    def __init__(self, modrm='no', disp='no', imm='no'):
        self.modrm = modrm
        self.disp = disp # currently unused
        self.imm = imm # currently unused

def init_ild_gap():
    """Initialize ild_gaps with fall-back information."""
    global ild_gaps
    ild_gaps = {}
    ild_gaps['legacy_map0'] = {}
    ild_gaps['legacy_map1'] = {}        
    for opcode in range(0, 256):
        ild_gaps['legacy_map0'][opcode]=ild_gap_fill_t()
        ild_gaps['legacy_map1'][opcode]=ild_gap_fill_t()


# initialized by caller of init_ild_gap(); Used to fill in holes in
# opcode space when we do not have instructions defined for specific
# values of legacy map 0 and 1.
ild_gaps = None

def ild_gap_modrm(insn_map, opcode):
    global ild_gaps
    return ild_gaps[insn_map][opcode].modrm
