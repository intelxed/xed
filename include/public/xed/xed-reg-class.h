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
/// @file xed-reg-class.h
/// 

#ifndef XED_REG_CLASS_H
# define  XED_REG_CLASS_H

#include "xed-types.h"
#include "xed-reg-enum.h" // a generated file
#include "xed-reg-class-enum.h" // a generated file

/// Returns the register class of the given input register.
///@ingroup REGINTFC
XED_DLL_EXPORT xed_reg_class_enum_t xed_reg_class(xed_reg_enum_t r);

/// Returns the specific width GPR reg class (like XED_REG_CLASS_GPR32 or
///  XED_REG_CLASS_GPR64)
///  for a given GPR register. Or XED_REG_INVALID if not a GPR.
///@ingroup REGINTFC
XED_DLL_EXPORT xed_reg_class_enum_t xed_gpr_reg_class(xed_reg_enum_t r);

/// Returns the largest enclosing register for any kind of register; This
/// is mostly useful for GPRs. (64b mode assumed)
///@ingroup REGINTFC
XED_DLL_EXPORT xed_reg_enum_t
xed_get_largest_enclosing_register(xed_reg_enum_t r);

/// Returns the largest enclosing register for any kind of register; This
/// is mostly useful for GPRs in 32b mode.
///@ingroup REGINTFC
XED_DLL_EXPORT xed_reg_enum_t
xed_get_largest_enclosing_register32(xed_reg_enum_t r);

/// Returns the  width, in bits, of the named register. 32b mode
///@ingroup REGINTFC
XED_DLL_EXPORT xed_uint32_t
xed_get_register_width_bits(xed_reg_enum_t r);

/// Returns the  width, in bits, of the named register. 64b mode.
///@ingroup REGINTFC
XED_DLL_EXPORT xed_uint32_t
xed_get_register_width_bits64(xed_reg_enum_t r);

////////////////////////////////////////////////////////////////////////////

#endif
