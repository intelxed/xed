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


#include "xed/xed-interface.h"
#include <stdio.h>

int main(int argc, char** argv);

int main(int argc, char** argv)
{
    xed_bool_t long_mode = 1;
    xed_decoded_inst_t xedd;
    xed_state_t dstate;
    unsigned char itext[15] = { 0xf2, 0x2e, 0x4f, 0x0F, 0x85, 0x99,
                                0x00, 0x00, 0x00 };

    xed_tables_init(); // one time per process

    if (long_mode) 
        dstate.mmode=XED_MACHINE_MODE_LONG_64;
    else 
        dstate.mmode=XED_MACHINE_MODE_LEGACY_32;

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    xed_ild_decode(&xedd, itext, XED_MAX_INSTRUCTION_BYTES);
    printf("length = %u\n",xed_decoded_inst_get_length(&xedd));
    
    return 0;
    (void) argc; (void) argv; //pacify compiler

}
