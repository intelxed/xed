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
/// @file xed-decode-supp.H
/// 


#ifndef XED_DECODE_SUPP_H
# define XED_DECODE_SUPP_H
#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-error-enum.h"
#include "xed-operand-values-interface.h"
#include "xed-operand-width-enum.h"



/// Sets the ERROR field in the operand storage if the register arg is
/// XED_REG_ERROR.
static XED_INLINE void xed_check_reg(xed_reg_enum_t reg, 
                                     xed_decoded_inst_t* xds) {
    if (reg == XED_REG_ERROR)
        xed3_operand_set_error(xds,XED_ERROR_BAD_REGISTER);
}



#endif
