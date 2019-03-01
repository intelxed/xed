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
    
/// @file xed-ex5-enc.c

// encoder example. (uses decoder too)

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h> // malloc, etc.
#include <string.h> //strcmp
#include <assert.h> 

int main(int argc, char** argv);

int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error;
    xed_state_t dstate32, dstate64;
    xed_uint8_t itext[XED_MAX_INSTRUCTION_BYTES];
    unsigned int ilen = XED_MAX_INSTRUCTION_BYTES;
    unsigned int i, j, olen = 0, ninst=0;
    xed_encoder_request_t enc_req;
#define NINST 50
    xed_encoder_instruction_t x[NINST];
    xed_bool_t convert_ok;
#if defined(XED_DECODER)
    xed_bool_t ok;
# define DBUFLEN 1000
    char buffer[DBUFLEN];

    xed_decoded_inst_t xedd;
#endif

    xed_tables_init();
    xed_state_zero(&dstate32);
    xed_state_zero(&dstate64);
    
    dstate32.stack_addr_width=XED_ADDRESS_WIDTH_32b;
    dstate32.mmode=XED_MACHINE_MODE_LEGACY_32;
    
    dstate64.stack_addr_width=XED_ADDRESS_WIDTH_64b;
    dstate64.mmode=XED_MACHINE_MODE_LONG_64;

    xed_inst1(x+ninst, dstate64, XED_ICLASS_JMP, 64,
              xed_relbr(0x11223344, 32));
    ninst++;
    
    /* using 0 for instructions that have the default effective operand
     * width for their mode. The default effective operand width for 16b
     * mode is 16b. The default effective operand width for 32b and 64b
     * modes is 32b. */

    // add an lock and xacquire 
    xed_inst2(x+ninst, dstate32, XED_ICLASS_XOR_LOCK, 0,
              xed_mem_bd(XED_REG_EDX, xed_disp(0x11, 8), 32),
              xed_reg(XED_REG_ECX)    );
    xed_repne(x+ninst); // xacquire
    ninst++;

    xed_inst2(x+ninst, 
              dstate32, XED_ICLASS_ADD, 0, 
              xed_reg(XED_REG_EAX), 
              xed_mem_bd(XED_REG_EDX, xed_disp(0x11223344, 32), 32));
    ninst++;

    xed_inst2(x+ninst, 
              dstate32, XED_ICLASS_ADD, 0, 
              xed_reg(XED_REG_EAX), 
              xed_mem_gbisd(XED_REG_FS,
                         XED_REG_EAX,
                         XED_REG_ESI,4, xed_disp(0x11223344, 32), 32));
    ninst++;

    // displacment-only LEA
    xed_inst2(x+ninst, 
              dstate32, XED_ICLASS_LEA, 32, 
              xed_reg(XED_REG_EAX), 
              xed_mem_bd(XED_REG_INVALID, xed_disp(0x11223344, 32), 32));
    ninst++;


    xed_inst0(x+ninst, dstate32, XED_ICLASS_REPE_CMPSB, 0);
    ninst++;

    /* nondefault effective operand width for 32b mode so we must specify
       it. XED could figure it out from the opcode, but currently does
       not. */ 
    xed_inst0(x+ninst, dstate32, XED_ICLASS_REPE_CMPSW, 16);
    ninst++;

    xed_inst0(x+ninst, dstate32, XED_ICLASS_REPE_CMPSD, 0);
    ninst++;

    xed_inst1(x+ninst, dstate32, XED_ICLASS_PUSH, 0, xed_reg(XED_REG_ECX));
    ninst++;

    xed_inst2(x+ninst, dstate32, XED_ICLASS_XOR, 0,
              xed_reg(XED_REG_ECX),
              xed_reg(XED_REG_EDX));
    ninst++;

    
    /* this one has a nondefault effective operand width for 64b mode so we
       must specify it.  XED could figure this output from the operands,
       but currently it does not. */ 
    
    xed_inst2(x+ninst, dstate64, XED_ICLASS_XOR, 64,
              xed_reg(XED_REG_RCX),
              xed_reg(XED_REG_RDX));
    ninst++;

    /* nondefault effective operand width for 64b mode so we must specify
       it. XED could figure it out from the opcode, but currently does
       not. */ 
    xed_inst0(x+ninst, dstate64, XED_ICLASS_REPE_CMPSQ, 64);
    ninst++;

    /* here it is ambiguous from the opcode what the effective operand
     * width is. I could use the operand, but do not do that yet. */
    xed_inst1(x+ninst, dstate64, XED_ICLASS_PUSH, 64, xed_reg(XED_REG_RCX));
    ninst++;

    /* again, here's one where I could infer that the operation is 64b from
     * the memory operand, but not yet. */
    xed_inst1(x+ninst, dstate64, XED_ICLASS_PUSH, 64,
              xed_mem_bd(XED_REG_RDX, xed_disp(0x11223344, 32), 64));
    ninst++;

    // move a 64b quantity in to RAX using only a 64b displacment
    xed_inst2(x+ninst, dstate64, XED_ICLASS_MOV, 64,
              xed_reg(XED_REG_RAX),
              xed_mem_bd(XED_REG_INVALID, xed_disp(0x1122334455667788, 64), 64));
    ninst++;



    xed_inst1(x+ninst, dstate64, XED_ICLASS_JMP_FAR, 64,
              xed_mem_bd(XED_REG_RAX, xed_disp(0x20, 8), 80));

    ninst++;

    xed_inst2(x+ninst, 
              dstate64, XED_ICLASS_ADD, 64, 
              xed_reg(XED_REG_RAX), 
              xed_imm0(0x77,8));
    ninst++;

    xed_inst2(x+ninst, 
              dstate64, XED_ICLASS_ADD, 64, 
              xed_reg(XED_REG_RAX), 
              xed_imm0(0x44332211,32));
    ninst++;

    xed_inst2(x+ninst, 
              dstate64, XED_ICLASS_MOV_CR, 64, 
              xed_reg(XED_REG_CR3),
              xed_reg(XED_REG_RDI));
    ninst++;

    xed_inst2(x+ninst, 
              dstate64, XED_ICLASS_MOV, 32,
              xed_mem_bisd(XED_REG_R8, XED_REG_RBP, 1, xed_disp(0xf8, 8), 32),
              xed_simm0(0x0,32));
    ninst++;


    // example showing how to set the effective address size to 32b in 64b
    // mode.  Normally XED deduces that from the memory operand base
    // register, but in this case the memops are implicit.
    xed_inst0(x+ninst, 
              dstate64, XED_ICLASS_STOSQ, 64);
    xed_addr(x+ninst, 32);
    ninst++;

    
    xed_inst1(x+ninst,
              dstate32,
              XED_ICLASS_JECXZ,
              4,
              xed_relbr(5, 8));
    ninst++;
    
    xed_inst1(x+ninst,
              dstate64,
              XED_ICLASS_JECXZ,
              4,
              xed_relbr(5, 8));
    xed_addr(x+ninst,32);
    ninst++;
    
    xed_inst1(x+ninst,
              dstate64,
              XED_ICLASS_JRCXZ,
              4,
              xed_relbr(5, 8));
    ninst++;
              
    
#if defined(XED_AVX)
    xed_inst2(x+ninst,
              dstate64,
              XED_ICLASS_VBROADCASTSD,
              32,
              xed_reg(XED_REG_YMM4),
              xed_mem_gbisd(XED_REG_GS,XED_REG_INVALID,0,0,
                            xed_disp(0x808, 32),
                            64));
    ninst++;
#endif

#if defined(XED_SUPPORTS_AVX512)
    // example showing how to set EVEX features.
    // increase the number of operands and use xed_other(...)
    xed_inst5(x+ninst,
              dstate64,
              XED_ICLASS_VADDPS,
              32,
              xed_reg(XED_REG_XMM1),
              xed_reg(XED_REG_K1),
              xed_reg(XED_REG_XMM2),
              xed_mem_b(XED_REG_RCX,  16),
              xed_other(XED_OPERAND_ZEROING,1));
    ninst++;
#endif

   
    for(i=0;i<ninst;i++) {
        xed_encoder_request_zero_set_mode(&enc_req, &(x[i].mode));
        convert_ok = xed_convert_to_encoder_request(&enc_req, x+i);
        if (!convert_ok) {
            fprintf(stderr,"conversion to encode request failed\n");
            continue;
        }
        xed_error = xed_encode(&enc_req, itext, ilen, &olen);
        if (xed_error != XED_ERROR_NONE) {
            fprintf(stderr,"ENCODE ERROR: %s\n",
                    xed_error_enum_t2str(xed_error));
            continue;
        }
        printf("Result: %d\n\t", (int)i);
        for(j=0;j<olen;j++) 
            printf("%02x ", itext[j]);

        printf("\n");
#if defined(XED_DECODER)
        xed_decoded_inst_zero_set_mode(&xedd, &(x[i].mode));
        xed_error = xed_decode(&xedd, itext, olen);
        if (xed_error != XED_ERROR_NONE) {
            fprintf(stderr,"DECODE ERROR: %s\n",
                    xed_error_enum_t2str(xed_error));
            continue;
        }
        ok = xed_format_context(XED_SYNTAX_INTEL, &xedd, buffer, DBUFLEN, 0, 0, 0);
        if (ok)
            printf("\t%s\n", buffer);
        else 
            fprintf(stderr,"DISASSEMBLY ERROR\n");
#endif

    }
    return 0;
    (void) argc;
    (void) argv;
}
