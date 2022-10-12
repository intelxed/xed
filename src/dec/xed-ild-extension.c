/*BEGIN_LEGAL 

Copyright (c) 2022 Intel Corporation

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

xed_bool_t xed_ild_ext_handle_ubit_avx512(xed_decoded_inst_t *d)
{
    xed_bool_t ubit = xed3_operand_get_ubit(d);

    xed3_operand_set_vexvalid(d, 2);
    if (ubit==0)
        xed3_operand_set_error(d, XED_ERROR_BAD_EVEX_UBIT);

    return ubit;
}

void xed_ild_ext_set_legacy_map(xed_decoded_inst_t *d)
{
    xed3_operand_set_map(d, XED_ILD_LEGACY_MAP0);
}

xed_uint_t xed_ild_ext_init_internal_prefixes(xed_uint8_t* prefixes_ext)
{
    (void)prefixes_ext;
    return 0;
}

void xed_ild_ext_catch_invalid_rex_prefixes(xed_decoded_inst_t* d)
{
    // REX is not allowed before VEX or EVEX prefixes
    if (xed_ild_ext_mode_64b(d) && xed3_operand_get_rex(d))
            xed3_operand_set_error(d,XED_ERROR_BAD_REX_PREFIX);
}

xed_bool_t xed_ild_ext_internal_prefix_scanner(
    xed_decoded_inst_t* d, 
    xed_uint8_t* const nprefixes,
    xed_uint8_t* const inst_length, 
    xed_uint8_t rex)
{
    (void)d;
    (void)nprefixes;
    (void)inst_length;
    (void)rex;
    return 0;
}

void xed_ild_ext_catch_invalid_legacy_map(xed_decoded_inst_t* d)
{
    (void)d;
}
