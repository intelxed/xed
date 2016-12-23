/*BEGIN_LEGAL 

Copyright (c) 2016 Intel Corporation

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

/// AVX512 ILD getters

#if !defined(XED_ILD_AVX512_GETTERS_H)
#define XED_ILD_AVX512_GETTERS_H
#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-types.h"
#include "xed-ild.h"


/* ild getters */

static XED_INLINE
xed_uint32_t xed3_operand_get_mask_not0(const xed_decoded_inst_t *d) {
    /* aaa != 0  */
    return xed3_operand_get_mask(d) != 0;
}
static XED_INLINE
xed_uint32_t xed3_operand_get_mask_zero(const xed_decoded_inst_t *d) {
    /* aaa == 0  */
    return xed3_operand_get_mask(d) == 0;
}


#endif
