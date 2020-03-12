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


#ifndef XED_ENCODE_DIRECT_H
# define XED_ENCODE_DIRECT_H
#include "xed-common-hdrs.h"
#include "xed-portability.h"
#include "xed-types.h"
#include "xed-error-enum.h"
#include <stdarg.h>
#include <string.h>

/// This structure is filled in by the various XED ENC2 functions. It
/// should not be directly manipulated by user code.
/// @ingroup ENC2
typedef struct {
    xed_uint8_t* itext;  // supplied by user during init
    xed_uint32_t cursor; // where we write next byte

    xed_uint32_t has_sib:1;
    xed_uint32_t has_disp8:1;
    xed_uint32_t has_disp16:1;
    xed_uint32_t has_disp32:1;

    xed_uint32_t rexw:1; // and vex, evex
    xed_uint32_t rexr:1; // and vex, evex
    xed_uint32_t rexx:1; // and vex, evex
    xed_uint32_t rexb:1; // and vex, evex

    xed_uint32_t need_rex:1;  // for SIL,DIL,BPL,SPL
    xed_uint32_t evexrr:1;
    xed_uint32_t vexl:1;
    xed_uint32_t evexb:1;  // also sae enabler for reg-only & vl=512
    
    xed_uint32_t evexvv:1;
    xed_uint32_t evexz:1;
    xed_uint32_t evexll:2; // also rc bits in some case
    
    xed_uint32_t mod:2;
    xed_uint32_t reg:3;
    xed_uint32_t rm:3;
    xed_uint32_t sibscale:2;
    xed_uint32_t sibindex:3;
    xed_uint32_t sibbase:3;
    xed_uint32_t evexaaa:3;
    xed_uint32_t map:3;
    xed_uint32_t vexpp:3; // and evex
    xed_uint32_t vvvv:4;
    xed_uint32_t opcode_srm:3; /// for "partial opcode" instructions
    
    xed_uint8_t imm8_reg; // for _SE imm8-specified registers.

} xed_enc2_req_payload_t;


/// A wrapper for #xed_enc2_req_payload_t .
/// @ingroup ENC2
typedef union {
    xed_enc2_req_payload_t s;
} xed_enc2_req_t;

/// Zero out a #xed_enc2_req_t structure and set the output pointer.
/// Required before calling and any ENC2 encoding function.
/// @ingroup ENC2
static XED_INLINE void xed_enc2_req_t_init(xed_enc2_req_t* r, xed_uint8_t* output_buffer) {
    memset(r, 0, sizeof(xed_enc2_req_t));
    r->s.itext = output_buffer;
}

/// Returns the number of bytes that were used for the encoding.
/// @ingroup ENC2
static XED_INLINE xed_uint32_t xed_enc2_encoded_length(xed_enc2_req_t* r) {
    return r->s.cursor;
}


/// Emit a legacy segment prefix byte in to the specified request's output buffer.
/// @ingroup ENC2
XED_DLL_EXPORT void xed_emit_seg_prefix(xed_enc2_req_t* r,
                                        xed_reg_enum_t reg);


typedef void (xed_user_abort_handler_t)(const char* format, va_list args);

/// Set a function taking a variable-number-of-arguments (stdarg) to handle
/// the errors and die.  The argument are like printf with a format string
/// followed by a varaible number of arguments.
/// @ingroup ENC2
XED_DLL_EXPORT void xed_enc2_set_error_handler(xed_user_abort_handler_t* fn);

/// The error handler routine. This function is called by encoder functions
/// upon detecting argument errors. It fist attempts to call the
/// user-registered handler (configured by #xed_enc2_set_error_handler() ),
/// or if no user handler is set, then this function calls printf() and
/// then abort(). If the user handler returns, abort() is still called.
/// @ingroup ENC2
XED_DLL_EXPORT void xed_enc2_error(const char* fmt, ...);

#endif
