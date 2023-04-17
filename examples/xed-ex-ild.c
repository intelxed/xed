/* BEGIN_LEGAL 

Copyright (c) 2023 Intel Corporation

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
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include "xed/xed-interface.h"

#define HEX_BUFLEN 200
#define MAX_INPUT_NIBBLES (XED_MAX_INSTRUCTION_BYTES*2)


static xed_uint8_t letter_cvt(char a, char base) {
    return (a-base);
}

xed_uint8_t
convert_ascii_nibble(char c)
{
  if (c >= '0' && c <= '9') {
      return letter_cvt(c,'0');
  }
  else if (c >= 'a' && c <= 'f') {
      return (xed_uint8_t)(letter_cvt(c,'a') + 10U);
  }
  else if (c >= 'A' && c <= 'F') {
      return (xed_uint8_t)(letter_cvt(c,'A') + 10U);
  }
  else {
      printf("[XED CLIENT ERROR] Invalid character in hex string: %c\n", c);
      exit(1);
  }
}

xed_uint8_t convert_ascii_nibbles(char c1, char c2) {
    xed_uint8_t a = (xed_uint8_t)(convert_ascii_nibble(c1) * 16 + convert_ascii_nibble(c2));
    return a;
}

unsigned int
convert_ascii_to_hex(const char* src, xed_uint8_t* dst, 
                         unsigned int max_bytes)
{
    unsigned int j;
    unsigned int p = 0;
    unsigned int i = 0;

    const unsigned int len = XED_STATIC_CAST(unsigned int,strlen(src));
    if ((len & 1) != 0) {
        printf("test string was not an even number of nibbles");
        exit(1);
    }
    
    if (len > (max_bytes * 2) ) {
        printf("test string was too long");
        exit(1);
    }

    for(j=0; j<max_bytes; j++) 
        dst[j] = 0;

    for(;i<len/2;i++) {
        dst[i] = convert_ascii_nibbles(src[p], src[p+1]);
        p=p+2;
    }
    return i;
}


int main(int argc, char** argv)
{
    xed_bool_t long_mode = 1;
    xed_decoded_inst_t xedd;
    xed_state_t dstate;
    xed_uint_t i, j, bytes, input_nibbles=0;
    xed_error_enum_t xed_error;
    xed_uint8_t itext[XED_MAX_INSTRUCTION_BYTES];
    char src[MAX_INPUT_NIBBLES+1];
    xed_uint_t first_argv = 1;
    xed_uint_t uargc = (xed_uint_t)argc;

    if (first_argv >= uargc) {
        printf("Need some hex instruction nibbles");
        exit(1);
    }
    
    for(i=first_argv;i<uargc;i++) { 
        for(j=0; argv[i][j]; j++) {
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

    bytes = convert_ascii_to_hex(src, itext, XED_MAX_INSTRUCTION_BYTES);
                            
    printf("Attempting to decode: ");
    for(i=0;i<bytes;i++) {
        printf("%02x", itext[i]);
    }
    printf("\n");

    xed_tables_init(); // one time per process
    xed_state_zero(&dstate);

    if (long_mode) 
        dstate.mmode=XED_MACHINE_MODE_LONG_64;
    else 
        dstate.mmode=XED_MACHINE_MODE_LEGACY_32;

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    xed_error = xed_ild_decode(&xedd, itext, bytes);

    switch(xed_error) {
        case XED_ERROR_NONE:
            break;
        case XED_ERROR_BUFFER_TOO_SHORT:
            printf("Not enough bytes provided\n");
            return 1;
        case XED_ERROR_GENERAL_ERROR:
            printf("Could not decode given input.\n");
            return 1;
        default:
            printf("Unhandled error code %s\n",xed_error_enum_t2str(xed_error));
            return 1;
    }

    printf("length = %u\n",xed_decoded_inst_get_length(&xedd));
    
    return 0;
}
