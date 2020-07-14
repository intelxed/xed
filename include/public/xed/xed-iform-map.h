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
/// @file xed-iform-map.h
/// 

#if !defined(XED_IFORM_MAP_H)
# define XED_IFORM_MAP_H

#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-iform-enum.h"       /* generated */
#include "xed-iclass-enum.h"      /* generated */
#include "xed-category-enum.h"    /* generated */
#include "xed-extension-enum.h"   /* generated */
#include "xed-isa-set-enum.h"     /* generated */

/// @ingroup IFORM
/// Statically available information about iforms.
/// Values are returned by #xed_iform_map().
typedef struct xed_iform_info_s {
    xed_uint32_t  iclass    :16; // xed_iclass_enum_t
    xed_uint32_t  category  :8; //xed_category_enum_t
    xed_uint32_t  extension :8; //xed_extension_enum_t
    
    xed_uint32_t  isa_set   :16; //xed_isa_set_enum_t
      /* if nonzero, index in to the disassembly string table */
    xed_uint32_t  string_table_idx:16;
} xed_iform_info_t;


/// @ingroup IFORM
/// Map the #xed_iform_enum_t to a pointer to a #xed_iform_info_t which
/// indicates the #xed_iclass_enum_t, the #xed_category_enum_t and the
/// #xed_extension_enum_t for the iform. Returns 0 if the iform is not a
/// valid iform.
XED_DLL_EXPORT
const xed_iform_info_t* xed_iform_map(xed_iform_enum_t iform);

/// @ingroup IFORM
/// Return the maximum number of iforms for a particular iclass.  This
/// function returns valid data as soon as global data is
/// initialized. (This function does not require a decoded instruction as
/// input).
XED_DLL_EXPORT
xed_uint32_t xed_iform_max_per_iclass(xed_iclass_enum_t iclass);

/// @ingroup IFORM
/// Return the first of the iforms for a particular iclass.  This function
/// returns valid data as soon as global data is initialized. (This
/// function does not require a decoded instruction as input).
XED_DLL_EXPORT
xed_uint32_t xed_iform_first_per_iclass(xed_iclass_enum_t iclass);

/// @ingroup IFORM
/// Return the iclass for a given iform. This 
/// function returns valid data as soon as global data is initialized. (This
/// function does not require a decoded instruction as input).
static
XED_INLINE xed_iclass_enum_t xed_iform_to_iclass(xed_iform_enum_t iform) {
    const xed_iform_info_t* ii = xed_iform_map(iform);
    if (ii)
        return (xed_iclass_enum_t) ii->iclass;
    return XED_ICLASS_INVALID;
}

/// @ingroup IFORM
/// Return the category for a given iform. This 
/// function returns valid data as soon as global data is initialized. (This
/// function does not require a decoded instruction as input).
XED_DLL_EXPORT
xed_category_enum_t xed_iform_to_category(xed_iform_enum_t iform);

/// @ingroup IFORM
/// Return the extension for a given iform. This function returns valid
/// data as soon as global data is initialized. (This function does not
/// require a decoded instruction as input).
XED_DLL_EXPORT
xed_extension_enum_t xed_iform_to_extension(xed_iform_enum_t iform);

/// @ingroup IFORM
/// Return the isa_set for a given iform. This function returns valid data
/// as soon as global data is initialized. (This function does not require
/// a decoded instruction as input).
XED_DLL_EXPORT
xed_isa_set_enum_t xed_iform_to_isa_set(xed_iform_enum_t iform);

/// @ingroup IFORM
/// Return a pointer to a character string of the iclass. This
/// translates the internal disambiguated names to the more ambiguous
/// names that people like to see. This returns the ATT SYSV-syntax name.
XED_DLL_EXPORT
char const* xed_iform_to_iclass_string_att(xed_iform_enum_t iform);


/// @ingroup IFORM
/// Return a pointer to a character string of the iclass. This
/// translates the internal disambiguated names to the more ambiguous
/// names that people like to see. This returns the Intel-syntax name.
XED_DLL_EXPORT
char const* xed_iform_to_iclass_string_intel(xed_iform_enum_t iform);

#endif
