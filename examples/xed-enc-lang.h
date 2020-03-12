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

/// @file xed-enc-lang.h

#if !defined(XED_ENC_LANG_H)
# define XED_ENC_LANG_H

#include "xed/xed-interface.h" 

typedef  struct 
{
    xed_state_t dstate;
    char const* command;
} ascii_encode_request_t;


xed_encoder_request_t
parse_encode_request(ascii_encode_request_t areq);

#endif
