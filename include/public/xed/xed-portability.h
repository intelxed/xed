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
/// @file xed-portability.h
/// 

#ifndef XED_PORTABILITY_H
# define XED_PORTABILITY_H
# include "xed-common-hdrs.h"
# include "xed-types.h"


#define XED_STATIC_CAST(x,y) ((x) (y))
#define XED_REINTERPRET_CAST(x,y) ((x) (y))
#define XED_CAST(x,y) ((x) (y))


    
XED_DLL_EXPORT xed_uint_t xed_strlen(const char* s);
XED_DLL_EXPORT void xed_strcat(char* dst, const char* src);
XED_DLL_EXPORT void xed_strcpy(char* dst, const char* src);

/// returns the number of bytes remaining for the next use of
/// #xed_strncpy() or #xed_strncat() .
XED_DLL_EXPORT int xed_strncpy(char* dst, const char* src,  int len);

/// returns the number of bytes remaining for the next use of
/// #xed_strncpy() or #xed_strncat() .
XED_DLL_EXPORT int xed_strncat(char* dst, const char* src,  int len);

#if defined(__INTEL_COMPILER)
# if defined(_WIN32) && defined(_MSC_VER)
#   if _MSC_VER >= 1400
#     define XED_MSVC8_OR_LATER 1
#   endif
# endif
#endif

/* recognize VC98 */
#if !defined(__INTEL_COMPILER)
# if defined(_WIN32) && defined(_MSC_VER)
#   if _MSC_VER == 1200
#     define XED_MSVC6 1
#   endif
# endif
# if defined(_WIN32) && defined(_MSC_VER)
#   if _MSC_VER == 1310
#     define XED_MSVC7 1
#   endif
# endif
# if defined(_WIN32) && defined(_MSC_VER)
#   if _MSC_VER >= 1400
#     define XED_MSVC8_OR_LATER 1
#   endif
#   if _MSC_VER == 1400
#     define XED_MSVC8 1
#   endif
#   if _MSC_VER == 1500
#     define XED_MSVC9 1
#   endif
#   if _MSC_VER >= 1500
#     define XED_MSVC9_OR_LATER 1
#   endif
#   if _MSC_VER == 1600
#     define XED_MSVC10 1
#   endif
#   if _MSC_VER >= 1600
#     define XED_MSVC10_OR_LATER 1
#   endif
# endif
#endif

/* I've had compatibility problems here so I'm using a trivial indirection */
#if defined(__GNUC__)
#  if defined(__CYGWIN__)
      /* cygwin's gcc 3.4.4 on windows  complains */
#    define XED_FMT_X "%lx"
#    define XED_FMT_08X "%08lx"
#    define XED_FMT_D "%ld"
#    define XED_FMT_U "%lu"
#    define XED_FMT_9U "%9lu"
#  else
#    define XED_FMT_X "%x"
#    define XED_FMT_08X "%08x"
#    define XED_FMT_D "%d"
#    define XED_FMT_U "%u"
#    define XED_FMT_9U "%9u"
#  endif
#else
#  define XED_FMT_X "%x"
#  define XED_FMT_08X "%08x"
#  define XED_FMT_D "%d"
#  define XED_FMT_U "%u"
#  define XED_FMT_9U "%9u"
#endif

// Go write portable code... Sigh
#if defined(__APPLE__)  // clang *32b* and 64b
# define XED_FMT_SIZET "%lu"
#elif defined(__LP64__)  // 64b gcc, icc
# define XED_FMT_SIZET "%lu"
#elif defined (_M_X64)   // 64b msvs, ICL
  // MSVS/x64 accepts %llu or %lu, icl/x64 does not)
# define XED_FMT_SIZET "%llu"
#else  // 32b everything else
# define XED_FMT_SIZET "%u"
#endif

#if defined(__GNUC__) && defined(__LP64__) && !defined(__APPLE__)
# define XED_FMT_LX "%lx"
# define XED_FMT_LX_UPPER "%lX"
# define XED_FMT_LU "%lu"
# define XED_FMT_LU12 "%12lu"
# define XED_FMT_LD "%ld"
# define XED_FMT_LX16 "%016lx"
# define XED_FMT_LX16_UPPER "%016lX"
#else
# define XED_FMT_LX "%llx"
# define XED_FMT_LX_UPPER "%llX"
# define XED_FMT_LU "%llu"
# define XED_FMT_LU12 "%12llu"
# define XED_FMT_LD "%lld"
# define XED_FMT_LX16 "%016llx"
# define XED_FMT_LX16_UPPER "%016llX"
#endif

#if defined(__LP64__) || defined (_M_X64) 
# define XED_64B 1
#endif

#if defined(_M_IA64)
# define XED_IPF
# define XED_FMT_SIZET "%lu"
#endif

#if defined(__GNUC__)    
     /* gcc4.2.x has a bug with c99/gnu99 inlining */
#  if __GNUC__ == 4 && __GNUC_MINOR__ == 2
#    define XED_INLINE inline
#  else
#    if __GNUC__ == 2
#       define XED_INLINE 
#    else 
#       define XED_INLINE inline
#    endif
# endif
# define XED_NORETURN __attribute__ ((noreturn))
# if __GNUC__ == 2
#   define XED_NOINLINE 
# else
#   define XED_NOINLINE __attribute__ ((noinline))
# endif
#else
# define XED_INLINE __inline
# if defined(XED_MSVC6)
#   define XED_NOINLINE 
# else
#   define XED_NOINLINE __declspec(noinline)
# endif
# define XED_NORETURN __declspec(noreturn)
#endif



#define XED_MAX(a, b) (((a) > (b)) ? (a):(b))
#define XED_MIN(a, b) (((a) < (b)) ? (a):(b))




#endif  // XED_PORTABILITY_H

