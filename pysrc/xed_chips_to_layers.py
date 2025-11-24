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


"""
A dict mapping of all chips to a list of corresponding ISA layers and other defines.
Specific configuration files can be added using their relative path (e.g layer/file.cfg).
"""

CHIPS_TO_LAYER = {
        'lakefield' : ['lakefield'],
        'via'       : ['via/files-via-padlock.cfg'],
        'amd'       : ['amd/files-amd.cfg',
                       'amd/amdxop/files.cfg',
                       'wbnoinvd'],
        'mpx'       : ['mpx'],
        'cet'       : ['cet'],
        'skl'       : ['skl', 
                       'sgx', 
                       'xsaves', 
                       'xsavec', 
                       'clflushopt'],
        'skx'       : ['skx', 
                       'pku', 
                       'clwb', 
                       'avx512f', 
                       'avx512cd', 
                       'avx512-skx', 
                       'avx-common-types'], # no ISA, just defines
        'clx'       : ['clx', 
                       'vnni'],
        'cpx'       : ['cpx', 
                       'avx512-bf16'],
        'knl'       : ['knl', 
                       'avx512f', 
                       'avx512cd'],
        'knm'       : ['knm', 
                       '4fmaps-512', 
                       '4vnniw-512', 
                       'vpopcntdq-512'],
        'cnl'       : ['cnl', 
                       'sha', 
                       'avx512ifma', 
                       'avx512vbmi'],
        'icl'       : ['icl', 
                       'rdpid', 
                       'bitalg', 
                       'vbmi2', 
                       'vnni', 
                       'vpopcntdq-512', 
                       'vpopcntdq-vl',
                       'wbnoinvd', # icl server
                       'sgx-enclv', # icl server
                       'pconfig', # icl server
                       'gfni-vaes-vpcl/files-sse.cfg', 
                       'gfni-vaes-vpcl/files-avx-avx512.cfg'],
        'tgl'       : ['tgl', 
                       'cet', 
                       'movdir', 
                       'vp2intersect', 
                       'keylocker'],
        'adl'       : ['adl', 
                       'hreset', 
                       'avx-vnni', 
                       'keylocker', 
                       'wbnoinvd'],
        'spr'       : ['spr', 
                       'hreset', 
                       'cldemote', 
                       'avx-vnni', 
                       'amx-spr', 
                       'waitpkg', 
                       'avx512-bf16',
                       'enqcmd', 
                       'tsx-ldtrk', 
                       'serialize', 
                       'avx512-fp16', 
                       'evex-map5-6'],
        'emr'       : ['emr', 
                       'tdx'],
        'gnr'       : ['gnr', 
                       'amx-fp16', 
                       'amx-complex', 
                       'iprefetch'],
        'dmr'       : ['dmr', 
                       'vex-map5', 
                       'vex-map7', 
                       'amx-dmr', 
                       'avx10-2', 
                       'movrs', 
                       'apx-f', # no promoted rao int
                       'sm4-evex', 
                       'avx-ifma', 
                       'avx-ne-convert', 
                       'avx-vnni-int8', 
                       'cmpccxadd',
                       'avx-vnni-int16', 
                       'sha512', 
                       'sm3', 
                       'sm4', 
                       'uintr'],
        'srf'       : ['srf', 
                       'avx-ifma', 
                       'avx-ne-convert', 
                       'avx-vnni-int8', 
                       'avx-common-types', # no ISA, just defines
                       'cmpccxadd', 
                       'msrlist', 
                       'vex-map7', 
                       'wrmsrns', 
                       'uintr', 
                       'enqcmd', 
                       'wbnoinvd'],
        'cwf'       : ['cwf', 
                       'user-msr', 
                       'iprefetch', 
                       'avx-vnni-int16', 
                       'sha512', 
                       'sm3', 
                       'sm4', 
                       'msr-imm'],
        'arl'       : ['arrow-lake', 
                       'uintr', 
                       'avx-ifma', 
                       'avx-ne-convert', 
                       'avx-common-types', # no ISA, just defines
                       'avx-vnni-int8', 
                       'cmpccxadd', 
                       'avx-vnni-int16', 
                       'sha512', 
                       'sm3', 
                       'sm4'],
        'lnl'       : ['lunar-lake'],
        'ptl'       : ['ptl', 
                       'iprefetch', 
                       'msrlist', 
                       'wrmsrns', 
                       'fred',
                       'pbndkb'],
        'future'    : ['future', 
                       'rao-int', 
                       'apx-f/apx-f-future-ext.cfg'],
    }

# Chip is a group of layers. Technology is a group of chips.
TECHNOLOGIES : set[str] = {'avx512'}

def get_chip_to_layer_dict() -> dict[str, list[str]]:
    return CHIPS_TO_LAYER

def get_technology_set() -> set[str]:
    return TECHNOLOGIES

def get_chips_and_techs() -> set[str]:
    """Return the set of all chip and technology exclusion options
    used in the XED builder config."""
    chips: set[str] = set(get_chip_to_layer_dict().keys())
    techs: set[str] = get_technology_set()
    builds = chips.union(techs)
    return builds