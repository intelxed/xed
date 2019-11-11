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
/// @file xed3-static-decode.c
/// static info decoder (xed_inst_t)



#include "xed-ild.h"
#include "xed-ild-enum.h"
#include "xed3-phash.h"

/* returns the index for xed_inst_table */
XED_DLL_EXPORT
void xed3_static_decode(xed_decoded_inst_t* d)
{
    xed_uint_t vv = xed3_operand_get_vexvalid(d);
    xed_ild_map_enum_t map = xed3_operand_get_map(d);
    xed_uint32_t xed3_idx=0;
    const xed_inst_t* inst;

    if (map < XED_PHASH_MAP_LIMIT)
    {
        // KW gets a false positive on the next line for indices.
        xed3_find_func_t const* find_f_arr = xed3_phash_lu[vv][map];    
        if (find_f_arr) // very predictable branch, mostly taken
        {
            xed_uint8_t opcode;
            xed3_find_func_t find_f;
                        
            opcode = (xed_uint8_t)xed3_operand_get_nominal_opcode(d);
            // we have 0 for undefined map-opcodes as function pointer
            find_f = find_f_arr[opcode];
            if (find_f)
                xed3_idx = (*find_f)(d);
        }
    }
    inst = xed_inst_table + xed3_idx;
    xed_decoded_inst_set_inst(d, inst);
}

