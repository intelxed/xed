/*BEGIN_LEGAL 

Copyright (c) 2021 Intel Corporation

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
/// @file xed-ex-agen.c  

// decoder example with agen callbacks.

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h> //strcmp
#include <assert.h> 

int main(int argc, char** argv);


/* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */
/* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */
/* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */
/* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */

xed_uint64_t register_callback(xed_reg_enum_t reg, void* context, xed_bool_t* error) {
    (void) context;   // pacify compiler
    (void) error;

    /* After we register this function (see xed_agen_register_callback in
     * main()), this function is called as needed by xed_agen().  This
     * function provides register values for xed_agen(). In a real usage,
     * you would probably pass in a context (in your call to xed_agen())
     * that contains the actual values.  */

    
    /* Note that AL is required for the XLAT instruction. That is the only
       byte reg needed. Also note, that for real mode, raw segement
       selectors are returned by this function.  */

    /* in reality, you'd have to return valid values for each case */

    /* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */
    
    switch(reg) {
      case XED_REG_RAX:
      case XED_REG_EAX:
      case XED_REG_AX:
        return 0xAABBCC00;
        break;
      case XED_REG_AL: // FOR XLAT
        break;

      case XED_REG_RCX:
      case XED_REG_ECX:
      case XED_REG_CX:
        return 0xAABBCCDD;
        break;
      case XED_REG_RDX:
      case XED_REG_EDX:
      case XED_REG_DX:
        break;
      case XED_REG_RBX:
      case XED_REG_EBX:
      case XED_REG_BX:
        return 0x11223344;
        break;
      case XED_REG_RSP:
      case XED_REG_ESP:
      case XED_REG_SP:
        break;
      case XED_REG_RBP:
      case XED_REG_EBP:
      case XED_REG_BP:
        break;
      case XED_REG_RSI:
      case XED_REG_ESI:
      case XED_REG_SI:
        return 0x1122334455;
        break;
      case XED_REG_RDI:
      case XED_REG_EDI:
      case XED_REG_DI:
        return 0x6655443322;
        break;
      case XED_REG_R8:
      case XED_REG_R8D:
      case XED_REG_R8W:
        break;
      case XED_REG_R9:
      case XED_REG_R9D:
      case XED_REG_R9W:
        break;
      case XED_REG_R10:
      case XED_REG_R10D:
      case XED_REG_R10W:
        break;
      case XED_REG_R11:
      case XED_REG_R11D:
      case XED_REG_R11W:
        break;
      case XED_REG_R12:
      case XED_REG_R12D:
      case XED_REG_R12W:
        break;
      case XED_REG_R13:
      case XED_REG_R13D:
      case XED_REG_R13W:
        break;
      case XED_REG_R14:
      case XED_REG_R14D:
      case XED_REG_R14W:
        break;
      case XED_REG_R15:
      case XED_REG_R15D:
      case XED_REG_R15W:
        break;
      case XED_REG_RIP:
        return 0x7990100020003000ULL;

      case XED_REG_EIP:
      case XED_REG_IP:
        break;
      case XED_REG_CS:
      case XED_REG_DS:
      case XED_REG_ES:
      case XED_REG_SS:
      case XED_REG_FS:
      case XED_REG_GS:
        break;
      default:
        assert(0);
    }
    return 0;
}

xed_uint64_t segment_callback(xed_reg_enum_t reg, void* context, xed_bool_t* error) {
    /* for protected mode, this function returns the valid segment base values */

    /* in reality, you'd have to return valid valies for each case */
    /* THIS IS JUST AN EXAMPLE FOR TESTING AND DOES NOT RETURN REAL DATA */

    (void) context;   // pacify compiler
    (void) error;
    
    switch(reg) {
      case XED_REG_CS:
      case XED_REG_DS:
      case XED_REG_ES:
      case XED_REG_SS:
        return 0;
      case XED_REG_FS:
        return 0;
        break;
      case XED_REG_GS:
        return 0;
        break;
      default:
        assert(0);
        break;
    }
    return 0;
}




int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error;

    xed_bool_t long_mode = 0;
    xed_bool_t real_mode = 0;
    xed_bool_t protected_16 = 0;
    xed_state_t dstate;
    unsigned int first_argv;
    unsigned int bytes = 0;
    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    unsigned int i;
    unsigned int argcu = (unsigned int)argc;
    unsigned int u;
    xed_decoded_inst_t xedd;
#define BUFLEN  1000
    char buffer[BUFLEN];
    xed_bool_t ok;
    unsigned int isyntax;
    xed_syntax_enum_t syntax;
    unsigned int memop_index = 0;    
    unsigned int memops = 0;
    xed_uint64_t out_addr = 0;

    xed_tables_init();

    // register callbacks that provide actual values. These functions will
    // be called by xed_agen() later on when values are needed.
    xed_agen_register_callback( register_callback, segment_callback);

    xed_state_zero(&dstate);
    //xed_set_verbosity( 99 );

    if (argcu > 2 && strcmp(argv[1], "-64") == 0) 
        long_mode = 1;
    if (argcu > 2 && strcmp(argv[1], "-r") == 0) 
        real_mode = 1;
    if (argcu > 2 && strcmp(argv[1], "-16") == 0) 
        protected_16 = 1;

    if (long_mode) {
        first_argv = 2;
        dstate.mmode=XED_MACHINE_MODE_LONG_64;
    }
    else if (protected_16) {
        first_argv = 2;
        xed_state_init(&dstate,
                       XED_MACHINE_MODE_LEGACY_16,
                       XED_ADDRESS_WIDTH_16b, 
                       XED_ADDRESS_WIDTH_16b);
    }
    else if (real_mode) {
        first_argv = 2;
        /* we say that real mode uses 16b addressing even though the
           addresses returned are 20b long. */
        xed_state_init(&dstate,
                       XED_MACHINE_MODE_REAL_16,
                       XED_ADDRESS_WIDTH_16b,
                       XED_ADDRESS_WIDTH_16b);
    }
    else {
        first_argv=1;
        xed_state_init(&dstate,
                       XED_MACHINE_MODE_LEGACY_32, 
                       XED_ADDRESS_WIDTH_32b, 
                       XED_ADDRESS_WIDTH_32b);
    }

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    for( i=first_argv ;i < argcu; i++)    {
        xed_uint8_t x = (xed_uint8_t)(xed_atoi_hex(argv[i]));
        assert(bytes < XED_MAX_INSTRUCTION_BYTES);
        itext[bytes++] = x;
    }
    if (bytes == 0)    {
        fprintf(stderr, "Must supply some hex bytes\n");
        exit(1);
    }

    printf("PARSING BYTES: ");
    for( u=0;u<bytes; u++) 
        printf("%02x ", XED_STATIC_CAST(unsigned int,itext[u]));
    printf("\n");

    // call XED decode
    
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
        fprintf(stderr,"Unhandled error code %s\n", xed_error_enum_t2str(xed_error));
        exit(1);
    }

    // print the output a few different ways
    printf("iclass: %s\n",
           xed_iclass_enum_t2str(xed_decoded_inst_get_iclass(&xedd)));
    printf("iform: %s\n", 
           xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(&xedd)));

    for(isyntax=  XED_SYNTAX_XED; isyntax < XED_SYNTAX_LAST; isyntax++)    {
        syntax = XED_STATIC_CAST(xed_syntax_enum_t, isyntax);
        ok = xed_format_context(syntax, &xedd, buffer, BUFLEN, 0, 0, 0);
        if (ok)
            printf("%s syntax: %s\n", xed_syntax_enum_t2str(syntax), buffer);
        else
            printf("Error disassembling %s syntax\n", xed_syntax_enum_t2str(syntax));
    }

    memops = xed_decoded_inst_number_of_memory_operands(&xedd);
    printf("\nNumber of memory operands: %d\n", (int)memops);

    // call the address generation (agen) calculator for each memop.
    //  It will  call the  callbacks you registered at top of main().
    
    for(memop_index=0;memop_index<memops;memop_index++) {
        // The  "context" passed to your registered callbacks when they are asked
        // to produce values. In this example we don't require a real context.
        void* context = 0;
        xed_error = xed_agen(&xedd, memop_index, context, &out_addr);
        if (xed_error != XED_ERROR_NONE) {
            fprintf(stderr,"Agen error code %s\n", xed_error_enum_t2str(xed_error));
            exit(1);
        }
        printf("\tMemory agen%d: 0x" XED_FMT_LX16 "\n", (int)memop_index, out_addr);
    }
    return 0;
}
