/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

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
#include "xed-decoded-inst.h"
#include "xed-decoded-inst-api.h"
#include "xed-decoded-inst-private.h"
#include "xed-util.h"
#include "xed-operand-values-interface.h"
#include "xed-reg-class.h"
#include "xed-isa-set.h" 
#include "xed-ild.h"

xed_reg_enum_t xed_decoded_inst_get_reg(const xed_decoded_inst_t* p, 
                                        xed_operand_enum_t reg_operand) {
    
    switch(reg_operand) {
      case XED_OPERAND_REG0:  return xed3_operand_get_reg0(p);
      case XED_OPERAND_REG1:  return xed3_operand_get_reg1(p);
      case XED_OPERAND_REG2:  return xed3_operand_get_reg2(p);
      case XED_OPERAND_REG3:  return xed3_operand_get_reg3(p);
      case XED_OPERAND_REG4:  return xed3_operand_get_reg4(p);
      case XED_OPERAND_REG5:  return xed3_operand_get_reg5(p);
      case XED_OPERAND_REG6:  return xed3_operand_get_reg6(p);
      case XED_OPERAND_REG7:  return xed3_operand_get_reg7(p);
      case XED_OPERAND_REG8:  return xed3_operand_get_reg8(p);
      case XED_OPERAND_BASE0: return xed3_operand_get_base0(p);
      case XED_OPERAND_BASE1: return xed3_operand_get_base1(p);
      case XED_OPERAND_SEG0:  return xed3_operand_get_seg0(p);
      case XED_OPERAND_SEG1:  return xed3_operand_get_seg1(p);
      case XED_OPERAND_INDEX: return xed3_operand_get_index(p);
      default:
        return XED_REG_INVALID;
    }

}


xed_uint32_t
xed_decoded_inst_get_attribute(const xed_decoded_inst_t* p,
                               xed_attribute_enum_t attr)
{
    xed_assert(p->_inst != 0);
    return xed_inst_get_attribute(p->_inst, attr);
}

xed_attributes_t
xed_decoded_inst_get_attributes(const xed_decoded_inst_t* p)
{
    xed_assert(p->_inst != 0);
    return xed_inst_get_attributes(p->_inst);
}

/* xrelease is valid when we have:
    1: F3 (REP) prefix  AND
    2: (a) xchg inst.   OR
       (b) lock prefix  OR
       (c) mov mem,reg or mov mem,imm where reg is a normal register.

    ** cmpxchg16b inst. is special and can not have xacquire 
*/
xed_uint32_t
xed_decoded_inst_is_xrelease(const xed_decoded_inst_t* p){
    xed_iclass_enum_t iclass;
    const xed_operand_values_t* ov;
    xed_uint32_t rel_able =
        xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_HLE_REL_ABLE);    
    
    if (rel_able){
        ov = xed_decoded_inst_operands_const(p);
        if (xed_operand_values_has_rep_prefix(ov)){
            iclass = xed_decoded_inst_get_iclass(p);
            if (xed_operand_values_get_atomic(ov) || iclass == XED_ICLASS_MOV){
                //mov instruction do not need the lock prefix
                return 1;
            }
        }
    }
    return 0;
}

/* xacquire is valid when we have:
    1: F2 (REPNE) prefix
    2: xchg inst. OR lock prefix 
    ** cmpxchg16b inst. is special and can not have xacquire 
*/
xed_uint32_t
xed_decoded_inst_is_xacquire(const xed_decoded_inst_t* p){
    const xed_operand_values_t* ov;
    xed_uint32_t acq_able =
        xed_decoded_inst_get_attribute(p,XED_ATTRIBUTE_HLE_ACQ_ABLE);
    
    if (acq_able){
        ov = xed_decoded_inst_operands_const(p);
        if (xed_operand_values_has_repne_prefix(ov)){
            return xed_operand_values_get_atomic(ov);
        }
    }
    return 0;
}

xed_uint32_t
xed_decoded_inst_has_mpx_prefix(const xed_decoded_inst_t* p){
    const xed_operand_values_t* ov;
    xed_uint32_t mpx_able = xed_decoded_inst_get_attribute(p,
                                              XED_ATTRIBUTE_MPX_PREFIX_ABLE);
    if (mpx_able){
        ov = xed_decoded_inst_operands_const(p);
        if (xed_operand_values_has_repne_prefix(ov)){
            return 1;
        }
    }
    return 0;
}

xed_uint8_t
xed_decoded_inst_get_modrm(const xed_decoded_inst_t* p)
{
    return xed3_operand_get_modrm_byte(p);
}

/////////////////////////////////////////////////////////////////////////
xed_int32_t
xed_decoded_inst_get_branch_displacement(const xed_decoded_inst_t* p) {
  return xed_operand_values_get_branch_displacement_int32(p);
}
xed_uint_t
xed_decoded_inst_get_branch_displacement_width(const xed_decoded_inst_t* p) {
  return xed3_operand_get_brdisp_width(p)/8;
}
xed_uint_t
xed_decoded_inst_get_branch_displacement_width_bits(const xed_decoded_inst_t* p) {
  return xed3_operand_get_brdisp_width(p);
}
/////////////////////////////////////////////////////////////////////////


xed_uint64_t
xed_decoded_inst_get_unsigned_immediate(const xed_decoded_inst_t* p) {
    return xed_operand_values_get_immediate_uint64(p);
}
xed_int32_t
xed_decoded_inst_get_signed_immediate(const xed_decoded_inst_t* p) {
    xed_int64_t y =  xed_operand_values_get_immediate_int64(p);
    return XED_STATIC_CAST(xed_int32_t,y);
}
xed_uint_t
xed_decoded_inst_get_immediate_width(const xed_decoded_inst_t* p) {
    return xed3_operand_get_imm_width(p)/8;
}
xed_uint_t
xed_decoded_inst_get_immediate_width_bits(const xed_decoded_inst_t* p) {
    return xed3_operand_get_imm_width(p);
}

xed_uint_t
xed_decoded_inst_get_immediate_is_signed(const xed_decoded_inst_t* p) {
    //return xed_operand_values_get_immediate_is_signed(p);
    return xed3_operand_get_imm0signed(p);
}


/////////////////////////////////////////////////////////////////////////

xed_int64_t
xed_decoded_inst_get_memory_displacement(const xed_decoded_inst_t* p,
                                         unsigned int mem_idx)
{
    if (xed_operand_values_has_memory_displacement(p))
    {
        switch(mem_idx)
        {
          case 0:
            return xed_operand_values_get_memory_displacement_int64(p);
            
          case 1:
            return 0;
            
          default:
            xed_assert(mem_idx == 0 || mem_idx == 1);
        }
    }
    return 0;
}
xed_uint_t
xed_decoded_inst_get_memory_displacement_width(const xed_decoded_inst_t* p,
                                               unsigned int mem_idx)
{
    return xed_decoded_inst_get_memory_displacement_width_bits(p,mem_idx)/8;
}
xed_uint_t
xed_decoded_inst_get_memory_displacement_width_bits(
    const xed_decoded_inst_t* p,
    unsigned int mem_idx)
{

    if (xed_operand_values_has_memory_displacement(p))
    {
        switch(mem_idx) {
          case 0:
            return xed_operand_values_get_memory_displacement_length_bits(p);
          case 1:
            return 0;
            
          default:
            xed_assert(mem_idx == 0 || mem_idx == 1);
        }
    }
    return 0;
}

xed_reg_enum_t xed_decoded_inst_get_seg_reg(const xed_decoded_inst_t* p,
                                            unsigned int mem_idx) {
    switch(mem_idx) {
      case 0: return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_seg0(p)); 
      case 1: return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_seg1(p)); 
      default: xed_assert(mem_idx == 0 || mem_idx == 1);
    }
    return XED_REG_INVALID;
}
xed_reg_enum_t xed_decoded_inst_get_base_reg(const xed_decoded_inst_t* p,
                                             unsigned int mem_idx) {
    switch(mem_idx) {
      case 0: return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_base0(p));
      case 1: return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_base1(p));
      default: xed_assert(mem_idx == 0 || mem_idx == 1);
    }
    return XED_REG_INVALID;
}
xed_reg_enum_t xed_decoded_inst_get_index_reg(const xed_decoded_inst_t* p,
                                              unsigned int mem_idx) {
    switch(mem_idx) {
      case 0: return XED_STATIC_CAST(xed_reg_enum_t,xed3_operand_get_index(p));
      case 1: return XED_REG_INVALID;
      default: xed_assert(mem_idx == 0 || mem_idx == 1);
    }
    return XED_REG_INVALID;
}
xed_uint_t xed_decoded_inst_get_scale(const xed_decoded_inst_t* p,
                                      unsigned int mem_idx) {
    switch(mem_idx) {
      case 0: return xed3_operand_get_scale(p);
      case 1: return 1;
      default: xed_assert(mem_idx == 0 || mem_idx == 1);
    }
    return XED_REG_INVALID;
}

xed_bool_t xed_decoded_inst_mem_read(const xed_decoded_inst_t* p,
                                     unsigned int mem_idx) {
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)    {
        const xed_operand_t* o = xed_inst_operand(inst,i);
        if ((mem_idx == 0 && xed_operand_name(o) == XED_OPERAND_MEM0) ||
            (mem_idx == 1 && xed_operand_name(o) == XED_OPERAND_MEM1))
            switch(xed_decoded_inst_operand_action(p,i))
            {
              case XED_OPERAND_ACTION_RW:
              case XED_OPERAND_ACTION_R:
              case XED_OPERAND_ACTION_RCW:
              case XED_OPERAND_ACTION_CRW:
              case XED_OPERAND_ACTION_CR:
                return 1;
              default:
                break;
            }
    }
    return 0;

}

xed_bool_t
xed_decoded_inst_mem_written(const xed_decoded_inst_t* p,
                             unsigned int mem_idx) 
{
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)
    {
        const xed_operand_t* o = xed_inst_operand(inst,i);
        if ((mem_idx == 0 && xed_operand_name(o) == XED_OPERAND_MEM0) ||
            (mem_idx == 1 && xed_operand_name(o) == XED_OPERAND_MEM1))
            switch(xed_decoded_inst_operand_action(p,i))
            {
              case XED_OPERAND_ACTION_RW:
              case XED_OPERAND_ACTION_W:
              case XED_OPERAND_ACTION_RCW:
              case XED_OPERAND_ACTION_CRW:
              case XED_OPERAND_ACTION_CW:
                return 1;
              default:
                break;
            }
    }
    return 0;
}


xed_bool_t
xed_decoded_inst_conditionally_writes_registers(const xed_decoded_inst_t* p )
{
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++) {
        switch(xed_decoded_inst_operand_action(p,i)) {
          case XED_OPERAND_ACTION_RCW:
          case XED_OPERAND_ACTION_CW:
            return 1;
          default:
            break;
        }
    }
    return 0;
}

xed_bool_t
xed_decoded_inst_mem_written_only(const xed_decoded_inst_t* p,
                                  unsigned int mem_idx) 
{
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)
    {
        const xed_operand_t* o = xed_inst_operand(inst,i);

        if ((mem_idx == 0 && xed_operand_name(o) == XED_OPERAND_MEM0) ||
            (mem_idx == 1 && xed_operand_name(o) == XED_OPERAND_MEM1))
            switch(xed_decoded_inst_operand_action(p,i))
            {
              case XED_OPERAND_ACTION_W:
              case XED_OPERAND_ACTION_CW:
                return 1;
              default:
                break;
            }
    }
    return 0;
}


static XED_INLINE unsigned int 
xed_decoded_inst_get_find_memop(const xed_decoded_inst_t* p,
                                xed_uint_t memop_idx) {
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)    {     //FIXME: slow scan...
        const xed_operand_t* o = xed_inst_operand(inst,i);
        const xed_operand_enum_t op_name = xed_operand_name(o);
        if ((memop_idx == 0 && op_name == XED_OPERAND_MEM0) ||
            (memop_idx == 1 && op_name == XED_OPERAND_MEM1))   {
            return i;
        }
    }
    xed_assert(0);
    return 0;
}

unsigned int 
xed_decoded_inst_get_memop_address_width(const xed_decoded_inst_t* p,
                                         xed_uint_t memop_idx) {
    /* Return the addressing width for memop_idx (0 or 1).
     *
     * In 16/32b modes, if the memop is an implicit stack reference, then
     * use the stack addressing width as the effective address size for
     * that memop. This DOES NOT include base references that use rSP/rBP
     * which implicitly have SS as their stack selector (if not
     * overridden).
     *
     * In 64b mode, the effective addressing width of a reference that
     * would use the stack is 64b. 
     */

    const xed_inst_t* inst = p->_inst;
    const xed_uint32_t i   = xed_decoded_inst_get_find_memop(p,memop_idx);
    const xed_operand_t* o = xed_inst_operand(inst,i);
    const xed_operand_width_enum_t width = xed_operand_width(o);
    xed_uint32_t bits;

    if ( width == XED_OPERAND_WIDTH_SSZ ||
         width == XED_OPERAND_WIDTH_SPW ||  
         width == XED_OPERAND_WIDTH_SPW2 ||  
         width == XED_OPERAND_WIDTH_SPW3 ||
         width == XED_OPERAND_WIDTH_SPW8 ) {
        bits=xed_operand_values_get_stack_address_width(
            xed_decoded_inst_operands_const(p));
    }
    else {
        bits=xed_operand_values_get_effective_address_width(
            xed_decoded_inst_operands_const(p));
    }
    return bits;
}


static XED_INLINE unsigned int 
xed_decoded_inst_get_operand_width_bits(const xed_decoded_inst_t* p,
                                        const xed_operand_t* o ) {
    const xed_operand_width_enum_t width = xed_operand_width(o);
    unsigned int  bits=0;
    if (width == XED_OPERAND_WIDTH_SSZ) {
        bits=xed_operand_values_get_stack_address_width(
                               xed_decoded_inst_operands_const(p));
    }
    else if (width == XED_OPERAND_WIDTH_ASZ) {
        bits=xed_operand_values_get_effective_address_width(
                               xed_decoded_inst_operands_const(p));
    }
    else {
        const xed_uint32_t eosz = xed3_operand_get_eosz(p);
        xed_assert(width < XED_OPERAND_WIDTH_LAST);
        xed_assert(eosz <= 3);
        bits = xed_width_bits[width][eosz];
    }
    return bits;
}


static xed_uint32_t
xed_decoded_inst_compute_variable_width(const xed_decoded_inst_t* p, 
                                        const xed_operand_t* o) {
    const xed_uint32_t        nelem = xed3_operand_get_nelem(p);
    const xed_uint32_t element_size = xed3_operand_get_element_size(p);
    return nelem*element_size;
    (void)o; // pacify compiler
}


unsigned int  
xed_decoded_inst_compute_memory_operand_length(const xed_decoded_inst_t* p, 
                                               unsigned int memop_idx)  {
    const xed_inst_t* inst = p->_inst;
    const unsigned int i = xed_decoded_inst_get_find_memop(p, memop_idx);
    const xed_operand_t* o = xed_inst_operand(inst,i);
    xed_uint32_t bits =  xed_decoded_inst_get_operand_width_bits(p,o);
    if (bits)
        return bits>>3;
    bits = xed_decoded_inst_compute_variable_width(p,o);
    return bits>>3;
}

// returns bytes
unsigned int
xed_decoded_inst_get_memory_operand_length(const xed_decoded_inst_t* p, 
                                           unsigned int memop_idx)
{
    if (xed_decoded_inst_number_of_memory_operands(p) > memop_idx)
        return xed_decoded_inst_compute_memory_operand_length(p,memop_idx);
    return 0;
}

static xed_uint32_t
xed_decoded_inst_operand_length_bits_register(
    const xed_decoded_inst_t* p, 
    unsigned int operand_index)
{
    xed_uint32_t mode = 0;
    xed_uint_t idx = 0; // default for 16b and 32b
    const xed_inst_t* inst = p->_inst;
    const xed_operand_t* o = xed_inst_operand(inst,operand_index);
    xed_operand_enum_t op_name = xed_operand_name(o);

    xed_reg_enum_t r;
    
    /* some registers have a special width specified */
    const xed_operand_width_enum_t width = xed_operand_width(o);
    if (width != XED_OPERAND_WIDTH_INVALID)
        return xed_decoded_inst_get_operand_width_bits(p,o);
    
    r = xed_decoded_inst_get_reg(p,op_name);
    mode = xed_decoded_inst_get_machine_mode_bits(p);
    if (mode == 64) 
        idx = 1;
    return xed_reg_width_bits[r][idx];
}


unsigned int
xed_decoded_inst_operand_length_bits(
    const xed_decoded_inst_t* p, 
    unsigned int operand_index)
{
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    const xed_operand_t* o = xed_inst_operand(inst,operand_index);
    xed_operand_enum_t op_name;
    xed_uint32_t len;
    if (noperands <= operand_index)
        return 0;


    op_name = xed_operand_name(o);
    if (xed_operand_template_is_register(o)) {
        len= xed_decoded_inst_operand_length_bits_register( p,operand_index);
        return len;
    }
    else if (op_name == XED_OPERAND_AGEN) {
        len=xed_operand_values_get_effective_address_width(
            xed_decoded_inst_operands_const(p));
        
        return len;
    }
    // MEM0, MEM1,PTR, IMM0, IMM1, and RELBR use the width codes now.
    // use the "scalable" width codes from the operand template.

    len =  xed_decoded_inst_get_operand_width_bits(p,o);
    if (len)
        return len;

    // variable width stuff must compute it based on nelem * element_size
    len = xed_decoded_inst_compute_variable_width(p,o);
    return len;
}

unsigned int xed_decoded_inst_operand_length(const xed_decoded_inst_t* p, 
                                              unsigned int operand_index)  {
    unsigned int bits = xed_decoded_inst_operand_length_bits(p, operand_index);
    return bits >> 3;
}



/*******************************************************************/

// The number of elements in the operand
unsigned int  xed_decoded_inst_operand_elements(const xed_decoded_inst_t* p, 
                                                unsigned int operand_index) 
{
    unsigned int nelem = 1;
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    const xed_operand_t* o = xed_inst_operand(inst,operand_index);
    xed_operand_width_enum_t width;
    xed_operand_element_xtype_enum_t xtype;
    const xed_operand_type_info_t* q;

    if ( operand_index >= noperands ) 
        return 0;

    width = xed_operand_width(o);
    if ( width >= XED_OPERAND_WIDTH_LAST)
        return 0;

    xtype = xed_operand_xtype(o);
    if ( xtype >= XED_OPERAND_XTYPE_LAST)
        return 0;

    q = xed_operand_xtype_info+xtype;
    if (q->bits_per_element) {
        const xed_uint_t bits =
            xed_decoded_inst_operand_length_bits(p, operand_index);
        
        nelem = bits / q->bits_per_element;
    }
    else if (q->dtype == XED_OPERAND_ELEMENT_TYPE_STRUCT) {
        nelem = 1;
    }
    else if (q->dtype == XED_OPERAND_ELEMENT_TYPE_VARIABLE) {
        nelem = xed3_operand_get_nelem(p);
    }
    else { // XED_OPERAND_ELEMENT_TYPE_INT, XED_OPERAND_ELEMENT_TYPE_UINT
        nelem  = 1;
    }
    
    return nelem;
}

unsigned int
xed_decoded_inst_operand_element_size_bits(
    const xed_decoded_inst_t* p, 
    unsigned int operand_index) 
{

    unsigned int element_size = 0;
    const xed_inst_t* inst = p->_inst;
    const xed_operand_t* o = xed_inst_operand(inst,operand_index);
    const xed_operand_element_xtype_enum_t xtype = xed_operand_xtype(o);
    const xed_operand_type_info_t* q;
    if ( xtype >= XED_OPERAND_XTYPE_LAST)
        return 0;

    q = xed_operand_xtype_info+xtype;
    if (q->bits_per_element) {
        element_size = q->bits_per_element;
    }
    else if ( q->dtype == XED_OPERAND_ELEMENT_TYPE_STRUCT ||
              q->dtype == XED_OPERAND_ELEMENT_TYPE_INT  ||
              q->dtype == XED_OPERAND_ELEMENT_TYPE_UINT  ) {
        element_size  = xed_decoded_inst_operand_length_bits(p, operand_index);
    }
    else if (q->dtype == XED_OPERAND_ELEMENT_TYPE_VARIABLE) {
        element_size = xed3_operand_get_element_size(p);
    }
    else if (xed_operand_template_is_register(o)) {
        return xed_decoded_inst_operand_length_bits_register(p, operand_index);
    }
    else { 
        // catch all
        xed_assert(0);
    }
    return element_size;
}

xed_operand_element_type_enum_t
xed_decoded_inst_operand_element_type(const xed_decoded_inst_t* p, 
                                      unsigned int operand_index)
{
    xed_operand_element_type_enum_t dtype = XED_OPERAND_ELEMENT_TYPE_INVALID;    
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    const xed_operand_t* o = xed_inst_operand(inst,operand_index);
    xed_operand_width_enum_t width;
    xed_operand_element_xtype_enum_t xtype;
    if ( operand_index >= noperands ) 
        return dtype;

    width = xed_operand_width(o);
    if ( width >= XED_OPERAND_WIDTH_LAST)
        return dtype;

    xtype = xed_operand_xtype(o);
    if ( xtype < XED_OPERAND_XTYPE_LAST) {

        const xed_operand_type_info_t* q = xed_operand_xtype_info+xtype;
        dtype = q->dtype;
        /* This is a catch case for the register NTs that do not have 
           type codes. It is not 100% accurate */
        if (dtype == XED_OPERAND_ELEMENT_TYPE_INVALID) 
            return XED_OPERAND_ELEMENT_TYPE_INT; 
        else if (dtype == XED_OPERAND_ELEMENT_TYPE_VARIABLE) 
            dtype = XED_STATIC_CAST(xed_operand_element_type_enum_t,
                                    xed3_operand_get_type(p));
    }
    return dtype;
}

/*******************************************************************/


xed_bool_t 
xed_decoded_inst_uses_rflags(const xed_decoded_inst_t* q) 
{
    const xed_simple_flag_t* p = xed_decoded_inst_get_rflags_info(q);
    if (p && xed_simple_flag_get_nflags(p) > 0 )
        return 1;
    return 0;
}


static xed_uint8_t 
xed_decoded_inst__compute_masked_immediate( const xed_decoded_inst_t* p)
{
    xed_uint8_t imm_byte;
    xed_uint8_t masked_imm_byte;
    xed_uint8_t mask = 0x1F;
    if (xed_operand_values_get_effective_operand_width(p) == 64)
        mask = 0x3F;
    xed_assert(xed3_operand_get_imm_width(p) == 8);
    imm_byte = xed3_operand_get_uimm0(p);
    masked_imm_byte = imm_byte & mask;
    return masked_imm_byte;
}

const xed_simple_flag_t*
xed_decoded_inst_get_rflags_info(const xed_decoded_inst_t* q) 
{
    xed_uint32_t complex_simple_index;
    const xed_complex_flag_t*  p;

    // no flags
    const xed_inst_t* inst = xed_decoded_inst_inst(q);
    xed_uint32_t t_index = inst->_flag_info_index;
    if(t_index == 0)
        return 0;

    // simple

    if (inst->_flag_complex==0)
        return xed_flags_simple_table+t_index;

    // complex

    complex_simple_index=0;
    p = xed_flags_complex_table + t_index;
    if (p->check_rep)
    {   
        if (xed_operand_values_has_real_rep(q))
            complex_simple_index = p->cases[XED_FLAG_CASE_HAS_REP];
        else
            complex_simple_index = p->cases[XED_FLAG_CASE_NO_REP];
    }
    else  if (p->check_imm)
    {
        xed_uint8_t masked_imm_byte =
            xed_decoded_inst__compute_masked_immediate(q);

        if (masked_imm_byte == 0)
            complex_simple_index = p->cases[XED_FLAG_CASE_IMMED_ZERO];
        else if (masked_imm_byte == 1)
            complex_simple_index = p->cases[XED_FLAG_CASE_IMMED_ONE];
        else
            complex_simple_index = p->cases[XED_FLAG_CASE_IMMED_OTHER];
    }
    else
        xed_assert(0);

    if (complex_simple_index == 0)
        return 0;
    return xed_flags_simple_table+complex_simple_index;
}

xed_bool_t
xed_decoded_inst_is_prefetch(const xed_decoded_inst_t* p) 
{
    return xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_PREFETCH);    
}

xed_uint_t
xed_decoded_inst_number_of_memory_operands(const xed_decoded_inst_t* p) {
    return (xed3_operand_get_mem0(p) +
            xed3_operand_get_mem1(p) + xed3_operand_get_agen(p));
}




//////////////////////////////////////////////////////////////////////////
// Modifying decoded instructions before re-encoding    


void xed_decoded_inst_set_scale(xed_decoded_inst_t* p, xed_uint_t scale) {
    xed3_operand_set_scale(p,scale);
}
void xed_decoded_inst_set_memory_displacement(xed_decoded_inst_t* p,
                                              xed_int64_t disp,
                                              xed_uint_t length_bytes) {
    xed_operand_values_set_memory_displacement(p, disp, length_bytes);
}
void xed_decoded_inst_set_branch_displacement(xed_decoded_inst_t* p,
                                              xed_int32_t disp,
                                              xed_uint_t length_bytes) {
    xed_operand_values_set_branch_displacement(p, disp, length_bytes);
}

void xed_decoded_inst_set_immediate_signed(xed_decoded_inst_t* p,
                                           xed_int32_t x,
                                           xed_uint_t length_bytes) {
    xed_operand_values_set_immediate_signed(p, x,length_bytes);
}
void xed_decoded_inst_set_immediate_unsigned(xed_decoded_inst_t* p,
                                             xed_uint64_t x,
                                             xed_uint_t length_bytes) {
    xed_operand_values_set_immediate_unsigned(p, x,length_bytes);
}

////////

void xed_decoded_inst_set_memory_displacement_bits(xed_decoded_inst_t* p,
                                                   xed_int64_t disp,
                                                   xed_uint_t length_bits) {
    xed_operand_values_set_memory_displacement_bits(p, disp, length_bits);
}
void xed_decoded_inst_set_branch_displacement_bits(xed_decoded_inst_t* p,
                                                   xed_int32_t disp,
                                                   xed_uint_t length_bits) {
    xed_operand_values_set_branch_displacement_bits(p, disp, length_bits);
}

void xed_decoded_inst_set_immediate_signed_bits(xed_decoded_inst_t* p,
                                                xed_int32_t x,
                                                xed_uint_t length_bits) {
    xed_operand_values_set_immediate_signed_bits(p, x,length_bits);
}
void xed_decoded_inst_set_immediate_unsigned_bits(xed_decoded_inst_t* p,
                                                  xed_uint64_t x,
                                                  xed_uint_t length_bits) {
    xed_operand_values_set_immediate_unsigned_bits(p, x,length_bits);
}


////////////////////////////////////////////////////////////////////////////


xed_uint32_t xed_decoded_inst_get_operand_width(const xed_decoded_inst_t* p) {
    if (xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_BYTEOP)) 
        return 8;
    return xed_operand_values_get_effective_operand_width(p);
}



xed_bool_t
xed_decoded_inst_valid_for_chip(xed_decoded_inst_t const* const p,
                                xed_chip_enum_t chip)
{
    xed_isa_set_enum_t isa_set;
    
    isa_set = xed_decoded_inst_get_isa_set( p);
    return xed_isa_set_is_valid_for_chip(isa_set, chip);
}

xed_uint_t
xed_decoded_inst_vector_length_bits(xed_decoded_inst_t const* const p)
{
    xed_uint_t vl_bits=0;
#if defined(XED_AVX)
    xed_uint_t vl_encoded;
    // only valid for VEX, EVEX (and XOP) instructions.
    if (xed3_operand_get_vexvalid(p) == 0)
        return 0;
            
    /* vl_encoded 0=128,1=256,2=512*/
    vl_encoded = xed3_operand_get_vl(p);
    
    /* 0->128, 1->256, 2->512 */
    vl_bits = 1 << (vl_encoded+7);
#endif
    return  vl_bits;
    (void)p; // pacify (msvs) compiler for noavx builds
}

xed_bool_t
xed_decoded_inst_masked_vector_operation(xed_decoded_inst_t* p)
{
    // pre-evex masked operations
    xed_uint32_t maskop =
        xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_MASKOP);
    if (maskop)
        return 1;
    // if evex, and not k0, and not mask-as-control, then report it as a
    // masked operation. Evex operations that mask-as-control are a
    // different kind of masked operation.

    if (xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_MASKOP_EVEX) &&
        !xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_MASK_AS_CONTROL))
    {
        const xed_uint_t write_mask_operand = 1;
        const xed_operand_t* op = xed_inst_operand(p->_inst, write_mask_operand);
        xed_operand_enum_t op_name = xed_operand_name(op);
        if (op_name == XED_OPERAND_REG0 || op_name == XED_OPERAND_REG1) {
            xed_reg_enum_t r = xed_decoded_inst_get_reg(p, op_name);
            if (xed_reg_class(r) == XED_REG_CLASS_MASK) {
                if (r != XED_REG_K0)
                    return 1;
            }
        }
    }
    
    return 0;
}
                                         


xed_uint_t
xed_decoded_inst_get_nprefixes(xed_decoded_inst_t* p) {
    return xed3_operand_get_nprefixes(p);
}

xed_bool_t xed_decoded_inst_masking(const xed_decoded_inst_t* p) {
#if defined(XED_SUPPORTS_AVX512) || defined(XED_SUPPORTS_KNC)
    if (xed3_operand_get_mask(p) != 0)
        return 1;
#endif
    return 0;
    (void)p; //pacify compiler
}
xed_bool_t xed_decoded_inst_merging(const xed_decoded_inst_t* p) {
#if defined(XED_SUPPORTS_AVX512) || defined(XED_SUPPORTS_KNC)
    if (xed3_operand_get_mask(p) != 0)
#   if defined(XED_SUPPORTS_AVX512)
        if (xed3_operand_get_zeroing(p) == 0)
            if (!xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_MASK_AS_CONTROL))            
                return 1;
#   elif defined(XED_SUPPORTS_KNC)
        return 1;
#   endif
#endif
    return 0;
    (void)p; //pacify compiler
}
xed_bool_t xed_decoded_inst_zeroing(const xed_decoded_inst_t* p) {
#if defined(XED_SUPPORTS_AVX512)
    if (xed3_operand_get_mask(p) != 0)
        if (xed3_operand_get_zeroing(p) == 1)
            return 1;
#endif
    return 0;
    (void)p; //pacify compiler
}

xed_operand_action_enum_t
xed_decoded_inst_operand_action(const xed_decoded_inst_t* p,
                                unsigned int operand_index)
{

    /* For the 0th operand, except for stores and except if attribute MASK_AS_CONTROL
                             RW             W   <<< SDM/XED notion
      ===========================================
      aaa=0   control     n/a             w
      aaa=0   merging     rw              w
      aaa=0   zeroing     n/a             n/a
      
      aaa!=0  control     n/a             w
      aaa!=0  merging     r+cw            r+cw  <<< This one requires special handling
      aaa!=0  zeroing     r+w             w
     */
    
    const xed_inst_t* xi = xed_decoded_inst_inst(p);
    const xed_operand_t* op = xed_inst_operand(xi,operand_index);
    xed_operand_action_enum_t rw = xed_operand_rw(op);

    if (operand_index == 0)
    {
        if (xed_decoded_inst_masking(p) && xed_decoded_inst_merging(p))
        {
            if (rw == XED_OPERAND_ACTION_RW)
                return XED_OPERAND_ACTION_RCW;
            //need to filter out stores which do NOT read memory when merging.
            if (rw == XED_OPERAND_ACTION_W)
            {
                const xed_operand_t* zero_op = xed_inst_operand(xi,0);
                if (xed_operand_name(zero_op) == XED_OPERAND_MEM0)
                    return XED_OPERAND_ACTION_CW;
                // reflect dest register input dependence when merging
                return XED_OPERAND_ACTION_RCW;
            }

        }
    }
    
    return rw;
}

xed_bool_t
xed_decoded_inst_uses_embedded_broadcast(const xed_decoded_inst_t* p)
{
#if defined(XED_SUPPORTS_AVX512)
    if (xed_decoded_inst_get_attribute(p, XED_ATTRIBUTE_BROADCAST_ENABLED))
        if (xed3_operand_get_bcast(p))  
            return 1;
#endif
    return 0;
    (void) p;
}
xed_bool_t
xed_decoded_inst_is_broadcast_instruction(const xed_decoded_inst_t* p)
{
#if defined(XED_AVX)  // also reports AVX512 broadcast instr
    if (xed_decoded_inst_get_category(p) == XED_CATEGORY_BROADCAST)
        return 1;
#endif
    return 0;
    (void) p;
}
xed_bool_t
xed_decoded_inst_is_broadcast(const xed_decoded_inst_t* p)
{
    //FIXME: add an enum for the broadcast values so we can give a better answer here
    if (xed_decoded_inst_is_broadcast_instruction(p))
        return 1;
    if (xed_decoded_inst_uses_embedded_broadcast(p))
        return 1;
     return 0;
}
