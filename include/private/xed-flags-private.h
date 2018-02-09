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
/// @file xed-flags-private.H
/// 

#ifndef XED_FLAGS_PRIVATE_H
# define XED_FLAGS_PRIVATE_H

#include "xed-flags.h"


// during decode: store the pointer to the lowest level xed_simple_flag_t
// in the xedd based on an examination of the shift-operand. Need to know
// what operand discriminates the choices. Add that to the text table.

// common the flags in the parser.


typedef enum
{
    XED_FLAG_CASE_IMMED_ZERO,
    XED_FLAG_CASE_IMMED_ONE,
    XED_FLAG_CASE_IMMED_OTHER,
    XED_FLAG_CASE_HAS_REP, // implies may-dependence for writes
    XED_FLAG_CASE_NO_REP,
    XED_FLAG_CASE_LAST
} xed_flag_cases_enum_t;


typedef struct xed_complex_flag_s  {

    // pointers to an array of dense flags. Only the cases that matter are
    // non-null.  We need to search for case of: register-counts,
    // immediate-0, immediate-1, and other-immediate

    xed_bool_t check_rep :1;
    xed_bool_t check_imm :1;
    xed_uint16_t cases[XED_FLAG_CASE_LAST];

} xed_complex_flag_t;

void xed_complex_flag_zero(xed_complex_flag_t* p);

#endif
