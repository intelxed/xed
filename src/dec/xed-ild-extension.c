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

// set the UBIT value of a decoded instruction.
// Requires special care for APX instructions, since the UBIT is reinterpreted
// as the X4 bit in REX2 prefix
void xed_ild_ext_set_ubit(xed_decoded_inst_t *d, xed_uint8_t ubit)
{
#if defined(XED_APX)
    if (xed_ild_ext_apx_supported(d)) {
        // APX reinterprets the Ubit with memory fourth index EGPR bit.
        xed3_operand_set_rexx4(d, ~ubit & 1);
        xed3_operand_set_ubit(d, 1);  // Satisfies instruction pattern's UBIT condition
        return;
    }
#endif // XED_APX
    
    xed3_operand_set_ubit(d, ubit & 1);
}
