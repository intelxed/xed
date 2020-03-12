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

/// @file xed-ild.h
/// instruction length decoder
    
#if !defined(XED_ILD_H)
# define XED_ILD_H
#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-types.h"
#include "xed-decoded-inst.h"

#include "xed-operand-accessors.h"


/// This function just does instruction length decoding.
/// It does not return a fully decoded instruction.
///  @param xedd  the decoded instruction of type #xed_decoded_inst_t .
///               Mode/state sent in via xedd; See the #xed_state_t .
///  @param itext the pointer to the array of instruction text bytes
///  @param bytes the length of the itext input array.
///              1 to 15 bytes, anything more is ignored.
/// @return #xed_error_enum_t indicating success (#XED_ERROR_NONE) or
///       failure.
/// Only two failure codes are valid for this function:
///  #XED_ERROR_BUFFER_TOO_SHORT and #XED_ERROR_GENERAL_ERROR.
/// In general this function cannot tell if the instruction is valid or
/// not. For valid instructions, XED can figure out if enough bytes were
/// provided to decode the instruction. If not enough were provided,
/// XED returns #XED_ERROR_BUFFER_TOO_SHORT. 
/// From this function, the #XED_ERROR_GENERAL_ERROR is an indication
/// that XED could not decode the instruction's length because  the
/// instruction was so invalid that even its length
/// may across implmentations.
///
/// @ingroup DEC
XED_DLL_EXPORT xed_error_enum_t 
xed_ild_decode(xed_decoded_inst_t* xedd, 
               const xed_uint8_t* itext, 
               const unsigned int bytes);


#endif

