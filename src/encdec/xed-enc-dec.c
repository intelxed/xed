/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
  
END_LEGAL */
/// @file xed-encode.c

////////////////////////////////////////////////////////////////////////////
// This file contains the public interface to the encoder. 
////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-encode-private.h"
#include "xed-operand-accessors.h"

void  xed_encoder_request_init_from_decode(xed_decoded_inst_t* d) {
    // copy the non-suppressed operands to the encode order array
    const xed_inst_t* inst = d->_inst;
    const xed_uint_t noperands = xed_inst_noperands(inst);
    xed_uint_t i, eops=0;
    for( i=0;i<noperands;i++) {
        const xed_operand_t* o = xed_inst_operand(inst,i);
        const xed_operand_visibility_enum_t vis = xed_operand_operand_visibility(o);
        if (vis != XED_OPVIS_SUPPRESSED) {
            xed_assert(eops < XED_ENCODE_ORDER_MAX_OPERANDS);
            d->_operand_order[eops++] = xed_operand_name(o);
        }
    }
    d->_n_operand_order=eops;

    // the decoder does not set the iclass field
    xed3_operand_set_iclass(d,xed_decoded_inst_get_iclass(d));

    if (xed3_operand_get_mem0(d))
        xed_decoded_inst_cache_memory_operand_length(d);
    
    
    xed3_operand_set_rex(d,0);
    xed3_operand_set_rexb(d,0);
    xed3_operand_set_rexr(d,0);
    xed3_operand_set_rexw(d,0);
    xed3_operand_set_rexx(d,0);
    xed3_operand_set_norex(d,0);
    xed3_operand_set_needrex(d,0);
    xed3_operand_set_osz(d,0);
}
