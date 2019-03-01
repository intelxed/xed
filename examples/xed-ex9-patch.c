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
    
// encoder patching example. (uses decoder too)

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h> // malloc, etc.
#include <string.h> //strcmp
#include <assert.h>


xed_error_enum_t ex_make_patchable_instr(xed_encoder_instruction_t* to_enc,
                                         xed_decoded_inst_t* xedd,
                                         xed_uint8_t* itext,
                                         xed_uint_t ilen)
{
    xed_encoder_request_t xede;
    xed_bool_t convert_ok;
    xed_error_enum_t xed_error;
    xed_uint_t olen = 0;
    
    xed_encoder_request_zero_set_mode(&xede, &(to_enc->mode));
    convert_ok = xed_convert_to_encoder_request(&xede,to_enc);
    if (!convert_ok) {
        fprintf(stderr,"conversion to encode request failed\n");
        return XED_ERROR_GENERAL_ERROR;
    }
    xed_error = xed_encode(&xede, itext, ilen, &olen);
    if (xed_error) 
        return xed_error;

    // decode in to xedd
    xed_decoded_inst_zero_set_mode(xedd, &(to_enc->mode));
    xed_error = xed_decode(xedd, itext, olen);

    return xed_error;
}


#define NINST 50
#define DBUFLEN 1000

int main(int argc, char** argv);

int 
main(int argc, char** argv)
{
    xed_error_enum_t xed_error;
    xed_state_t dstate32, dstate64;
    
    xed_uint8_t itext[NINST][XED_MAX_INSTRUCTION_BYTES];
    unsigned int ilen[NINST];
    xed_encoder_instruction_t to_enc[NINST];
    xed_decoded_inst_t xedd[NINST];
    
    unsigned int i, ninst=0;

    xed_bool_t ok;
    char buffer[DBUFLEN];

    for(i=0;i<NINST;i++)
        ilen[i] = XED_MAX_INSTRUCTION_BYTES;
    
    xed_tables_init();
    xed_state_zero(&dstate32);
    xed_state_zero(&dstate64);
    
    dstate32.stack_addr_width=XED_ADDRESS_WIDTH_32b;
    dstate32.mmode=XED_MACHINE_MODE_LEGACY_32;
    
    dstate64.stack_addr_width=XED_ADDRESS_WIDTH_64b;
    dstate64.mmode=XED_MACHINE_MODE_LONG_64;

    xed_inst1(to_enc+ninst, dstate64, XED_ICLASS_JMP, 64,
              xed_relbr(0x11223344, 32));
    ninst++;
    
    /* using 0 for instructions that have the default effective operand
     * width for their mode. The default effective operand width for 16b
     * mode is 16b. The default effective operand width for 32b and 64b
     * modes is 32b. */

    xed_inst2(to_enc+ninst, dstate32, XED_ICLASS_XOR_LOCK, 0,
              xed_mem_bd(XED_REG_EDX, xed_disp(0x11, 8), 32),
              xed_reg(XED_REG_ECX)    );
    ninst++;

    xed_inst2(to_enc+ninst, 
              dstate32, XED_ICLASS_ADD, 0, 
              xed_reg(XED_REG_EAX), 
              xed_mem_bd(XED_REG_EDX, xed_disp(0x11223344, 32), 32));
    ninst++;

    xed_inst2(to_enc+ninst, 
              dstate64, XED_ICLASS_ADD, 64, 
              xed_reg(XED_REG_RAX), 
              xed_imm0(0x77,8));
    ninst++;

    /* make patchable instructions (encode -> decode) */
    
    for(i=0;i<ninst;i++) {
        xed_error = ex_make_patchable_instr(to_enc+i, xedd+i, itext[i], ilen[i]);
        
        if (xed_error) {
            fprintf(stderr,"DECODE ERROR: %s\n",
                    xed_error_enum_t2str(xed_error));
            continue;
        }
    }


    /* patch the displacements or immediates */
       
    ok = xed_patch_relbr(xedd+0, itext[0], xed_relbr(0x55667788,32));
    if (!ok) fprintf(stderr,"Patching failed for 1st instr\n");
    
    ok = xed_patch_disp(xedd+1, itext[1], xed_disp(0x55,8));
    if (!ok) fprintf(stderr,"Patching failed for 2nd instr\n");
    
    ok = xed_patch_disp(xedd+2, itext[2], xed_disp(0x55446677,32));
    if (!ok) fprintf(stderr,"Patching failed for 3rd instr\n");
    
    ok = xed_patch_imm0(xedd+3, itext[3], xed_imm0(0x22,8));
    if (!ok) fprintf(stderr,"Patching failed for 4rd instr\n");

    /* print out the patched instructions */

    for(i=0;i<ninst;i++) {
        xed_decoded_inst_zero_set_mode(xedd+i, &(to_enc[i].mode));
        xed_error = xed_decode(xedd+i, itext[i], ilen[i]); //FIXME: use actual length?
        if (xed_error != XED_ERROR_NONE) {
            fprintf(stderr,"DECODE ERROR: %s\n",
                    xed_error_enum_t2str(xed_error));
            continue;
        }
        ok = xed_format_context(XED_SYNTAX_INTEL, xedd+i, buffer, DBUFLEN, 0, 0, 0);
        if (ok)
            printf("\t%s\n", buffer);
        else 
            fprintf(stderr,"DISASSEMBLY ERROR\n");
    }
    return 0;
    (void) argc;
    (void) argv;
}
