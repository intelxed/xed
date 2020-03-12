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
/// @file xed-agen.h 
/// 


#ifndef XED_AGEN_H
# define XED_AGEN_H
#include "xed-decoded-inst.h"
#include "xed-error-enum.h"


/// A function for obtaining register values. 32b return values should be
/// zero extended to 64b. The error value is set to nonzero if the callback
/// experiences some sort of problem.  @ingroup AGEN
typedef xed_uint64_t (*xed_register_callback_fn_t)(xed_reg_enum_t reg,
                                                   void* context,
                                                   xed_bool_t* error);

/// A function for obtaining the segment base values. 32b return values
/// should be zero extended zero extended to 64b. The error value is set to
/// nonzero if the callback experiences some sort of problem. 
/// @ingroup AGEN
typedef xed_uint64_t (*xed_segment_base_callback_fn_t)(xed_reg_enum_t reg,
                                                       void* context,
                                                       xed_bool_t* error);


/// Initialize the callback functions. Tell XED what to call when using
/// #xed_agen. 
/// @ingroup AGEN
XED_DLL_EXPORT void xed_agen_register_callback(xed_register_callback_fn_t register_fn,
                                               xed_segment_base_callback_fn_t segment_fn);

/// Using the registered callbacks, compute the memory address for a
/// specified memop in a decoded instruction. memop_index can have the
/// value 0 for XED_OPERAND_MEM0, XED_OPERAND_AGEN, or 1 for
/// XED_OPERAND_MEM1. Any other value results in an error being
/// returned. The context parameter which is passed to the registered
/// callbacks can be used to identify which thread's state is being
/// referenced. The context parameter can also be used to specify which
/// element of a vector register should be returned for gather an scatter
/// operations.
/// @ingroup AGEN
XED_DLL_EXPORT xed_error_enum_t xed_agen(xed_decoded_inst_t* xedd,
                                         unsigned int memop_index,
                                         void* context,
                                         xed_uint64_t* out_address);


#endif
