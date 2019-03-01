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
/// @file xed-ex7.c

// decoder  example - printing register operands

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h> //strcmp
#include <assert.h> 

int main(int argc, char** argv);

void print_operands(xed_decoded_inst_t* xedd) {
    unsigned int i = 0;
    xed_inst_t const* const xi = xed_decoded_inst_inst(xedd);
    const unsigned int noperands = xed_inst_noperands(xi);

    for( i=0; i < noperands ; i++) { 
        xed_operand_t const* op = xed_inst_operand(xi,i);
        xed_operand_enum_t op_name = xed_operand_name(op);
        if (xed_operand_is_register(op_name)) {
            xed_reg_enum_t reg = xed_decoded_inst_get_reg(xedd,op_name);
            xed_operand_action_enum_t rw = xed_decoded_inst_operand_action(xedd,i);
            printf("%2d: %5s %5s\n", 
                   (int)i,
                   xed_reg_enum_t2str(reg),
                   xed_operand_action_enum_t2str(rw));
        }
    }
}


int 
main(int argc, char** argv) {
    xed_error_enum_t xed_error;
    xed_bool_t long_mode = 0;
    xed_bool_t prot16 = 0;
    unsigned int first_argv;
    unsigned int bytes = 0;
    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    unsigned int i;
    unsigned int argcu = (unsigned int) argc;
    unsigned int u;
    xed_decoded_inst_t xedd;
    xed_machine_mode_enum_t mmode;
    xed_address_width_enum_t stack_addr_width;

    xed_tables_init();
    xed_set_verbosity( 99 );

    if (argcu > 2 && strcmp(argv[1], "-64") == 0) 
        long_mode = 1;
    else if (argcu > 2 && strcmp(argv[1], "-16") == 0) 
        prot16 = 1;

    if (long_mode) {
        first_argv = 2;
        mmode=XED_MACHINE_MODE_LONG_64;
        stack_addr_width =XED_ADDRESS_WIDTH_64b;
    }
    else if (prot16) {
        first_argv = 2;
        mmode=XED_MACHINE_MODE_LEGACY_16;
        stack_addr_width =XED_ADDRESS_WIDTH_16b;
    }
    else {
        first_argv=1;
        mmode=XED_MACHINE_MODE_LEGACY_32;
        stack_addr_width =XED_ADDRESS_WIDTH_32b;
    }

    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);

    for( i=first_argv ;i < argcu; i++)    {
        if (strlen(argv[i]) != 2) {
            fprintf(stderr, "not two hex characters: \"%s\"\n", argv[i]);
            exit(1);
        }
        xed_uint8_t x = (xed_uint8_t)(xed_atoi_hex(argv[i]));
        assert(bytes < XED_MAX_INSTRUCTION_BYTES);
        itext[bytes++] = x;
    }
    if (bytes == 0)    {
        fprintf(stderr, "Must supply some hex bytes, e.g., 48 89 C0\n");
        exit(1);
    }

    printf("PARSING BYTES: ");
    for( u=0;u<bytes; u++) 
        printf("%02x ", XED_STATIC_CAST(unsigned int,itext[u]));
    printf("\n");

    xed_error = xed_decode(&xedd, 
                           XED_REINTERPRET_CAST(const xed_uint8_t*,itext),
                           bytes);
    switch(xed_error)
    {
      case XED_ERROR_NONE:
        break;
      case XED_ERROR_BUFFER_TOO_SHORT:
        fprintf(stderr,"Not enough bytes provided\n");
        exit(1);
      case XED_ERROR_GENERAL_ERROR:
        fprintf(stderr,"Could not decode given input.\n");
        exit(1);
      default:
        fprintf(stderr,"Unhandled error code %s\n", 
                xed_error_enum_t2str(xed_error));
        exit(1);
    }
        

    print_operands(&xedd);


    return 0;
}
