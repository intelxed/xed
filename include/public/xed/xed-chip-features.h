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

#if !defined(XED_CHIP_FEATURES_H)
# define XED_CHIP_FEATURES_H
    
#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-isa-set-enum.h"     /* generated */
#include "xed-chip-enum.h"        /* generated */

#define XED_FEATURE_VECTOR_MAX 4
/// @ingroup ISASET
typedef struct 
{
    xed_uint64_t f[XED_FEATURE_VECTOR_MAX];
} xed_chip_features_t;


/// fill in the contents of p with the vector of chip features.
XED_DLL_EXPORT void
xed_get_chip_features(xed_chip_features_t* p, xed_chip_enum_t chip);

/// present = 1 to turn the feature on. present=0 to remove the feature.
XED_DLL_EXPORT void
xed_modify_chip_features(xed_chip_features_t* p,
                         xed_isa_set_enum_t isa_set,
                         xed_bool_t present);

    
#endif
