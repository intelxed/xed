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
/// @file xed-operand-values-interface.c
/// 


#include "xed-internal-header.h"
#include "xed-operand-values-interface.h"
#include "xed-util.h"
#include "xed-util-private.h"
#include "xed-init-pointer-names.h"
#include "xed-operand-ctype-enum.h"
#include "xed-operand-ctype-map.h"
#include "xed-reg-class.h"
#include "xed-operand-accessors.h"

void xed_operand_values_init(xed_operand_values_t* p) {
    unsigned int i;
    xed_uint32_t* xp = (xed_uint32_t*)p;
    for(i=0;i<sizeof(xed_operand_storage_t)/4;i++)
        xp[i]=0;
}

void xed_operand_values_init_keep_mode( xed_operand_values_t* dst,
                                        const xed_operand_values_t* src) {
    const xed_bits_t real_mode  = xed3_operand_get_realmode(src);
    const xed_bits_t mode  = xed3_operand_get_mode(src);
    const xed_bits_t smode = xed3_operand_get_smode(src);
    xed_operand_values_init(dst);
    xed3_operand_set_realmode(dst,real_mode);
    xed3_operand_set_mode(dst,mode);
    xed3_operand_set_smode(dst,smode);
}


void xed_operand_values_init_set_mode(xed_operand_values_t* p,
                                      const xed_state_t* dstate)  {
    xed_operand_values_init(p);
    xed_operand_values_set_mode(p,dstate);
}

void xed_operand_values_set_mode(xed_operand_values_t* p,
                                 const xed_state_t* dstate)  {

    /* set MODE, SMODE and REALMODE */
    xed3_operand_set_realmode(p,0);
    switch(xed_state_get_machine_mode(dstate))
    {
      case XED_MACHINE_MODE_LONG_64:
        xed3_operand_set_mode(p,2);
        xed3_operand_set_smode(p,2);
        return;
        
      case XED_MACHINE_MODE_LEGACY_32:
      case XED_MACHINE_MODE_LONG_COMPAT_32:
        xed3_operand_set_mode(p,1);
        break;

      case XED_MACHINE_MODE_REAL_16:
        xed3_operand_set_realmode(p,1);
        xed3_operand_set_mode(p,0);
        break;
        
      case XED_MACHINE_MODE_REAL_32:
        xed3_operand_set_realmode(p,1);
        xed3_operand_set_mode(p,1);
        break;

      case XED_MACHINE_MODE_LEGACY_16:
      case XED_MACHINE_MODE_LONG_COMPAT_16:
        xed3_operand_set_mode(p,0);
        break;
      default:
        xed_derror("Bad machine mode in xed_operand_values_set_mode() call");
    }

    // 64b mode returns above. this is for 16/32b modes only
    switch(xed_state_get_stack_address_width(dstate))    {
      case XED_ADDRESS_WIDTH_16b:
        xed3_operand_set_smode(p,0);
        break;
      case XED_ADDRESS_WIDTH_32b:
        xed3_operand_set_smode(p,1);
        break;
      default:
        break;
    }
}

xed_bool_t xed_operand_values_get_long_mode(const xed_operand_values_t* p) {
    return (xed3_operand_get_mode(p)==2);
}
xed_bool_t xed_operand_values_get_real_mode(const xed_operand_values_t* p) {
    return (xed3_operand_get_realmode(p)!=0);
}


xed_uint32_t
xed_operand_values_get_stack_address_width(const xed_operand_values_t* p) {
    xed_uint32_t smode = xed3_operand_get_smode(p);
    switch(smode)    {
      case 0:        return 16;
      case 1:        return 32;
      case 2:        return 64;
      default:       xed_assert(0);        return 0;
    }
}
xed_uint32_t
xed_operand_values_get_effective_address_width(const xed_operand_values_t* p) {
    xed_uint32_t easz = xed3_operand_get_easz(p);
    switch(easz)    {
      case 0:        xed_assert(0);        return 0;
      case 1:        return 16;
      case 2:        return 32;
      case 3:        return 64;
      default:       xed_assert(0);        return 0;
    }
}

xed_uint32_t
xed_operand_values_get_effective_operand_width(const xed_operand_values_t* p)
{
    xed_uint32_t eosz = xed3_operand_get_eosz(p);
    switch(eosz)    {
      case 0:        return 8;
      case 1:        return 16;
      case 2:        return 32;
      case 3:        return 64;
      default:       xed_assert(0);        return 0;
    }
}

#if defined(XED_DECODER)
xed_bool_t
xed_operand_values_has_real_rep(const xed_operand_values_t* p) {
    xed_uint32_t rep = xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_REP);    
    if ( rep ) {
        xed_bits_t r = xed3_operand_get_rep(p);
        return (r == 3 || r == 2);
    }
    return 0;
}
#endif

xed_bool_t
xed_operand_values_has_rep_prefix(const xed_operand_values_t* p) {
    return xed3_operand_get_rep(p) == 3;
}

xed_bool_t
xed_operand_values_has_repne_prefix(const xed_operand_values_t* p) {
    return xed3_operand_get_rep(p) == 2;
}

//FIXME: 2015-05-27: DEPRECATED -- remove when pin is fixed to not call
//this function.
void xed_operand_values_clear_rep(xed_operand_values_t* p) {
    xed3_operand_set_rep(p,0);
}


xed_bool_t
xed_operand_values_has_segment_prefix(const xed_operand_values_t* p)
{
    return xed3_operand_get_seg_ovd(p) != 0;
}

xed_reg_enum_t
xed_operand_values_segment_prefix(const xed_operand_values_t* p)
{
    switch(xed3_operand_get_seg_ovd(p)) {
      case 0: return XED_REG_INVALID;
      case 1: return XED_REG_CS;
      case 2: return XED_REG_DS;
      case 3: return XED_REG_ES;
      case 4: return XED_REG_FS;
      case 5: return XED_REG_GS;
      case 6: return XED_REG_SS;
    }
    return XED_REG_INVALID;
}

xed_bool_t
xed_operand_values_has_lock_prefix(const xed_operand_values_t* p) {
    return xed3_operand_get_lock(p) != 0;
}

#if defined(XED_DECODER)
xed_bool_t
xed_operand_values_get_atomic(const xed_operand_values_t* p) {
    return xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_LOCKED)
#if defined(XED_ATTRIBUTE_ATOMIC_DEFINED)
        || xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_ATOMIC)
#endif
        ;
}


xed_bool_t
xed_operand_values_lockable(const xed_operand_values_t* p) {
    if (xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_LOCKABLE))
        return 1;
    //XCHG accessing memory is always atomic, lockable
    if (xed3_operand_get_iclass(p) == XED_ICLASS_XCHG)
        if (xed3_operand_get_mem0(p))
            return 1;
    return 0;
}
#endif

xed_bool_t
xed_operand_values_using_default_segment(const xed_operand_values_t* p,
                                         unsigned int i) {

    switch(i){
    case(0): return xed3_operand_get_using_default_segment0(p);
    case(1): return xed3_operand_get_using_default_segment1(p);
    default: xed_assert(0);
    }
    return 0; //will not ever happen, pacify the compiler

}

xed_bool_t 
xed_operand_values_memop_without_modrm(const xed_operand_values_t* p) {
    return (xed3_operand_get_mem0(p) &&
            xed3_operand_get_disp_width(p) &&
            xed3_operand_get_has_modrm(p)==0);
}

xed_bool_t 
xed_operand_values_has_modrm_byte(const xed_operand_values_t* p) {
    return xed3_operand_get_has_modrm(p);
}
xed_bool_t 
xed_operand_values_has_sib_byte(const xed_operand_values_t* p) {
    return xed3_operand_get_has_sib(p);
}

xed_bool_t
xed_operand_values_has_immediate(const xed_operand_values_t* p) {
    if (xed3_operand_get_imm_width(p))
        return 1;
    return 0;
}


xed_bool_t
xed_operand_values_has_displacement(const xed_operand_values_t* p)
{
    if (xed3_operand_get_disp_width(p))
        return 1;
    if (xed3_operand_get_brdisp_width(p))
        return 1;
    return 0;
}

xed_bool_t
xed_operand_values_has_memory_displacement(const xed_operand_values_t* p)
{
    if (xed3_operand_get_brdisp_width(p))
        return 0;
    if (xed3_operand_get_disp_width(p))
        return 1;
    return 0;
}
xed_bool_t
xed_operand_values_has_branch_displacement(const xed_operand_values_t* p)
{
    if (xed3_operand_get_brdisp_width(p))
        return 1;
    return 0;
}

xed_bool_t
xed_operand_values_get_displacement_for_memop(const xed_operand_values_t* p)
{
    return xed_operand_values_has_memory_displacement(p);
}


xed_uint32_t
xed_operand_values_get_branch_displacement_length(
    const xed_operand_values_t* p)
{
    return xed3_operand_get_brdisp_width(p)/8;
}
xed_uint32_t
xed_operand_values_get_branch_displacement_length_bits(
    const xed_operand_values_t* p)
{
    return xed3_operand_get_brdisp_width(p);
}

xed_uint32_t
xed_operand_values_get_memory_displacement_length(
    const xed_operand_values_t* p)
{
    return xed_operand_values_get_memory_displacement_length_bits(p)/8;
}

xed_bool_t 
xed_operand_values_has_address_size_prefix(const xed_operand_values_t* p)
{
    if (xed3_operand_get_asz(p))
        return 1;
    return 0;
}

xed_bool_t 
xed_operand_values_has_operand_size_prefix(const xed_operand_values_t* p)
{
    // If REFINING66() executed, then we zero the OSZ variable. The other
    // osz's live on to be returned as 1 here.  The REFINING indicator is
    // not removed for OSZ-nonrefining operations.
    if ( xed3_operand_get_osz(p))
        return 1;
    return 0;
}
xed_bool_t 
xed_operand_values_has_66_prefix(const xed_operand_values_t* p)
{
    if ( xed3_operand_get_prefix66(p))
        return 1;
    return 0;
}

xed_bool_t 
xed_operand_values_has_rexw_prefix(const xed_operand_values_t* p)
{
    if ( xed3_operand_get_rexw(p))
        return 1;
    return 0;
}

xed_bool_t
xed_operand_values_accesses_memory(const xed_operand_values_t* p)
{
    if (xed3_operand_get_mem0(p) ||
        xed3_operand_get_mem1(p) )
        return 1;
    return 0;
}

unsigned int
xed_operand_values_number_of_memory_operands(const xed_operand_values_t* p) {
    unsigned int memops = xed3_operand_get_mem0(p) + 
                          xed3_operand_get_mem1(p);
    return memops;
}


xed_reg_enum_t
xed_operand_values_get_base_reg(const xed_operand_values_t* p,
                                unsigned int memop_idx)  {
    if (memop_idx == 0)
        return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_base0(p));
    if (memop_idx == 1)
        return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_base1(p));
    xed_assert(0);
    return XED_REG_INVALID;
}

xed_reg_enum_t
xed_operand_values_get_seg_reg(const xed_operand_values_t* p,
                                         unsigned int memop_idx) 
{
    if (memop_idx == 0)
        return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_seg0(p));
    if (memop_idx == 1)
        return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_seg1(p));
    xed_assert(0);
    return XED_REG_INVALID;
}

xed_reg_enum_t
xed_operand_values_get_index_reg(const xed_operand_values_t* p,
                                           unsigned int memop_idx) 
{
    if (memop_idx == 0)
        return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_index(p));
    xed_assert(0);
    return XED_REG_INVALID;
}

unsigned int
xed_operand_values_get_scale(const xed_operand_values_t* p)
{
    if (xed3_operand_get_mem0(p) || xed3_operand_get_agen(p)) 
        return (xed3_operand_get_scale(p))?xed3_operand_get_scale(p):1;
    return 0;
}

xed_bool_t
xed_operand_values_branch_not_taken_hint(const xed_operand_values_t* p)
{
    if (xed3_operand_get_hint(p)==3)
        return 1;
    return 0;
}
xed_bool_t
xed_operand_values_branch_taken_hint(const xed_operand_values_t* p)
{
    if (xed3_operand_get_hint(p)==4)
        return 1;
    return 0;
}

xed_bool_t
xed_operand_values_cet_no_track(const xed_operand_values_t* p)
{
    if (xed3_operand_get_hint(p)==5)
        return 1;
    return 0;
}

    

xed_bool_t
xed_operand_values_is_nop(const xed_operand_values_t* p)
{
    const xed_iclass_enum_t iclass = xed_operand_values_get_iclass(p);

    if (iclass == XED_ICLASS_NOP)
        return 1;
    if (iclass >= XED_ICLASS_NOP2 && iclass <= XED_ICLASS_NOP9)
        return 1;

    if (iclass == XED_ICLASS_XCHG) {
        xed_reg_enum_t r0 = XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_reg0(p));
        xed_reg_enum_t r1 = XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_reg1(p));

        // EAX is special on the 32b 1-byte NOP in 64b mode. It is a
        // NOP. That is critically caught by the above test!!!! 

        //Any other register in this situation is NOT a nop! Even EAX with
        //a non-one-byte XCHG is not a NOP! It zero's the upper part of
        //RAX. (or whatever dest reg). So we exclude the 32b regs below in
        //64b mode.

        // we can also call xchg reg64,reg64 a nop xchg reg8,reg8 xchg
        // reg16,reg16 NOPs if the regs are the same in any mode. Those
        // are not official NOPs but act like them.

        if (r0 == r1) {
            if (xed_operand_values_get_long_mode(p)) 
                if (xed_gpr_reg_class(r0) == XED_REG_CLASS_GPR32)
                    return 0;
            return 1;
        }
    }

    return 0;
}





xed_int32_t
xed_operand_values_get_branch_displacement_int32(
    const xed_operand_values_t* p)
{
    const xed_decoded_inst_t* xedd = (const xed_decoded_inst_t*)p; // same type
    unsigned int len = xed3_operand_get_brdisp_width(xedd);
    switch(len) {
      case 8:
      case 16: 
      case 32: 
        return xed3_operand_get_disp(xedd);
      default:
        return 0;
    }
}

xed_int64_t
xed_operand_values_get_immediate_int64(const xed_operand_values_t* p)
{
    xed_uint8_t len = xed3_operand_get_imm_width(p);
    xed_uint64_t raw_imm = xed3_operand_get_uimm0(p);
    switch(len){
    case 8:  return xed_sign_extend8_64(raw_imm);
    case 16: return xed_sign_extend16_64(raw_imm);
    case 32: return xed_sign_extend32_64(raw_imm);
    case 64: return raw_imm;
    default:
        return 0;
    }
    return 0;
    
}

xed_uint64_t
xed_operand_values_get_immediate_uint64(const xed_operand_values_t* p) {
    return xed3_operand_get_uimm0(p);
}

xed_uint_t
xed_operand_values_get_immediate_is_signed(const xed_operand_values_t* p) {
    return xed3_operand_get_imm0signed(p);
}

xed_uint8_t
xed_operand_values_get_immediate_byte(const xed_operand_values_t* p,
                                      unsigned int i) {
    unsigned int len = xed3_operand_get_imm_width(p);
    if (xed3_operand_get_imm0(p)) {
        xed_uint64_t y = xed_operand_values_get_immediate_uint64(p); //FIXME: BENDIAN
        return xed_get_byte(y, i, len); 
    }
    return 0;
}

xed_uint8_t
xed_operand_values_get_second_immediate(const xed_operand_values_t* p) {
    if (xed3_operand_get_imm1(p))
        return xed3_operand_get_uimm1(p);
    return 0;
}

xed_uint8_t
xed_operand_values_get_memory_displacement_byte(const xed_operand_values_t* p,
                                                unsigned int i) {
    unsigned int len = xed3_operand_get_disp_width(p);
    xed_uint64_t y = xed_operand_values_get_memory_displacement_int64(p); //FIXME: BENDIAN
    return xed_get_byte(y, i, len);
}

xed_uint8_t
xed_operand_values_get_branch_displacement_byte(const xed_operand_values_t* p,
                                                unsigned int i) {
    unsigned int len = xed3_operand_get_brdisp_width(p);
    xed_int32_t v = xed_operand_values_get_branch_displacement_int32(p); //FIXME: BENDIAN
    return xed_get_byte(v, i, len);
}

xed_iclass_enum_t
xed_operand_values_get_iclass(const xed_operand_values_t* p) {
    return XED_STATIC_CAST(xed_iclass_enum_t,xed3_operand_get_iclass(p));
}

////////////////////////////////////////////////////////////////////
// ENCODE
////////////////////////////////////////////////////////////////////
void xed_operand_values_zero_immediate(xed_operand_values_t* p) {
   xed3_operand_set_imm_width(p,0);
   xed3_operand_set_uimm0(p,0);
}

void xed_operand_values_zero_branch_displacement(xed_operand_values_t* p) {
   xed3_operand_set_brdisp_width(p,0);
   xed3_operand_set_disp(p,0);
}

void xed_operand_values_zero_memory_displacement(xed_operand_values_t* p) {
   xed3_operand_set_disp_width(p,0);
   xed3_operand_set_disp(p,0);
}

void xed_operand_values_set_lock(xed_operand_values_t* p) {
    xed3_operand_set_lock(p,1);
}
void xed_operand_values_zero_segment_override(xed_operand_values_t* p) {
    xed3_operand_set_seg_ovd(p,0);
    /* Also remove the segment specifiers in SEG0/SEG1. If they are
     * default, they don't matter for encoding. This is assumed to be part
     * of a re-encode sequence. 2008-10-01 */
    xed3_operand_set_seg0(p,XED_REG_INVALID);
    xed3_operand_set_seg1(p,XED_REG_INVALID);
}

void
xed_operand_values_set_iclass(xed_operand_values_t* p,
                              xed_iclass_enum_t iclass) {
    xed3_operand_set_iclass(p,iclass);
}

void
xed_operand_values_set_relbr(xed_operand_values_t* p) {
    xed3_operand_set_relbr(p,1);
}

void
xed_operand_values_set_effective_operand_width(xed_operand_values_t* p,
                                               unsigned int width) {
    unsigned int eosz=0;
    switch(width)  {
      case 8:         eosz=0;        break;
      case 16:        eosz=1;        break;
      case 32:        eosz=2;        break;
      case 64:        eosz=3;        break; // default is 2
      default:        xed_assert(0);
    }
    xed3_operand_set_eosz(p,eosz);
}

void
xed_operand_values_set_effective_address_width(xed_operand_values_t* p,
                                               unsigned int width) {
    unsigned int easz=0;
    switch(width)  {
      case 16:        easz=1;        break;
      case 32:        easz=2;        break;
      case 64:        easz=3;        break;
      default:        xed_assert(0);
    }
    xed3_operand_set_easz(p,easz);
}

void
xed_operand_values_set_memory_operand_length(xed_operand_values_t* p,
                                             unsigned int memop_length) {
    xed3_operand_set_mem_width(p,XED_STATIC_CAST(xed_uint16_t,memop_length));
}

unsigned int
xed_operand_values_get_memory_operand_length(const xed_operand_values_t* p,
                                             unsigned int memop_idx)  {
    return xed3_operand_get_mem_width(p);
    (void)memop_idx;
}

void
xed_operand_values_set_memory_displacement(xed_operand_values_t* p,
                                           xed_int64_t x,
                                           unsigned int len) {
    xed_operand_values_set_memory_displacement_bits(p,x,len*8);
}

void
xed_operand_values_set_memory_displacement_bits(xed_operand_values_t* p,
                                                xed_int64_t x,
                                                unsigned int len) {
    /* Set the real displacement value x in big-endian form for emitting.
     * Make sure that the LSB of x is the MSB of the xed3_operand_get_(p)* field
     * because we emit them starting from the MSB based on the width */
    
    xed_assert(len==0 || len==8 || len==16 || len==32 || len==64);
    if (len==0){
        xed3_operand_set_disp(p,0); 
    }
    else{
        xed3_operand_set_disp(p,x); 
    }
    xed3_operand_set_disp_width(p, XED_STATIC_CAST(xed_uint8_t, len));
}

void
xed_operand_values_set_branch_displacement(xed_operand_values_t* p,
                                           xed_int32_t x,
                                           unsigned int len) {
    xed_operand_values_set_branch_displacement_bits(p,x,len*8);
}
void
xed_operand_values_set_branch_displacement_bits(xed_operand_values_t* p,
                                                xed_int32_t x,
                                                unsigned int len) {
    /* Set the real displacement value x in big-endian form for emitting.
     * Make sure that the LSB of x is the MSB of the xed3_operand_get_(p)* field
     * because we emit them starting from the MSB based on the width */
    xed_assert(len==0 || len==8 || len==16 || len==32);
    if (len ==0){
        xed3_operand_set_disp(p,0);
    }
    else{
        xed3_operand_set_disp(p,x);
    }
    xed3_operand_set_brdisp_width(p,XED_STATIC_CAST(xed_uint8_t,len));

}

void xed_operand_values_set_immediate_signed(xed_operand_values_t* p,
                                             xed_int32_t x,
                                             unsigned int len) {
    xed_operand_values_set_immediate_signed_bits(p,x,len*8);
}

void xed_operand_values_set_immediate_signed_bits(xed_operand_values_t* p,
                                                  xed_int32_t x,
                                                  unsigned int len) {

    xed_int64_t x_64 = x; //for sign extension  
    xed_operand_values_set_immediate_unsigned_bits(p,x_64,len);
    xed3_operand_set_imm0signed(p,1);
}

void xed_operand_values_set_immediate_unsigned(xed_operand_values_t* p,
                                               xed_uint64_t x,
                                               unsigned int bytes)  {
    xed_operand_values_set_immediate_unsigned_bits(p,x,bytes*8);
}
void xed_operand_values_set_immediate_unsigned_bits(xed_operand_values_t* p,
                                                    xed_uint64_t x,
                                                    unsigned int bits)  {

    /* Set the real displacement value x in big-endian form for emitting.
     * Make sure that the LSB of x is the MSB of the xed3_operand_get_(p)* field
     * because we emit them starting from the MSB based on the width */

    xed_assert(bits==0 || bits==8 || bits==16 || bits==32 || bits==64);
    if (bits == 0){
        xed3_operand_set_uimm0(p,0);
    }
    else{
        xed3_operand_set_uimm0(p,x);
    }
    
    xed3_operand_set_imm_width(p, XED_STATIC_CAST(xed_uint8_t,bits));
    xed3_operand_set_imm0signed(p,0);
}


/*-----------------------------------------------------------------------------*/

void xed_operand_values_set_base_reg(xed_operand_values_t* p,
                                     unsigned int memop_idx,
                                     xed_reg_enum_t new_base)  {
    if (memop_idx == 0)
        xed3_operand_set_base0(p,new_base);
    else if (memop_idx == 1)
        xed3_operand_set_base1(p,new_base);
    else
        xed_assert(0);
}

void xed_operand_values_set_seg_reg(xed_operand_values_t* p,
                                    unsigned int memop_idx,
                                    xed_reg_enum_t new_seg) {
    if (memop_idx == 0)
        xed3_operand_set_seg0(p,new_seg);
    else if (memop_idx == 1)
        xed3_operand_set_seg1(p,new_seg);
    else 
        xed_assert(0);
}


void xed_operand_values_set_index_reg(xed_operand_values_t* p,
                                      unsigned int memop_idx,
                                      xed_reg_enum_t new_index) {
    if (memop_idx == 0)
        xed3_operand_set_index(p,new_index);
    else
        xed_assert(0);
}

void xed_operand_values_set_scale(xed_operand_values_t* p,
                                  xed_uint_t memop_idx,
                                  xed_uint_t new_scale) {
    if (memop_idx == 0)
        xed3_operand_set_scale(p,new_scale);
    else
        xed_assert(0);
}

void
xed_operand_values_set_operand_reg(xed_operand_values_t* p,
                                   xed_operand_enum_t operand_name,
                                   xed_reg_enum_t reg_name) {
    switch(operand_name){
    case XED_OPERAND_REG0: xed3_operand_set_reg0(p,reg_name); break;
    case XED_OPERAND_REG1: xed3_operand_set_reg1(p,reg_name); break;
    case XED_OPERAND_REG2: xed3_operand_set_reg2(p,reg_name); break;
    case XED_OPERAND_REG3: xed3_operand_set_reg3(p,reg_name); break;
    case XED_OPERAND_REG4: xed3_operand_set_reg4(p,reg_name); break;
    case XED_OPERAND_REG5: xed3_operand_set_reg5(p,reg_name); break;
    case XED_OPERAND_REG6: xed3_operand_set_reg6(p,reg_name); break;
    case XED_OPERAND_REG7: xed3_operand_set_reg7(p,reg_name); break;
    case XED_OPERAND_REG8: xed3_operand_set_reg8(p,reg_name); break;
    case XED_OPERAND_REG9: xed3_operand_set_reg9(p,reg_name); break;
    case XED_OPERAND_BASE0: xed3_operand_set_base0(p,reg_name); break;
    case XED_OPERAND_BASE1: xed3_operand_set_base1(p,reg_name); break;
    case XED_OPERAND_INDEX: xed3_operand_set_index(p,reg_name); break;
    case XED_OPERAND_SEG0: xed3_operand_set_seg0(p,reg_name); break;
    case XED_OPERAND_SEG1: xed3_operand_set_seg1(p,reg_name); break;
    default: xed_assert(0);
    }
}

////////////////////////////////////////////////////////////////////
// PRINTING
////////////////////////////////////////////////////////////////////
static const char* xed_ptr_size(xed_uint_t bytes) {
    extern const char* xed_pointer_name[XED_MAX_POINTER_NAMES];
    if (bytes < XED_MAX_POINTER_NAMES)
        if (xed_pointer_name[bytes])
            return xed_pointer_name[bytes];
    return "";
}

void xed_operand_values_print_short(const xed_operand_values_t* ov, char* buf,  int buflen) {
    xed_operand_values_dump(ov,buf, buflen);
}

static xed_bool_t add_comma(xed_bool_t emitted, char* buf, int* blen) { 
    if (emitted)
        *blen = xed_strncat(buf,", ", *blen);
    return 1;
}

static int emit_agen_and_mem(const xed_operand_values_t* ov,
                            char * buf,
                            int i,
                            int buflen)
{
    xed_reg_enum_t base = xed3_operand_get_base0(ov);
    xed_reg_enum_t seg =  xed3_operand_get_seg0(ov);
    xed_reg_enum_t index = xed3_operand_get_index(ov);
    xed_int64_t be_disp = xed_operand_values_get_memory_displacement_int64(ov);
    xed_bits_t scale = xed3_operand_get_scale(ov);
    xed_bool_t started = 0;
    xed_bool_t leading_zeros = 0;
    xed_uint_t bytes = xed_operand_values_get_memory_operand_length(ov,0);
    int blen = buflen;
    blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
    blen = xed_strncat(buf, ":", blen);
    blen = xed_strncat(buf, xed_ptr_size(bytes),blen);
    blen = xed_strncat(buf,"ptr ",blen);
    if (seg != XED_REG_INVALID)
        if (i != XED_OPERAND_AGEN)
            blen = xed_strncat(buf, xed_reg_enum_t2str(seg),blen);
    blen = xed_strncat(buf,"[",blen);
    if (base != XED_REG_INVALID) {
        blen = xed_strncat(buf, xed_reg_enum_t2str(base),blen);
        started = 1;
    }
    if (index != XED_REG_INVALID) {
        if (started) 
            blen = xed_strncat(buf,"+",blen);
        started = 1;
        blen = xed_strncat(buf, xed_reg_enum_t2str(index),blen);
        blen = xed_strncat(buf,"*",blen);
        blen = xed_itoa(buf+xed_strlen(buf), XED_STATIC_CAST(xed_uint_t,scale),blen);
    }

    if (be_disp != 0) {
        unsigned int disp_bits = xed_operand_values_get_memory_displacement_length_bits(ov);
        xed_uint_t negative = (be_disp < 0) ? 1 : 0;
        if (started) {
            if (negative) {
                blen = xed_strncat(buf,"-",blen);
                be_disp = - be_disp;
            }
            else
                blen = xed_strncat(buf,"+",blen);
        }
        blen = xed_strncat(buf,"0x",blen);
        blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), be_disp, disp_bits, leading_zeros,blen);
    }
    blen = xed_strncat(buf,"]",blen);
    return blen;
}

void
xed_operand_values_dump(    const xed_operand_values_t* ov,
                            char* buf,
                            int buflen)
{
    xed_uint_t i = XED_OPERAND_INVALID+1;
    xed_bool_t leading_zeros = 0;
    xed_bool_t emitted = 0;
    int blen = buflen;
    *buf = 0; /* allow use of xed_strncat */
    for( ; i<XED_OPERAND_LAST ; i++) {
        switch(i) {
          case XED_OPERAND_ICLASS:/* these get printed by other fields */
          case XED_OPERAND_BASE0: 
          case XED_OPERAND_BASE1:
          case XED_OPERAND_INDEX:
          case XED_OPERAND_SEG0:
          case XED_OPERAND_SEG1:
          case XED_OPERAND_DISP:
          case XED_OPERAND_SCALE:
          case XED_OPERAND_UIMM0:
          case XED_OPERAND_UIMM1:
            break;
            
          case XED_OPERAND_AGEN:
            if (xed3_operand_get_agen(ov)){
                emitted = add_comma(emitted,buf,&blen);
                blen = emit_agen_and_mem(ov,buf,i,blen);
            }
            break;
                  
          case XED_OPERAND_MEM0:
            if (xed3_operand_get_mem0(ov)){
                emitted = add_comma(emitted,buf,&blen);
                blen = emit_agen_and_mem(ov,buf,i,blen);
            }
            
            break;
          case XED_OPERAND_MEM1:
            if (xed3_operand_get_mem1(ov)) {
                xed_reg_enum_t base = xed3_operand_get_base1(ov);
                xed_reg_enum_t seg = xed3_operand_get_seg1(ov);
                emitted = add_comma(emitted,buf,&blen);
                blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                blen = xed_strncat(buf, ":",blen);
                if (seg != XED_REG_INVALID)
                    blen = xed_strncat(buf, xed_reg_enum_t2str(seg),blen);
                blen = xed_strncat(buf, "[",blen);
                if (base != XED_REG_INVALID) 
                    blen = xed_strncat(buf, xed_reg_enum_t2str(base),blen);
                blen = xed_strncat(buf, "]",blen);
            }
            break;
          case XED_OPERAND_IMM0:
            if (xed3_operand_get_imm0(ov)) {
                xed_uint_t bits = xed3_operand_get_imm_width(ov);
                emitted = add_comma(emitted,buf,&blen);
                blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                blen = xed_strncat(buf,":0x",blen);
                if (xed3_operand_get_imm0signed(ov)) {
                    xed_int64_t simm = xed_operand_values_get_immediate_int64(ov);
                    blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), simm, bits, leading_zeros,blen);
                }
                else {
                    xed_uint64_t uimm = xed_operand_values_get_immediate_uint64(ov);
                    blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), uimm, bits,leading_zeros,blen);
                }
            }
            break;
          case XED_OPERAND_IMM1: 
            if (xed3_operand_get_imm1(ov)) { // The ENTER instruction
                xed_uint64_t imm1 = xed3_operand_get_imm1(ov); //1B always
                emitted = add_comma(emitted,buf,&blen);
                blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                blen = xed_strncat(buf,":0x",blen);
                blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), imm1, 8,leading_zeros, blen);
            }
            break;
          case XED_OPERAND_PTR: 
            if (xed3_operand_get_ptr(ov)) {
                xed_int64_t be_disp = xed_operand_values_get_branch_displacement_int32(ov);
                xed_bool_t long_mode = xed_operand_values_get_long_mode(ov);
                xed_uint_t xed_bits_to_print = long_mode ? 8*8 : 4*8;
                emitted = add_comma(emitted,buf,&blen);
                blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                blen = xed_strncat(buf,":0x",blen);
                blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), be_disp, xed_bits_to_print, leading_zeros, blen);
            }
            break;
          case XED_OPERAND_RELBR: 
            if (xed3_operand_get_relbr(ov)) {
                xed_int64_t be_disp = xed_operand_values_get_branch_displacement_int32(ov);
                xed_uint64_t effective_addr;
                xed_bool_t long_mode;
                xed_uint_t xed_bits_to_print;
                emitted = add_comma(emitted,buf,&blen);
                blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                blen = xed_strncat(buf, ":",blen);

                effective_addr = be_disp;

                long_mode = xed_operand_values_get_long_mode(ov);
                xed_bits_to_print = long_mode ? 8*8 :4*8;
                blen = xed_strncat(buf,"0x",blen);
                blen = xed_itoa_hex_zeros(buf+xed_strlen(buf), effective_addr,xed_bits_to_print, leading_zeros,blen);
            }
            break;
          default:
            {
                xed_operand_ctype_enum_t  ctype = xed_operand_get_ctype(XED_STATIC_CAST(xed_operand_enum_t,i));
                unsigned int w = xed_operand_decider_get_width(XED_STATIC_CAST(xed_operand_enum_t,i));
                char tmp_buf[512];
                int need_to_emit = 0;
                *tmp_buf = 0; //to use strncat
                
                    switch(ctype) {
                      case XED_OPERAND_CTYPE_XED_BITS_T: {
                          xed_bits_t b;
                          xed3_get_generic_operand(ov,i,&b);
                          if (b){
                              blen = xed_itoa(tmp_buf, XED_STATIC_CAST(xed_uint_t,b),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_UINT16_T: {
                          xed_uint16_t b;
                          xed3_get_generic_operand(ov,i,&b);
                          if (b){
                              blen = xed_itoa_signed(tmp_buf, b, blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_UINT8_T: {
                          xed_uint8_t b;
                          xed3_get_generic_operand(ov,i,&b);
                          if (b){
                              blen = xed_itoa(tmp_buf, b, blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_ERROR_ENUM_T: {
                          xed_error_enum_t b = xed3_operand_get_error(ov);
                          if (b){
                              blen = xed_strncpy(tmp_buf, xed_error_enum_t2str(b),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_ICLASS_ENUM_T: {
                          xed_iclass_enum_t b = xed3_operand_get_iclass(ov);
                          if (b){
                              blen = xed_strncpy(tmp_buf, xed_iclass_enum_t2str(b),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_REG_ENUM_T: { 
                          xed_reg_enum_t reg;
                          xed3_get_generic_operand(ov,i,&reg);
                          if (reg){
                              blen = xed_strncpy(tmp_buf, xed_reg_enum_t2str(reg),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
                      case XED_OPERAND_CTYPE_XED_CHIP_ENUM_T: { 
                          xed_chip_enum_t chip = xed3_operand_get_chip(ov);
                          if (chip){
                              blen = xed_strncpy(tmp_buf, xed_chip_enum_t2str(chip),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
#if defined(XED_OPERAND_ELEMENT_TYPE_ENUM_T_DEFINED) // used by KNC
                      case XED_OPERAND_ELEMENT_TYPE_ENUM_T: {
                          xed_operand_element_type_enum_t etype = xed3_operand_get_type(ov);
                          if (etype){
                              blen = xed_strncpy(tmp_buf, xed_operand_element_type_enum_t2str(etype),blen);
                              need_to_emit = 1;
                          }
                          break;
                      }
#endif
                      default: {
                        xed_bits_t b;
                        xed3_get_generic_operand(ov,i,&b);
                        if (b) {   
                            blen = xed_strncat(buf,"NOT HANDLING CTYPE ",blen);
                            blen = xed_strncat(buf, xed_operand_ctype_enum_t2str(ctype),blen);
                            xed_assert(0);
                        }
                      }
                    } /* inner switch */
                    /* only print nonzero generic stuff */
                    if (need_to_emit){
                        emitted = add_comma(emitted,buf,&blen);
                        blen = xed_strncat(buf, xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,i)),blen);
                        if (w > 1){
                            blen = xed_strncat(buf, ":", blen);
                            blen = xed_strncat(buf+xed_strlen(tmp_buf), tmp_buf,blen);
                        }
                    }
              } /* default block*/
            } /* switch */
        } /* for */
    }



