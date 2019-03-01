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
/// @file xed3-dynamic-decode.c
/// dynamic info decoder

#include "xed-decoded-inst.h"

#include "xed3-static-decode.h"
#include "xed3-chain-capture-lu.h"
#include "xed3-op-chain-capture-lu.h"
#include "xed3-dynamic-part1-capture.h"



XED_DLL_EXPORT xed_error_enum_t 
xed3_dynamic_decode_part2(xed_decoded_inst_t* d) {
    xed_uint32_t inum = 
            (xed_uint32_t)(d->_inst - xed_inst_table);
    
    xed3_chain_function_t capture_fptr;
        
        
    capture_fptr = xed3_chain_fptr_lu[inum];

    return (*capture_fptr)(d); 
}

/* sets information about register operands with ntluf */
XED_DLL_EXPORT
xed_error_enum_t xed3_decode_operands(xed_decoded_inst_t* d)
{
    xed_uint32_t inum = 
            (xed_uint32_t)(d->_inst - xed_inst_table);
    
    xed3_chain_function_t capture_fptr;
        
        
    capture_fptr = xed3_op_chain_fptr_lu[inum];

    return (*capture_fptr)(d); 
}

