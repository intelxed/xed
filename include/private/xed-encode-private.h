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
/// @file xed-encode-private.H
/// 


#if !defined(XED_ENCODE_PRIVATE_H)
# define XED_ENCODE_PRIVATE_H

#include "xed-types.h"
#include "xed-encode-types.h"
#include "xed-portability.h"
#include "xed-error-enum.h"
#include "xed-operand-values-interface.h"
#include "xed-operand-width-enum.h"
#include "xed-ild-private.h"
#include "xed-encoder-iforms.h" //generated
#include "xed-encoder-gen-defs.h" //generated
#include <string.h> // for memset

#define XED_GLOBAL_EXTERN extern
#include "xed-encode-tables.h"
#undef  XED_GLOBAL_EXTERN

static XED_INLINE const xed_encoder_vars_t*
xed_encoder_request_ev_const(const xed_encoder_request_t* p) {
    return p->u.ev;
}
static XED_INLINE xed_encoder_vars_t* xed_encoder_request_ev(xed_encoder_request_t* p) {
    return p->u.ev;
}

static XED_INLINE void xed_encoder_request_vars_remove(xed_encoder_request_t* p) {
    p->u.ev = 0; // clear the internal data so no one sees it.
}

static XED_INLINE void xed_encoder_request_vars_zero(xed_encoder_request_t* p) {
    xed_encoder_vars_t* q = xed_encoder_request_ev(p);
    if (q) {
       q->_ilen = 0;
       q->_olen = 0;    
       q->_bit_offset = 0;
       memset(&(q->_iforms),0,sizeof(xed_encoder_iforms_t));
    }
}

static XED_INLINE void xed_encoder_request_set_encoder_vars(xed_encoder_request_t* p,
                                                            xed_encoder_vars_t* xev) {
    p->u.ev = xev;
    xed_encoder_request_vars_zero(p);
}

static XED_INLINE xed_uint16_t
xed_encoder_request_get_iform_index(const xed_encoder_request_t* p) {
    return xed_encoder_request_ev_const(p)->_iform_index;
}

static XED_INLINE void
xed_encoder_request_set_iform_index(xed_encoder_request_t* p, 
                                  xed_uint16_t iform_index) {
    xed_encoder_request_ev(p)->_iform_index = iform_index;
}

                                                           
static XED_INLINE xed_encoder_iforms_t* xed_encoder_request_iforms(xed_encoder_request_t* p) {
    return &(xed_encoder_request_ev(p)->_iforms);
}

static XED_INLINE xed_uint32_t xed_encoder_request_ilen(const xed_encoder_request_t* p) {
    return xed_encoder_request_ev_const(p)->_ilen;
}

static XED_INLINE xed_uint32_t xed_encoder_request_olen(const xed_encoder_request_t* p) {
    return xed_encoder_request_ev_const(p)->_olen;
}
static XED_INLINE xed_uint32_t xed_encoder_request_bit_offset(const xed_encoder_request_t* p) {
    return xed_encoder_request_ev_const(p)->_bit_offset;
}


static XED_INLINE void xed_encoder_request_set_ilen(xed_encoder_request_t* p, xed_uint32_t ilen) {
    xed_encoder_request_ev(p)->_ilen= ilen;
}
static XED_INLINE void xed_encoder_request_set_olen(xed_encoder_request_t* p, xed_uint32_t olen) {
    xed_encoder_request_ev(p)->_olen=olen;
}
static XED_INLINE void
xed_encoder_request_set_bit_offset( xed_encoder_request_t* p, xed_uint32_t bit_offset) {
    xed_encoder_request_ev(p)->_bit_offset = bit_offset;
}
static XED_INLINE void
xed_encoder_request_update_bit_offset( xed_encoder_request_t* p, xed_uint32_t bit_offset_delta) {
    xed_encoder_request_ev(p)->_bit_offset += bit_offset_delta;
}

static XED_INLINE const xed_encoder_iform_t*
xed_encoder_get_encoder_iform(const xed_encoder_request_t* r){
    xed_uint16_t iform_index = xed_encoder_request_get_iform_index(r);
    // KW false positive. Correct by construction.
    return xed_encode_iform_db + iform_index;
}


void
xed_encoder_request_emit_bytes(xed_encoder_request_t* q,
                               const xed_uint8_t bits,
                               const xed_uint64_t value);
void
xed_encoder_request_encode_emit(xed_encoder_request_t* q,
                                const unsigned int bits,
                                const xed_uint64_t value);
    
xed_bool_t
xed_encoder_request__memop_compatible(const xed_encoder_request_t* p,
                                      xed_operand_width_enum_t operand_width);


static XED_INLINE xed_ptrn_func_ptr_t
xed_encoder_get_fb_ptrn(const xed_encoder_request_t* p){
    const xed_encoder_iform_t* enc_iform =  xed_encoder_get_encoder_iform(p);
    return xed_encode_fb_lu_table[enc_iform->_fb_ptrn_index];
}

static XED_INLINE xed_ptrn_func_ptr_t
xed_encoder_get_emit_ptrn(const xed_encoder_request_t* p){
    const xed_encoder_iform_t* enc_iform =  xed_encoder_get_encoder_iform(p);
    return xed_encode_emit_lu_table[enc_iform->_emit_ptrn_index];
}

static XED_INLINE xed_uint8_t
xed_encoder_get_nominal_opcode(const xed_encoder_request_t* p){
    const xed_encoder_iform_t* enc_iform =  xed_encoder_get_encoder_iform(p);
    return enc_iform->_nom_opcode;
}


static XED_INLINE xed_uint16_t
xed_encoder_get_fb_values_index(const xed_encoder_request_t* p){
    const xed_encoder_iform_t* enc_iform =  xed_encoder_get_encoder_iform(p);
    return enc_iform->_fb_values_index;
}

        
static XED_INLINE const xed_uint8_t*
xed_encoder_get_start_field_value(const xed_encoder_request_t* p){
    xed_uint16_t base_index = xed_encoder_get_fb_values_index(p);    
    return xed_encode_fb_values_table + base_index;
}


static XED_INLINE xed_encode_function_pointer_t
xed_encoder_get_group_encoding_function(xed_iclass_enum_t iclass){
    xed_uint16_t indx = xed_enc_iclass2group[iclass];
    return xed_encode_groups[indx];
}

static XED_INLINE xed_uint8_t
xed_encoder_get_iclasses_index_in_group(const xed_encoder_request_t* p){
    xed_iclass_enum_t iclass = xed_encoder_request_get_iclass(p);
    return xed_enc_iclass2index_in_group[iclass];
}


#endif
