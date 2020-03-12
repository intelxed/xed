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


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "xed-examples-util.h"

int main(int argc, char** argv);

#include "xed/xed-interface.h"

#define BUFLEN  1024
#define XDPRINT(x)     printf("%23s = %d\n", #x , i-> x );
#define XXPRINT(x)     printf("%23s = 0x%x\n", #x ,i-> x )
void print_ild(xed_decoded_inst_t* p) {

    char buf[BUFLEN];
    xed_chip_enum_t chip = xed_decoded_inst_get_input_chip(p);
    xed_decoded_inst_dump(p, buf,  BUFLEN);
    printf("%23s = %s\n", "chip",
           xed_chip_enum_t2str(chip));
}

#define MAX_INPUT_NIBBLES (XED_MAX_INSTRUCTION_BYTES*2)

int main(int argc, char** argv) {
    xed_decoded_inst_t ild;
    xed_uint_t uargc = (xed_uint_t)argc;
    xed_uint_t length = 0;
    xed_uint_t dlen = 0;    
    xed_uint_t i,j,input_nibbles=0;
    xed_uint8_t itext[XED_MAX_INSTRUCTION_BYTES];
    char src[MAX_INPUT_NIBBLES+1];
    xed_state_t dstate;
    xed_decoded_inst_t xedd;
    xed_uint_t first_argv;
    xed_uint_t bytes;
    xed_error_enum_t xed_error;
    xed_chip_enum_t chip = XED_CHIP_INVALID;
    int already_set_mode = 0;
    
    // initialize the XED tables -- one time.
    xed_tables_init();

    xed_state_zero(&dstate);

    first_argv = 1;
    dstate.mmode=XED_MACHINE_MODE_LEGACY_32;
    dstate.stack_addr_width=XED_ADDRESS_WIDTH_32b;

    for(i=1;i< uargc;i++) {
        if (strcmp(argv[i], "-64") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LONG_64;
            first_argv++;
        }
        else if (strcmp(argv[i], "-16") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LEGACY_16;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        }
        else if (strcmp(argv[i], "-s16") == 0) {
            already_set_mode = 1;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        }
        else if (strcmp(argv[i], "-chip") == 0) {
            assert(i+1 < uargc);
            chip = str2xed_chip_enum_t(argv[i+1]);
            printf("Setting chip to %s\n", xed_chip_enum_t2str(chip));
            assert(chip != XED_CHIP_INVALID);
            first_argv+=2;
        }

    }

    assert(first_argv < uargc);

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);

    if (first_argv >= uargc) {
      printf("Need some hex instruction nibbles");
      exit(1);
    }
    
    for(i=first_argv;i<uargc;i++) { 
      for(j=0;argv[i][j];j++) {
        assert(input_nibbles < MAX_INPUT_NIBBLES);
        src[input_nibbles] = argv[i][j];
        input_nibbles++;
      }
    }
    src[input_nibbles] = 0;
    if (input_nibbles & 1) {
      printf("Need an even number of nibbles");
      exit(1);
    }

    bytes = xed_convert_ascii_to_hex(src, itext, XED_MAX_INSTRUCTION_BYTES);
                            
    printf("Attempting to decode: ");
    for(i=0;i<bytes;i++) {
      printf("%02x", itext[i]);
    }
    printf("\n");

    xed_decoded_inst_zero_set_mode(&ild, &dstate);
    xed_decoded_inst_set_input_chip(&ild, chip);
    xed_decode(&ild, itext, XED_MAX_INSTRUCTION_BYTES);
    length = xed_decoded_inst_get_length(&ild);

    print_ild(&ild);
    printf("ILD length = %u\n",length);


    xed_decoded_inst_set_input_chip(&xedd, chip);
    xed_error = xed_decode(&xedd, 
                           XED_REINTERPRET_CAST(const xed_uint8_t*,itext), 
                           bytes);

    switch(xed_error)    {
      case XED_ERROR_NONE:
        break;
      case XED_ERROR_BUFFER_TOO_SHORT:
        printf("Not enough bytes provided\n");
        exit(1);
      case XED_ERROR_INVALID_FOR_CHIP:
        printf("The instruction was not valid for the specified chip.\n");
        exit(1);
      case XED_ERROR_GENERAL_ERROR:
        printf("Could not decode given input.\n");
        exit(1);
      default:
        printf("Unhandled error code %s\n",xed_error_enum_t2str(xed_error));
        exit(1);
    }
        
    dlen =  xed_decoded_inst_get_length(&xedd);
    printf ("Traditional length =  %u\n", dlen);
    if (dlen != length) {
      printf ("Length error\n");
      exit(1);
    }
    printf ("Length matched\n");
    return 0;
}

