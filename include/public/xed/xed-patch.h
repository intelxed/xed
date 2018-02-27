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
#ifndef XED_PATCH_H
# define XED_PATCH_H
#include "xed-encoder-hl.h"

/// @name Patching decoded instructions
//@{


/// Replace a memory displacement.
/// The widths of original displacement and replacement must match.
/// @param xedd A decoded instruction.
/// @param itext The corresponding encoder output, byte array.
/// @param disp  A xed_enc_displacement_t object describing the new displacement.
/// @returns xed_bool_t  1=success, 0=failure
/// @ingroup ENCHLPATCH
XED_DLL_EXPORT xed_bool_t
xed_patch_disp(xed_decoded_inst_t* xedd,
               xed_uint8_t* itext,
               xed_enc_displacement_t disp);

/// Replace a branch displacement.
/// The widths of original displacement and replacement must match.
/// @param xedd A decoded instruction.
/// @param itext The corresponding encoder output, byte array.
/// @param disp  A xed_encoder_operand_t object describing the new displacement.
/// @returns xed_bool_t  1=success, 0=failure
/// @ingroup ENCHLPATCH
XED_DLL_EXPORT xed_bool_t
xed_patch_relbr(xed_decoded_inst_t* xedd,
                xed_uint8_t* itext,
                xed_encoder_operand_t disp);

/// Replace an imm0 immediate value.
/// The widths of original immediate and replacement must match.
/// @param xedd A decoded instruction.
/// @param itext The corresponding encoder output, byte array.
/// @param imm0  A xed_encoder_operand_t object describing the new immediate.
/// @returns xed_bool_t  1=success, 0=failure
/// @ingroup ENCHLPATCH
XED_DLL_EXPORT xed_bool_t
xed_patch_imm0(xed_decoded_inst_t* xedd,
               xed_uint8_t* itext,
               xed_encoder_operand_t imm0);

//@}
#endif
