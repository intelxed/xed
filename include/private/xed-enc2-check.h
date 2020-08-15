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

#if !defined(XED_ENC2_CHECK_H)
# define XED_ENC2_CHECK_H
    
#include "xed-types.h"
#include "xed-reg-enum.h"

extern xed_bool_t xed_enc2_check_args;

void xed_enc2_invalid_cr(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_dr(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_seg(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr16(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr32(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr64(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr16_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr32_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_gpr64_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);


void xed_enc2_invalid_gpr8(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_kreg(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_kreg_not0(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_mmx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_x87(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_xmm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_xmm_avx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_ymm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_ymm_avx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_zmm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn);
void xed_enc2_invalid_rcsae(xed_uint_t mode, xed_uint_t rcsae,const char* argname,const char* pfn);
void xed_enc2_invalid_scale(xed_uint_t mode, xed_uint_t scale,const char* argname,const char* pfn);
void xed_enc2_invalid_zeroing(xed_uint_t mode, xed_uint_t zeroing,const char* argname,const char* pfn);

# if defined(XED_REG_TREG_FIRST_DEFINED)
void xed_enc2_invalid_tmm(xed_uint_t mode, xed_reg_enum_t reg,
                          const char* argname, const char* pfn);
# endif
#endif
