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

#if !defined(XED_CHIP_FEATURES_PRIVATE_H)
# define XED_CHIP_FEATURES_PRIVATE_H
    
#include "xed-types.h"
#include "xed-chip-features.h"
#include "xed-isa-set.h"

xed_bool_t
xed_test_chip_features(xed_chip_features_t* p,
                       xed_isa_set_enum_t isa_set);

    
#endif
