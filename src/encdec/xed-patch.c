/*BEGIN_LEGAL 

Copyright (c) 2019 Intel Corporation

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

#include "xed-internal-header.h"
#include "xed-encoder-hl.h"
#include "xed-patch.h"

xed_bool_t
xed_patch_disp(xed_decoded_inst_t* xedd,
               xed_uint8_t* itext,
               xed_enc_displacement_t disp)
{
    xed_uint_t disp_width = xed3_operand_get_disp_width(xedd);
    xed_uint_t disp_pos   = xed3_operand_get_pos_disp(xedd);
    xed_uint_t i;

    if (disp_pos == 0)
        return 0;
    if (disp_width != disp.displacement_bits)
        return 0;
    for (i=0;i<disp_width/8;i++) 
        itext[disp_pos+i] = (disp.displacement >> (i*8)) & 0xff;
    return 1;
}


xed_bool_t
xed_patch_relbr(xed_decoded_inst_t* xedd,
                xed_uint8_t* itext,
                xed_encoder_operand_t disp)
{
    xed_uint_t disp_width = xed3_operand_get_disp_width(xedd);
    xed_uint_t disp_pos   = xed3_operand_get_pos_disp(xedd);
    xed_uint_t i;

    if (disp_pos == 0)
        return 0;
    if (disp_width != disp.width_bits)
        return 0;
    for (i=0;i<disp_width/8;i++) 
        itext[disp_pos+i] = (disp.u.brdisp >> (i*8)) & 0xff;
    return 1;
}

xed_bool_t
xed_patch_imm0(xed_decoded_inst_t* xedd,
               xed_uint8_t* itext,
               xed_encoder_operand_t imm0)
{
    xed_uint_t imm_width = xed3_operand_get_imm_width(xedd);
    xed_uint_t imm_pos   = xed3_operand_get_pos_imm(xedd);
    xed_uint_t i;

    if (imm_pos == 0)
        return 0;
    if (imm_width != imm0.width_bits)
        return 0;
    for (i=0;i<imm_width/8;i++) 
        itext[imm_pos+i] = (imm0.u.imm0 >> (i*8)) & 0xff;
    return 1;
}



