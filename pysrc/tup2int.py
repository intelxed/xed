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


def tuple2int(t, cnames, op_widths_dict):
    """Convert list of values in the input parameter t to a hash key by
       shifting and adding (OR'ing really) the values together. Must
       factor in the max width of each field. The max width of each
       component comes from the cnames and op_widths_dict parameters).
    """
    res = 0
    bit_shift = 0
    for i,byte in enumerate(t):
        opwidth = op_widths_dict[cnames[i]]
        res += byte << bit_shift
        bit_shift += opwidth
    return res
