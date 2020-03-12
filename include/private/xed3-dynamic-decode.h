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

/// @file xed3-dynamic-decode.h
/// dynamic information decoder
    
#if !defined(XED3_DYNAMIC_DECODE_H)
#define XED3_DYNAMIC_DECODE_H


#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-types.h"
#include "xed-decoded-inst.h"

/// Set the operands information.
/// should be called after dynamic_decode_part2
/// @ingroup XED3
/* sets information about register operands with ntluf */
xed_error_enum_t xed3_decode_operands(xed_decoded_inst_t* d);


/// decode instruction after xed_inst_t was set.
/// captures all NTs that appear in pattern.
/// xds should be initialized.
/// @ingroup XED3
xed_error_enum_t 
xed3_dynamic_decode_part2(xed_decoded_inst_t* d);



#endif

