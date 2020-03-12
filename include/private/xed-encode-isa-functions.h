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
/// @file xed-encode-isa-functions.h
/// 

#ifndef XED_ENCODE_ISA_FUNCTIONS_H
# define XED_ENCODE_ISA_FUNCTIONS_H

#include "xed-encode.h"


xed_bool_t xed_encode_nonterminal_INSTRUCTIONS_EMIT(xed_encoder_request_t* xes);
xed_bool_t xed_encode_nonterminal_INSTRUCTIONS_BIND(xed_encoder_request_t* xes);


#endif

