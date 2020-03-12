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
/// @file xed-disas.h
/// 

#if !defined(XED_DISAS_H)
# define XED_DISAS_H

#include "xed-types.h"

/// @ingroup PRINT
/// A #xed_disassembly_callback_fn_t takes an address, a pointer to a
/// symbol buffer of buffer_length bytes, and a pointer to an offset. The
/// function fills in the symbol_buffer and sets the offset to the desired
/// offset for that symbol.  If the function succeeds, it returns 1. 
//  The call back should return 0 if the buffer is not long enough to
//  include the null termination.If no symbolic information is
//  located, the function returns zero.
///  @param address The input address for which we want symbolic name and offset
///  @param symbol_buffer A buffer to hold the symbol name. The callback function should fill this in and terminate
///                       with a null byte.
///  @param buffer_length The maximum length of the symbol_buffer including then null
///  @param offset A pointer to a xed_uint64_t to hold the offset from the provided symbol.
///  @param context This void* pointer passed to the disassembler's new interface so that the caller can identify 
///                     the proper context against which to resolve the symbols. 
///                     The disassembler passes this value to
///                     the callback. The legacy formatters 
///                     that do not have context will pass zero for this parameter.
///  @return 0 on failure, 1 on success.
typedef  int (*xed_disassembly_callback_fn_t)(
    xed_uint64_t  address,
    char*         symbol_buffer,
    xed_uint32_t  buffer_length,
    xed_uint64_t* offset,
    void*         context);

#endif
