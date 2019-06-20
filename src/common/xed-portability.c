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
/// @file xed-portability.cpp
/// 



////////////////////////////////////////////////////////////////////////////
#include "xed-portability.h"
#include "xed-util.h"
#include <string.h> // strcat, strncat, strlen
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



#if 0 /* not used */
void xed_strcat(char* dst, const char* src) {
#if defined(_WIN32) && !defined(__GNUC__) 
# if defined(XED_MSVC6) || defined(XED_MSVC7) || defined(XED_IPF) || defined(PIN_CRT)
    strcat(dst, src);
# else
    // total hack to avoid warnings. Assuming people don't overflow their
    // input buffers. FIXME
    strcat_s(dst,xed_strlen(dst)+xed_strlen(src)+1, src);
# endif
#else
    strcat(dst,src);
#endif
}
#endif

int xed_strncat(char* dst, const char* src, int len) {
    int dst_len  = XED_STATIC_CAST(int,xed_strlen(dst));
    int orig_max = dst_len + len;
    int new_length =  dst_len + XED_STATIC_CAST(int,xed_strlen(src)) + 1; /* with null */
    if (len <= 0)
        return 0;
    /* if our source string with our dest string overflows the buffer, then
     * stop adding stuff to the buffer. The null is included in the
     * estimate of the new string length. */
    if (new_length > orig_max) 
        return 0; 
    // len is the maximum number of bytes to copy.
#if defined(_WIN32) && !defined(__GNUC__)
# if defined(XED_MSVC6) || defined(XED_MSVC7) || defined(XED_IPF) || defined(PIN_CRT)
    strncat(dst, src, len);
# else
    // MS wants the total length of the dst buffer and not the number of
    // bytes to copy.
    strcat_s(dst, xed_strlen(dst)+len, src);
# endif
#else
    strncat(dst,src,len);
#endif
    return orig_max - XED_STATIC_CAST(int,xed_strlen(dst));
}

xed_uint_t xed_strlen(const char* s) {
    return XED_STATIC_CAST(xed_uint_t,strlen(s));
}

void xed_strcpy(char* dst, const char* src) {
    const char* psrc = src;
    char* pdst = dst;
    while(*psrc)  
        *pdst++ = *psrc++;
    *pdst = 0;
}
int xed_strncpy(char* dst, const char* src,  int len) {
    int orig_max = len;
    const char* psrc = src;
    char* pdst = dst;
    int i=0;
    if (len <= 0)
        return 0;
    for(;*psrc && i<len;i++)
        *pdst++ = *psrc++;
    if (i<len)
        *pdst = 0;
    return orig_max - XED_STATIC_CAST(int,xed_strlen(dst));
}




