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

#ifndef XED_ENCODER_HL_H
# define XED_ENCODER_HL_H
#include "xed-types.h"
#include "xed-reg-enum.h"
#include "xed-state.h"
#include "xed-iclass-enum.h"
#include "xed-portability.h"
#include "xed-encode.h"
#include "xed-util.h"


typedef struct {
    xed_int64_t    displacement; 
    xed_uint32_t   displacement_bits;
} xed_enc_displacement_t; /* fixme bad name */

/// @name Memory Displacement
//@{
/// @ingroup ENCHL
/// a memory displacement (not for branches)
/// @param displacement The value of the displacement
/// @param displacement_bits The width of the displacement in bits. Typically 8 or 32.
/// @returns #xed_enc_displacement_t
static XED_INLINE
xed_enc_displacement_t xed_disp(xed_int64_t   displacement,
                                xed_uint32_t   displacement_bits   ) {
    xed_enc_displacement_t x;
    x.displacement = displacement;
    x.displacement_bits = displacement_bits;
    return x;
}
//@}

typedef struct {
    xed_reg_enum_t seg;
    xed_reg_enum_t base;
    xed_reg_enum_t index;
    xed_uint32_t   scale;
    xed_enc_displacement_t disp;
} xed_memop_t;


typedef enum {
    XED_ENCODER_OPERAND_TYPE_INVALID,
    XED_ENCODER_OPERAND_TYPE_BRDISP,
    XED_ENCODER_OPERAND_TYPE_REG,
    XED_ENCODER_OPERAND_TYPE_IMM0,
    XED_ENCODER_OPERAND_TYPE_SIMM0,
    XED_ENCODER_OPERAND_TYPE_IMM1,
    XED_ENCODER_OPERAND_TYPE_MEM,
    XED_ENCODER_OPERAND_TYPE_PTR,
    
     /* special for things with suppressed implicit memops */
    XED_ENCODER_OPERAND_TYPE_SEG0,
    
     /* special for things with suppressed implicit memops */
    XED_ENCODER_OPERAND_TYPE_SEG1,
    
    /* specific operand storage fields -- must supply a name */
    XED_ENCODER_OPERAND_TYPE_OTHER  
} xed_encoder_operand_type_t;

typedef struct {
    xed_encoder_operand_type_t  type;
    union {
        xed_reg_enum_t reg;
        xed_int32_t brdisp;
        xed_uint64_t imm0;
        xed_uint8_t imm1;
        struct {
            xed_operand_enum_t operand_name;
            xed_uint32_t       value;
        } s;
        xed_memop_t mem;
    } u;
    xed_uint32_t width_bits;
} xed_encoder_operand_t;

/// @name Branch Displacement
//@{
/// @ingroup ENCHL
/// a relative branch displacement operand
/// @param brdisp The branch displacement
/// @param width_bits The width of the displacement in bits. Typically 8 or 32.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_relbr(xed_int32_t brdisp,
                                                   xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_BRDISP;
    o.u.brdisp = brdisp;
    o.width_bits = width_bits;
    return o;
}
//@}

/// @name Pointer Displacement
//@{
/// @ingroup ENCHL
/// a relative displacement for a PTR operand -- the subsequent imm0 holds
///the 16b selector
/// @param brdisp The displacement for a far pointer operand
/// @param width_bits The width of the far pointr displacement in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_ptr(xed_int32_t brdisp,
                                                 xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_PTR;
    o.u.brdisp = brdisp;
    o.width_bits = width_bits;
    return o;
}
//@}

/// @name Register and Immediate Operands
//@{
/// @ingroup ENCHL
/// a register operand
/// @param reg A #xed_reg_enum_t register operand
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_reg(xed_reg_enum_t reg) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_REG;
    o.u.reg = reg;
    o.width_bits = 0;
    return o;
}

/// @ingroup ENCHL
/// a first immediate operand (known as IMM0)
/// @param v An immdediate operand.
/// @param width_bits The immediate width in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_imm0(xed_uint64_t v,
                                                  xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_IMM0;
    o.u.imm0 = v;
    o.width_bits = width_bits;
    return o;
}
/// @ingroup ENCHL
/// an 32b signed immediate operand
/// @param v An signed immdediate operand.
/// @param width_bits The immediate width in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_simm0(xed_int32_t v,
                                                   xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_SIMM0;
    /* sign conversion: we store the int32 in an uint64. It gets sign
    extended.  Later we convert it to the right width_bits for the
    instruction. The maximum width_bits of a signed immediate is currently
    32b. */
    o.u.imm0 = XED_STATIC_CAST(xed_uint64_t,xed_sign_extend32_64(v));
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// The 2nd immediate operand (known as IMM1) for rare instructions that require it.
/// @param v The 2nd immdediate (byte-width) operand
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_imm1(xed_uint8_t v) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_IMM1;
    o.u.imm1 = v; 
    o.width_bits = 8;
    return o;
}


/// @ingroup ENCHL
/// an operand storage field name and value
static XED_INLINE  xed_encoder_operand_t xed_other(
                                            xed_operand_enum_t operand_name,
                                            xed_int32_t value) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_OTHER;
    o.u.s.operand_name = operand_name;
    o.u.s.value = XED_STATIC_CAST(xed_uint32_t,value);
    o.width_bits = 0;
    return o;
}
//@}


//@}

/// @name Memory and Segment-releated Operands
//@{

/// @ingroup ENCHL
/// seg reg override for implicit suppressed memory ops
static XED_INLINE  xed_encoder_operand_t xed_seg0(xed_reg_enum_t seg0) {
    xed_encoder_operand_t o;
    o.width_bits = 0;
    o.type = XED_ENCODER_OPERAND_TYPE_SEG0;
    o.u.reg = seg0;
    return o;
}

/// @ingroup ENCHL
/// seg reg override for implicit suppressed memory ops
static XED_INLINE  xed_encoder_operand_t xed_seg1(xed_reg_enum_t seg1) {
    xed_encoder_operand_t o;
    o.width_bits = 0;
    o.type = XED_ENCODER_OPERAND_TYPE_SEG1;
    o.u.reg = seg1;
    return o;
}

/// @ingroup ENCHL
/// memory operand - base only 
/// @param base The base register
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_b(xed_reg_enum_t base,
                                                   xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = XED_REG_INVALID;
    o.u.mem.index= XED_REG_INVALID;
    o.u.mem.scale = 0;
    o.u.mem.disp.displacement = 0;
    o.u.mem.disp.displacement_bits = 0;
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// memory operand - base and displacement only
/// @param base The base register
/// @param disp The displacement
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_bd(xed_reg_enum_t base, 
                              xed_enc_displacement_t disp,
                              xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = XED_REG_INVALID;
    o.u.mem.index= XED_REG_INVALID;
    o.u.mem.scale = 0;
    o.u.mem.disp =disp;
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// memory operand - base, index, scale, displacement
/// @param base The base register
/// @param index The index register
/// @param scale The scale for the index register value
/// @param disp The displacement
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_bisd(xed_reg_enum_t base, 
                                xed_reg_enum_t index, 
                                xed_uint_t scale,
                                xed_enc_displacement_t disp,
                                xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = XED_REG_INVALID;
    o.u.mem.index= index;
    o.u.mem.scale = scale;
    o.u.mem.disp = disp;
    o.width_bits = width_bits;
    return o;
}


/// @ingroup ENCHL
/// memory operand - segment and base only
/// @param seg The segment override register
/// @param base The base register
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_gb(xed_reg_enum_t seg,
                                                    xed_reg_enum_t base,
                                                    xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = seg;
    o.u.mem.index= XED_REG_INVALID;
    o.u.mem.scale = 0;
    o.u.mem.disp.displacement = 0;
    o.u.mem.disp.displacement_bits = 0;
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// memory operand - segment, base and displacement only
/// @param seg The segment override register
/// @param base The base register
/// @param disp The displacement
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_gbd(xed_reg_enum_t seg,
                                                  xed_reg_enum_t base, 
                                                  xed_enc_displacement_t disp,
                                                  xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = seg;
    o.u.mem.index= XED_REG_INVALID;
    o.u.mem.scale = 0;
    o.u.mem.disp = disp;
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// memory operand - segment and displacement only
/// @param seg The segment override register
/// @param disp The displacement
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_gd(xed_reg_enum_t seg,
                               xed_enc_displacement_t disp,
                               xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = XED_REG_INVALID;
    o.u.mem.seg = seg;
    o.u.mem.index= XED_REG_INVALID;
    o.u.mem.scale = 0;
    o.u.mem.disp = disp;
    o.width_bits = width_bits;
    return o;
}

/// @ingroup ENCHL
/// memory operand - segment, base, index, scale, and displacement
/// @param seg The segment override register
/// @param base The base register
/// @param index The index register
/// @param scale The scale for the index register value
/// @param disp The displacement
/// @param width_bits The length of the memory reference in bits.
/// @returns xed_encoder_operand_t An operand.
static XED_INLINE  xed_encoder_operand_t xed_mem_gbisd(xed_reg_enum_t seg, 
                                 xed_reg_enum_t base, 
                                 xed_reg_enum_t index, 
                                 xed_uint_t scale,
                                 xed_enc_displacement_t disp, 
                                 xed_uint_t width_bits) {
    xed_encoder_operand_t o;
    o.type = XED_ENCODER_OPERAND_TYPE_MEM;
    o.u.mem.base = base;
    o.u.mem.seg = seg;
    o.u.mem.index= index;
    o.u.mem.scale = scale;
    o.u.mem.disp = disp;
    o.width_bits = width_bits;
    return o;
}
//@}

typedef union {
    struct {
        xed_uint32_t rep               :1;
        xed_uint32_t repne             :1;
        xed_uint32_t br_hint_taken     :1;
        xed_uint32_t br_hint_not_taken :1;
    } s;
    xed_uint32_t i;
}  xed_encoder_prefixes_t;

#define XED_ENCODER_OPERANDS_MAX 8 /* FIXME */
typedef struct {
    xed_state_t mode;
    xed_iclass_enum_t iclass; /*FIXME: use iform instead? or allow either */
    xed_uint32_t effective_operand_width;

    /* the effective_address_width is only requires to be set for
     *  instructions * with implicit suppressed memops or memops with no
     *  base or index regs.  When base or index regs are present, XED pick
     *  this up automatically from the register names.

     * FIXME: make effective_address_width required by all encodes for
     * unifority. Add to xed_inst[0123]() APIs??? */
    xed_uint32_t effective_address_width; 

    xed_encoder_prefixes_t prefixes;
    xed_uint32_t noperands;
    xed_encoder_operand_t operands[XED_ENCODER_OPERANDS_MAX];
} xed_encoder_instruction_t;

/// @name Instruction Properties and prefixes
//@{
/// @ingroup ENCHL
/// This is to specify effective address size different than the
/// default. For things with base or index regs, XED picks it up from the
/// registers. But for things that have implicit memops, or no base or index
/// reg, we must allow the user to set the address width directly. 
/// @param x The #xed_encoder_instruction_t being filled in.
/// @param width_bits The intended effective address size in bits.  Values: 16, 32 or 64.
static XED_INLINE void xed_addr(xed_encoder_instruction_t* x, 
                                xed_uint_t width_bits) {
    x->effective_address_width = width_bits;
}


/// @ingroup ENCHL
/// To add a REP (0xF3) prefix.
/// @param x The #xed_encoder_instruction_t being filled in.
static XED_INLINE  void xed_rep(xed_encoder_instruction_t* x) { 
    x->prefixes.s.rep=1;
}

/// @ingroup ENCHL
/// To add a REPNE (0xF2) prefix.
/// @param x The #xed_encoder_instruction_t being filled in.
static XED_INLINE  void xed_repne(xed_encoder_instruction_t* x) { 
    x->prefixes.s.repne=1;
}




/// @ingroup ENCHL
/// convert a #xed_encoder_instruction_t to a #xed_encoder_request_t for
/// encoding
XED_DLL_EXPORT xed_bool_t
xed_convert_to_encoder_request(xed_encoder_request_t* out,
                               xed_encoder_instruction_t* in);

//@}

/// @name Creating instructions from operands
//@{

/// @ingroup ENCHL
/// instruction with no operands
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits 
static XED_INLINE  void xed_inst0(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width) {

    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->noperands = 0;
}

/// @ingroup ENCHL
/// instruction with one operand
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param op0 the operand
static XED_INLINE  void xed_inst1(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_encoder_operand_t op0) {
    
    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->operands[0] = op0;
    inst->noperands = 1;
}

/// @ingroup ENCHL
/// instruction with two operands
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param op0 the 1st operand
/// @param op1 the 2nd operand
static XED_INLINE  void xed_inst2(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_encoder_operand_t op0,
    xed_encoder_operand_t op1) {

    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->operands[0] = op0;
    inst->operands[1] = op1;
    inst->noperands = 2;
}

/// @ingroup ENCHL
/// instruction with three operands
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param op0 the 1st operand
/// @param op1 the 2nd operand
/// @param op2 the 3rd operand
static XED_INLINE  void xed_inst3(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_encoder_operand_t op0,
    xed_encoder_operand_t op1,
    xed_encoder_operand_t op2) {

    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->operands[0] = op0;
    inst->operands[1] = op1;
    inst->operands[2] = op2;
    inst->noperands = 3;
}


/// @ingroup ENCHL
/// instruction with four operands
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param op0 the 1st operand
/// @param op1 the 2nd operand
/// @param op2 the 3rd operand
/// @param op3 the 4th operand
static XED_INLINE  void xed_inst4(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_encoder_operand_t op0,
    xed_encoder_operand_t op1,
    xed_encoder_operand_t op2,
    xed_encoder_operand_t op3) {

    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->operands[0] = op0;
    inst->operands[1] = op1;
    inst->operands[2] = op2;
    inst->operands[3] = op3;
    inst->noperands = 4;
}

/// @ingroup ENCHL
/// instruction with five operands
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param op0 the 1st operand
/// @param op1 the 2nd operand
/// @param op2 the 3rd operand
/// @param op3 the 4th operand
/// @param op4 the 5th operand
static XED_INLINE  void xed_inst5(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_encoder_operand_t op0,
    xed_encoder_operand_t op1,
    xed_encoder_operand_t op2,
    xed_encoder_operand_t op3,
    xed_encoder_operand_t op4) {

    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    inst->operands[0] = op0;
    inst->operands[1] = op1;
    inst->operands[2] = op2;
    inst->operands[3] = op3;
    inst->operands[4] = op4;
    inst->noperands = 5;
}


/// @ingroup ENCHL
/// instruction with an array of operands. The maximum number is
/// XED_ENCODER_OPERANDS_MAX. The array's contents are copied.
/// @param inst The #xed_encoder_instruction_t to be filled in
/// @param mode  The xed_state_t including the machine mode and stack address width.
/// @param iclass The #xed_iclass_enum_t
/// @param effective_operand_width in bits
/// @param number_of_operands length of the subsequent array
/// @param operand_array An array of #xed_encoder_operand_t objects
static XED_INLINE  void xed_inst(
    xed_encoder_instruction_t* inst,
    xed_state_t mode,
    xed_iclass_enum_t iclass,
    xed_uint_t effective_operand_width,
    xed_uint_t number_of_operands,
    const xed_encoder_operand_t* operand_array) {

    xed_uint_t i;
    inst->mode=mode;
    inst->iclass = iclass;
    inst->effective_operand_width = effective_operand_width;
    inst->effective_address_width = 0;
    inst->prefixes.i = 0;
    xed_assert(number_of_operands < XED_ENCODER_OPERANDS_MAX);
    for(i=0;i<number_of_operands;i++) {
        inst->operands[i] = operand_array[i];
    }
    inst->noperands = number_of_operands;
}

//@}

/*
 xed_encoder_instruction_t x,y;

 xed_inst2(&x, state, XED_ICLASS_ADD, 32, 
           xed_reg(XED_REG_EAX), 
           xed_mem_bd(XED_REG_EDX, xed_disp(0x11223344, 32), 32));
  
 xed_inst2(&y, state, XED_ICLASS_ADD, 32, 
           xed_reg(XED_REG_EAX), 
           xed_mem_gbisd(XED_REG_FS, XED_REG_EAX, XED_REG_ESI,4,
                      xed_disp(0x11223344, 32), 32));

 */

#endif
