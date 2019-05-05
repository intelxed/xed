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
#include "xed-encode-private.h"
#include "xed-operand-accessors.h"
#include "xed-reg-class.h"
#include "xed-encode-direct.h"

#include "enc2-m64-a64/hdr/xed-enc2-m64-a64.h"
#include <stdio.h>

extern xed_uint32_t (*test_functions_m64_a64)(xed_uint8_t* output_buffer)[];

typedef  xed_uint32_t (*test_function_t)(xed_uint8_t* output_buffer);

void test_m64_a64(void) {
    xed_uint32_t tests=0;
    xed_uint32_t errors = 0;
    test_function_t** p = test_functions_m64_a64;
    xed_uint8_t output_buffer[2*XED_MAX_INSTRUCTION_BYTES];
    xed_state_t dstate;

    xed_state_zero(&dstate);
    dstate.mmode=XED_MACHINE_MODE_LONG_64;
    //dstate.mmode=XED_MACHINE_MODE_LEGACY_32;
    //dstate.mmode=XED_MACHINE_MODE_LEGACY_16;
    //dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
    //dstate.stack_addr_width=XED_ADDRESS_WIDTH_32b;
    
    while(p) {
        xed_decoded_inst_t xedd;
        xed_uint32_t enclen;
        xed_error_enum_t err;
        
        printf("Calling test function %d\n",i);
        enclen = (*p)(output_buffer);

        // This stuff should problably move in to the individual tests so
        // that we can do more validation about the iclass and operands.
        
        if (enclen > XED_MAX_INSTRUCTION_BYTES) {
            printf("\t ERROR: %s\n", "ENCODE TOO LONG")
            errors++;
        }
            
        xed_decoded_inst_zero_set_mode(&xedd, &dstate);
        err = xed_decode(xedd, output_buffer, enclen);
        if (err != XED_ERROR_NONE) {
            printf("\t ERROR: %s\n",xed_error_enum_t2str(err));
            errors++;
        }
        p++;
        tests++;
    }

    printf("Tests:  %6d\n", tests);
    printf("Errors: %6d\n", errors);
}

int main(int argc, char** argv) {
    xed_tables_init();

    test_m64_a64();
    return 0;
}
