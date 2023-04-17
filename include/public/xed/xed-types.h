/* BEGIN_LEGAL 

Copyright (c) 2022 Intel Corporation

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
/// @file xed-types.h
/// 


#ifndef XED_TYPES_H
# define XED_TYPES_H

////////////////////////////////////////////////////////////////////////////

#include "xed-common-hdrs.h"

#if defined(__GNUC__) || defined(__ICC) || defined(__clang__)
#  include <stdint.h>
#  define xed_uint8_t   uint8_t 
#  define xed_uint16_t  uint16_t
#  define xed_uint32_t  uint32_t
#  define xed_uint64_t  uint64_t
#  define xed_int8_t     int8_t 
#  define xed_int16_t 	 int16_t
#  define xed_int32_t    int32_t
#  define xed_int64_t    int64_t
#elif defined(_WIN32)
#  define xed_uint8_t  unsigned __int8
#  define xed_uint16_t unsigned __int16
#  define xed_uint32_t unsigned __int32
#  define xed_uint64_t unsigned __int64
#  define xed_int8_t   __int8
#  define xed_int16_t  __int16
#  define xed_int32_t  __int32
#  define xed_int64_t  __int64
#else
#  error "XED types unsupported platform? Need windows, gcc, or icc."
#endif

typedef unsigned int  xed_uint_t;
typedef          int  xed_int_t;
typedef unsigned int  xed_bits_t;
typedef unsigned int  xed_bool_t;

#if defined(__LP64__)  || defined (_M_X64)
typedef xed_uint64_t xed_addr_t;
#else
typedef xed_uint32_t xed_addr_t;
#endif


typedef union {
   xed_uint8_t   byte[2]; 
   xed_int8_t  s_byte[2]; 

  struct {
    xed_uint8_t b0; /*low 8 bits*/
    xed_uint8_t b1; /*high 8 bits*/
  } b;
  xed_int16_t  i16;
  xed_uint16_t u16;
} xed_union16_t ;

typedef union {
   xed_uint8_t   byte[4]; 
   xed_uint16_t  word[2]; 
   xed_int8_t  s_byte[4]; 
   xed_int16_t s_word[2]; 

  struct {
    xed_uint8_t b0; /*low 8 bits*/
    xed_uint8_t b1; 
    xed_uint8_t b2; 
    xed_uint8_t b3; /*high 8 bits*/
  } b;

  struct {
    xed_uint16_t w0; /*low 16 bits*/
    xed_uint16_t w1; /*high 16 bits*/
  } w;
  xed_int32_t  i32;
  xed_uint32_t u32;
} xed_union32_t ;

typedef union {
   xed_uint8_t      byte[8]; 
   xed_uint16_t     word[4]; 
   xed_uint32_t    dword[2]; 
   xed_int8_t     s_byte[8]; 
   xed_int16_t    s_word[4]; 
   xed_int32_t   s_dword[2]; 

  struct {
    xed_uint8_t b0; /*low 8 bits*/
    xed_uint8_t b1; 
    xed_uint8_t b2; 
    xed_uint8_t b3; 
    xed_uint8_t b4; 
    xed_uint8_t b5; 
    xed_uint8_t b6; 
    xed_uint8_t b7; /*high 8 bits*/
  } b;

  struct {
    xed_uint16_t w0; /*low 16 bits*/
    xed_uint16_t w1;
    xed_uint16_t w2;
    xed_uint16_t w3; /*high 16 bits*/
  } w;
  struct {
    xed_uint32_t lo32;
    xed_uint32_t hi32;
  } s;
    xed_uint64_t u64;
    xed_int64_t i64;
} xed_union64_t ;

////////////////////////////////////////////////////////////////////////////
#endif
