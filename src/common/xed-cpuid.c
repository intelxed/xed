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


#include "xed-internal-header.h"

extern const xed_cpuid_group_enum_t xed_isa_set_to_cpuid_group_mapping[][XED_MAX_CPUID_GROUPS_PER_ISA_SET];
extern const xed_cpuid_rec_enum_t xed_cpuid_group_to_rec_mapping[][XED_MAX_CPUID_RECS_PER_GROUP];
extern const xed_cpuid_rec_t xed_cpuid_info[];

xed_cpuid_group_enum_t xed_get_cpuid_group_enum_for_isa_set(xed_isa_set_enum_t isaset, xed_uint_t i)
{
    if (isaset > XED_ISA_SET_INVALID &&
        isaset < XED_ISA_SET_LAST &&
        i < XED_MAX_CPUID_GROUPS_PER_ISA_SET)
    {
        return xed_isa_set_to_cpuid_group_mapping[isaset][i];
    }
    return XED_CPUID_GROUP_INVALID;
}

xed_cpuid_rec_enum_t xed_get_cpuid_rec_enum_for_group(xed_cpuid_group_enum_t group, xed_uint_t i)
{
    if (group > XED_CPUID_GROUP_INVALID &&
        group < XED_CPUID_GROUP_LAST &&
        i < XED_MAX_CPUID_RECS_PER_GROUP)
    {
        return xed_cpuid_group_to_rec_mapping[group][i];
    }
    return XED_CPUID_REC_INVALID;
}

xed_bool_t xed_get_cpuid_rec(xed_cpuid_rec_enum_t rec_enum, xed_cpuid_rec_t* cpuid_rec)
{
    if (rec_enum > XED_CPUID_REC_INVALID &&
        rec_enum < XED_CPUID_REC_LAST)
    {
        xed_assert(cpuid_rec!=0);
        *cpuid_rec = xed_cpuid_info[rec_enum];
        return 1;
    }
    return 0;
}

