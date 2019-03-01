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
/// @file xed-reg-class.c

#include "xed-util.h"
#include "xed-reg-class.h"
#include "xed-tables-extern.h"

xed_reg_class_enum_t xed_reg_class(xed_reg_enum_t r) {
    if (r < XED_REG_LAST)
        return xed_reg_class_array[r];
    return XED_REG_CLASS_INVALID;
}
xed_reg_class_enum_t xed_gpr_reg_class(xed_reg_enum_t r) {
    if (r < XED_REG_LAST) 
        return xed_gpr_reg_class_array[r];
    return XED_REG_CLASS_INVALID;
}

xed_reg_enum_t  xed_get_largest_enclosing_register(xed_reg_enum_t r) {
    if (r < XED_REG_LAST) 
        return xed_largest_enclosing_register_array[r];
    return XED_REG_INVALID;
}

xed_reg_enum_t  xed_get_largest_enclosing_register32(xed_reg_enum_t r) {
    if (r < XED_REG_LAST) 
        return xed_largest_enclosing_register_array_32[r];
    return XED_REG_INVALID;
}

xed_uint32_t xed_get_register_width_bits(xed_reg_enum_t r) {
   if (r < XED_REG_LAST) 
        return xed_reg_width_bits[r][0];
    return 0;
}

// Another option would be to make an function that takes the
// mode as a parameter.
xed_uint32_t xed_get_register_width_bits64(xed_reg_enum_t r) {
   if (r < XED_REG_LAST) 
        return xed_reg_width_bits[r][1];
    return 0;
}
    
