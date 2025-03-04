/* BEGIN_LEGAL 

Copyright (c) 2024 Intel Corporation

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

#if !defined(XED_CHIP_MODES_OVERRIDE)
# define XED_CHIP_MODES_OVERRIDE

# include "xed-chip-enum.h"
# include "xed-decoded-inst.h"
# include "xed-chip-features.h"
#include "xed-chip-features-private.h"
#include "xed-operand-accessors.h"
#include "xed-isa-set.h"

typedef struct{
    xed_uint64_t isa_set;
    xed_uint64_t operand; // xed operand
} isa2op_t;

void xed_chip_modes_override1(xed_decoded_inst_t* xedd,
                              xed_chip_enum_t chip,
                              xed_features_elem_t const*const features);

void xed_chip_modes_override2(xed_decoded_inst_t* xedd,
                              xed_chip_enum_t chip,
                              xed_features_elem_t const*const features);

static XED_INLINE void set_decoder_control_ops(xed_decoded_inst_t* xedd,
                                        isa2op_t const*const isa2op,
                                        xed_features_elem_t const*const features)
{
    xed_uint_t i = 0;

    xed_assert(features);
    xed_assert(isa2op);

    while (isa2op[i].isa_set != XED_ISA_SET_INVALID)
    {
        xed_bool_t status = xed_test_features(features, isa2op[i].isa_set);
        xed3_set_generic_operand(xedd, isa2op[i].operand, status);
        i++;
    }
}

#endif
