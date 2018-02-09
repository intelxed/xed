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
/// @file xed-inst-private.H
/// 


#if !defined(XED_INST_PRIVATE_H)
# define XED_INST_PRIVATE_H

#include "xed-types.h"
#include "xed-portability.h"
#include "xed-inst.h"

xed_nonterminal_enum_t
xed_operand_nt_lookup_fn_enum(const xed_operand_t* p);

////////////////////////////////////////////////////////////////////


void xed_inst_init(xed_inst_t* p);

#endif
