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
#include "xed-types.h"
#include "xed-reg-enum.h"
#include "xed/xed-encode-check.h"
#include "xed/xed-encode-direct.h"
#include "xed-enc2-private.h"
#include "xed-enc2-check.h"

/// Check functions


void xed_enc2_invalid_cr(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    switch(reg) {
      case XED_REG_CR0:
      case XED_REG_CR2:
      case XED_REG_CR3:
      case XED_REG_CR4:
        break;
      case XED_REG_CR8:
        if (mode == 64)
            break;
        //fallthrough
      default:
        xed_enc2_error("Bad cr %s arg_name %s in function %s", reg, argname, pfn);
    }
}
void xed_enc2_invalid_dr(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_DR0 || reg > XED_REG_DR7) 
        xed_enc2_error("Bad dr %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_seg(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_ES || reg > XED_REG_GS) 
        xed_enc2_error("Bad seg reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_gpr16(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_GPR16_FIRST || reg > XED_REG_GPR16_LAST) 
        xed_enc2_error("Bad gpr16 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_R8W) 
        xed_enc2_error("Bad gpr16 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_gpr32(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_GPR32_FIRST || reg > XED_REG_GPR32_LAST) 
        xed_enc2_error("Bad gpr32 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_R8D) 
        xed_enc2_error("Bad gpr32 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_gpr64(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_GPR64_FIRST || reg > XED_REG_GPR64_LAST) 
        xed_enc2_error("Bad gpr64 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void) mode;
}

void xed_enc2_invalid_gpr16_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg != XED_REG_SI && reg != XED_REG_DI) 
        xed_enc2_error("Bad gpr16 index %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}

void xed_enc2_invalid_gpr32_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_GPR32_FIRST || reg > XED_REG_GPR32_LAST) 
        xed_enc2_error("Bad gpr32 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_R8D) 
        xed_enc2_error("Bad gpr32 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (reg == XED_REG_ESP) 
        xed_enc2_error("Cannot use ESP as gpr32_index, arg_name %s in function %s", argname, pfn);
}
void xed_enc2_invalid_gpr64_index(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_GPR64_FIRST || reg > XED_REG_GPR64_LAST) 
        xed_enc2_error("Bad gpr64 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (reg == XED_REG_RSP) 
        xed_enc2_error("Cannot use RSP as gpr64_index, arg_name %s in function %s", argname, pfn);
    (void) mode;
}



void xed_enc2_invalid_gpr8(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if ( (reg < XED_REG_GPR8_FIRST || reg > XED_REG_GPR8_LAST) &&
         (reg < XED_REG_GPR8h_FIRST || reg > XED_REG_GPR8h_LAST) )
        xed_enc2_error("Bad gpr8 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && (reg >= XED_REG_R8B || (reg >= XED_REG_SPL && reg <= XED_REG_DIL)))
        xed_enc2_error("Bad gpr8 %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_kreg(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_K0 || reg > XED_REG_K7) 
        xed_enc2_error("Bad mask reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_kreg_not0(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_K1 || reg > XED_REG_K7) 
        xed_enc2_error("Bad (!k0) mask reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_mmx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_MMX_FIRST || reg > XED_REG_MMX_LAST) 
        xed_enc2_error("Bad mmx reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_rcsae(xed_uint_t mode, xed_uint_t rcsae,const char* argname,const char* pfn) {
    if (rcsae > 3)
        xed_enc2_error("Bad RCSAE value %d arg_name %s in function %s", rcsae, argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_scale(xed_uint_t mode, xed_uint_t scale,const char* argname,const char* pfn) {
    if (scale != 1 && scale != 2 && scale != 4 && scale != 8)
        xed_enc2_error("Bad scale value %d arg_name %s in function %s", scale, argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_x87(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_X87_FIRST || reg > XED_REG_X87_LAST) 
        xed_enc2_error("Bad x87 reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    (void)mode;
}
void xed_enc2_invalid_xmm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_XMM_FIRST || reg > XED_REG_XMM_LAST) 
        xed_enc2_error("Bad xmm reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_XMM8)
        xed_enc2_error("Bad xmm %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_xmm_avx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_XMM_FIRST || reg > XED_REG_XMM15) 
        xed_enc2_error("Bad xmm reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_XMM8)
        xed_enc2_error("Bad xmm %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_ymm_avx(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_YMM_FIRST || reg > XED_REG_YMM15) 
        xed_enc2_error("Bad ymm reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_YMM8)
        xed_enc2_error("Bad ymm %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_ymm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_YMM_FIRST || reg > XED_REG_YMM_LAST) 
        xed_enc2_error("Bad ymm reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_YMM8)
        xed_enc2_error("Bad ymm %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
void xed_enc2_invalid_zeroing(xed_uint_t mode, xed_uint_t zeroing,const char* argname,const char* pfn) {
    if (zeroing != 0 && zeroing != 1)
        xed_enc2_error("Bad zeroing value %d arg_name %s in function %s", zeroing, argname, pfn);
    (void) mode;
}
void xed_enc2_invalid_zmm(xed_uint_t mode, xed_reg_enum_t reg,const char* argname,const char* pfn) {
    if (reg < XED_REG_ZMM_FIRST || reg > XED_REG_ZMM_LAST) 
        xed_enc2_error("Bad zmm reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64 && reg >= XED_REG_ZMM8)
        xed_enc2_error("Bad zmm %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}

xed_bool_t xed_enc2_check_args = 1;
void xed_enc2_set_check_args(xed_bool_t on) {
    xed_enc2_check_args = on;
}


#if defined(XED_REG_TREG_FIRST_DEFINED)
void xed_enc2_invalid_tmm(xed_uint_t mode, xed_reg_enum_t reg,
                          const char* argname, const char* pfn)
{
    if (reg < XED_REG_TREG_FIRST || reg > XED_REG_TREG_LAST) 
        xed_enc2_error("Bad TMM reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
    if (mode != 64)
        xed_enc2_error("Non-64b-mode TMM reg %s arg_name %s in function %s", xed_reg_enum_t2str(reg), argname, pfn);
}
#endif
