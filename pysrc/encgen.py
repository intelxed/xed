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
from __future__ import print_function
import os
import sys
import copy
import types
import glob
import re

import genutil


def _get_encspace(ii):
    if 'VV0' in ii.ipattern_input:
        return 'legacy'
    if 'VV1' in ii.ipattern_input:
        return 'vex'
    if 'EVV' in ii.ipattern_input:
        return 'evex'
    if 'XOPV' in ii.ipattern_input:
        return 'xop'
    if 'KVV' in ii.ipattern_input:
        return 'knc'
    return 'legacy'

def _create_enc_fn(agi, ii):
    s = [ii.iclass]
    s.append(_get_encspace(ii))
    
    for op in ii.operands:
        kmask = False
        if op.lookupfn_name == 'MASK1':
            kmask = True
            s[-1] = s[-1] + '-kmask'
        elif op.lookupfn_name == 'MASKNOT0':
            kmask = True
            s[-1] = s[-1] + '-kmask!0'
        if kmask and  'ZEROING=0' in ii.ipattern_input:
            s[-1] = s[-1] + '-nz'

            
        if op.visibility != 'SUPPRESSED' and not kmask:
            s.append(op.name)
            if op.lookupfn_name:
                s.append('({})'.format(op.lookupfn_name))
            elif op.bits and op.bits != '1':
                s.append('[{}]'.format(op.bits))
            if op.name == 'MEM0':
                if op.oc2:
                    s[-1] = s[-1] + '-' + op.oc2
                if op.xtype:
                    s[-1] = s[-1] + '-X:' + op.xtype
                if 'UISA_VMODRM_XMM()' in ii.ipattern_input:
                    s[-1] = s[-1] + '-uvx'
                elif 'UISA_VMODRM_YMM()' in ii.ipattern_input:
                    s[-1] = s[-1] + '-uvy'
                elif 'UISA_VMODRM_ZMM()' in ii.ipattern_input:
                    s[-1] = s[-1] + '-uvz'
                elif 'VMODRM_XMM()' in ii.ipattern_input:
                    s[-1] = s[-1] + '-vx'
                elif 'VMODRM_YMM()' in ii.ipattern_input:
                    s[-1] = s[-1] + '-nvy'
                
    print("XX {}".format(" ".join(s)))
    


def work(agi):
    ilist = []
    for generator in agi.generator_list:
        ii = generator.parser_output.instructions[0]
        if not genutil.field_check(ii,'iclass'):
            continue
        for ii in generator.parser_output.instructions:
            ilist.append(ii)
            
    for ii in ilist:
        _create_enc_fn(agi,ii)
            
