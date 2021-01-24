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

#include "xed-internal-header.h"
#include "xed-decoded-inst.h"
#include "xed-operand-values-interface.h"
#include <string.h> // memset
/* INITIALIZATION */
static XED_INLINE void zero_inst(xed_decoded_inst_t* p)
{
    memset(p,0,sizeof(xed_decoded_inst_t));
}
XED_DLL_EXPORT void
xed_decoded_inst_zero_set_mode(xed_decoded_inst_t* p,
                               const xed_state_t* dstate)
{
    zero_inst(p);
    xed_operand_values_set_mode(p,dstate);
}

XED_DLL_EXPORT void
xed_decoded_inst_zero(xed_decoded_inst_t* p) {
    zero_inst(p);
}

XED_DLL_EXPORT void
xed_decoded_inst_zero_keep_mode_from_operands(
    xed_decoded_inst_t* p,
    const xed_operand_values_t* operands)
{
    xed_operand_values_init_keep_mode(p, operands);
    p->_decoded_length = 0;
    p->_inst = 0;
    p->u.user_data = 0;
}

XED_DLL_EXPORT void
xed_decoded_inst_zero_keep_mode(xed_decoded_inst_t* p) {
    xed_decoded_inst_zero_keep_mode_from_operands(p, p);
}


