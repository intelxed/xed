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

"""
Build a bit vector based on the operand names
"""
################################################################################
import genutil

def build_operand_bitvector(operand_names):
    """Build a bit vector in C of the operand names. Return the lines
    of the typedef.  Also return a dictionary of the operand names,
    and the bit positions & masks to be used for building up the
    initialization."""
    lines = []
    dct = {}
    chunk_size = 32
    #n_elements = (len(operand_names)+(chunk_size-1)) / chunk_size
    n_elements = 4
    lines.append("typedef union {")
    lines.append("   xed_uint%d_t i[%d];" % (chunk_size,n_elements)) # must be first
    lines.append("   struct {")
    for i,n in enumerate(operand_names):
        # figure out which chunk_size chunk it is in, and what offset in that chunk
        dct[n] = ( "XED_OPERAND_%s" % (n), i, i/chunk_size, i % chunk_size, 1<<(i%chunk_size) )
        cmt = "%02d:%02d" % (i/chunk_size,i%chunk_size)
        s = "     xed_uint%d_t  x_%s : 1; /* %s */" % (chunk_size,n,cmt)
        lines.append(s)
    #nelem = (i+chunk_size-1)/chunk_size
    nelem = 4
    lines.append("   } s;")
    lines.append("} xed_operand_bitvec_t;")
    return (lines, dct, nelem)

def build_init(operand_names, dct, nelem):
    """Given a list of operand names and a dictionary built by
    build_operand_bitvector, return an data initialization string"""
    values = [0] * nelem
    for o in operand_names:
        try:
            (xed_operand, biti, chunki, pos_in_chunk, mask) = dct[o]
        except:
            genutil.die("Could not find %s in operand names" % (o))
        values[chunki] |= mask
    t = []
    for v in values:
        t.append("%s" %(hex(v)))
    s = "XED_BIT_PAIR( %s )" % ",".join(t)
    return s
        
