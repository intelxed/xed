/* BEGIN_LEGAL 

Copyright (c) 2025 Intel Corporation

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

/// @file xed-enc2.c
/// @brief Showcases the use of ENC2 encode APIs

#include "xed/xed-interface.h"
#include "xed/xed-enc2-m64-a64.h"
#include <stdio.h>
#include <stdlib.h>

static xed_uint32_t test_0_xed_enc_add_lock_m8_r8_b_a64(xed_uint8_t* output_buffer, xed_decoded_inst_t* xedd)
{
   xed_enc2_req_t* r;
   xed_reg_enum_t base;
   xed_reg_enum_t reg0;
   xed_enc2_req_t request;
   xed_uint32_t enc2_len;
   xed_error_enum_t err;
   xed_enc2_req_t_init(&request, output_buffer);
   r = &request;
   base = XED_REG_RDX;
   reg0 = XED_REG_AL;
   xed_enc_add_lock_m8_r8_b_a64(r /*req*/,base /*gpr64*/,reg0 /*gpr8*/);
   enc2_len = xed_enc2_encoded_length(r);
   if (enc2_len == 0)
     return 0;
   err = xed_decode(xedd, output_buffer, enc2_len);
   if (err != XED_ERROR_NONE)
     return 0;
   xed_bool_t conditions_satisfied = (xed3_operand_get_base0(xedd) == XED_REG_RDX) &&
    (xed3_operand_get_reg0(xedd) == XED_REG_AL);
   if (conditions_satisfied == 0)
      return 0;
   return enc2_len;
}


static xed_uint32_t test_0_xed_enc_lea_r64_m_bisd32_a64(xed_uint8_t* output_buffer, xed_decoded_inst_t* xedd)
{
   xed_enc2_req_t* r;
   xed_reg_enum_t reg0;
   xed_reg_enum_t base;
   xed_reg_enum_t index;
   xed_uint_t scale;
   xed_int32_t disp32;
   xed_enc2_req_t request;
   xed_uint32_t enc2_len;
   xed_error_enum_t err;
   xed_enc2_req_t_init(&request, output_buffer);
   r = &request;
   reg0 = XED_REG_R10;
   base = XED_REG_R11;
   index = XED_REG_R15;
   scale = 2;
   disp32 = 0xAABBCCDD;
   xed_enc_lea_r64_m_bisd32_a64(r /*req*/,reg0 /*gpr64*/,base /*gpr64*/,index /*gpr64_index*/,scale /*scale*/,disp32 /*int32*/);
   enc2_len = xed_enc2_encoded_length(r);
   if (enc2_len == 0)
     return 0;
   err = xed_decode(xedd, output_buffer, enc2_len);
   if (err != XED_ERROR_NONE)
     return 0;
   xed_bool_t conditions_satisfied = (xed3_operand_get_reg0(xedd) == XED_REG_R10) &&
    (xed3_operand_get_base0(xedd) == XED_REG_R11) &&
    (xed3_operand_get_index(xedd) == XED_REG_R15) &&
    (xed3_operand_get_scale(xedd) == 2) &&
    (xed_operand_values_get_memory_displacement_int64(xedd) == -1430532899);
   if (conditions_satisfied == 0)
      return 0;
   return enc2_len;
}

static xed_uint32_t test_0_xed_enc_vpblendvb_x_x_x_x_128_md32(xed_uint8_t* output_buffer, xed_decoded_inst_t* xedd)
{
   xed_enc2_req_t* r;
   xed_reg_enum_t reg0;
   xed_reg_enum_t reg1;
   xed_reg_enum_t reg2;
   xed_reg_enum_t reg3;
   xed_enc2_req_t request;
   xed_uint32_t enc2_len;
   xed_error_enum_t err;
   xed_enc2_req_t_init(&request, output_buffer);
   r = &request;
   reg0 = XED_REG_XMM2;
   reg1 = XED_REG_XMM3;
   reg2 = XED_REG_XMM4;
   reg3 = XED_REG_XMM5;
   xed_enc_vpblendvb_x_x_x_x_128(r /*req*/,reg0 /*xmm*/,reg1 /*xmm*/,reg2 /*xmm*/,reg3 /*xmm*/);
   enc2_len = xed_enc2_encoded_length(r);
   if (enc2_len == 0)
     return 0;
   err = xed_decode(xedd, output_buffer, enc2_len);
   if (err != XED_ERROR_NONE)
     return 0;
   xed_bool_t conditions_satisfied = (xed3_operand_get_reg0(xedd) == XED_REG_XMM2) &&
    (xed3_operand_get_reg1(xedd) == XED_REG_XMM3) &&
    (xed3_operand_get_reg2(xedd) == XED_REG_XMM4) &&
    (xed3_operand_get_reg3(xedd) == XED_REG_XMM5);
   if (conditions_satisfied == 0)
      return 0;
   return enc2_len;
}

static void dump(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    for(i=0;i<len;i++) 
        printf("%02x ",buf[i]);
}

static void disassemble(xed_decoded_inst_t* xedd)
{
    xed_bool_t ok;
    xed_print_info_t pi;
#define XBUFLEN 200
    char buf[XBUFLEN];
    
    xed_init_print_info(&pi);
    pi.p = xedd;
    pi.blen = XBUFLEN;
    pi.buf = buf;
    pi.buf[0]=0; //allow use of strcat
    
    ok = xed_format_generic(&pi);
    if (ok) 
        printf("Disassembly: %s\n", buf);
    else
        printf("Disassembly: %%ERROR%%\n");
}

void my_error_handler(const char* fmt, va_list args) {
    printf("LOCAL HANDLER FOR XED ENC2 ERROR: ");
    vprintf(fmt, args);
    printf(".\n");
    exit(1); 
}

int main(int argc, char** argv) {
    xed_uint8_t output_buffer[XED_MAX_INSTRUCTION_BYTES];
    xed_uint32_t enclen;
    xed_state_t dstate;
    xed_decoded_inst_t xedd;

    xed_tables_init();

    xed_state_zero(&dstate);
    dstate.mmode=XED_MACHINE_MODE_LONG_64;
    xed_decoded_inst_zero_set_mode(&xedd, &dstate);

    xed_enc2_set_error_handler(my_error_handler);
    // uncomment this line to disable runtime checking
    //xed_enc2_set_check_args(0);

    // encode an ADD LOCK instruction
    enclen = test_0_xed_enc_add_lock_m8_r8_b_a64(output_buffer, &xedd);
    if (enclen == 0){
        printf("Could not encode then decode ADD LOCK instruction\n");
    }
    else{
        printf("Encoded ADD LOCK instruction: ");
        dump(output_buffer, enclen);
        printf("\n");
        disassemble(&xedd);
    }

    // encode an LEA instruction
    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    enclen = test_0_xed_enc_lea_r64_m_bisd32_a64(output_buffer, &xedd);
    if (enclen == 0){
        printf("Could not encode then decode LEA instruction\n");
    }
    else{
        printf("Encoded LEA instruction: ");
        dump(output_buffer, enclen);
        printf("\n");
        disassemble(&xedd);
    }

    // encode a VPBLENDVB instruction with 4 XMMs
    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    enclen = test_0_xed_enc_vpblendvb_x_x_x_x_128_md32(output_buffer, &xedd);
    if (enclen == 0){
        printf("Could not encode then decode VPBLENDVB instruction\n");
    }
    else{
        printf("Encoded VPBLENDVB instruction: ");
        dump(output_buffer, enclen);
        printf("\n");
        disassemble(&xedd);
    }
    (void)argc; (void)argv;
    return 0;
}
