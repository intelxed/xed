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
/// @file xed-operand-values-interface.c
/// 


#include "xed-internal-header.h"
#include "xed-operand-values-interface.h"
#include "xed-util.h"
#include "xed-init-pointer-names.h"
#include "xed-operand-ctype-enum.h"
#include "xed-operand-ctype-map.h"
#include "xed-reg-class.h"

#include "xed-ild.h"


xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits_raw(
    const xed_operand_values_t* p)
{
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    return xed_operand_values_get_memory_displacement_length_bits(p);
}

xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits(
                                         const xed_operand_values_t* p)
{
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    return xed3_operand_get_disp_width(p);
}


xed_int64_t  xed_operand_values_get_memory_displacement_int64(
                                         const xed_operand_values_t* p) {
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;

    return xed3_operand_get_disp(p);
}

// unscaled. the raw vs scaled distinction is only relevant for AVX512
xed_int64_t
xed_operand_values_get_memory_displacement_int64_raw(
    const xed_operand_values_t* p)
{
    return xed_operand_values_get_memory_displacement_int64(p); 
}


