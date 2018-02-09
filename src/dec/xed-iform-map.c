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
/// @file xed-iform-map.c

#include "xed-internal-header.h"
#include "xed-decoded-inst.h"
#include "xed-iform-map.h"
////////////////////////////////////////////////////////////////////////////

const xed_iform_info_t* xed_iform_map(xed_iform_enum_t iform) {

   if (iform < XED_IFORM_LAST) {
       const xed_iform_info_t* p = xed_iform_db + iform;
       return p;
   }
   return 0;
}

xed_uint32_t xed_iform_max_per_iclass(xed_iclass_enum_t iclass) {

    xed_assert(iclass < XED_ICLASS_LAST);
    return xed_iform_max_per_iclass_table[iclass];
}


xed_uint32_t xed_iform_first_per_iclass(xed_iclass_enum_t iclass) {

    xed_assert(iclass < XED_ICLASS_LAST);
    return xed_iform_first_per_iclass_table[iclass];
}

xed_category_enum_t xed_iform_to_category(xed_iform_enum_t iform) {
    const xed_iform_info_t* ii = xed_iform_map(iform);
    if (ii)
        return (xed_category_enum_t) ii->category;
    return XED_CATEGORY_INVALID;
}
xed_extension_enum_t xed_iform_to_extension(xed_iform_enum_t iform) {
    const xed_iform_info_t* ii = xed_iform_map(iform);
    if (ii)
        return (xed_extension_enum_t)ii->extension;
    return XED_EXTENSION_INVALID;
}

xed_isa_set_enum_t xed_iform_to_isa_set(xed_iform_enum_t iform) {
    const xed_iform_info_t* ii = xed_iform_map(iform);
    if (ii)
        return (xed_isa_set_enum_t)ii->isa_set;
    return XED_ISA_SET_INVALID;
}


char const* xed_iform_to_iclass_string(xed_iform_enum_t iform, int att) {
    const xed_iform_info_t* ii = xed_iform_map(iform);
    if (ii) {
        if (ii->string_table_idx) {
            char const* p = 0;
            xed_assert(ii->string_table_idx + att < XED_ICLASS_NAME_STR_MAX);
            p = xed_iclass_string[ii->string_table_idx + att];
            if (p)
                return p;
        }
        return xed_iclass_enum_t2str( ii->iclass );
    }
    return "unknown";
}

char const* xed_iform_to_iclass_string_att(xed_iform_enum_t iform) {
    return xed_iform_to_iclass_string(iform, 1);
}

char const* xed_iform_to_iclass_string_intel(xed_iform_enum_t iform) {
    return xed_iform_to_iclass_string(iform, 0);
}
