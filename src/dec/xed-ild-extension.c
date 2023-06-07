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
/// @file xed-ild-extension.c
/// instruction length decoder extension

#include "xed-ild-extension.h"
#include "xed-error-enum.h"
#include "xed-ild-enum.h"

void xed_ild_ext_internal_scanner(xed_decoded_inst_t *d)
{
    (void)d;
}

xed_bool_t xed_ild_ext_opcode_scanner_needed(xed_decoded_inst_t *d)
{
    xed_bool_t yes = !xed3_operand_get_error(d);
#if defined(XED_AVX)
    return (yes && !xed3_operand_get_vexvalid(d));
#else
    return yes;
#endif
}

void xed_ild_ext_set_ubit(xed_decoded_inst_t *d, xed_uint8_t ubit)
{
    xed3_operand_set_ubit(d, ubit & 1);
    xed3_operand_set_vexvalid(d, 2);
    
    if (ubit==0)
        xed3_operand_set_error(d, XED_ERROR_BAD_EVEX_UBIT);
}

xed_uint8_t xed_ild_ext_set_evex_map(xed_decoded_inst_t* d, xed_uint8_t map)
{
    xed3_operand_set_map(d, map);
    return map;
}

void xed_ild_ext_finalize_evex(xed_decoded_inst_t *d, xed_uint_t length)
{
    (void)d;
    (void)length;
}

void xed_ild_ext_finalize(xed_decoded_inst_t *d)
{
    (void)d;
}
