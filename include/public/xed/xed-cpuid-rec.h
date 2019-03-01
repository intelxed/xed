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

#ifndef XED_CPUID_REC_H
# define XED_CPUID_REC_H
#include "xed-types.h"
#include "xed-portability.h"
#include "xed-cpuid-bit-enum.h"
#include "xed-isa-set-enum.h"


typedef struct {
    xed_uint32_t leaf;    // cpuid leaf
    xed_uint32_t subleaf; // cpuid subleaf
    xed_uint32_t bit;     // the bit number for the feature
    xed_reg_enum_t reg;   // the register containing the bit (EAX,EBX,ECX,EDX)
} xed_cpuid_rec_t;

#define XED_MAX_CPUID_BITS_PER_ISA_SET (4)

/// Returns the name of the i'th cpuid bit associated with this isa-set.
/// Call this repeatedly, with 0 <= i <
/// XED_MAX_CPUID_BITS_PER_ISA_SET. Give up when i ==
/// XED_MAX_CPUID_BITS_PER_ISA_SET or the return value is
/// XED_CPUID_BIT_INVALID.
XED_DLL_EXPORT
xed_cpuid_bit_enum_t
xed_get_cpuid_bit_for_isa_set(xed_isa_set_enum_t isaset,
                              xed_uint_t i);

/// This provides the details of the CPUID bit specification, if the
/// enumeration value is not sufficient.  Returns 1 on success and fills in
/// the structure pointed to by p. Returns 0 on failure.
XED_DLL_EXPORT
xed_int_t
xed_get_cpuid_rec(xed_cpuid_bit_enum_t cpuid_bit,
                  xed_cpuid_rec_t* p);

#endif

