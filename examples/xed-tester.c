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
/// @file xed-tester.c

#include "xed/xed-interface.h"
#include <stdio.h>

int main(int argc, char** argv);

typedef struct
{
    unsigned int len;
    unsigned char itext[15];
} xed_test_t;

xed_test_t tests[] = {
    { 2, { 0, 0 } },
    { 2, { 2, 0 } },
    { 2, { 0xF3, 0x90 } },
    { 0 }
};

int main(int argc, char** argv) {
    unsigned int i,j;
    xed_state_t dstate;
    xed_tables_init();
    xed_state_zero(&dstate);
    xed_state_init(&dstate,
                   XED_MACHINE_MODE_LEGACY_32, 
                   XED_ADDRESS_WIDTH_32b, 
                   XED_ADDRESS_WIDTH_32b);
    for (  i=0; tests[i].len ; i++) {
        xed_bool_t okay;
        xed_error_enum_t xed_error;
        xed_decoded_inst_t xedd;
        xed_decoded_inst_zero_set_mode(&xedd, &dstate);
        printf("Testing: ");
        for( j=0; j< tests[i].len; j++) 
            printf("%02x ",XED_STATIC_CAST(unsigned int,tests[i].itext[j]));
        printf("\n");

        xed_error = xed_decode(&xedd, 
                               XED_REINTERPRET_CAST(xed_uint8_t*,tests[i].itext),
                               tests[i].len);
        
        okay = (xed_error == XED_ERROR_NONE);
        if (okay) {
            printf("OK\n");
        }
    }
    (void) argc; (void) argv; //pacify compiler
    return 0;
}
