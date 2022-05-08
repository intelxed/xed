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
#include "xed-operand-accessors.h"
#include "xed-error-enum.h"

xed_bool_t xed_ild_extension_handle_ubit_avx512(xed_decoded_inst_t *d)
{
    xed_bool_t ubit = xed3_operand_get_ubit(d);

    // When not supporting KNC, we put KNC (EVEX.U=0)
    // stuff in vv=2(EVEX) and let the UBIT error tank it later.
    xed3_operand_set_vexvalid(d, 2);

    if (ubit==0)
        xed3_operand_set_error(d, XED_ERROR_BAD_EVEX_UBIT);

    return ubit;
}
