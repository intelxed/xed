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

// decoder example - cpuid-based defeaturing

#include "xed/xed-interface.h"
#include "xed-examples-util.h" // xed_atoi_hex()
#include <stdio.h>
#include <stdlib.h>
#include <string.h> //strcmp
#include <assert.h> 

int main(int argc, char** argv);

int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error = XED_ERROR_NONE;
    unsigned int first_argv = 1;
    unsigned int bytes = 0;
    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    xed_uint_t i=1;
    xed_uint_t u=0;
    xed_decoded_inst_t xedd;
    xed_machine_mode_enum_t mmode=XED_MACHINE_MODE_LEGACY_32;
    xed_address_width_enum_t stack_addr_width=XED_ADDRESS_WIDTH_32b;
    xed_chip_features_t features;
    xed_chip_enum_t chip = XED_CHIP_HASWELL;
    xed_uint_t uargc = (xed_uint_t)argc;
    xed_bool_t already_set_mode = 0;
    xed_bool_t bmi = 1;

    xed_tables_init();

    for( i=1 ; i < uargc ; i++ )
    {
        if (strcmp(argv[i], "-64") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            mmode=XED_MACHINE_MODE_LONG_64;
            stack_addr_width =XED_ADDRESS_WIDTH_64b;
            first_argv++;
        }
        else if (strcmp(argv[i], "-16") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            mmode=XED_MACHINE_MODE_LEGACY_16;
            stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        }

        else if (strcmp(argv[i], "-chip") == 0) {
            assert(i+1 < uargc);
            chip = str2xed_chip_enum_t(argv[i+1]);
            printf("Setting chip to %s\n", xed_chip_enum_t2str(chip));
            assert(chip != XED_CHIP_INVALID);
            first_argv+=2;
            i++;
        }
        else if (strcmp(argv[i], "-nobmi") == 0) {
            bmi = 0;
            first_argv++;
            i++;
        }
        else { // if not one of the thigns we're working on, break
            break; 
        }
            
    }

    for( i=first_argv ;i < uargc; i++)    {
        xed_uint8_t x = (xed_uint8_t)(xed_atoi_hex(argv[i]));
        assert(bytes < XED_MAX_INSTRUCTION_BYTES);
        itext[bytes++] = x;
    }
    if (bytes == 0)    {
        fprintf(stderr, "Must supply some hex bytes\n");
        exit(1);
    }

    printf("PARSING BYTES: ");
    for( u=0 ; u < bytes ; u++ )  {
        printf("%02x ", XED_STATIC_CAST(unsigned int,itext[u]));
    }
    printf("\n");

    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);
    xed_decoded_inst_set_input_chip(&xedd, chip);

    // Start with a HSW (default) and (conditionally) turn off BMI1 so that
    // TZCNT decodes as BSF
    xed_get_chip_features(&features, chip);
    if (bmi == 0)  {
        xed_modify_chip_features(&features, XED_ISA_SET_BMI1, 0);
    }
    
    xed_error = xed_decode_with_features(&xedd, 
                                         XED_REINTERPRET_CAST(const xed_uint8_t*,itext),
                                         bytes,
                                         &features);
    switch(xed_error)
    {
      case XED_ERROR_NONE: {
#define OBUFLEN 1024
          char outbuf[OBUFLEN];
          if (xed_format_context(XED_SYNTAX_INTEL, &xedd, outbuf, OBUFLEN, 0, 0, 0))  {
              printf("DISASM %s\n", outbuf);
          }
          else {
              fprintf(stderr,"DISASM printing error\n");
              exit(1);
          }

      }
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
        
    return 0;
}
