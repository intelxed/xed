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

#include "xed-internal-header.h"
#include "xed-chip-features.h"
#include "xed-chip-features-private.h" // for xed_test_chip_features()
#include "xed-chip-features-table.h" 
void
xed_get_chip_features(xed_chip_features_t* p, xed_chip_enum_t chip)
{
    if (p)
    {
        if (chip < XED_CHIP_LAST)
        {
            xed_uint_t i;
            for(i=0;i<XED_FEATURE_VECTOR_MAX;i++)
                p->f[i] = xed_chip_features[chip][i];
        }
        else
        {
            xed_uint_t i;
            for(i=0;i<XED_FEATURE_VECTOR_MAX;i++)
                p->f[i] = 0;
        }
    }
}


static XED_INLINE void
set_bit(xed_uint64_t* p,
        xed_uint64_t bitnum,
        xed_bool_t value)
{
    const xed_uint64_t one = 1;
    // turn off the existing bit in *p
    const xed_uint64_t q = *p & ~(one<<bitnum);
    // OR-in the new bit, shifted to the right spot.
    *p = q | ( (XED_CAST(xed_uint64_t,value)&1) << bitnum);
}

void
xed_modify_chip_features(xed_chip_features_t* p,
                         xed_isa_set_enum_t isa_set,
                         xed_bool_t present)
{
    if (p)
    {
        const unsigned int f = XED_CAST(unsigned int,isa_set);
        const unsigned int n = f / 64;
        set_bit(p->f+n, f-(64*n), present);
   }
}

xed_bool_t
xed_test_chip_features(xed_chip_features_t* p,
                       xed_isa_set_enum_t isa_set)
{
    const xed_uint64_t one = 1;
    const unsigned int n = XED_CAST(unsigned int,isa_set) / 64;
    const unsigned int r = XED_CAST(unsigned int,isa_set) - (64*n);
    if (p->f[n] & (one<<r))
        return 1;
    return 0;
}

