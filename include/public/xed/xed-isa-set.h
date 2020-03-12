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
/// @file xed-isa-set.h


#if !defined(XED_ISA_SET_H)
# define XED_ISA_SET_H
    
#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-isa-set-enum.h"     /* generated */
#include "xed-chip-enum.h"        /* generated */

/// @ingroup ISASET
/// return 1 if the isa_set is part included in the specified chip, 0
///  otherwise.
XED_DLL_EXPORT xed_bool_t
xed_isa_set_is_valid_for_chip(xed_isa_set_enum_t isa_set,
                              xed_chip_enum_t chip);

    
#endif
