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
/// @file xed-encode-types.H
/// 


#if !defined(XED_ENCODE_TYPES_H)
# define XED_ENCODE_TYPES_H

#include "xed-types.h"
#include "xed-encode.h"

// Type signature for an encode function
typedef xed_uint_t (*xed_encode_function_pointer_t)(xed_encoder_request_t* enc_req);
typedef xed_bool_t (*xed_nt_func_ptr_t)(xed_encoder_request_t*);
typedef xed_bool_t (*xed_ntluf_func_ptr_t)(xed_encoder_request_t*, xed_reg_enum_t);
typedef void (*xed_ptrn_func_ptr_t)(xed_encoder_request_t*);

typedef struct xed_encoder_iform_s{
    //index of the field binding function in xed_encode_fb_lu_table
    xed_uint8_t _fb_ptrn_index;
    
    //index of the emit function in xed_encode_emit_lu_table
    xed_uint8_t _emit_ptrn_index;
    
    xed_uint8_t _nom_opcode;
    xed_uint8_t _legacy_map;
    
    //start index of the field values in xed_encode_fb_values_table
    xed_int16_t _fb_values_index;    
} xed_encoder_iform_t;

typedef struct xed_encoder_vars_s {
    /// _iforms is a dynamically generated structure containing the values of
    /// various encoding decisions
    xed_encoder_iforms_t _iforms;
       
    // the index of the iform in the xed_encode_iform_db table
    xed_uint16_t _iform_index;
    
    /// Encode output array size, specified by caller of xed_encode()
    xed_uint32_t _ilen;

    /// Used portion of the encode output array
    xed_uint32_t _olen;

    xed_uint32_t _bit_offset;
} xed_encoder_vars_t;


#endif
