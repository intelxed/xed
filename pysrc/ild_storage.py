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
import collections

import ild_info
import genutil

def _die(s):
    genutil.die(s)

class ild_storage_t(object):
    """Storage for table indexed by map and opcode. Storing lists of
      ild_info_t objects."""

    def __init__(self, is_amd=True, info_lookup=None):
        self.is_amd = is_amd
        if info_lookup == None:
            self.lookup = {}
            for insn_map in ild_info.get_maps(is_amd):
                self.lookup[insn_map] = collections.defaultdict(list)
        else:
            self.lookup = info_lookup
    
    #returns by reference
    def get_info_list(self, insn_map, opcode):
        try:
            return self.lookup[insn_map][opcode]
        except:
            _die("get_info_list failed map: %s  opcode: %s" %
                    (insn_map, opcode))
    
    def append_info(self, insn_map, opcode, info):
        self.lookup[insn_map][opcode].append(info)
    
    def set_info_list(self, insn_map, opcode, info_list):
        self.lookup[insn_map][opcode] = info_list
    
    def get_all_infos(self):
        all_infos = []
        for opcode_dict in self.lookup.values():
            for info_list in opcode_dict.values():
                all_infos.extend(info_list)
        return all_infos
    
    def get_maps(self):
        return list(self.lookup.keys())
