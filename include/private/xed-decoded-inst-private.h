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
/// @file xed-decoded-inst-private.H
/// 


#if !defined(XED_DECODED_INST_PRIVATE_H)
# define XED_DECODED_INST_PRIVATE_H

#include "xed-types.h"
#include "xed-portability.h"
#include "xed-decoded-inst.h"

static XED_INLINE xed_error_enum_t
xed_decoded_inst_get_error(xed_decoded_inst_t* p) {
    return xed3_operand_get_error(p);
}

static XED_INLINE void
xed_decoded_inst_set_inst(xed_decoded_inst_t* p, const xed_inst_t* inst) {
    p->_inst = inst;
    xed3_operand_set_iclass(p,xed_inst_iclass(inst));
}

unsigned int
xed_decoded_inst_compute_memory_operand_length(const xed_decoded_inst_t* p, 
                                               unsigned int memop_idx);

// sets MEM_WIDTH
static XED_INLINE void
xed_decoded_inst_cache_memory_operand_length(xed_decoded_inst_t* p) {
    xed_uint16_t mem_width =
        (xed_uint16_t)xed_decoded_inst_compute_memory_operand_length(p, 0);
    xed3_operand_set_mem_width(p,mem_width);
}


static XED_INLINE xed_uint_t
xed_decoded_inst_set_length(xed_decoded_inst_t* p,
                            unsigned char length) {
    return p->_decoded_length = length;
}


static XED_INLINE xed_uint_t
xed_decoded_inst_inc_length(xed_decoded_inst_t* p) {
    return p->_decoded_length++;
}

static XED_INLINE xed_uint32_t
xed_phash_invalid(xed_decoded_inst_t* d) {
    return 0;
    (void) d; 
}
static XED_INLINE xed_uint32_t
xed_phash_invalid_const(const xed_decoded_inst_t* d) {
    return 0;
    (void) d; 
}

static XED_INLINE void xed_ild_set_has_modrm(xed_decoded_inst_t* d, xed_uint8_t v) {
    d->u.ild_data.s.has_modrm = v;
}
static XED_INLINE xed_uint8_t xed_ild_get_has_modrm(xed_decoded_inst_t const* d) {
    return d->u.ild_data.s.has_modrm;
}

static XED_INLINE void xed_ild_set_has_disp(xed_decoded_inst_t* d, xed_uint8_t v) {
    d->u.ild_data.s.has_disp = v;
}
static XED_INLINE xed_uint8_t xed_ild_get_has_disp(xed_decoded_inst_t const* d) {
    return d->u.ild_data.s.has_disp;
}

static XED_INLINE void xed_ild_set_has_imm(xed_decoded_inst_t* d, xed_uint8_t v) {
    d->u.ild_data.s.has_imm = v;
}
static XED_INLINE xed_uint8_t xed_ild_get_has_imm(xed_decoded_inst_t const* d) {
    return d->u.ild_data.s.has_imm;
}


#endif
