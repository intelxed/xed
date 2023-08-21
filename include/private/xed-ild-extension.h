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

#define XED_GRAMMAR_MODE_64 2
#define XED_GRAMMAR_MODE_32 1
#define XED_GRAMMAR_MODE_16 0

void xed_ild_ext_set_ubit(xed_decoded_inst_t *d, xed_uint8_t ubit);

static XED_INLINE xed_uint_t xed_ild_ext_mode_64b(xed_decoded_inst_t* d) 
{
    return (xed3_operand_get_mode(d) == XED_GRAMMAR_MODE_64);
}

#if defined(XED_APX)
static XED_INLINE xed_bool_t xed_ild_ext_apx_supported(xed_decoded_inst_t *d)
{
    return (!xed3_operand_get_no_apx(d) && xed_ild_ext_mode_64b(d));
}
#endif // XED_APX

#endif

