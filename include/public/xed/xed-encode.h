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
/// @file xed-encode.h


#ifndef XED_ENCODE_H
# define XED_ENCODE_H
#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-error-enum.h"
#include "xed-operand-values-interface.h"
#include "xed-operand-width-enum.h"
#include "xed-encoder-iforms.h" //generated
#include "xed-encoder-gen-defs.h" //generated

// we now (mostly) share the decode data structure
#include "xed-decoded-inst.h" 


// establish a type equivalence for the xed_encoder_request_t and the
// corresponding xed_decoded_inst_t.

/// @ingroup ENC
typedef struct  xed_decoded_inst_s xed_encoder_request_s; 
/// @ingroup ENC
typedef xed_decoded_inst_t xed_encoder_request_t; 



/// @ingroup ENC
XED_DLL_EXPORT xed_iclass_enum_t 
xed_encoder_request_get_iclass( const xed_encoder_request_t* p);

/////////////////////////////////////////////////////////
// set functions

/// @ingroup ENC
XED_DLL_EXPORT void  
xed_encoder_request_set_iclass( xed_encoder_request_t* p, 
                                xed_iclass_enum_t iclass);

/// @name Prefixes
//@{
/// @ingroup ENC
/// for  REPNE(F2) prefix on string ops
XED_DLL_EXPORT void xed_encoder_request_set_repne(xed_encoder_request_t* p);
/// @ingroup ENC
/// for REP(F3) prefix on string ops
XED_DLL_EXPORT void xed_encoder_request_set_rep(xed_encoder_request_t* p);
/// @ingroup ENC
/// clear the REP prefix indicator
XED_DLL_EXPORT void xed_encoder_request_clear_rep(xed_encoder_request_t* p);
//@}

/// @name Primary Encode Functions
//@{
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_effective_operand_width( xed_encoder_request_t* p, 
                                                 xed_uint_t width_bits);
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_effective_address_size( xed_encoder_request_t* p, 
                                                xed_uint_t width_bits);
/*! @ingroup ENC
 *
 * Set the operands array element indexed by operand to the actual register
 * name reg.
 *
 * @param[in] p            xed_encoder_request_t
 * @param[in] operand      indicates which register operand storage field to use
 * @param[in] reg          the actual register represented (EAX, etc.)  to store.
 */
XED_DLL_EXPORT void xed_encoder_request_set_reg(xed_encoder_request_t* p,
                                                xed_operand_enum_t operand, 
                                                xed_reg_enum_t reg);
//@}

/// @name Operand Order
//@{
/*! @ingroup ENC
 * Specify the name as the n'th operand in the operand order. 
 *
 * The complication of this function is that the register operand names are
 * specific to the position of the operand (REG0, REG1, REG2...). One can
 * use this function for registers or one can use the
 * xed_encoder_request_set_operand_name_reg() which takes integers instead
 * of operand names.
 *
 * @param[in] p                #xed_encoder_request_t
 * @param[in] operand_index    xed_uint_t representing n'th operand position
 * @param[in] name             #xed_operand_enum_t operand name.
 */
XED_DLL_EXPORT void
xed_encoder_request_set_operand_order(xed_encoder_request_t* p, 
                                      xed_uint_t operand_index, 
                                      xed_operand_enum_t name);

/*! @ingroup ENC
 * Retrieve the name of the n'th operand in the operand order. 
 *
 * @param[in] p                #xed_encoder_request_t
 * @param[in] operand_index    xed_uint_t representing n'th operand position
 * @return The #xed_operand_enum_t operand name.
 */
XED_DLL_EXPORT xed_operand_enum_t
xed_encoder_request_get_operand_order(xed_encoder_request_t* p, 
                                      xed_uint_t operand_index);
                                                                        

/// @ingroup ENC
/// Retrieve the number of entries in the encoder operand order array
/// @return The number of entries in the encoder operand order array
static XED_INLINE xed_uint_t
xed_encoder_request_operand_order_entries(xed_encoder_request_t* p)
{
    return  p->_n_operand_order;
}

//@}


/// @name branches and far pointers
//@{
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_relbr(xed_encoder_request_t* p);
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_branch_displacement(xed_encoder_request_t* p,
                                            xed_int32_t brdisp,
                                            xed_uint_t nbytes);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_ptr(xed_encoder_request_t* p);
//@}


/// @name Immediates
//@{
/// @ingroup ENC
/// Set the uimm0 using a BYTE  width.
XED_DLL_EXPORT void xed_encoder_request_set_uimm0(xed_encoder_request_t* p,
                                                  xed_uint64_t uimm,
                                                  xed_uint_t nbytes);
/// @ingroup ENC
/// Set the uimm0 using a BIT  width.
XED_DLL_EXPORT void xed_encoder_request_set_uimm0_bits(xed_encoder_request_t* p,
                                                       xed_uint64_t uimm,
                                                       xed_uint_t nbits);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_uimm1(xed_encoder_request_t* p,
                                                  xed_uint8_t uimm);
/// @ingroup ENC
/// same storage as uimm0
XED_DLL_EXPORT void xed_encoder_request_set_simm(xed_encoder_request_t* p,
                                                 xed_int32_t simm,
                                                 xed_uint_t nbytes);

/// @name Memory
//@{
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_memory_displacement(xed_encoder_request_t* p,
                                            xed_int64_t memdisp,
                                            xed_uint_t nbytes);

/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_agen(xed_encoder_request_t* p);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_mem0(xed_encoder_request_t* p);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_mem1(xed_encoder_request_t* p);
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_memory_operand_length(xed_encoder_request_t* p,
                                              xed_uint_t nbytes);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_seg0(xed_encoder_request_t* p,
                                  xed_reg_enum_t seg_reg);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_seg1(xed_encoder_request_t* p,
                                  xed_reg_enum_t seg_reg);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_base0(xed_encoder_request_t* p,
                                   xed_reg_enum_t base_reg);
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_base1(xed_encoder_request_t* p,
                                   xed_reg_enum_t base_reg) ;
/// @ingroup ENC
XED_DLL_EXPORT void xed_encoder_request_set_index(xed_encoder_request_t* p,
                                   xed_reg_enum_t index_reg);
/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_set_scale(xed_encoder_request_t* p,
                              xed_uint_t scale);
//@}

//////////////////////////////////////////////
/// @ingroup ENC
XED_DLL_EXPORT const xed_operand_values_t*
xed_encoder_request_operands_const(const xed_encoder_request_t* p);
/// @ingroup ENC
XED_DLL_EXPORT xed_operand_values_t*
xed_encoder_request_operands(xed_encoder_request_t* p);

/// @name Initialization
//@{
/*! @ingroup ENC
 * clear the operand order array
 * @param[in] p                xed_encoder_request_t
 */
XED_DLL_EXPORT void
xed_encoder_request_zero_operand_order(xed_encoder_request_t* p);

/// @ingroup ENC
XED_DLL_EXPORT void
xed_encoder_request_zero_set_mode(xed_encoder_request_t* p,
                                  const xed_state_t* dstate);
/// @ingroup ENC
XED_DLL_EXPORT void  xed_encoder_request_zero(xed_encoder_request_t* p) ;
//@}

struct xed_decoded_inst_s; //fwd decl
/// @ingroup ENC
/// Converts an decoder request to a valid encoder request.
XED_DLL_EXPORT void
xed_encoder_request_init_from_decode(struct xed_decoded_inst_s* d);

/// @name String Printing
//@{
/// @ingroup ENC        
XED_DLL_EXPORT void xed_encode_request_print(const xed_encoder_request_t* p, 
                                             char* buf, xed_uint_t buflen);
//@}




/// @name Encoding
//@{
///   This is the main interface to the encoder. The array should be
///   at most 15 bytes long. The ilen parameter should indicate
///   this length. If the array is too short, the encoder may fail to
///   encode the request.  Failure is indicated by a return value of
///   type #xed_error_enum_t that is not equal to
///   #XED_ERROR_NONE. Otherwise, #XED_ERROR_NONE is returned and the
///   length of the encoded instruction is returned in olen.
///
/// @param r encoder request description (#xed_encoder_request_t), includes mode info
/// @param array the encoded instruction bytes are stored here
/// @param ilen the input length of array.
/// @param olen the actual  length of array used for encoding
/// @return success/failure as a #xed_error_enum_t
/// @ingroup ENC
XED_DLL_EXPORT xed_error_enum_t
xed_encode(xed_encoder_request_t* r,
           xed_uint8_t* array, 
           const unsigned int ilen,
           unsigned int* olen);

/// This function will attempt to encode a NOP of exactly ilen
/// bytes. If such a NOP is not encodeable, then false will be returned.
///
/// @param array the encoded instruction bytes are stored here
/// @param  ilen the input length array.
/// @return success/failure as a #xed_error_enum_t
/// @ingroup ENC
XED_DLL_EXPORT xed_error_enum_t
xed_encode_nop(xed_uint8_t* array, 
               const unsigned int ilen);
//@}

#endif
