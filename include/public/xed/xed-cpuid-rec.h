/* BEGIN_LEGAL 

Copyright (c) 2023 Intel Corporation

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

/// @file xed-cpuid-rec.h
/// CPUID getter APIs

#ifndef XED_CPUID_REC_H
# define XED_CPUID_REC_H
#include "xed-types.h"
#include "xed-portability.h"
#include "xed-cpuid-rec-enum.h"
#include "xed-cpuid-group-enum.h"
#include "xed-isa-set-enum.h"

/// @ingroup CPUID
/// @brief a data structure representing a CPUID record
typedef struct {
    xed_uint32_t leaf;      ///< cpuid leaf
    xed_uint32_t subleaf;   ///< cpuid subleaf
    xed_reg_enum_t reg;     ///< the register containing the bits (EAX,EBX,ECX,EDX)
    xed_uint8_t bit_start;  ///< the bit start index for the feature
    xed_uint8_t bit_end;    ///< the bit end index for the feature
    xed_uint32_t value;     ///< the required feature value
} xed_cpuid_rec_t;

#define XED_MAX_CPUID_GROUPS_PER_ISA_SET (2)
#define XED_MAX_CPUID_RECS_PER_GROUP     (4)

/// @ingroup CPUID
/// @brief Returns the name of the i'th cpuid group associated with the given isa-set.
/// This function is called repeatedly, with i = 0 until reaching 
/// XED_MAX_CPUID_GROUPS_PER_ISA_SET or when the return value is
/// XED_CPUID_GROUP_INVALID.
/// An ISA-SET is supported by a chip if CPUID match is found for a single CPUID 
/// group (OR relationship between groups).
XED_DLL_EXPORT
xed_cpuid_group_enum_t 
xed_get_cpuid_group_enum_for_isa_set(xed_isa_set_enum_t isaset, 
                                     xed_uint_t i);
/// @ingroup CPUID
/// @brief Returns the name of the i'th cpuid record associated with the given cpuid group.
/// This function is called repeatedly, with i = 0 until reaching 
/// XED_MAX_CPUID_RECS_PER_GROUP or when the return value is
/// XED_CPUID_REC_INVALID.
/// A cpuid group is satisfied if all of its cpuid records are 
/// set (AND relationship between records).
XED_DLL_EXPORT
xed_cpuid_rec_enum_t 
xed_get_cpuid_rec_enum_for_group(xed_cpuid_group_enum_t group, 
                             xed_uint_t i);
/// @ingroup CPUID
/// @brief provides the details of the CPUID specification, if the
/// enumeration value is not sufficient. 
/// stores the values of the CPUID record in the given pointer p
/// @returns xed_bool_t 1=success , 0=failure
XED_DLL_EXPORT
xed_bool_t
xed_get_cpuid_rec(xed_cpuid_rec_enum_t cpuid_bit,
                  xed_cpuid_rec_t* p);

#endif

