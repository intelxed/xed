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
/// @file xed-immdis.h
/// 



#ifndef XED_IMMDIS_H
# define XED_IMMDIS_H

#include "xed-types.h"
#include "xed-common-defs.h"
#include "xed-util.h"


////////////////////////////////////////////////////////////////////////////
// DEFINES
////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////
// TYPES
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
// PROTOTYPES
////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////
// GLOBALS
////////////////////////////////////////////////////////////////////////////

#define XED_MAX_IMMDIS_BYTES 8

// A union for speed of zeroing
union xed_immdis_values_t
{
    xed_uint8_t x[XED_MAX_IMMDIS_BYTES];// STORED LITTLE ENDIAN. BYTE 0 is LSB
    xed_uint64_t q;
};

/// Stores immediates and displacements for the encoder & decoder.
typedef struct xed_immdis_s {
    union xed_immdis_values_t value;
    unsigned int currently_used_space :4; // current number of assigned bytes
    unsigned int max_allocated_space :4; // max allocation, 4 or 8
    xed_bool_t present : 1;
    xed_bool_t immediate_is_unsigned : 1;
} xed_immdis_t;




XED_DLL_EXPORT void xed_immdis_init(xed_immdis_t* p, int max_bytes);

/// @name Sizes and lengths
//@{
/// return the number of bytes added
XED_DLL_EXPORT unsigned int xed_immdis_get_bytes(const xed_immdis_t* p) ;

//@}

/// @name Accessors for the value of the immediate or displacement
//@{
XED_DLL_EXPORT xed_int64_t 
xed_immdis_get_signed64(const xed_immdis_t* p);

XED_DLL_EXPORT xed_uint64_t 
xed_immdis_get_unsigned64(const xed_immdis_t* p);

XED_DLL_EXPORT xed_bool_t
xed_immdis_is_zero(const xed_immdis_t* p) ;

XED_DLL_EXPORT xed_bool_t
xed_immdis_is_one(const xed_immdis_t* p) ;

/// Access the i'th byte of the immediate
XED_DLL_EXPORT xed_uint8_t   xed_immdis_get_byte(const xed_immdis_t* p, unsigned int i) ;
//@}

/// @name Presence / absence of an immediate or displacement
//@{
XED_DLL_EXPORT void    xed_immdis_set_present(xed_immdis_t* p) ;

/// True if the object has had a value or individual bytes added to it.
XED_DLL_EXPORT xed_bool_t    xed_immdis_is_present(const xed_immdis_t* p) ;
//@}


/// @name Initialization and setup
//@{
XED_DLL_EXPORT void     xed_immdis_set_max_len(xed_immdis_t* p, unsigned int mx) ;
XED_DLL_EXPORT void
xed_immdis_zero(xed_immdis_t* p);

XED_DLL_EXPORT unsigned int    xed_immdis_get_max_length(const xed_immdis_t* p) ;

//@}

/// @name Signed vs Unsigned
//@{ 
/// Return true if  signed.
XED_DLL_EXPORT xed_bool_t
xed_immdis_is_unsigned(const xed_immdis_t* p) ;
/// Return true if signed.
XED_DLL_EXPORT xed_bool_t
xed_immdis_is_signed(const xed_immdis_t* p) ;
    
/// Set the immediate to be signed; For decoder use only.
XED_DLL_EXPORT void 
xed_immdis_set_signed(xed_immdis_t* p) ;
/// Set the immediate to be unsigned; For decoder use only.
XED_DLL_EXPORT void 
xed_immdis_set_unsigned( xed_immdis_t* p) ;
//@}


/// @name Adding / setting values
//@{
XED_DLL_EXPORT void
xed_immdis_add_byte(xed_immdis_t* p, xed_uint8_t b);


XED_DLL_EXPORT void
xed_immdis_add_byte_array(xed_immdis_t* p, int nb, xed_uint8_t* ba);

/// Add 1, 2, 4 or 8 bytes depending on the value x and the mask of
/// legal_widths. The default value of legal_widths = 0x5 only stops
/// adding bytes only on 1 or 4 byte quantities - depending on which
/// bytes of x are zero -- as is used for most memory addressing.  You
/// can set legal_widths to 0x7 for branches (1, 2 or 4 byte branch
/// displacements). Or if you have an 8B displacement, you can set
/// legal_widths to 0x8. NOTE: add_shortest_width will add up to
/// XED_MAX_IMMDIS_BYTES if the x value requires it. NOTE: 16b memory
/// addressing can have 16b immediates.
XED_DLL_EXPORT void
xed_immdis_add_shortest_width_signed(xed_immdis_t* p, xed_int64_t x, xed_uint8_t legal_widths);

/// See add_shortest_width_signed()
XED_DLL_EXPORT void
xed_immdis_add_shortest_width_unsigned(xed_immdis_t* p, xed_uint64_t x, xed_uint8_t legal_widths );


/// add an 8 bit value to the byte array
XED_DLL_EXPORT void
xed_immdis_add8(xed_immdis_t* p, xed_int8_t d);

/// add a 16 bit value to the byte array
XED_DLL_EXPORT void
xed_immdis_add16(xed_immdis_t* p, xed_int16_t d);

/// add a 32 bit value to the byte array
XED_DLL_EXPORT void
xed_immdis_add32(xed_immdis_t* p, xed_int32_t d);

/// add a 64 bit value to the byte array.
XED_DLL_EXPORT void
xed_immdis_add64(xed_immdis_t* p, xed_int64_t d);

//@}


/// @name printing / debugging
//@{

/// just print the raw bytes in hex with a leading 0x
XED_DLL_EXPORT int xed_immdis_print(const xed_immdis_t* p, char* buf, int buflen);

/// Print the value as a signed or unsigned number depending on the
/// value of the immediate_is_unsigned variable.
XED_DLL_EXPORT int
xed_immdis_print_signed_or_unsigned(const xed_immdis_t* p, char* buf, int buflen);

/// print the signed value, appropriate width, with a leading 0x
XED_DLL_EXPORT int
xed_immdis_print_value_signed(const xed_immdis_t* p, char* buf, int buflen);

/// print the unsigned value, appropriate width, with a leading 0x
XED_DLL_EXPORT int
xed_immdis_print_value_unsigned(const xed_immdis_t* p, char* buf, int buflen);

#endif

//@}


