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
/// @file xed-isa-set.c

#include "xed-isa-set.h"
#include "xed-util.h"
#include "xed-chip-features-table.h"
xed_bool_t
xed_isa_set_is_valid_for_chip(xed_isa_set_enum_t isa_set,
                              xed_chip_enum_t chip) {
    const xed_uint64_t one=1;
    const unsigned int n = XED_CAST(unsigned int,isa_set) / 64;
    const unsigned int r = XED_CAST(unsigned int,isa_set) - (64*n);
    xed_uint64_t features = 0;
    
    xed_assert(chip < XED_CHIP_LAST); 
    xed_assert(isa_set > XED_ISA_SET_INVALID && isa_set  < XED_ISA_SET_LAST);
    features = xed_chip_features[chip][n];
    if (features & (one<<r))
        return 1;
    return 0;
}
