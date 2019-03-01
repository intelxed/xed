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
/// @file xed-util.c
/// 


////////////////////////////////////////////////////////////////////////////

#include "xed-types.h"
#include "xed-util.h"
#include "xed-util-private.h"
#include "xed-portability.h"
#include "xed-portability-private.h"
#include "xed-common-defs.h"
#include "xed-common-hdrs.h"

#if defined(__linux__) && defined(__STDC_HOSTED__) && __STDC_HOSTED__ == 0
   extern void abort (void)  __attribute__ ((__noreturn__));
#else
#  include <stdlib.h>
#endif

#include <ctype.h>


////////////////////////////////////////////////////////////////////////////
int xed_verbose   = 2;

#include <stdio.h> //required for fprintf,stderr in xed_abort()
#if defined(XED_MESSAGES)
FILE* xed_log_file;
#endif

////////////////////////////////////////////////////////////////////////////
void xed_set_verbosity(int v) {
    xed_verbose = v;
}

void  xed_set_log_file(void* o) {
#if defined(XED_MESSAGES)
    xed_log_file = (FILE*)o;
#else
    (void)o;
#endif

}





#if !defined(XED_64B)
static XED_INLINE xed_uint64_t get_bit63(xed_uint64_t x) {
    const xed_uint64_t s = 63;
    return (x >> s) & 1;
}

static XED_INLINE  xed_uint64_t xed_divide_by_10_64by32(xed_uint64_t numerator) {
    /* ONLY WORKS FOR DIVIDE BY 10 because 2*9+1=19 and that is < 20, so I can use subtract */
    int i=0;
    const xed_uint32_t denominator = 10;
    xed_uint64_t tn=numerator;
    xed_uint64_t tqlo=0;
    xed_uint32_t ir=0,b=0;
    xed_uint32_t num=0;
    xed_uint32_t qbit=0;

    /* binary long division */
    for(i=0;i<64;i++) {
        b = get_bit63(tn);          // next bit of the numerator
        num = (ir << 1) | b;        // intermediate remainder from last step + new numerator bit 
        if (num >= denominator) { 
            ir  = num - denominator;         
            qbit = 1;
        }
        else {
            ir = num; 
            qbit = 0;
        }
        tqlo = (tqlo <<1) | qbit;                 
        tn   = tn << 1;
    }

    // ignore quotient overflow;
    return tqlo;
}
#endif

int xed_itoa(char* buf, xed_uint64_t f, int buflen) {
    char tbuf[100];
    char* p = tbuf;
    char* fp;
    xed_uint64_t t = f;
    xed_uint64_t x,v;

    if (f == 0) {
        *p++ = '0';
        *p  = 0;
        return xed_strncpy(buf,tbuf,buflen);
    }

    while(t)    {
#if defined(XED_64B)
        x = t / 10;
#else
        x = xed_divide_by_10_64by32(t);
#endif
        v = t - (x*10);
        *p++ = XED_STATIC_CAST(char, '0' + v);
        t = x;
    }
    /* reverse string */
    *p=0;
    p--;
    fp = tbuf;
    while(fp < p) {
        char ec = *p;
        char fc = *fp;
        *fp = ec;
        *p  = fc;
        fp++;
        p--;
    }

    return xed_strncpy(buf,tbuf,buflen);
}

static int add_leading_zeros(char* buf,
                             char* tbuf,
                             int buflen,
                             xed_uint_t bits_to_print)
{
    char* p = buf;
    xed_uint_t ilen = xed_strlen(tbuf);
    if (ilen < bits_to_print) {
        xed_uint_t i;
        xed_uint_t zeros = bits_to_print - ilen;
        for(i=0 ; i < zeros && buflen>0 ; i++) {
            buflen--;
            *p++ = '0';
        }
    }
    return xed_strncpy(p,tbuf,buflen);
}
        

int xed_itoa_hex_ul(char* buf, 
                    xed_uint64_t f, 
                    xed_uint_t bits_to_print,
                    xed_bool_t leading_zeros,                            
                    int buflen,
                    xed_bool_t lowercase)
{
    const xed_uint64_t one = 1;
    xed_uint_t nibbles_to_print = (bits_to_print+3)/4;
    xed_uint64_t mul,rdiv;
    xed_uint64_t n;
    char tbuf[100];
    char* p = tbuf;
    //  mask the value to the bits we care about. makes everything else easier.
    xed_uint64_t ff,t; 
    xed_uint_t div = 0;
    xed_uint64_t base_letter;

    if (bits_to_print == 64) // no masking required
        ff = f;
    else
        ff = f & ((one<<bits_to_print)-1);

    if (ff == 0) {
        *p++ = '0';
        *p  = 0;
        if (leading_zeros)
            return add_leading_zeros(buf,tbuf,buflen,bits_to_print);
        else 
            return xed_strncpy(buf,tbuf,buflen);
    }

    t = ff;
    while(t)    {
        t = t >> 4;
        div++;
    }

    n = ff;
    
    if (lowercase)
        base_letter = XED_STATIC_CAST(xed_uint64_t,'a');
    else
        base_letter = XED_STATIC_CAST(xed_uint64_t,'A');

    while(div > 0) {

        div--;
        rdiv = one<<(4*div);
        //mul =  xed_divide(n,rdiv);
        mul =  (n >> (4*div)) & 0xF;
        if (div <= nibbles_to_print) {
            if (mul<10)
                *p++ = XED_STATIC_CAST(char,mul + '0');
            else
                *p++ = XED_STATIC_CAST(char,mul - 10  + base_letter);
        }
        n = n - (mul*rdiv);
    }
        
    // tack on a null
    *p = 0;
    if (leading_zeros)
        return add_leading_zeros(buf,tbuf,buflen,bits_to_print);
    return xed_strncpy(buf,tbuf,buflen);
}

int xed_itoa_hex_zeros(char* buf, 
                       xed_uint64_t f, 
                       xed_uint_t bits_to_print, 
                       xed_bool_t leading_zeros, 
                       int buflen) {
    const xed_bool_t lowercase=1;
    return xed_itoa_hex_ul(buf,f,bits_to_print, leading_zeros, buflen, lowercase);
    (void) leading_zeros;
}

int xed_itoa_hex(char* buf, 
                 xed_uint64_t f, 
                 xed_uint_t bits_to_print, 
                 int buflen)
{
    const xed_bool_t lowercase = 1;
    const xed_bool_t leading_zeros = 0;
    return xed_itoa_hex_ul(buf, f, bits_to_print, leading_zeros, buflen, lowercase);
}

int xed_itoa_signed(char* buf, xed_int64_t f, int buflen) {
    xed_uint64_t x;
    int blen = buflen;
    if (f<0) {
        blen = xed_strncpy(buf,"-",blen);
        x = XED_STATIC_CAST(xed_uint64_t,-f);
    }
    else
        x = XED_STATIC_CAST(xed_uint64_t,f);
    return xed_itoa(buf+xed_strlen(buf), x, blen);
}

int xed_sprintf_uint8_hex(char* buf, xed_uint8_t x, int buflen) {
    return xed_itoa_hex(buf,x,8,buflen);
}
int xed_sprintf_uint16_hex(char* buf, xed_uint16_t x, int buflen) {
    return xed_itoa_hex(buf,x,16,buflen);
}
int xed_sprintf_uint32_hex(char* buf, xed_uint32_t x, int buflen) {
    return xed_itoa_hex(buf,x,32,buflen);
}
int xed_sprintf_uint64_hex(char* buf, xed_uint64_t x, int buflen) {
    return xed_itoa_hex(buf,x,64,buflen);
}
int xed_sprintf_uint8(char* buf, xed_uint8_t x, int buflen) {
    return xed_itoa(buf, x, buflen);
}
int xed_sprintf_uint16(char* buf, xed_uint16_t x, int buflen) {
    return xed_itoa(buf, x, buflen);
}
int xed_sprintf_uint32(char* buf, xed_uint32_t x, int buflen) {
    return xed_itoa(buf, x, buflen);
}
int xed_sprintf_uint64(char* buf, xed_uint64_t x, int buflen) {
    return xed_itoa(buf, x, buflen);
}
int xed_sprintf_int8(char* buf, xed_int8_t x, int buflen) {
    return xed_itoa_signed(buf,x,buflen);
}
int xed_sprintf_int16(char* buf, xed_int16_t x, int buflen) {
    return xed_itoa_signed(buf,x,buflen);
}
int xed_sprintf_int32(char* buf, xed_int32_t x, int buflen) {
    return xed_itoa_signed(buf,x,buflen);
}
int xed_sprintf_int64(char* buf, xed_int64_t x, int buflen) {
    return xed_itoa_signed(buf,x,buflen);
}

char xed_to_ascii_hex_nibble(xed_uint_t x, xed_bool_t lowercase) {
    if (x<=9)
        return XED_STATIC_CAST(char,x+'0');
    if (x<=15)  {
        if (lowercase)
            return XED_STATIC_CAST(char,x-10+'a');
        else
            return XED_STATIC_CAST(char,x-10+'A');
    }
    return '?';
}
static char xed_tolower(char c) {
    if (c >= 'A' && c <= 'Z')
        return c-'A'+'a';
    return c;
}


int xed_strncat_lower(char* dst, const char* src, int len) {
    xed_uint_t dst_len = xed_strlen(dst) ;
    xed_uint_t orig_max = dst_len + XED_STATIC_CAST(xed_uint_t,len);
    xed_uint_t i;
    xed_uint_t src_len = xed_strlen(src);
    xed_uint_t copy_max = src_len;
    xed_uint_t ulen = (xed_uint_t)len-1;
    if (len <= 0) 
        return 0;

    /* do not copy more bytes than fit in the buffer including the null */

    if (src_len > ulen)
        copy_max = ulen;
        
    for(i=0;i<copy_max;i++) 
        dst[dst_len+i]=xed_tolower(src[i]);

    dst[dst_len+copy_max]=0;
    // should never go negative
    return XED_STATIC_CAST(int,orig_max - xed_strlen(dst));
}



////////////////////////////////////////////////////////////////////////////

/* arbitrary sign extension from a qty of "bits" length to 64b */
xed_int64_t xed_sign_extend_arbitrary_to_64(xed_uint64_t x, unsigned int bits) {
    xed_uint64_t one = 1;
    xed_int64_t mask = one<<(bits-1);
    xed_int64_t vmask, o=0;
    if (bits < 64) {
        vmask = (one<<bits)-1;
        o = ((x&vmask) ^ mask)- mask;
    }
    else if (bits == 64) 
        o=x;
    else 
        xed_assert(0);
    return o;
}

/* arbitrary sign extension from a qty of "bits" length to 32b */
xed_int32_t xed_sign_extend_arbitrary_to_32(xed_uint32_t x, unsigned int bits) {
    xed_int32_t mask = 1<<(bits-1);
    xed_int32_t vmask, o=0;
    if (bits < 32) {
        vmask = (1<<bits)-1;
        o = ((x&vmask) ^ mask)- mask;
    }
    else if (bits == 32) 
        o=x;
    else 
        xed_assert(0);
    return o;
}


xed_int64_t xed_sign_extend32_64(xed_int32_t x) {
    return x;
}
xed_int64_t xed_sign_extend16_64(xed_int16_t x) {
    return x;
}
xed_int64_t xed_sign_extend8_64(xed_int8_t x) {
    return x;
}
xed_int32_t xed_sign_extend16_32(xed_int16_t x) {
    return x;
}
xed_int32_t xed_sign_extend8_32(xed_int8_t x) {
    return x;
}
xed_int16_t xed_sign_extend8_16(xed_int8_t x) {
    return x;
}


xed_uint64_t xed_zero_extend32_64(xed_uint32_t x) {
    return x;
}
xed_uint64_t xed_zero_extend16_64(xed_uint16_t x) {
    return x;
}
xed_uint64_t xed_zero_extend8_64(xed_uint8_t x) {
    return x;
}
xed_uint32_t xed_zero_extend16_32(xed_uint16_t x) {
    return x;
}
xed_uint32_t xed_zero_extend8_32(xed_uint8_t x) {
    return x;
}
xed_uint16_t xed_zero_extend8_16(xed_uint8_t x) {
    return x;
}

#if defined(XED_LITTLE_ENDIAN_SWAPPING)
static XED_INLINE xed_int64_t xed_sign_extend4_64(xed_int8_t x) {
    const xed_int64_t eight = 8;
    xed_int64_t o = (x ^ eight)- eight;
    return o;
}
static XED_INLINE xed_int32_t xed_sign_extend4_32(xed_int8_t x) {
    xed_int32_t o = (x ^ 0x00000008)- 0x00000008;
    return o;
}

xed_int64_t xed_little_endian_hilo_to_int64(xed_uint32_t hi_le, xed_uint32_t lo_le, unsigned int len) {
    switch(len)    {
      case 4:
        return xed_sign_extend4_64(XED_STATIC_CAST(xed_int8_t,lo_le&0xF));
      case 8:
        return xed_sign_extend8_64(XED_STATIC_CAST(xed_int8_t,lo_le));
      case 16:
        return xed_sign_extend16_64(xed_bswap16(XED_STATIC_CAST(xed_uint16_t,lo_le)));
      case 32: {
          xed_int32_t y = xed_bswap32(XED_STATIC_CAST(xed_uint32_t,lo_le));
          xed_int64_t z;
          //printf("BSWAPING %lx -> %x\n", x,y);
          z= xed_sign_extend32_64(y);
          //printf("SEXT -> %lx\n", z);
          return z;
      }
      case 64:   {
        xed_uint64_t z = xed_make_uint64(xed_bswap32(hi_le),xed_bswap32(lo_le));
        return XED_STATIC_CAST(xed_int64_t,z);
      }
      default:
        xed_assert(0);
        return 0;
    }
}
xed_uint64_t xed_little_endian_hilo_to_uint64(xed_uint32_t hi_le, xed_uint32_t lo_le, unsigned int len) {
    switch(len)     {
      case 4:
        return XED_STATIC_CAST(xed_uint8_t,lo_le&0xF);
      case 8:
        return XED_STATIC_CAST(xed_uint8_t,lo_le);
      case 16:
        return xed_bswap16(XED_STATIC_CAST(xed_uint16_t,lo_le));
      case 32:
        return xed_bswap32(XED_STATIC_CAST(xed_uint32_t,lo_le));
      case 64:
        return xed_make_uint64(xed_bswap32(hi_le),xed_bswap32(lo_le));
      default:
        xed_assert(0);
        return 0;
    }
}

xed_uint64_t  xed_little_endian_to_uint64(xed_uint64_t x, unsigned int len) {
    switch(len)     {
      case 4:
        return XED_STATIC_CAST(xed_uint8_t,x&0xF);
      case 8:
        return XED_STATIC_CAST(xed_uint8_t,x);
      case 16:
        return xed_bswap16(XED_STATIC_CAST(xed_uint16_t,x));
      case 32:
        return xed_bswap32(XED_STATIC_CAST(xed_uint32_t,x));
      case 64:
        return xed_bswap64(x);
      default:
        xed_assert(0);
        return 0;
    }
}

xed_int64_t xed_little_endian_to_int64(xed_uint64_t x, unsigned int len){
    switch(len)    {
      case 4:
        return xed_sign_extend4_64(XED_STATIC_CAST(xed_int8_t,x&0xF));
      case 8:
        return xed_sign_extend8_64(XED_STATIC_CAST(xed_int8_t,x));
      case 16:
        return xed_sign_extend16_64(xed_bswap16(XED_STATIC_CAST(xed_uint16_t,x)));
      case 32: {
          xed_int32_t y = xed_bswap32(XED_STATIC_CAST(xed_uint32_t,x));
          xed_int64_t z;
          //printf("BSWAPING %lx -> %x\n", x,y);
          z= xed_sign_extend32_64(y);
          //printf("SEXT -> %lx\n", z);
          return z;
      }
      case 64:
        return XED_STATIC_CAST(xed_int64_t,xed_bswap64(x));
      default:
        xed_assert(0);
        return 0;
    }
}

xed_int32_t xed_little_endian_to_int32(xed_uint64_t x, unsigned int len){
    // heavily reliant on the type system
    switch(len)    {
      case 4:
        return xed_sign_extend4_32(XED_STATIC_CAST(xed_int8_t,x&0xF));
      case 8:
        return xed_sign_extend8_32(XED_STATIC_CAST(xed_int8_t,x));
      case 16:
        return xed_sign_extend16_32(xed_bswap16(XED_STATIC_CAST(xed_uint16_t,x)));
      case 32: {
          xed_int32_t y = xed_bswap32(XED_STATIC_CAST(xed_uint32_t,x));
          return y;
      }
      default:
        xed_assert(0);
        return 0;
    }
}
#endif    
    
xed_uint8_t xed_get_byte(xed_uint64_t x, unsigned int i, unsigned int len) {
    // THIS IS THE "IN REGISTER" VIEW!
    // 1B      .. .. .. .. .. .. .. 00
    // 2B      .. .. .. .. .. .. 11 00
    // 4B      .. .. .. .. 33 22 11 00
    // 8B      77 66 55 44 33 22 11 00
    // (The least significant byte is  00)

    xed_assert (i < len);
    return XED_BYTE_CAST(x >> (i*8));
    (void)len; //pacify compiler
}



xed_uint_t
xed_shortest_width_signed(xed_int64_t x, xed_uint8_t legal_widths) {
    static const  xed_int64_t max1[] = { 0x7f, 0x7fff, 0x7fffffff };
    static const  xed_int64_t min1[] = {
        -128,
        // supposedly the negative 64b values w/leading F digit is machine
        // dependent. So we use a leading minus sign to cause the compiler
        // to do 2s complement and install the desired values.
        -0x8000LL,       // == 0xffffffffffff8000LL
        -0x80000000LL    // == 0xffffffff80000000LL
    };
    /*historical note: I experimented with different ways of computing the
     * constants without making memory references, by shifting, etc. The
     * thing is that any way I coded it, Gcc's optimizer unrolled the loop,
     * removed the shifts or memops and did the right thing!  I was
     * astounded.  This version of the code was the simplest to maintain
     * and understand so I'm sticking with it.
     */
    unsigned int i,j;
    for(i=0;i<3;i++)  
    {
        j = 1 << i;
        if ((j & legal_widths)==j) 
            if (x <= max1[i] && x >= min1[i])
                break;
    }
    /* returns 1,2,4 or 8 */
    return 1<<i;
}

xed_uint_t
xed_shortest_width_unsigned(xed_uint64_t x, xed_uint8_t legal_widths) {

    unsigned int i,j;
    const xed_uint64_t one = 1;
    for(i=0;i<3; i++)
    {
        j = 1 << i;
        if ((j & legal_widths)==j)
            if (x < (one<<(j*8)))
                break;
    }
    /* returns 1,2,4 or 8 */
    return 1<<i;
}



void xed_derror(const char* s) {
    XED2DIE((xed_log_file,"%s\n", s));
    (void)s; // needed for when msgs are disabled and compiler warnings  are errors
}

//////////////////////////////////////////

static xed_user_abort_function_t xed_user_abort_function = 0;


static void* xed_user_abort_other = 0;

void xed_register_abort_function(xed_user_abort_function_t fn,
                                 void* other) {
    xed_user_abort_function = fn;
    xed_user_abort_other = other;
}

void xed_internal_assert( const char* msg, const char* file, int line) {
    if (xed_user_abort_function) {
      (*xed_user_abort_function)(msg, file, line, xed_user_abort_other);
    }
    else {
      fprintf(stderr,"ASSERTION FAILURE %s at %s:%d\n", msg, file, line);
    }
    abort();
}


