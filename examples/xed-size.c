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
int main(int argc, char** argv) {
    /* I use this to keep track of the size of my per-instruction data structures */
    xed_decoded_inst_t x;
    /*xed_tables_init();  */
    printf("xed_decoded_inst_t         %12d\n", (int)sizeof(xed_decoded_inst_t));
    printf("xed_inst_t                 %12d\n", (int)sizeof(xed_inst_t));    
    printf("xed_operand_t              %12d\n", (int)sizeof(xed_operand_t));
    printf("xed_iform_info_t           %12d\n", (int)sizeof(xed_iform_info_t));    
    return 0;
    (void) argc; (void) argv; //pacify compiler
    (void) x;
}
