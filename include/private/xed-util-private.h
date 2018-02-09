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
/// @file xed-util.h 
/// 



#ifndef XED_UTIL_PRIVATE_H
# define XED_UTIL_PRIVATE_H

#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-portability.h"
#include "xed-util.h"
  
/* copy from src to dst, downcasing bytes as the copy proceeds. len is the
 * available space in the buffer*/
int xed_strncat_lower(char* dst, const char* src, int len);

int xed_itoa_signed(char* buf, xed_int64_t f, int buflen);

char xed_to_ascii_hex_nibble(xed_uint_t x, xed_bool_t lowercase);

int xed_sprintf_uint8_hex(char* buf, xed_uint8_t x, int buflen);
int xed_sprintf_uint16_hex(char* buf, xed_uint16_t x, int buflen);
int xed_sprintf_uint32_hex(char* buf, xed_uint32_t x, int buflen);
int xed_sprintf_uint64_hex(char* buf, xed_uint64_t x, int buflen);
int xed_sprintf_uint8(char* buf, xed_uint8_t x, int buflen);
int xed_sprintf_uint16(char* buf, xed_uint16_t x, int buflen);
int xed_sprintf_uint32(char* buf, xed_uint32_t x, int buflen);
int xed_sprintf_uint64(char* buf, xed_uint64_t x, int buflen);
int xed_sprintf_int8(char* buf, xed_int8_t x, int buflen);
int xed_sprintf_int16(char* buf, xed_int16_t x, int buflen);
int xed_sprintf_int32(char* buf, xed_int32_t x, int buflen);
int xed_sprintf_int64(char* buf, xed_int64_t x, int buflen);

void xed_derror(const char* s);
void xed_dwarn(const char* s);


#endif
