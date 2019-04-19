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
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h> //strcmp
#include <assert.h> 
#include "xed-encode-direct.h"

int main(int argc, char** argv);

static void dump_encoding(xed_enc2_req_t* r)
{
    xed_uint_t i;
    for(i=0;i<r->s.cursor;i++) {
        if (i>0)
            printf(" ");
        printf("%02X", r->s.itext[i]);
    }
    printf("\n");
}

int main(int argc, char** argv) {
    xed_enc2_req_t r;
    xed_tables_init();

    xed_enc2_req_t_init(&r);
    encode_mov16_reg_reg(&r, XED_REG_AX, XED_REG_SI);
    dump_encoding(&r);

    xed_enc2_req_t_init(&r);
    encode_mov32_reg_reg(&r, XED_REG_EAX, XED_REG_ECX);
    dump_encoding(&r);

    xed_enc2_req_t_init(&r);
    encode_mov64_reg_reg(&r, XED_REG_R10, XED_REG_RSI);
    dump_encoding(&r);

    xed_enc2_req_t_init(&r);
    encode_mov32_reg_mem_disp32_a32(&r, XED_REG_EAX, XED_REG_EBP, XED_REG_ESI, 4, 0x11223344);
    dump_encoding(&r);
    
    xed_enc2_req_t_init(&r);
    encode_mov32_reg_mem_disp8_a32(&r, XED_REG_EAX, XED_REG_EBP, XED_REG_ESI, 8, 0xFF);
    dump_encoding(&r);

    // this one requires the encoder to add a fake disp due to the sib encoding.
    xed_enc2_req_t_init(&r);
    encode_mov32_reg_mem_nodisp_a32(&r, XED_REG_EAX, XED_REG_EBP, XED_REG_ESI, 2);
    dump_encoding(&r);
    

    xed_enc2_req_t_init(&r);
    encode_mov64_reg_mem_nodisp_a64(&r, XED_REG_RAX, XED_REG_RBX, XED_REG_INVALID, 1);
    dump_encoding(&r);
    
    xed_enc2_req_t_init(&r);
    encode_mov64_reg_mem_disp8_a64(&r, XED_REG_RAX, XED_REG_RCX, XED_REG_RBX, 8, 0x55);
    dump_encoding(&r);
    
    xed_enc2_req_t_init(&r);
    encode_mov64_reg_mem_disp32_a64(&r, XED_REG_RAX, XED_REG_RIP, XED_REG_INVALID, 1, 0x11223344);
    dump_encoding(&r);

    return 0;
}
