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

#include "xed/xed-interface.h"
#include "xed/xed-enc2-m64-a64.h"
#include <stdio.h>
#include <stdlib.h>

static xed_uint32_t test_add_lock_byte(xed_uint8_t* output_buffer)
{
    xed_reg_enum_t reg0;
    xed_reg_enum_t base;
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    reg0 = XED_REG_AH;
    base = XED_REG_RBX;
    xed_enc_add_lock_m8_r8_b_a64(&request,base,reg0);
    return xed_enc2_encoded_length(&request);
}
static xed_uint32_t test_0_xed_enc_lea_rm_q_bisd32_a64(xed_uint8_t* output_buffer)
{
    xed_enc2_req_t* r;
    xed_reg_enum_t reg0;
    xed_reg_enum_t base;
    xed_reg_enum_t index;
    xed_uint_t scale;
    xed_int32_t disp32;
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    r = &request;
    reg0 = XED_REG_R11;
    base = XED_REG_R12;
    index = XED_REG_R13;
    scale = 1;
    disp32 = 0x11223344;
    xed_enc_lea_r64_m_bisd32_a64(r /*req*/,reg0 /*gpr64*/,base /*gpr64*/,index /*gpr64*/,scale /*scale*/,disp32 /*int32*/);
    return xed_enc2_encoded_length(r);
}

xed_uint32_t test_0_xed_enc_vpblendvb_xxxx(xed_uint8_t* output_buffer)
{
    xed_enc2_req_t* r;
    xed_reg_enum_t reg0;
    xed_reg_enum_t reg1;
    xed_reg_enum_t reg2;
    xed_reg_enum_t reg3;
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    r = &request;
    reg0 = XED_REG_XMM6;
    reg1 = XED_REG_XMM7;
    reg2 = XED_REG_XMM8;
    reg3 = XED_REG_XMM9;
    xed_enc_vpblendvb_x_x_x_x_128(r /*req*/,reg0 /*xmm*/,reg1 /*xmm*/,reg2 /*xmm*/,reg3 /*xmm*/);
    return xed_enc2_encoded_length(r);
}

// The decoder drags in a lot of stuff to the final executable.
#define DECO

#if defined(DECO)
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

static int decode(xed_uint8_t* buf, xed_uint32_t len) {
    xed_decoded_inst_t xedd;
    xed_error_enum_t err;
    xed_state_t dstate;
    static int first = 1;
    if (first) {
        xed_tables_init();
        first = 0;
    }
    xed_state_zero(&dstate);
    dstate.mmode=XED_MACHINE_MODE_LONG_64;

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    err = xed_decode(&xedd, buf, len);
    if (err == XED_ERROR_NONE) {
        disassemble(&xedd);
        return 0;
    }
    printf("ERROR: %s\n", xed_error_enum_t2str(err));
    return 1;
}
#endif

static void dump(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    for(i=0;i<len;i++) 
        printf("%02x ",buf[i]);
}

int main(int argc, char** argv) {
    xed_uint8_t output_buffer[XED_MAX_INSTRUCTION_BYTES];
    xed_uint32_t enclen;
    int retval=0, r=0;

    // encode an LEA instruction
    enclen = test_0_xed_enc_lea_rm_q_bisd32_a64(output_buffer);
    printf("Encoded: ");
    dump(output_buffer, enclen);
    printf("\n");
#if defined(DECO)
    r =  decode(output_buffer, enclen);
    retval += r;
    printf("decode returned %d\n",r);
#endif
    
    // encode an VPBLENDVB instruction with 4 xmm regs
    enclen = test_0_xed_enc_vpblendvb_xxxx(output_buffer);
    printf("Encoded: ");
    dump(output_buffer, enclen);
    printf("\n");
#if defined(DECO)
    r = decode(output_buffer, enclen);
    retval += r;
    printf("decode returned %d\n",r);
#endif

    
    enclen = test_add_lock_byte(output_buffer);
    printf("Encoded: ");
    dump(output_buffer, enclen);
    printf("\n");
#if defined(DECO)
    r = decode(output_buffer, enclen);
    retval += r;
    printf("decode returned %d\n",r);
#endif
    
    return retval;
    (void)argc; (void)argv;
}
