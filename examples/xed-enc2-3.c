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

static xed_uint32_t test_push_reg(xed_uint8_t* output_buffer,
                                  xed_reg_enum_t reg)
{
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    xed_enc_push_r64(&request,reg);
    return xed_enc2_encoded_length(&request);
}
static xed_uint32_t test_push_reg_short(xed_uint8_t* output_buffer,
                                        xed_reg_enum_t reg)
{
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    xed_enc_push_r64_vr1(&request,reg);
    return xed_enc2_encoded_length(&request);
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

static void dump(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    for(i=0;i<len;i++) 
        printf("%02x ",buf[i]);
}

int main(int argc, char** argv) {
    xed_uint8_t output_buffer[XED_MAX_INSTRUCTION_BYTES];
    xed_uint32_t enclen;
    int retval=0, r=0,i=0;
    xed_reg_enum_t reg=XED_REG_INVALID;
               

    for(i=0;i<2;i++) {
        for (reg = XED_REG_RAX; reg<=XED_REG_R15; reg++) {
            if (i==0)
                enclen = test_push_reg_short(output_buffer,reg);
            else
                enclen = test_push_reg(output_buffer,reg);
            
            printf("Encoded: ");
            dump(output_buffer, enclen);
            printf("\n");
            r =  decode(output_buffer, enclen);
            retval += r;
            printf("decode returned %d\n\n",r);
        }
    }
    
    return retval;
    (void)argc; (void)argv;
}
