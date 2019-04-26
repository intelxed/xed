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
#include "xed-encode-private.h"
#include "xed-operand-accessors.h"
#include "xed-reg-class.h"
#include "xed-encode-direct.h"

// Turn off unused-function warning for this file while we are doing early development
#pragma GCC diagnostic ignored "-Wunused-function"


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

static const xed_uint_t scale_encode[9] = { 9,0,1,9, 2,9,9,9, 3};

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


void enc_modrm_reg_gpr8(xed_enc2_req_t* r,
                         xed_reg_enum_t dst) {
    /* encode modrm.reg with a register.  Might imply a rex bit setting */
    xed_uint_t offset = dst-XED_REG_GPR8_FIRST;   
    if (dst >= XED_REG_AH && dst <= XED_REG_BH)
        offset = dst-XED-REG_GPR8h_FIRST;  // AH,CH,DH,BH
   
    set_reg(r, offset & 7);
    set_rexr(r,offset >= 8);
    //SIL,DIL,BPL,SPL need REX no matter what
    if (dst >= XED_REG_SIL && dst <= XED_REG_SPL)
        set_need_rex(r);
}
    
void enc_modrm_rm_gpr8(xed_enc2_req_t* r,
                      xed_reg_enum_t dst) {
    /* encode modrm.rm with a register */
    xed_uint_t offset = dst-XED_REG_GPR8_FIRST; 
    if (dst >= XED_REG_AH && dst <= XED_REG_BH)
        offset = dst-XED-REG_GPR8h_FIRST;  // AH,CH,DH,BH

    set_mod(r, 3);
    set_rm(r, offset & 7);
    set_rexb(r, offset >= 8);
    //SIL,DIL,BPL,SPL need REX no matter what
    if (dst >= XED_REG_SIL && dst <= XED_REG_SPL)  
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

void emit_modrm_sib(xed_enc2_req_t* r) {
    emit_modrm(r);
    // some base reg encodings require sib and some of those require modrm
    // some base reg encodings require disp (rip-rel)
    if (get_has_sib(r))
        emit_sib(r);
}

void enc_error(xed_enc2_req_t* r, char const* msg) {
    // requires compilation with --messages --asserts
    XED2DIE((xed_log_file,"%s\n", msg));
    xed_assert(0);
}


static void scale_test_and_set(xed_enc2_req_t* r, xed_uint_t scale) {
    xed_uint8_t e = scale_encode[scale];
    if (scale > 8 || e > 8)
        enc_error(r, "bad scale value");
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
            enc_error(r,"Wrong size displacement for RIP relative addressing");
        set_mod(r,0); // disp32 for RIP-rel
        set_rm(r,5);
        if (indx != XED_REG_INVALID)
            enc_error(r, "cannot have index register with RIP as base");
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
                enc_error(r, "bad index register == RSP");
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
            enc_error(r, "cannot have index register with RIP as base");
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
                enc_error(r, "bad index register == RSP");
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

void enc_modrm_rm_mem_disp32_a64(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,2); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_disp8_a64(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx,
                                xed_uint_t scale)
{
    set_mod(r,1); 
    enc_modrm_rm_mem_disp_a64_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_nodisp_a64(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,0); // no-disp (may be overwritten if funky base specified)
    enc_modrm_rm_mem_nodisp_a64_internal(r,base,indx,scale);
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
                enc_error(r, "bad index register == ESP");
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
                enc_error(r, "bad index register == ESP");
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



void enc_modrm_rm_mem_disp32_a32(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,2); // disp32
    enc_modrm_rm_mem_disp_a32_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_disp8_a32(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx,
                                xed_uint_t scale)
{
    set_mod(r,1); // disp8
    enc_modrm_rm_mem_disp_a32_internal(r,base,indx,scale);
}
void enc_modrm_rm_mem_nodisp_a32(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx,
                                 xed_uint_t scale)
{
    set_mod(r,0); // no-disp (may be overwritten if EBP/R13D used as base)
    enc_modrm_rm_mem_nodisp_a32_internal(r,base,indx,scale);
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
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_BP:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,2); break;
          case XED_REG_DI:            set_rm(r,3); break;
          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_INVALID:  // look at index
        switch(indx) {
          case XED_REG_BX:            set_rm(r,7); break;
          case XED_REG_SI:            set_rm(r,4); break;
          case XED_REG_DI:            set_rm(r,5); break;
          case XED_REG_INVALID:       set_rm(r,6); break; // disp16!
          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_SI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,0); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,4); break;
          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_DI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,1); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,5); break;
          default:
            enc_error(r,"Bad 16b index reg");
        }
      default:
        enc_error(r,"Bad 16b base reg");
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
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_BP:
        switch(indx) {
          case XED_REG_SI:            set_rm(r,2); break;
          case XED_REG_DI:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,6); break; 
          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_INVALID:  // look at index
        switch(indx) {
          case XED_REG_BX:            set_rm(r,7); break;
          case XED_REG_BP:            set_rm(r,6); break;
          case XED_REG_SI:            set_rm(r,4); break;
          case XED_REG_DI:            set_rm(r,5); break;

          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_SI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,0); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,4); break;
          default:
            enc_error(r,"Bad 16b index reg");
        }
      case XED_REG_DI:
        switch(indx) {
          case XED_REG_BX:            set_rm(r,1); break;
          case XED_REG_BP:            set_rm(r,3); break;
          case XED_REG_INVALID:       set_rm(r,5); break;
          default:
            enc_error(r,"Bad 16b index reg");
        }
      default:
        enc_error(r,"Bad 16b base reg");
    }
}

void enc_modrm_rm_mem_nodisp_a16(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx)
{
    set_mod(r,0);
    enc_modrm_rm_mem_nodisp_a16_internal(r,base,indx);
}
void enc_modrm_rm_mem_disp8_a16(xed_enc2_req_t* r,
                                xed_reg_enum_t base,
                                xed_reg_enum_t indx)
{
    set_mod(r,1);
    enc_modrm_rm_mem_a16_disp_internal(r,base,indx);
}
void enc_modrm_rm_mem_disp16_a16(xed_enc2_req_t* r,
                                 xed_reg_enum_t base,
                                 xed_reg_enum_t indx)
{
    set_mod(r,2);
    enc_modrm_rm_mem_a16_disp_internal(r,base,indx);
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
    return opcode_out
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
xed_uint8_t emit_partial_opcode_and_rmreg_gpr32(xed_enc2_req_t* r,
                                                xed_uint8_t opcode,
                                                xed_reg_enum_t rmreg)
{
    return emit_partial_opcode_and_rmreg(r,opcode,rmreg, XED_REG_GPR64_FIRST);
}

////////////////////////////////////////////////////////////////////////////////

// INSTRUCTIONS

// FIXME: what about 16b moves in 16b mode?
//    add _osz{16,32,64}? assumes a mode...

void encode_mov16_reg_reg(xed_enc2_req_t* r,
                          xed_reg_enum_t dst,
                          xed_reg_enum_t src)
{  // this works for 16b moves in 32b or 64b mode. assumes two GPR16 inputs.

    enc_modrm_reg_gpr16(r,dst); // might also set rex bits
    enc_modrm_rm_gpr16(r,src);  // might also set rex bits
    emit(r,0x66);
    emit_rex_if_needed(r);
    emit(r,0x8B);
    emit_modrm(r);
}
void encode_mov32_reg_reg(xed_enc2_req_t* r,
                          xed_reg_enum_t dst,
                          xed_reg_enum_t src)
{  // this works for 32b moves in 32b or 64b mode. assumes two GPR32 inputs.

    enc_modrm_reg_gpr32(r,dst); // might also set rex bits
    enc_modrm_rm_gpr32(r,src);  // might also set rex bits
    emit_rex_if_needed(r);
    emit(r,0x8B);
    emit_modrm(r);
}
void encode_mov64_reg_reg(xed_enc2_req_t* r,
                          xed_reg_enum_t dst,
                          xed_reg_enum_t src)
{  // this works for 64b moves in 64b mode. assumes two GPR64 inputs.
    set_rexw(r);
    enc_modrm_reg_gpr64(r,dst); // might also set rex bits
    enc_modrm_rm_gpr64(r,src);  // might also set rex bits
    emit_rex(r);
    emit(r,0x8B);
    emit_modrm(r);
}




void encode_mov32_reg_mem_disp32_a32(xed_enc2_req_t* r,
                                     xed_reg_enum_t dst,
                                     xed_reg_enum_t base,
                                     xed_reg_enum_t indx,
                                     xed_uint_t scale,
                                     xed_int32_t disp) 

{  // this works for 32b moves in 32b mode. 

    enc_modrm_reg_gpr32(r,dst);

    // FIXME: copies disp32 twice unnecessarily... could just emit it
    enc_modrm_rm_mem_disp32_a32(r,base,indx,scale);  
    emit_rex_if_needed(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
    emit_i32(r,disp);
}
void encode_mov32_reg_mem_disp8_a32(xed_enc2_req_t* r,
                                    xed_reg_enum_t dst,
                                    xed_reg_enum_t base,
                                    xed_reg_enum_t indx,
                                    xed_uint_t scale,
                                    xed_int8_t disp) 

{  // this works for 32b moves in 32b mode. 

    enc_modrm_reg_gpr32(r,dst);

    // FIXME: copies disp32 twice unnecessarily... could just emit it
    enc_modrm_rm_mem_disp8_a32(r,base,indx,scale);  
    emit_rex_if_needed(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
    emit_i8(r,disp);
}
void encode_mov32_reg_mem_nodisp_a32(xed_enc2_req_t* r,
                                     xed_reg_enum_t dst,
                                     xed_reg_enum_t base,
                                     xed_reg_enum_t indx,
                                     xed_uint_t scale)
{  // this works for 32b moves in 32b mode. 

    enc_modrm_reg_gpr32(r,dst);

    // if the user specifies EBP or R13D as a base, we add a zero-valued
    // disp8.
    
    enc_modrm_rm_mem_nodisp_a32(r,base,indx,scale);  
    emit_rex_if_needed(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
}





void encode_mov64_reg_mem_nodisp_a64(xed_enc2_req_t* r,
                                     xed_reg_enum_t dst,
                                     xed_reg_enum_t base,
                                     xed_reg_enum_t indx,
                                     xed_uint_t scale)
{   // this works for 64b moves in 64b mode. 
    set_rexw(r); //64b operation
    enc_modrm_reg_gpr64(r,dst);

    // if the user specifies RSP, RBP, R12, R13 as a base, we add a
    // zero-valued disp8.
    
    enc_modrm_rm_mem_nodisp_a64(r,base,indx,scale);  
    emit_rex(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
}

void encode_mov64_reg_mem_disp32_a64(xed_enc2_req_t* r,
                                     xed_reg_enum_t dst,
                                     xed_reg_enum_t base,
                                     xed_reg_enum_t indx,
                                     xed_uint_t scale,
                                     xed_int32_t disp)
{   // this works for 64b moves in 64b mode. 
    set_rexw(r); //64b operation
    enc_modrm_reg_gpr64(r,dst);

    enc_modrm_rm_mem_disp32_a64(r,base,indx,scale);  
    emit_rex(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
    emit_i32(r,disp);
}

void encode_mov64_reg_mem_disp8_a64(xed_enc2_req_t* r,
                                     xed_reg_enum_t dst,
                                     xed_reg_enum_t base,
                                     xed_reg_enum_t indx,
                                     xed_uint_t scale,
                                     xed_int8_t disp)
{   // this works for 64b moves in 64b mode. 
    set_rexw(r); //64b operation
    enc_modrm_reg_gpr64(r,dst);

    enc_modrm_rm_mem_disp8_a64(r,base,indx,scale);  
    emit_rex(r);
    emit(r,0x8B);
    emit_modrm_sib(r);
    emit_i8(r,disp);
}

