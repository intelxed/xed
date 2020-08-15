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
/// @file xed-encode-direct.c

////////////////////////////////////////////////////////////////////////////
// This file contains the public interface to the encoder. 
////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-operand-accessors.h"
#include "xed-reg-class.h"
#include "xed-encode-direct.h"
#include <stdarg.h>  // va_list, etc
#include <stdlib.h>  //abort()
#include <stdio.h>  //vfprintf()

#if !defined(_MSC_VER)
// Turn off unused-function warning for this file while we are doing early development
# pragma GCC diagnostic ignored "-Wunused-function"
#endif



/// evex register for evex-VSIB
void enc_evex_vindex_xmm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_sibbase(r,offset&7);
    set_rexx(r,offset>=8);
    set_evexvv(r,!(offset>=16)); // FIXME: check inverted
}
void enc_evex_vindex_ymm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_sibbase(r,offset&7);
    set_rexx(r,offset>=8);
    set_evexvv(r,!(offset>=16)); // FIXME: check inverted
}
void enc_evex_vindex_zmm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ZMM_FIRST;
    set_sibbase(r,offset&7);
    set_rexx(r,offset>=8);
    set_evexvv(r,!(offset>=16)); // FIXME: check inverted
}

/// vex register for vex-VSIB
void enc_vex_vindex_xmm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_sibbase(r,offset&7);
    set_rexx(r,offset>=8);
}
void enc_vex_vindex_ymm(xed_enc2_req_t* r,
                        xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_sibbase(r,offset&7);
    set_rexx(r,offset>=8);
}

// evex registers k0..k7 regs
void enc_evex_vvvv_kreg(xed_enc2_req_t* r,
                        xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_vvvv(r, ~(offset & 7));
    set_evexvv(r,1);
}
void enc_evex_modrm_reg_kreg(xed_enc2_req_t* r,
                            xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_reg(r, offset & 7);
    //set_rexr(r,0);  // ZERO OPTIMIZATION
    //set_evexrr(r,0);
}
void enc_evex_modrm_rm_kreg(xed_enc2_req_t* r,
                            xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_rm(r, offset & 7);
    //set_rexb(r,0);   // ZERO OPTIMIZATION
    //set_rexx(r,0);
}

void enc_vex_vvvv_kreg(xed_enc2_req_t* r,     
                           xed_reg_enum_t dst) {  ///VEX
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_vvvv(r, ~(offset & 7));
}
void enc_modrm_reg_kreg(xed_enc2_req_t* r,
                        xed_reg_enum_t dst) { ///VEX
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,0); // gets inverted on vex emit
}
void enc_modrm_rm_kreg(xed_enc2_req_t* r,
                       xed_reg_enum_t dst) { ///VEX
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST; 
    set_rm(r, offset & 7);
    set_rexb(r,0); // gets inverted on vex emit
}


void enc_evex_kmask(xed_enc2_req_t* r,
                    xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MASK_FIRST;
    set_evexaaa(r, offset & 7);
}

// evex registers vvvv, modrm.reg, modrm.rm for xmm, ymm, zmm
void enc_evex_vvvv_reg_xmm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_vvvv(r, ~(offset & 15));
    set_evexvv(r, !(offset>15));    
}
void enc_evex_modrm_reg_xmm(xed_enc2_req_t* r,
                            xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r, (offset >= 8));
    set_evexrr(r, (offset >= 16));
}
void enc_evex_modrm_rm_xmm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r, (offset >= 8));
    set_rexx(r, (offset >= 16));
}

void enc_evex_vvvv_reg_ymm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_vvvv(r, ~(offset & 15));
    set_evexvv(r, !(offset>15));    
}
void enc_evex_modrm_reg_ymm(xed_enc2_req_t* r,
                            xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r, (offset >= 8));
    set_evexrr(r, (offset >= 16));
}
void enc_evex_modrm_rm_ymm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r, (offset >= 8));
    set_rexx(r, (offset >= 16));
}

void enc_evex_vvvv_reg_zmm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ZMM_FIRST;
    set_vvvv(r, ~(offset & 15));
    set_evexvv(r, !(offset>15));    
}
void enc_evex_modrm_reg_zmm(xed_enc2_req_t* r,
                            xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ZMM_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r, (offset >= 8));
    set_evexrr(r, (offset >= 16));
}
void enc_evex_modrm_rm_zmm(xed_enc2_req_t* r,
                           xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ZMM_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r, (offset >= 8));
    set_rexx(r, (offset >= 16));
}



void enc_evex_vvvv_reg_gpr32(xed_enc2_req_t* r,
                             xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_vvvv(r, ~(offset & 15));
    set_evexvv(r,1);
}
void enc_evex_modrm_reg_gpr32(xed_enc2_req_t* r,
                              xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r, (offset >= 8));
}
void enc_evex_modrm_rm_gpr32(xed_enc2_req_t* r,
                             xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r, (offset >= 8));
}



void enc_evex_vvvv_reg_gpr64(xed_enc2_req_t* r,
                             xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_vvvv(r, ~(offset & 15));
    set_evexvv(r,1);
}
void enc_evex_modrm_reg_gpr64(xed_enc2_req_t* r,
                              xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r, (offset >= 8));
}
void enc_evex_modrm_rm_gpr64(xed_enc2_req_t* r,
                             xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r, (offset >= 8));
}



/// AVX register

void enc_vvvv_reg_xmm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_vvvv(r, ~(offset & 15));
}
void enc_vvvv_reg_ymm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_vvvv(r, ~(offset & 15));
}

#if defined(XED_REG_TREG_FIRST_DEFINED)
void enc_vvvv_reg_tmm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_TREG_FIRST;
    set_vvvv(r, 8|(~(offset & 7)));
}

void enc_modrm_reg_tmm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_TREG_FIRST;
    set_reg(r, offset & 7);
    //set_rexr(r,0); // zero init optimization
}

void enc_modrm_rm_tmm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_TREG_FIRST;
    set_rm(r, offset & 7);
    //set_rexb(r,0); // zero init optimization
}

#endif

void enc_vvvv_reg_gpr32(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_vvvv(r, ~(offset & 15));
}
void enc_vvvv_reg_gpr64(xed_enc2_req_t* r,
                        xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_vvvv(r, ~(offset & 15));
}



void enc_modrm_rm_x87(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ST0;
    set_rm(r, offset & 7);
}
void enc_modrm_reg_xmm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
}
void enc_modrm_rm_xmm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r,offset >= 8);
}
void enc_modrm_reg_ymm(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
}

void enc_modrm_rm_ymm(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_rm(r, offset & 7);
    set_rexb(r,offset >= 8);
}


/// MMX registers

void enc_modrm_reg_mmx(xed_enc2_req_t* r,
                       xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MMX0;
    set_reg(r, offset & 7);
}
void enc_modrm_rm_mmx(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_MMX0;
    set_rm(r, offset & 7);
}

/// GPRs

void enc_modrm_reg_gpr8(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    /* encode modrm.reg with a register.  Might imply a rex bit setting */
    xed_uint_t offset = dst-XED_REG_GPR8_FIRST;   
    if (dst >= XED_REG_AH && dst <= XED_REG_BH)
        offset = dst-XED_REG_GPR8h_FIRST+4;  // AH,CH,DH,BH
   
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
    //SPL, BPL, SIL, DIL need REX no matter what
    if (dst >= XED_REG_SPL && dst <= XED_REG_DIL)
        set_need_rex(r);
}
    
void enc_modrm_rm_gpr8(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    /* encode modrm.rm with a register */
    xed_uint_t offset = dst-XED_REG_GPR8_FIRST; 
    if (dst >= XED_REG_AH && dst <= XED_REG_BH)
        offset = dst-XED_REG_GPR8h_FIRST+4;  // AH,CH,DH,BH

    set_mod(r, 3);
    set_rm(r, offset & 7);
    set_rexb(r, offset >= 8);
    //SPL, BPL, SIL, DIL need REX no matter what
    if (dst >= XED_REG_SPL && dst <= XED_REG_DIL)
        set_need_rex(r);
}

void enc_modrm_reg_gpr16(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    /* encode modrm.reg with a register.  Might imply a rex bit setting */
    xed_uint_t offset =  dst-XED_REG_GPR16_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
}
    
void enc_modrm_rm_gpr16(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    /* encode modrm.rm with a register */
    xed_uint_t offset =  dst-XED_REG_GPR16_FIRST;
    set_mod(r, 3);
    set_rm(r, offset & 7);
    set_rexb(r, offset >= 8);
}





void enc_modrm_reg_gpr32(xed_enc2_req_t* r,
                       xed_reg_enum_t dst) {
    /* encode modrm.reg with a register.  Might imply a rex bit setting */
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
}
    
void enc_modrm_rm_gpr32(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    /* encode modrm.rm with a register */
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_mod(r, 3);
    set_rm(r, offset & 7);
    set_rexb(r, offset >= 8);
}



void enc_modrm_reg_gpr64(xed_enc2_req_t* r,
                       xed_reg_enum_t dst) {
    /* encode modrm.reg with a register.  Might imply a rex bit setting */
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
}
    
void enc_modrm_rm_gpr64(xed_enc2_req_t* r,
                        xed_reg_enum_t dst) {
    /* encode modrm.rm with a register */
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_mod(r, 3);
    set_rm(r, offset & 7);
    set_rexb(r, offset >= 8);
}


 // partial opcode _SRM field

void enc_srm_gpr8(xed_enc2_req_t* r,
                   xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR8_FIRST;
    if (dst >= XED_REG_AH && dst <= XED_REG_BH)
        offset = dst-XED_REG_GPR8h_FIRST+4;  // AH,CH,DH,BH

    set_srm(r, offset & 7);
    set_rexb(r, offset >= 8);
    
    //SPL, BPL, SIL, DIL need REX no matter what
    if (dst >= XED_REG_SPL && dst <= XED_REG_DIL)
        set_need_rex(r);
}

void enc_srm_gpr16(xed_enc2_req_t* r,
                   xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR16_FIRST;
    set_srm(r, offset & 7);
    set_rexb(r, offset >= 8);
}
void enc_srm_gpr32(xed_enc2_req_t* r,
                   xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR32_FIRST;
    set_srm(r, offset & 7);
    set_rexb(r, offset >= 8);
}
void enc_srm_gpr64(xed_enc2_req_t* r,
                   xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_GPR64_FIRST;
    set_srm(r, offset & 7);
    set_rexb(r, offset >= 8);
}

void enc_imm8_reg_xmm(xed_enc2_req_t* r, // _SE imm8 reg
                      xed_reg_enum_t dst) { 
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_imm8_reg(r, offset<<4);
}
void enc_imm8_reg_ymm(xed_enc2_req_t* r,  // _SE imm8 reg
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_imm8_reg(r, offset<<4);
}

void enc_imm8_reg_xmm_and_imm(xed_enc2_req_t* r, // _SE imm8 reg
                              xed_reg_enum_t dst,
                              xed_uint_t imm) { 
    xed_uint_t offset =  dst-XED_REG_XMM_FIRST;
    set_imm8_reg(r, (offset<<4)|imm);
}
void enc_imm8_reg_ymm_and_imm(xed_enc2_req_t* r,  // _SE imm8 reg
                              xed_reg_enum_t dst,
                              xed_uint_t imm) {
    xed_uint_t offset =  dst-XED_REG_YMM_FIRST;
    set_imm8_reg(r, (offset<<4)|imm);
}

// CRs and DRs, SEG regs

void enc_modrm_reg_cr(xed_enc2_req_t* r,  
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_CR_FIRST;
    set_reg(r, offset&7);
    set_rexr(r, offset>=8);
}
void enc_modrm_reg_dr(xed_enc2_req_t* r, 
                      xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_DR_FIRST;
    set_reg(r, offset&7);
}
void enc_modrm_reg_seg(xed_enc2_req_t* r, 
                       xed_reg_enum_t dst) {
    xed_uint_t offset =  dst-XED_REG_ES;
    set_reg(r, offset&7);
}


void emit_modrm_sib(xed_enc2_req_t* r) {
    emit_modrm(r);
    // some base reg encodings require sib and some of those require modrm
    // some base reg encodings require disp (rip-rel)
    if (get_has_sib(r))
        emit_sib(r);
}

////////////////////////////////////////

/// ERROR HANDLING

static xed_user_abort_handler_t* user_abort_handler = 0;

void xed_enc2_set_error_handler(xed_user_abort_handler_t* fn) {
    user_abort_handler = fn;
}

void xed_enc2_error(const char* fmt, ...) { 
    va_list args;

    if (user_abort_handler) {
        va_start(args, fmt);
        (*user_abort_handler)(fmt, args);
        va_end(args);
    }
    else {
        printf("XED ENC2 ERROR: ");
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
        printf(".\n");
    }
    abort(); 
}


///////////////////////////////////



static void scale_test_and_set(xed_enc2_req_t* r, xed_uint_t scale) {
    static const xed_uint_t scale_encode[9] = { 9,0,1,9, 2,9,9,9, 3};
    xed_uint8_t e;
    if (scale > 8)
        xed_enc2_error( "bad scale value");
    e = scale_encode[scale];
    if (e > 8)
        xed_enc2_error( "bad scale value");
    set_sibscale(r, e);
}


// 64b addressing

static void enc_modrm_rm_mem_disp_a64_internal(xed_enc2_req_t* r,
                                               xed_reg_enum_t base,
                                               xed_reg_enum_t indx,
                                               xed_uint_t scale)
{
    //a64 = address size 64
    // FIXME: range test base & index for GPR64 + INVALID
    xed_uint_t offset = base - XED_REG_GPR64_FIRST;

    if (base == XED_REG_RIP) {
        if (get_mod(r) == 1)
            xed_enc2_error("Wrong size displacement for RIP relative addressing");
        set_mod(r,0); // disp32 for RIP-rel
        set_rm(r,5);
        if (indx != XED_REG_INVALID)
            xed_enc2_error( "cannot have index register with RIP as base");
    }
    else if (base == XED_REG_INVALID ||
             base == XED_REG_RSP ||
             base == XED_REG_R12 ||
             indx != XED_REG_INVALID) {         // need sib
        xed_uint_t offset_indx;
        set_has_sib(r);
        set_rm(r,4);

        if (base == XED_REG_INVALID) {
            set_sibbase(r,5);
        }
        else { 
            set_sibbase(r, offset & 7);
            set_rexb(r, offset >= 8);
        }
        
        // nothing speical required if base == XED_REG_RBP or XED_REG_R13
        // since we already have a displacment; the mod field will be set
        // to 1 or 2.

        if (indx == XED_REG_INVALID) {
            set_sibindex(r,4);
        }
        else {
            offset_indx = indx - XED_REG_GPR64_FIRST;
            if (indx == XED_REG_RSP)
                xed_enc2_error( "bad index register == RSP");
            set_sibindex(r,offset_indx & 7);
            set_rexx(r,offset_indx >= 8);

            scale_test_and_set(r, scale);
        }
    }
    else { // reasonable base, no index
        set_rm(r, offset & 7);
        set_rexb(r, offset >= 8);
    }
}
static void enc_modrm_rm_mem_nodisp_a64_internal(xed_enc2_req_t* r,
                                                 xed_reg_enum_t base,
                                                 xed_reg_enum_t indx,
                                                 xed_uint_t scale)
{
    //a64 = address size 64
    // FIXME: range test base & index for GPR64 + INVALID
    xed_uint_t offset = base - XED_REG_GPR64_FIRST;

    if (base == XED_REG_RIP) {
        set_has_disp32(r);// supply a fake zero valued disp
        set_rm(r,5);
        if (indx != XED_REG_INVALID)
            xed_enc2_error( "cannot have index register with RIP as base");
    }
    else if (base == XED_REG_INVALID ||
             base == XED_REG_RSP ||
             base == XED_REG_R12 ||
             base == XED_REG_RBP ||
             base == XED_REG_R13 ||
             indx != XED_REG_INVALID) {        // need sib
        xed_uint_t offset_indx;
     
        set_has_sib(r);
        set_rm(r,4);

        if (base == XED_REG_INVALID) {
            set_sibbase(r,5);
        }
        else { 
            set_sibbase(r, offset & 7);
            set_rexb(r, offset >= 8);
        }
        
        if ( base == XED_REG_RBP || base == XED_REG_R13  ) {
            set_mod(r,1);              // potentially overwriting earlier setting
            set_has_disp8(r);          // force a disp8 with value 0.
        }

        if (indx == XED_REG_INVALID) {
            set_sibindex(r,4);
        }
        else {
            offset_indx = indx - XED_REG_GPR64_FIRST;
            if (indx == XED_REG_RSP)
                xed_enc2_error( "bad index register == RSP");
            set_sibindex(r,offset_indx & 7);
            set_rexx(r,offset_indx >= 8);

            scale_test_and_set(r, scale);
        }
    }
    else { // reasonable base, no index
        set_rm(r,offset & 7);
        set_rexb(r, offset >= 8);
    }
}

void enc_modrm_rm_mem_bisd32_a64(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,2); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_bd32_a64(xed_enc2_req_t* r,
                                   xed_reg_enum_t base)
{
    set_mod(r,2); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,XED_REG_INVALID,0);
}
void enc_modrm_rm_mem_bisd8_a64(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx,
                                xed_uint_t scale)
{
    set_mod(r,1); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_bd8_a64(xed_enc2_req_t* r,
                              xed_reg_enum_t base)
{
    set_mod(r,1); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,XED_REG_INVALID,0);
}
void enc_modrm_rm_mem_bis_a64(xed_enc2_req_t* r,
                              xed_reg_enum_t base,
                              xed_reg_enum_t indx,
                              xed_uint_t scale)
{
    set_mod(r,0); // no-disp (may be overwritten if funky base specified)
    enc_modrm_rm_mem_nodisp_a64_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_b_a64(xed_enc2_req_t* r,
                            xed_reg_enum_t base)
{
    set_mod(r,0); // no-disp (may be overwritten if funky base specified)
    enc_modrm_rm_mem_nodisp_a64_internal(r,base,XED_REG_INVALID,0);
}


// 64b avx2 vsib

static void enc_modrm_vsib_bis_a64_internal_nodisp(xed_enc2_req_t* r,
                                                   xed_reg_enum_t base,
                                                   xed_reg_enum_t indx,
                                                   xed_uint_t scale,
                                                   xed_reg_enum_t vreg_first) {
    const xed_uint_t index_offset = indx-vreg_first;
    const xed_uint_t base_offset  = base-XED_REG_GPR64_FIRST;
    set_mod(r,0); // no-disp (may be overwritten if funky base specified)
    set_rm(r,4); // need sib
    set_has_sib(r);

    
    set_sibindex(r, index_offset & 7); // encode x/y/zmm as sibscale
    set_rexx(r, index_offset >= 8);
    set_evexvv(r, !(index_offset >= 16));
    
    scale_test_and_set(r,scale);

    if (base == XED_REG_RBP || base == XED_REG_R13) {
        set_mod(r,1);              // overwriting earlier setting
        set_has_disp8(r);          // force a disp8 with value 0.
    }
    set_sibbase(r,base_offset & 7);
    set_rexb(r,base_offset >= 8);
}
static void enc_modrm_vsib_a64_internal_disp(xed_enc2_req_t* r,
                                             xed_reg_enum_t base,
                                             xed_reg_enum_t indx,
                                             xed_uint_t scale,
                                             xed_reg_enum_t vreg_first) {
    const xed_uint_t index_offset = indx-vreg_first;
    const xed_uint_t base_offset  = base-XED_REG_GPR64_FIRST;
    set_rm(r,4); // need sib
    set_has_sib(r);
    
    set_sibindex(r, index_offset & 7); // encode xmm as sibscale
    set_rexx(r, index_offset >= 8);
    set_evexvv(r, !(index_offset >= 16));
    
    scale_test_and_set(r,scale);

    set_sibbase(r,base_offset & 7);
    set_rexb(r,base_offset >= 8);
}


void enc_avx_modrm_vsib_xmm_bis_a64(xed_enc2_req_t* r,
                                    xed_reg_enum_t base,
                                    xed_reg_enum_t indx,
                                    xed_uint_t scale) {
    enc_modrm_vsib_bis_a64_internal_nodisp(r,base,indx,scale,XED_REG_XMM_FIRST);
}



void enc_avx_modrm_vsib_xmm_bisd8_a64(xed_enc2_req_t* r,
                                      xed_reg_enum_t base,
                                      xed_reg_enum_t indx,
                                      xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx_modrm_vsib_xmm_bisd32_a64(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}

void enc_avx_modrm_vsib_ymm_bis_a64(xed_enc2_req_t* r,
                                    xed_reg_enum_t base,
                                    xed_reg_enum_t indx,
                                    xed_uint_t scale) {
    enc_modrm_vsib_bis_a64_internal_nodisp(r,base,indx,scale,XED_REG_YMM_FIRST);
}

void enc_avx_modrm_vsib_ymm_bisd8_a64(xed_enc2_req_t* r,
                                      xed_reg_enum_t base,
                                      xed_reg_enum_t indx,
                                      xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx_modrm_vsib_ymm_bisd32_a64(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


// 64b avx512 vsib

void enc_avx512_modrm_vsib_xmm_bis_a64(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a64_internal_nodisp(r,base,indx,scale,XED_REG_XMM_FIRST);
}

void enc_avx512_modrm_vsib_xmm_bisd8_a64(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_xmm_bisd32_a64(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


void enc_avx512_modrm_vsib_ymm_bis_a64(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a64_internal_nodisp(r,base,indx,scale,XED_REG_YMM_FIRST);
}

void enc_avx512_modrm_vsib_ymm_bisd8_a64(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_ymm_bisd32_a64(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


void enc_avx512_modrm_vsib_zmm_bis_a64(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a64_internal_nodisp(r,base,indx,scale,XED_REG_ZMM_FIRST);
}

void enc_avx512_modrm_vsib_zmm_bisd8_a64(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_ZMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_zmm_bisd32_a64(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a64_internal_disp(r,base,indx,scale, XED_REG_ZMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}




/// 32b addressing

static void enc_modrm_rm_mem_disp_a32_internal(xed_enc2_req_t* r,
                                               xed_reg_enum_t base,
                                               xed_reg_enum_t indx,
                                               xed_uint_t scale)
{
    //a32  (32b mode or 64b mode)  for MOD=1 (disp8) or MOD=2 (disp32)
    // FIXME: better not have rex.b or rex.x set in 32b mode
    // FIXME: range test base & index for GPR32 + INVALID
    xed_uint_t offset = base - XED_REG_GPR32_FIRST;

    if (base == XED_REG_INVALID ||
        base == XED_REG_ESP ||
        base == XED_REG_R12D ||
        indx != XED_REG_INVALID) {
        xed_uint_t offset_indx;
        // need sib
        set_has_sib(r);
        set_rm(r,4);
        if (base == XED_REG_INVALID) {
            set_sibbase(r,5);
        }
        else { 
            set_sibbase(r, offset & 7);
            set_rexb(r, offset >= 8); 
        }

        if (indx == XED_REG_INVALID) {
            set_sibindex(r,4);
        }
        else {
            offset_indx = indx - XED_REG_GPR32_FIRST;
            if (indx == XED_REG_ESP)
                xed_enc2_error( "bad index register == ESP");
            set_sibindex(r,offset_indx & 7);
            set_rexx(r,offset_indx >= 8);

            scale_test_and_set(r, scale);
        }
    }
    else { // reasonable base, no index
        set_rm(r,offset & 7);
        set_rexb(r, offset >= 8);
    }
}

static void enc_modrm_rm_mem_nodisp_a32_internal(xed_enc2_req_t* r,
                                                 xed_reg_enum_t base,
                                                 xed_reg_enum_t indx,
                                                 xed_uint_t scale)
{
    //a32  (32b mode or 64b mode)
    // FIXME: better not have rex.b or rex.x set in 32b mode
    // FIXME: range test base & index for GPR32 + INVALID
    
    // Note: using EBP or R13 as a base register requires that we add a
    // displacement. We add a disp8 with the value 0.
    
    xed_uint_t offset = base - XED_REG_GPR32_FIRST;

    if (base == XED_REG_INVALID ||
        base == XED_REG_ESP     ||
        base == XED_REG_R12D    ||
        base == XED_REG_EBP     ||
        base == XED_REG_R13D    ||
        indx != XED_REG_INVALID  ) {         // need sib
        xed_uint_t offset_indx;

        set_has_sib(r);
        set_rm(r,4);
        if (base == XED_REG_INVALID) {
            set_sibbase(r,5);
        }
        else { 
            set_sibbase(r, offset & 7);
            set_rexb(r, offset >= 8); 
        }
        if ( base == XED_REG_EBP || base == XED_REG_R13D  ) {
            set_mod(r,1);              // potentially overwriting earlier setting
            set_has_disp8(r);          // force a disp8 with value 0.
        }

        if (indx == XED_REG_INVALID) {
            set_sibindex(r,4);
        }
        else {
            offset_indx = indx - XED_REG_GPR32_FIRST;
            if (indx == XED_REG_ESP)
                xed_enc2_error( "bad index register == ESP");
            set_sibindex(r,offset_indx & 7);
            set_rexx(r,offset_indx >= 8);
                           
            scale_test_and_set(r, scale);
        }
    }
    else { // reasonable base, no index
        set_rm(r,offset & 7);
        set_rexb(r, offset >= 8);
    }
}



void enc_modrm_rm_mem_bisd32_a32(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,2); // disp32
    enc_modrm_rm_mem_disp_a32_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_bd32_a32(xed_enc2_req_t* r,
                               xed_reg_enum_t base)
{
    set_mod(r,2); // disp32
    enc_modrm_rm_mem_disp_a32_internal(r,base,XED_REG_INVALID,0);
}
void enc_modrm_rm_mem_bisd8_a32(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx,
                                xed_uint_t scale)
{
    set_mod(r,1); // disp8
    enc_modrm_rm_mem_disp_a32_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_bd8_a32(xed_enc2_req_t* r,
                              xed_reg_enum_t base)
{
    set_mod(r,1); // disp8
    enc_modrm_rm_mem_disp_a32_internal(r,base,XED_REG_INVALID,0);
}
void enc_modrm_rm_mem_bis_a32(xed_enc2_req_t* r,
                              xed_reg_enum_t base,
                              xed_reg_enum_t indx,
                              xed_uint_t scale)
{
    set_mod(r,0); // no-disp (may be overwritten if EBP/R13D used as base)
    enc_modrm_rm_mem_nodisp_a32_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_b_a32(xed_enc2_req_t* r,
                            xed_reg_enum_t base)

{
    set_mod(r,0); // no-disp (may be overwritten if EBP/R13D used as base)
    enc_modrm_rm_mem_nodisp_a32_internal(r,base,XED_REG_INVALID,0);
}





static void enc_modrm_vsib_bis_a32_internal_nodisp(xed_enc2_req_t* r,
                                                   xed_reg_enum_t base,
                                                   xed_reg_enum_t indx,
                                                   xed_uint_t scale,
                                                   xed_reg_enum_t vreg_first) {
    const xed_uint_t index_offset = indx-vreg_first;
    const xed_uint_t base_offset  = base-XED_REG_GPR32_FIRST;
    set_mod(r,0); // no-disp (may be overwritten if funky base specified)
    set_rm(r,4); // need sib
    set_has_sib(r);
    
    set_sibindex(r, index_offset & 7); // encode xmm as sibscale
    set_rexx(r, index_offset >= 8);
    set_evexvv(r, !(index_offset >= 16));
    
    scale_test_and_set(r,scale);

    if (base == XED_REG_EBP || base == XED_REG_R13D) {
        set_mod(r,1);              // overwriting earlier setting
        set_has_disp8(r);          // force a disp8 with value 0.
    }
    set_sibbase(r,base_offset & 7);
    set_rexb(r,base_offset >= 8);
}
static void enc_modrm_vsib_a32_internal_disp(xed_enc2_req_t* r,
                                             xed_reg_enum_t base,
                                             xed_reg_enum_t indx,
                                             xed_uint_t scale,
                                             xed_reg_enum_t vreg_first) {
    const xed_uint_t index_offset = indx-vreg_first;
    const xed_uint_t base_offset  = base-XED_REG_GPR32_FIRST;
    set_rm(r,4); // need sib
    set_has_sib(r);
    
    set_sibindex(r, index_offset & 7); // encode xmm as sibscale
    set_rexx(r, index_offset >= 8);
    set_evexvv(r, !(index_offset >= 16));
    
    scale_test_and_set(r,scale);

    set_sibbase(r,base_offset & 7);
    set_rexb(r,base_offset >= 8);
}


void enc_avx_modrm_vsib_xmm_bis_a32(xed_enc2_req_t* r,
                                    xed_reg_enum_t base,
                                    xed_reg_enum_t indx,
                                    xed_uint_t scale) {
    enc_modrm_vsib_bis_a32_internal_nodisp(r,base,indx,scale,XED_REG_XMM_FIRST);
}



void enc_avx_modrm_vsib_xmm_bisd8_a32(xed_enc2_req_t* r,
                                      xed_reg_enum_t base,
                                      xed_reg_enum_t indx,
                                      xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx_modrm_vsib_xmm_bisd32_a32(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}

void enc_avx_modrm_vsib_ymm_bis_a32(xed_enc2_req_t* r,
                                    xed_reg_enum_t base,
                                    xed_reg_enum_t indx,
                                    xed_uint_t scale) {
    enc_modrm_vsib_bis_a32_internal_nodisp(r,base,indx,scale,XED_REG_YMM_FIRST);
}

void enc_avx_modrm_vsib_ymm_bisd8_a32(xed_enc2_req_t* r,
                                      xed_reg_enum_t base,
                                      xed_reg_enum_t indx,
                                      xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx_modrm_vsib_ymm_bisd32_a32(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


// 64b avx512 vsib

void enc_avx512_modrm_vsib_xmm_bis_a32(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a32_internal_nodisp(r,base,indx,scale,XED_REG_XMM_FIRST);
}

void enc_avx512_modrm_vsib_xmm_bisd8_a32(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_xmm_bisd32_a32(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_XMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


void enc_avx512_modrm_vsib_ymm_bis_a32(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a32_internal_nodisp(r,base,indx,scale,XED_REG_YMM_FIRST);
}

void enc_avx512_modrm_vsib_ymm_bisd8_a32(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_ymm_bisd32_a32(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_YMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}


void enc_avx512_modrm_vsib_zmm_bis_a32(xed_enc2_req_t* r,
                                       xed_reg_enum_t base,
                                       xed_reg_enum_t indx,
                                       xed_uint_t scale) {
    enc_modrm_vsib_bis_a32_internal_nodisp(r,base,indx,scale,XED_REG_ZMM_FIRST);
}

void enc_avx512_modrm_vsib_zmm_bisd8_a32(xed_enc2_req_t* r,
                                         xed_reg_enum_t base,
                                         xed_reg_enum_t indx,
                                         xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_ZMM_FIRST);
    set_mod(r,1); // disp8
    set_has_disp8(r); 
}

void enc_avx512_modrm_vsib_zmm_bisd32_a32(xed_enc2_req_t* r,
                                          xed_reg_enum_t base,
                                          xed_reg_enum_t indx,
                                          xed_uint_t scale) {
    enc_modrm_vsib_a32_internal_disp(r,base,indx,scale, XED_REG_ZMM_FIRST);
    set_mod(r,2); // disp32
    set_has_disp32(r); 
}









// 16b addressing

static void enc_modrm_rm_mem_nodisp_a16_internal(xed_enc2_req_t* r,
                                                 xed_reg_enum_t base,
                                                 xed_reg_enum_t indx)
{
    //FIXME: replace with a table.
    // this has no disp, except for the no-base-or-index case (MOD=00)
    switch(base) {
      case XED_REG_BX:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,0); break;
          case XED_REG_DI:            set_rm(r,1); break;
          case XED_REG_INVALID:       set_rm(r,7); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_BP:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,2); break;
          case XED_REG_DI:            set_rm(r,3); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_INVALID:  // look at index
        switch(indx) {
          case XED_REG_BX:            set_rm(r,7); break;
          case XED_REG_SI:            set_rm(r,4); break;
          case XED_REG_DI:            set_rm(r,5); break;
          case XED_REG_INVALID:       set_rm(r,6); break; // disp16!
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_SI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,0); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,4); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_DI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,1); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,5); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      default:
        xed_enc2_error("Bad 16b base reg");
    }
}



static void enc_modrm_rm_mem_a16_disp_internal(xed_enc2_req_t* r,
                                               xed_reg_enum_t base,
                                               xed_reg_enum_t indx)
{
    //FIXME: replace with a table.
    // this has a disp8 or disp16 (MOD=1 or 2)
    switch(base) {
      case XED_REG_BX:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,0); break;
          case XED_REG_DI:            set_rm(r,1); break;
          case XED_REG_INVALID:       set_rm(r,7); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_BP:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,2); break;
          case XED_REG_DI:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,6); break; 
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_INVALID:  // look at index
        switch(indx) {
          case XED_REG_BX:            set_rm(r,7); break;
          case XED_REG_BP:            set_rm(r,6); break;
          case XED_REG_SI:            set_rm(r,4); break;
          case XED_REG_DI:            set_rm(r,5); break;

          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_SI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,0); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,4); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      case XED_REG_DI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,1); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,5); break;
          default:
            xed_enc2_error("Bad 16b index reg");
        }
      default:
        xed_enc2_error("Bad 16b base reg");
    }
}

void enc_modrm_rm_mem_bi_a16(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx)
{
    set_mod(r,0);
    enc_modrm_rm_mem_nodisp_a16_internal(r,base,indx);
}
void enc_modrm_rm_mem_b_a16(xed_enc2_req_t* r,
                            xed_reg_enum_t base)
{
    set_mod(r,0);
    enc_modrm_rm_mem_nodisp_a16_internal(r,base,XED_REG_INVALID);
}
void enc_modrm_rm_mem_bid8_a16(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx)
{
    set_mod(r,1);
    enc_modrm_rm_mem_a16_disp_internal(r,base,indx);
}
void enc_modrm_rm_mem_bd8_a16(xed_enc2_req_t* r,
                                xed_reg_enum_t base)
{
    set_mod(r,1);
    enc_modrm_rm_mem_a16_disp_internal(r,base,XED_REG_INVALID);
}
void enc_modrm_rm_mem_bid16_a16(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx)
{
    set_mod(r,2);
    enc_modrm_rm_mem_a16_disp_internal(r,base,indx);
}
void enc_modrm_rm_mem_bd16_a16(xed_enc2_req_t* r,
                                 xed_reg_enum_t base)
{
    set_mod(r,2);
    enc_modrm_rm_mem_a16_disp_internal(r,base,XED_REG_INVALID);
}

/// handling partial opcodes

xed_uint8_t emit_partial_opcode_and_rmreg(xed_enc2_req_t* r,
                                          xed_uint8_t opcode,
                                          xed_reg_enum_t rmreg,
                                          xed_reg_enum_t first)
{
    xed_uint_t offset = rmreg - first;
    xed_uint8_t opcode_out = opcode | (offset & 7);
    set_rexb(r, offset >= 8);
    return opcode_out;
}
xed_uint8_t emit_partial_opcode_and_rmreg_gpr16(xed_enc2_req_t* r,
                                                xed_uint8_t opcode,
                                                xed_reg_enum_t rmreg)
{
    return emit_partial_opcode_and_rmreg(r,opcode,rmreg, XED_REG_GPR16_FIRST);
}
xed_uint8_t emit_partial_opcode_and_rmreg_gpr32(xed_enc2_req_t* r,
                                                xed_uint8_t opcode,
                                                xed_reg_enum_t rmreg)
{
    return emit_partial_opcode_and_rmreg(r,opcode,rmreg, XED_REG_GPR32_FIRST);
}
xed_uint8_t emit_partial_opcode_and_rmreg_gpr64(xed_enc2_req_t* r,
                                                xed_uint8_t opcode,
                                                xed_reg_enum_t rmreg)
{
    return emit_partial_opcode_and_rmreg(r,opcode,rmreg, XED_REG_GPR64_FIRST);
}


void xed_emit_seg_prefix(xed_enc2_req_t* r,
                         xed_reg_enum_t reg) {
    static const xed_uint8_t seg_prefixes[] = { 0x26, 0x2e, 0x36, 0x3e, 0x64, 0x65 };
    if (reg >= XED_REG_ES && reg <= XED_REG_GS) {
        xed_uint_t offset = reg - XED_REG_ES;
        emit_u8(r,seg_prefixes[offset]);
    }
    else {
        xed_enc2_error("Bad segment register prefix");
    }
}

xed_int32_t xed_chose_evex_scaled_disp(xed_enc2_req_t* r,
                                       xed_int32_t requested_displacement,
                                       xed_uint32_t reference_width_bytes)
{
    xed_int32_t scaled_displacement = requested_displacement / reference_width_bytes;
    if (scaled_displacement >= -128 && scaled_displacement <= 127) {
        set_mod(r,1);
        set_has_disp8(r);
        return scaled_displacement;
    }
    set_mod(r,2);
    set_has_disp32(r);
    return requested_displacement;
}

xed_int32_t xed_chose_evex_scaled_disp16(xed_enc2_req_t* r,
                                         xed_int32_t requested_displacement,
                                         xed_uint32_t reference_width_bytes)
{
    xed_int32_t scaled_displacement = requested_displacement / reference_width_bytes;
    if (scaled_displacement >= -128 && scaled_displacement <= 127) {
        set_mod(r,1);
        set_has_disp8(r);
        return scaled_displacement;
    }
    set_mod(r,2);
    set_has_disp16(r);
    return requested_displacement;
}
