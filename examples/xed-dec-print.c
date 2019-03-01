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
/// @file xed-dec-print.c
// decode and print

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>

int main(int argc, char** argv);

int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error;
    xed_decoded_inst_t xedd;
#define BUFLEN  1000
    char buffer[BUFLEN];
    xed_bool_t ok;
    xed_machine_mode_enum_t mmode;
    xed_address_width_enum_t stack_addr_width;

    // example instructions
    xed_uint_t   bytes = 2;
    xed_uint8_t  itext[XED_MAX_INSTRUCTION_BYTES] = { 0x00, 0x00 };

    xed_tables_init();
    
    mmode=XED_MACHINE_MODE_LEGACY_32;
    stack_addr_width =XED_ADDRESS_WIDTH_32b;
    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);
    xed_error = xed_decode(&xedd, itext,bytes);
    if (xed_error == XED_ERROR_NONE)
    {
        ok = xed_format_context(XED_SYNTAX_ATT, &xedd, buffer, BUFLEN, 0, 0, 0);
        if (ok) {
            printf("%s\n", buffer);
            return 0;
        }
        printf("Error disassembling\n");
        return 1;
    }
    printf("Decoding error\n");
    return 1;
    (void) argv; (void)argc;
}
