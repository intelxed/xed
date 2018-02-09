/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

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

/// @file xed3-static-decode.h
/// instruction length decoder
    
#if !defined(XED3_STATIC_DECODE_H)
#define XED3_STATIC_DECODE_H

#include "xed-ild.h"


/// Static decoder.
///  @param d xed_decoded_inst_t.
/// Sets the xed_inst_t 
///
/// @ingroup XED3
void xed3_static_decode(xed_decoded_inst_t* d);

#endif

