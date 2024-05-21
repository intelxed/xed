/* BEGIN_LEGAL 

Copyright (c) 2024 Intel Corporation

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



#ifndef XED_UTIL_H
# define XED_UTIL_H

#include "xed-common-hdrs.h"
#include "xed-types.h"
#include "xed-portability.h"



extern int xed_verbose;
#if defined(XED_MESSAGES)
# include <stdio.h> 
extern  FILE* xed_log_file;
# define XED_EMIT_MESSAGES  (xed_verbose >= 1)
# define XED_INFO_VERBOSE   (xed_verbose >= 2)
# define XED_INFO2_VERBOSE  (xed_verbose >= 3)
# define XED_VERBOSE        (xed_verbose >= 4)
# define XED_MORE_VERBOSE   (xed_verbose >= 5)
# define XED_VERY_VERBOSE   (xed_verbose >= 6)
#else
# define XED_EMIT_MESSAGES  (0)
# define XED_INFO_VERBOSE   (0)
# define XED_INFO2_VERBOSE  (0)
# define XED_VERBOSE        (0)
# define XED_MORE_VERBOSE   (0)
# define XED_VERY_VERBOSE   (0)
#endif

#if defined(__GNUC__)
# define XED_FUNCNAME __func__
#else
# define XED_FUNCNAME ""
#endif

#if defined(XED_MESSAGES)
#define XED2IMSG(x)                                             \
    do {                                                        \
        if (XED_EMIT_MESSAGES) {                                \
            if (XED_VERY_VERBOSE) {                             \
                fprintf(xed_log_file,"%s:%d:%s: ",              \
                        __FILE__, __LINE__, XED_FUNCNAME);      \
            }                                                   \
            fprintf x;                                          \
            fflush(xed_log_file);                               \
        }                                                       \
    } while(0)

#define XED2TMSG(x)                                             \
    do {                                                        \
        if (XED_VERBOSE) {                                      \
            if (XED_VERY_VERBOSE) {                             \
                fprintf(xed_log_file,"%s:%d:%s: ",              \
                        __FILE__, __LINE__, XED_FUNCNAME);      \
            }                                                   \
            fprintf x;                                          \
            fflush(xed_log_file);                               \
        }                                                       \
    } while(0)

#define XED2VMSG(x)                                             \
    do {                                                        \
        if (XED_VERY_VERBOSE) {                                 \
            fprintf(xed_log_file,"%s:%d:%s: ",                  \
                    __FILE__, __LINE__, XED_FUNCNAME);          \
            fprintf x;                                          \
            fflush(xed_log_file);                               \
        }                                                       \
    } while(0)

// Example usage:
//     XED2DIE((xed_log_file,"%s\n", msg));

#define XED2DIE(x)                                              \
    do {                                                        \
        if (XED_EMIT_MESSAGES) {                                \
            fprintf(xed_log_file,"%s:%d:%s: ",                  \
                             __FILE__, __LINE__, XED_FUNCNAME); \
            fprintf x;                                          \
            fflush(xed_log_file);                               \
        }                                                       \
        xed_assert(0);                                          \
    } while(0)



#else
# define XED2IMSG(x) 
# define XED2TMSG(x)
# define XED2VMSG(x)
# define XED2DIE(x) do { xed_assert(0); } while(0)
#endif

#if defined(XED_ASSERTS)
#  define xed_assert(x)  do { if (( x )== 0) xed_internal_assert( #x, __FILE__, __LINE__); } while(0) 
#else
#  define xed_assert(x)  do {  } while(0) 
#endif
XED_NORETURN XED_NOINLINE XED_DLL_EXPORT void xed_internal_assert(const char* s, const char* file, int line);

typedef void (*xed_user_abort_function_t)(const char* msg,
                                          const char* file,
                                          int line,
                                          void* other);

/// @ingroup INIT
/// This is for registering a function to be called during XED's assert
/// processing. If you do not register an abort function, then the system's
/// abort function will be called. If your supplied function returns, then
/// abort() will still be called.
///
/// @param fn This is a function pointer for a function that should handle the
///        assertion reporting. The function pointer points to  a function that
///        takes 4 arguments: 
///                     (1) msg, the assertion message, 
///                     (2) file, the file name,
///                     (3) line, the line number (as an integer), and
///                     (4) other, a void pointer that is supplied as thei
///                         2nd argument to this registration.
/// @param other This is a void* that is passed back to your supplied function  fn
///        as its 4th argument. It can be zero if you don't need this
///        feature. You can used this to convey whatever additional context
///        to your assertion handler (like FILE* pointers etc.).
///
XED_DLL_EXPORT void xed_register_abort_function(xed_user_abort_function_t fn,
                                                void* other);


XED_DLL_EXPORT int xed_itoa(char* buf,
                            xed_uint64_t f,
                            int buflen);

/**
 * Convert the input value `f` into its binary representation as a string and store it in `buf`.
 * @param buf Pointer to the character array where the binary representation will be stored.
 * @param f Input value to be converted.
 * @param bits_to_print Number of bits to print (limited to 64 bits).
 * @param buflen Length of the `buf` array.
 * @return The number of characters actually copied (excluding the null terminator).
 */
XED_DLL_EXPORT int xed_itoa_bin(char *buf,
                                xed_uint64_t f,
                                xed_uint_t bits_to_print,
                                xed_uint_t buflen);

/// defaults to lowercase
XED_DLL_EXPORT int xed_itoa_hex_zeros(char* buf,
                                      xed_uint64_t f,
                                      xed_uint_t bits_to_print,
                                      xed_bool_t leading_zeros,
                                      int buflen);

/// defaults to lowercase
XED_DLL_EXPORT int xed_itoa_hex(char* buf,
                                xed_uint64_t f,
                                xed_uint_t bits_to_print,
                                int buflen);

XED_DLL_EXPORT int xed_itoa_hex_ul(char* buf, 
                                   xed_uint64_t f, 
                                   xed_uint_t bits_to_print,
                                   xed_bool_t leading_zeros,                            
                                   int buflen,
                                   xed_bool_t lowercase);


/// Set the FILE* for XED's log msgs. This takes a FILE* as a void* because
/// some software defines their own FILE* types creating conflicts.
XED_DLL_EXPORT void xed_set_log_file(void* o);


/// Set the verbosity level for XED
XED_DLL_EXPORT void xed_set_verbosity(int v);

XED_DLL_EXPORT xed_int64_t xed_sign_extend32_64(xed_int32_t x);
XED_DLL_EXPORT xed_int64_t xed_sign_extend16_64(xed_int16_t x);
XED_DLL_EXPORT xed_int64_t xed_sign_extend8_64(xed_int8_t x);

XED_DLL_EXPORT xed_int32_t xed_sign_extend16_32(xed_int16_t x);
XED_DLL_EXPORT xed_int32_t xed_sign_extend8_32(xed_int8_t x);

XED_DLL_EXPORT xed_int16_t xed_sign_extend8_16(xed_int8_t x);

///arbitrary sign extension from a qty of "bits" length to 32b 
XED_DLL_EXPORT xed_int32_t xed_sign_extend_arbitrary_to_32(xed_uint32_t x, unsigned int bits);

///arbitrary sign extension from a qty of "bits" length to 64b 
XED_DLL_EXPORT xed_int64_t xed_sign_extend_arbitrary_to_64(xed_uint64_t x, unsigned int bits);


XED_DLL_EXPORT xed_uint64_t xed_zero_extend32_64(xed_uint32_t x);
XED_DLL_EXPORT xed_uint64_t xed_zero_extend16_64(xed_uint16_t x);
XED_DLL_EXPORT xed_uint64_t xed_zero_extend8_64(xed_uint8_t x);

XED_DLL_EXPORT xed_uint32_t xed_zero_extend16_32(xed_uint16_t x);
XED_DLL_EXPORT xed_uint32_t xed_zero_extend8_32(xed_uint8_t x);

XED_DLL_EXPORT xed_uint16_t xed_zero_extend8_16(xed_uint8_t x);

#if defined(XED_LITTLE_ENDIAN_SWAPPING)
XED_DLL_EXPORT xed_int32_t 
xed_little_endian_to_int32(xed_uint64_t x, unsigned int len);

XED_DLL_EXPORT xed_int64_t 
xed_little_endian_to_int64(xed_uint64_t x, unsigned int len);
XED_DLL_EXPORT xed_uint64_t 
xed_little_endian_to_uint64(xed_uint64_t x, unsigned int len);

XED_DLL_EXPORT xed_int64_t 
xed_little_endian_hilo_to_int64(xed_uint32_t hi_le, xed_uint32_t lo_le, unsigned int len);
XED_DLL_EXPORT xed_uint64_t 
xed_little_endian_hilo_to_uint64(xed_uint32_t hi_le, xed_uint32_t lo_le, unsigned int len);
#endif

XED_DLL_EXPORT xed_uint8_t
xed_get_byte(xed_uint64_t x, unsigned int i, unsigned int len);

static XED_INLINE xed_uint64_t xed_make_uint64(xed_uint32_t hi, xed_uint32_t lo) {
    xed_union64_t y;
    y.s.lo32= lo;
    y.s.hi32= hi;
    return y.u64;
}
static XED_INLINE xed_int64_t xed_make_int64(xed_uint32_t hi, xed_uint32_t lo) {
    xed_union64_t y;
    y.s.lo32= lo;
    y.s.hi32= hi;
    return y.i64;
}

/// returns the number of bytes required to store the UNSIGNED number x
/// given a mask of legal lengths. For the legal_widths argument, bit 0
/// implies 1 byte is a legal return width, bit 1 implies that 2 bytes is a
/// legal return width, bit 2 implies that 4 bytes is a legal return width.
/// This returns 8 (indicating 8B) if none of the provided legal widths
/// applies.
XED_DLL_EXPORT xed_uint_t xed_shortest_width_unsigned(xed_uint64_t x, xed_uint8_t legal_widths);

/// returns the number of bytes required to store the SIGNED number x
/// given a mask of legal lengths. For the legal_widths argument, bit 0 implies 1
/// byte is a legal return width, bit 1 implies that 2 bytes is a legal
/// return width, bit 2 implies that 4 bytes is a legal return width.  This
/// returns 8 (indicating 8B) if none of the provided legal widths applies.
XED_DLL_EXPORT xed_uint_t xed_shortest_width_signed(xed_int64_t x, xed_uint8_t legal_widths);

#endif
