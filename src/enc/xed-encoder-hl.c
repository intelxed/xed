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
/// @file xed-encoder-hl.c

#include "xed-encoder-hl.h"
#include "xed-reg-class-enum.h"
#include "xed-reg-class.h"
#include "xed-operand-accessors.h"

/// convert a #xed_encoder_instruction_t to a #xed_encoder_request_t for encoding
xed_bool_t xed_convert_to_encoder_request(xed_encoder_request_t* out,
                                          xed_encoder_instruction_t* in) {

    /* this is basically what the encoder language example code does but in
     * a more uniform way. */
    xed_uint_t real_operands =  0;
    xed_uint_t i=0;
    xed_uint_t memops = 0;
    xed_uint_t regs = 0;
    xed_encoder_request_zero_set_mode(out, &(in->mode));
    xed_encoder_request_set_iclass(out, in->iclass );
    if (in->effective_operand_width)
        xed_encoder_request_set_effective_operand_width(out, in->effective_operand_width);
    if (in->effective_address_width)
        xed_encoder_request_set_effective_address_size(out, in->effective_address_width);


    for(; i< in->noperands ; i++ ) {
        xed_encoder_operand_t* op = in->operands + i;
        switch(op->type) {
          case XED_ENCODER_OPERAND_TYPE_PTR: 
            xed_encoder_request_set_branch_displacement(out,
                                                        op->u.brdisp,
                                                        op->width_bits/8); //FIXME: bits interface
            xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_PTR);
            xed_encoder_request_set_ptr(out);
            real_operands++;
            break;

          case XED_ENCODER_OPERAND_TYPE_BRDISP:
            xed_encoder_request_set_branch_displacement(out,
                                                        op->u.brdisp,
                                                        op->width_bits/8); //FIXME: bits interface
            xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_RELBR);
            xed_encoder_request_set_relbr(out);
            real_operands++;
            break;

          case XED_ENCODER_OPERAND_TYPE_SEG0:
            xed_encoder_request_set_seg0(out, op->u.reg);
            break;

          case XED_ENCODER_OPERAND_TYPE_SEG1:
            xed_encoder_request_set_seg1(out, op->u.reg);
            break;

          case XED_ENCODER_OPERAND_TYPE_REG: {
              xed_operand_enum_t r = XED_STATIC_CAST(xed_operand_enum_t,XED_OPERAND_REG0 + regs);
              xed_encoder_request_set_reg(out, r, op->u.reg);
              xed_encoder_request_set_operand_order(out, real_operands, r);
              real_operands++;
              regs++;
              break;
          }


          case XED_ENCODER_OPERAND_TYPE_IMM0:

            xed_encoder_request_set_uimm0_bits(out,
                                               op->u.imm0,
                                               op->width_bits);
            xed_encoder_request_set_operand_order(out, real_operands , XED_OPERAND_IMM0);
            real_operands++;
            break;

          case XED_ENCODER_OPERAND_TYPE_SIMM0:
            /* the max width of a signed immediate is 32b. */
            xed_encoder_request_set_simm(out,
                                         XED_STATIC_CAST(xed_int32_t,op->u.imm0),
                                         op->width_bits/8); //FIXME: bits interface
            xed_encoder_request_set_operand_order(out, real_operands , XED_OPERAND_IMM0);
            real_operands++;
            break;

          case XED_ENCODER_OPERAND_TYPE_IMM1:
            xed_encoder_request_set_uimm1(out, op->u.imm1);
            xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_IMM1);
            real_operands++;
            break;

          case XED_ENCODER_OPERAND_TYPE_OTHER:
            // this is used to set encode parameters for AVX512, like
            // zeroing, rounding or sae. It could be abused to set other
            // nonsensical things.
            xed3_set_generic_operand(out, op->u.s.operand_name,  op->u.s.value);
            break;

          case XED_ENCODER_OPERAND_TYPE_MEM: 
            {
                xed_reg_class_enum_t rc = xed_gpr_reg_class(op->u.mem.base);
                xed_reg_class_enum_t rci = xed_gpr_reg_class(op->u.mem.index);
                if (rc == XED_REG_CLASS_GPR32 || rci == XED_REG_CLASS_GPR32) 
                    xed_encoder_request_set_effective_address_size(out, 32);
                if (rc == XED_REG_CLASS_GPR16 || rci == XED_REG_CLASS_GPR16) 
                  xed_encoder_request_set_effective_address_size(out, 16);
            }
            
            if (in->iclass == XED_ICLASS_LEA) {
                xed_encoder_request_set_agen(out);
                xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_AGEN);
            }
            else if (memops == 0) {
                xed_encoder_request_set_mem0(out);
                xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_MEM0);
            }
            else {
                xed_encoder_request_set_mem1(out);
                xed_encoder_request_set_operand_order(out, real_operands, XED_OPERAND_MEM1);
            }
            real_operands++;

            if (memops == 0) {
                xed_encoder_request_set_base0(out, op->u.mem.base);
                xed_encoder_request_set_index(out, op->u.mem.index);
                xed_encoder_request_set_scale(out, op->u.mem.scale);
                xed_encoder_request_set_seg0(out, op->u.mem.seg);
            }
            else {
                xed_encoder_request_set_base1(out, op->u.mem.base);
                xed_encoder_request_set_seg1(out, op->u.mem.seg);
            }

            xed_encoder_request_set_memory_operand_length(out, op->width_bits>>3 ); // CVT TO BYTES --  FIXME make bits interface

            if (op->u.mem.disp.displacement_bits)
                xed_encoder_request_set_memory_displacement(out,
                                                            op->u.mem.disp.displacement,
                                                            op->u.mem.disp.displacement_bits/8); //FIXME: make bits interface

            memops++;
            break;
          case XED_ENCODER_OPERAND_TYPE_INVALID:
          default:
            return 0;
        }
    }
        
    return 1;
}

