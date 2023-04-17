/* BEGIN_LEGAL 

Copyright (c) 2023 Intel Corporation

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

/// @file xed-ild-extension.h
/// instruction length decoder extension header

#if !defined(XED_ILD_EXTENSION_H)
# define XED_ILD_EXTENSION_H

#include "xed-decoded-inst.h"
#include "xed-operand-accessors.h"
#include "xed-ild-enum.h"

#define MAX_PREFIXES_EXT 5

#define XED_GRAMMAR_MODE_64 2
#define XED_GRAMMAR_MODE_32 1
#define XED_GRAMMAR_MODE_16 0

void xed_ild_ext_internal_scanner(xed_decoded_inst_t *d);
xed_bool_t xed_ild_ext_opcode_scanner_needed(xed_decoded_inst_t *d);
// EVEX
void xed_ild_ext_set_ubit(xed_decoded_inst_t *d, xed_uint8_t ubit);
xed_uint8_t xed_ild_ext_set_evex_map(xed_decoded_inst_t* d, xed_uint8_t map);
void xed_ild_ext_finalize_evex(xed_decoded_inst_t *d, xed_uint_t length);

static XED_INLINE xed_uint_t xed_ild_ext_mode_64b(xed_decoded_inst_t* d) 
{
    return (xed3_operand_get_mode(d) == XED_GRAMMAR_MODE_64);
}

static XED_INLINE void xed_ild_ext_too_short(xed_decoded_inst_t* d)
{
    xed3_operand_set_out_of_bytes(d, 1);
    if ( xed3_operand_get_max_bytes(d) >= XED_MAX_INSTRUCTION_BYTES)
        xed3_operand_set_error(d,XED_ERROR_INSTR_TOO_LONG);
    else
        xed3_operand_set_error(d,XED_ERROR_BUFFER_TOO_SHORT);
}

static XED_INLINE void xed_ild_ext_bad_map(xed_decoded_inst_t* d)
{
    xed3_operand_set_map(d,XED_ILD_MAP_INVALID);
    xed3_operand_set_error(d,XED_ERROR_BAD_MAP);
}

#endif

