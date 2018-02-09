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
/// @file xed-decoded-inst.h
/// 

#if !defined(XED_DECODER_STATE_H)
# define XED_DECODER_STATE_H
#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-util.h"
#include "xed-types.h"
#include "xed-inst.h"
#include "xed-flags.h"
#if defined(XED_ENCODER)
# include "xed-encoder-gen-defs.h" //generated
#endif
#include "xed-chip-enum.h" //generated
#include "xed-operand-element-type-enum.h" // a generated file
#include "xed-operand-storage.h" // a generated file


struct xed_encoder_vars_s;
struct xed_decoder_vars_s;
/// @ingroup DEC
/// The main container for instructions. After decode, it holds an array of
/// operands with derived information from decode and also valid
/// #xed_inst_t pointer which describes the operand templates and the
/// operand order.  See @ref DEC for API documentation.
typedef struct xed_decoded_inst_s  {
    /// The _operands are storage for information discovered during
    /// decoding. They are also used by encode.  The accessors for these
    /// operands all have the form xed3_operand_{get,set}_*(). They should
    /// be considered internal and subject to change over time. It is
    /// preferred that you use xed_decoded_inst_*() or the
    /// xed_operand_values_*() functions when available.
    xed_operand_storage_t _operands;

#if defined(XED_ENCODER)
    /// Used for encode operand ordering. Not set by decode.
    xed_uint8_t _operand_order[XED_ENCODE_ORDER_MAX_OPERANDS];
    /// Length of the _operand_order[] array.
    xed_uint8_t _n_operand_order; 
#endif
    xed_uint8_t _decoded_length;

    /// when we decode an instruction, we set the _inst and get the
    /// properites of that instruction here. This also points to the
    /// operands template array.
    const xed_inst_t* _inst;

    // decoder does not change it, encoder does    
    union {
        xed_uint8_t* _enc;
        const xed_uint8_t* _dec;
    } _byte_array; 

    // The ev field is stack allocated by xed_encode(). It is per-encode
    // transitory data.
    union {
        /* user_data is available as a user data storage field after
         * decoding. It does not live across re-encodes or re-decodes. */
        xed_uint64_t user_data; 
#if defined(XED_ENCODER)
        struct xed_encoder_vars_s* ev;
#endif
    } u;
    
} xed_decoded_inst_t;

typedef xed_decoded_inst_t xed_operand_values_t;


#endif

