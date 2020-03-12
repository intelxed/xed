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
/// @file xed-inst.c


////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-inst.h"
#include "xed-inst-private.h"
#include "xed-portability.h"
#include "xed-tables-extern.h"
#include "xed-operand-action.h"


const xed_inst_t* xed_inst_table_base(void) {
    return xed_inst_table;
}


xed_uint_t xed_operand_read(const xed_operand_t* p) {
    return xed_operand_action_read(p->_rw);
}
xed_uint_t xed_operand_read_only(const xed_operand_t* p) {
    return xed_operand_action_read_only(p->_rw);
}
xed_uint_t xed_operand_written(const xed_operand_t* p) {
    return xed_operand_action_written(p->_rw);
}
xed_uint_t xed_operand_written_only(const xed_operand_t* p) {
    return xed_operand_action_written_only(p->_rw);
}
xed_uint_t xed_operand_read_and_written(const xed_operand_t* p) {
    return xed_operand_action_read_and_written(p->_rw);
}
xed_uint_t xed_operand_conditional_read(const xed_operand_t* p) {
    return xed_operand_action_conditional_read(p->_rw);
}
xed_uint_t xed_operand_conditional_write(const xed_operand_t* p) {
    return xed_operand_action_conditional_write(p->_rw);
}

xed_uint32_t xed_operand_width_bits(const xed_operand_t* p,
                                    const xed_uint32_t eosz) {
    const xed_operand_width_enum_t width = xed_operand_width(p);

    xed_assert(width < XED_OPERAND_WIDTH_LAST);
    xed_assert(eosz <= 3);
    return xed_width_bits[width][eosz];
}

xed_nonterminal_enum_t xed_operand_nt_lookup_fn_enum(const xed_operand_t* p) {
    return p->_u._nt;
}


        

void xed_inst_init(xed_inst_t* p) {
    //p->_confirmer = 0;
    p->_noperands = 0;
    p->_operand_base = 0;
    p->_flag_info_index = 0;
    p->_flag_complex = 0;
    p->_cpl=0;
}

unsigned int xed_inst_cpl(const xed_inst_t* p) {
    return p->_cpl;
}






    
xed_uint32_t xed_inst_flag_info_index(const xed_inst_t* p) {
    return p->_flag_info_index;
}


void xed_operand_print(const xed_operand_t* p, char* buf, int buflen) {
    int blen = buflen;
    blen = xed_strncpy(buf,xed_operand_enum_t2str(p->_name),blen);
    blen = xed_strncat(buf,"/",blen);
    blen = xed_strncat(buf,xed_operand_action_enum_t2str(p->_rw),blen);
    blen = xed_strncat(buf,"/",blen);
    blen = xed_strncat(buf, xed_operand_width_enum_t2str(p->_oc2),blen);
    blen = xed_strncat(buf,"/",blen);
    blen = xed_strncat(buf,  xed_operand_visibility_enum_t2str(p->_operand_visibility),blen);
    blen = xed_strncat(buf,"/",blen);
    blen = xed_strncat(buf, xed_operand_type_enum_t2str(p->_type),blen);
    if (p->_type == XED_OPERAND_TYPE_REG) {
        blen = xed_strncat(buf,"/",blen);
        blen = xed_strncat(buf, xed_reg_enum_t2str(xed_operand_reg(p)),blen);
    }
    else if (p->_type == XED_OPERAND_TYPE_IMM_CONST) {
        xed_bool_t leading_zeros = 0;
        char tbuf[50];
        blen = xed_strncat(buf,"/",blen);
        (void)xed_itoa_hex_zeros(tbuf,xed_operand_imm(p),64,leading_zeros,50);
        blen = xed_strncat(buf,tbuf,blen);
    }
    else if (p->_nt) {
        blen = xed_strncat(buf,"/",blen);
        blen = xed_strncat(buf,
                           xed_nonterminal_enum_t2str(xed_operand_nt_lookup_fn_enum(p)),
                           blen);
    }
}

unsigned int xed_attribute_max(void) {
    return XED_MAX_ATTRIBUTE_COUNT;
}

xed_attribute_enum_t xed_attribute(unsigned int i) {
    xed_assert(i < XED_MAX_ATTRIBUTE_COUNT);
    return xed_attributes_table[i];
}

extern const xed_attributes_t xed_attributes[XED_MAX_REQUIRED_ATTRIBUTES];

xed_uint32_t
xed_inst_get_attribute(const xed_inst_t* p, 
                       xed_attribute_enum_t attr) {

    const xed_attributes_t* a = xed_attributes + p->_attributes;
    const xed_uint64_t one = 1;
    if (XED_CAST(xed_uint_t,attr) < 64)  
        return  (a->a1 & (one<<attr)) != 0; 
    return (a->a2 & (one<<(attr-64))) != 0;
}


xed_attributes_t
xed_inst_get_attributes(const xed_inst_t* p) {
    return xed_attributes[p->_attributes];
}


const xed_operand_t*
xed_inst_operand(const xed_inst_t* p, unsigned int i)    {
    xed_assert(i <  p->_noperands);
    return &(xed_operand[xed_operand_sequences[p->_operand_base + i]]);
}

