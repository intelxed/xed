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
/// @file xed-ex4.c
// decoder example. This is the "C" version of xed-ex2.cpp (which is C++).

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h> //strcmp, memset
#include <assert.h> 

int main(int argc, char** argv);

int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error;

    xed_bool_t long_mode = 0;
    unsigned int bytes = 0;
    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    int i;
    unsigned int u;
    xed_decoded_inst_t xedd;
#define BUFLEN  1000
    char buffer[BUFLEN];
    xed_bool_t ok;
    unsigned int isyntax;
    xed_syntax_enum_t syntax;
    xed_machine_mode_enum_t mmode;
    xed_address_width_enum_t stack_addr_width;
    xed_format_options_t format_options;

    // one time initialization 
    xed_tables_init();
    xed_set_verbosity( 99 );
    memset(&format_options,0, sizeof(format_options));
    format_options.hex_address_before_symbolic_name=0;
    format_options.xml_a=0;
    format_options.omit_unit_scale=0;
    format_options.no_sign_extend_signed_immediates=0;

    for(i=1;i<argc;i++) {
        if (strcmp(argv[i], "-xml") == 0) 
            format_options.xml_a=1;
        else if (strcmp(argv[i], "-no-unit-scale") == 0) 
            format_options.omit_unit_scale=1;
        else if (strcmp(argv[i], "-no-sign-extend") == 0) 
            format_options.no_sign_extend_signed_immediates=1;
        else if (strcmp(argv[i], "-64") == 0) 
            long_mode = 1;
        else 
            break;
    }

    xed_format_set_options( format_options );

    /// begin processing of instructions...

    if (long_mode) {
        mmode=XED_MACHINE_MODE_LONG_64;
        stack_addr_width =XED_ADDRESS_WIDTH_64b;
    }
    else {
        mmode=XED_MACHINE_MODE_LEGACY_32;
        stack_addr_width =XED_ADDRESS_WIDTH_32b;
    }

    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);

    for(  ;i < argc; i++)    {
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
        

    xed_decoded_inst_dump(&xedd,buffer, BUFLEN);
    printf("%s\n",buffer);


    for(isyntax=  XED_SYNTAX_XED; isyntax < XED_SYNTAX_LAST; isyntax++)    {
        syntax = XED_STATIC_CAST(xed_syntax_enum_t, isyntax);
        ok = xed_format_context(syntax, &xedd, buffer, BUFLEN, 0, 0, 0);
        if (ok)
            printf("%s syntax: %s\n", xed_syntax_enum_t2str(syntax), buffer);
        else
            printf("Error disassembling %s syntax\n", xed_syntax_enum_t2str(syntax));
    }
    return 0;
}
