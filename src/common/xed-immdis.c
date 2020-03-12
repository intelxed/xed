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
/// @file xed-immdis.c
/// 



#include "xed-immdis.h"
#include "xed-util-private.h"
#include "xed-portability.h"

static int xed_immdis__print_ptr(const xed_immdis_t* p, char* buf, int buflen) {
    xed_uint_t i;
    char tbuf[100];
    char* x = tbuf;
    int blen = buflen;
    const xed_bool_t lowercase=1;
    blen =  xed_strncpy(buf,"PTR:",blen);
    // Note: no 0x needed because this is private and called in the context
    // where a leading 0x is provided.
    for( i=0; i< p->currently_used_space; i++ ) {
        *x++ = xed_to_ascii_hex_nibble(p->value.x[i]>>4, lowercase);
        *x++ = xed_to_ascii_hex_nibble(p->value.x[i]&0xF, lowercase);
    }
    *x = 0;
    blen = xed_strncat(buf, tbuf, blen);
    return blen;
}

static void xed_immdis__check(xed_immdis_t* q, xed_uint_t p)    {
    xed_assert(q->currently_used_space == 0);
    q->present = 1;
    q->currently_used_space  = p;
    xed_assert(q->currently_used_space <= q->max_allocated_space);
}


void xed_immdis_init(xed_immdis_t* p, xed_uint_t max_bytes) {
    xed_assert(max_bytes == 4 || max_bytes == 8);
    p->currently_used_space=0;
    p->max_allocated_space=max_bytes;
    p->present=0;
    p->immediate_is_unsigned=0; 
    p->value.q = 0;
}

/// return the number of bytes added
unsigned int xed_immdis_get_bytes(const xed_immdis_t* p) {
    return p->currently_used_space;
}



xed_bool_t
xed_immdis_is_zero(const xed_immdis_t* p) 
{
    //FIXME: could just check value.q if willing to rely on initialization
    xed_uint_t i;
    for(i=0; i < p->currently_used_space; i++)
    {
        if (p->value.x[i] != 0)
        {
            return 0; // not zero
        }
    }
    return 1;// is zero
}

xed_bool_t
xed_immdis_is_one(const xed_immdis_t* p) 
{
    if (p->value.x[0] == 1)
    {
        xed_uint_t i;
        for( i=1; i < p->currently_used_space; i++)
        {
            if (p->value.x[i] != 0)
            {
                return 0; // not one
            }
        }
        return 1; // a 1 and the rest, if any, are zeros
    }
    return 0; // not one
}

/// Access the i'th byte of the immediate
xed_uint8_t  xed_immdis_get_byte(const xed_immdis_t* p, unsigned int i)  {
    xed_assert(i < p->currently_used_space);
    return p->value.x[i];
}

/// @name Presence / absence of an immediate or displacement

void    xed_immdis_set_present(xed_immdis_t* p) 
{
    p->present = 1;
}
/// 1 if the object has had a value or individual bytes added to it.
xed_bool_t    xed_immdis_is_present(const xed_immdis_t* p)  {
    return p->present;
}


/// @name Initialization and setup

void     xed_immdis_set_max_len(xed_immdis_t* p, unsigned int mx) 
{
    xed_assert(mx <= XED_MAX_IMMDIS_BYTES);
    p->max_allocated_space = mx;
}
void
xed_immdis_zero(xed_immdis_t* p)
{
    p->present = 0;
    p->immediate_is_unsigned = 0;
    p->currently_used_space = 0;
#if defined(XED_SQUEAKY_CLEAN)
    p->value.q = 0;
#endif
}

unsigned int    xed_immdis_get_max_length(const xed_immdis_t* p)  {
    return p->max_allocated_space;
}


/// Return 1 if  signed.
xed_bool_t
xed_immdis_is_unsigned(const xed_immdis_t* p)  {
    return p->immediate_is_unsigned;
}
/// Return 1 if signed.
xed_bool_t
xed_immdis_is_signed(const xed_immdis_t* p)  {
    return !p->immediate_is_unsigned;
}
    
/// Set the immediate to be signed; For decoder use only.
void 
xed_immdis_set_signed(xed_immdis_t* p) {
    p->immediate_is_unsigned = 0;
}
/// Set the immediate to be unsigned; For decoder use only.
void 
xed_immdis_set_unsigned( xed_immdis_t* p) {
    p->immediate_is_unsigned = 1;
}


/// add an 8 bit value to the byte array
void
xed_immdis_add8(xed_immdis_t* p, xed_int8_t d)
{
    xed_immdis__check(p,1);
    p->value.x[0] = XED_BYTE_CAST(d);
}

/// add a 16 bit value to the byte array
void
xed_immdis_add16(xed_immdis_t* p, xed_int16_t d)
{
    xed_immdis__check(p,2);
    p->value.x[0] = XED_BYTE_CAST(d);
    p->value.x[1] = XED_BYTE_CAST(d>>8);
}

/// add a 32 bit value to the byte array
void
xed_immdis_add32(xed_immdis_t* p, xed_int32_t d)
{
    xed_immdis__check(p,4);
    p->value.x[0] = XED_BYTE_CAST(d);
    p->value.x[1] = XED_BYTE_CAST(d>>8);
    p->value.x[2] = XED_BYTE_CAST(d>>16);
    p->value.x[3] = XED_BYTE_CAST(d>>24);
}

/// add a 64 bit value to the byte array.
void
xed_immdis_add64(xed_immdis_t* p, xed_int64_t d)
{
    int i;
    xed_immdis__check(p,8);
    for(i = 0; i < 8 ;i++) {
        p->value.x[i] = XED_BYTE_CAST( d>>(8*i) );
    }
}



xed_uint64_t 
xed_immdis_get_unsigned64(const xed_immdis_t* p) 
{
    // Variable-width little endian storage.
    // If it were fixed width, I could just cast.
    xed_uint64_t v = 0;
    xed_uint64_t mul = 1;
    xed_uint_t i;
    for (  i=0 ; i< p->currently_used_space ; i++ )  
    {
        v = v + xed_immdis_get_byte(p,i) * mul;
        mul = mul * 256;
    }
    return v;
}

xed_int64_t 
xed_immdis_get_signed64(const xed_immdis_t* p) 
{
    // Variable-width little endian storage.
    // If it were fixed width, I could just cast.
    xed_uint64_t v = 0;
    xed_uint64_t mul = 1;
    xed_uint_t i;
    for (  i=0 ; i< p->currently_used_space ; i++ ) {
        v = v + xed_immdis_get_byte(p,i) * mul;
        mul = mul * 256;
    }
        
    if ( p->currently_used_space>0) {
        // sign extend 
        if ((xed_immdis_get_byte(p,p->currently_used_space-1) & 0x80) == 0x80) {
            const xed_uint64_t sext = 0xff;
            xed_uint_t j;
            for (  j = p->currently_used_space ; j < p->max_allocated_space ; j++ ) {
                v = v + sext * mul;
                mul = mul * 256;
            }
        }
    }

    //xed_int64_t r = xed_int64_t(v);
    return XED_STATIC_CAST(xed_int64_t,v);
}
    
void
xed_immdis_add_shortest_width_unsigned(xed_immdis_t* q, xed_uint64_t x, xed_uint8_t legal_widths)
{
    xed_uint64_t p = x;
    int i;
    XED2VMSG((xed_log_file, 
              "adding bytes from " XED_FMT_LX " using legal_widths %d\n",
              x, (int)legal_widths));
    for(i=0;i<XED_MAX_IMMDIS_BYTES; i++)  {
        xed_uint8_t b;
        if (p == 0 && i > 0) 
            if ( i == 1 || i == 2 || i == 4 )
                if ((i & legal_widths) == i) 
                    break;

        b = XED_BYTE_CAST(p);
        xed_immdis_add_byte(q,b);
        p  = p >> 8;
    }
    XED2VMSG((xed_log_file, "Stopped on byte %d\n",i));
}

void
xed_immdis_add_shortest_width_signed(xed_immdis_t* q, xed_int64_t x, xed_uint8_t legal_widths)
{
    xed_int64_t p = x;
    int i;
    int last_bit_high  = 0;

  
    XED2VMSG((xed_log_file, "adding bytes from " XED_FMT_LX " using legal_widths %d\n",
              x, (int)legal_widths));
    // Intestesting test cases:
    //   ff7777  Needs to know if the last iterations upper bit was 1.
    //   008888  Needs to know if the last iterations upper bit was 0.
    for(i=0;i<XED_MAX_IMMDIS_BYTES; i++) {
        xed_uint8_t b;
        XED2VMSG((xed_log_file, "i=%d p=" XED_FMT_LX " last_bit_high=%d\n", i,p,last_bit_high));
        if ( ( (p ==  0 && !last_bit_high) || 
               (p == -1 &&  last_bit_high)  ) 
            && i > 0)
        {
            if ( i == 1 || i == 2 || i == 4 ) {
                if ((i & legal_widths) == i)
                    break;
            }
        }

        b = XED_BYTE_CAST(p);
        XED2VMSG((xed_log_file,  "adding byte %x\n",(int)b));

        xed_immdis_add_byte(q,b);
        last_bit_high = (b >> 7) & 0x1;
        p  = p >> 8;
    }
    XED2VMSG((xed_log_file, "Stopped on byte %d\n",i));
}


int xed_immdis_print(const xed_immdis_t* p, char* buf, int buflen) {
    xed_uint_t i;
    int blen = buflen;
    char tbuf[100];
    char* x=tbuf;
    xed_bool_t uppercase=0;
    blen = xed_strncpy(buf,"0x",blen);
    for( i=0; i< p->currently_used_space; i++ ) {
        *x++ = xed_to_ascii_hex_nibble(p->value.x[i]>>4, uppercase);
        *x++ = xed_to_ascii_hex_nibble(p->value.x[i], uppercase);
    }
    *x = 0;
    blen = xed_strncat(buf,tbuf,blen);
    return blen;
}

int xed_immdis_print_signed_or_unsigned(const xed_immdis_t* p, char* buf, int buflen) {
    if (p->immediate_is_unsigned)
        return xed_immdis_print_value_unsigned(p,buf,buflen);
    else
        return xed_immdis_print_value_signed(p,buf,buflen);
}

static int xed_immdis_print_helper(xed_uint64_t d64, xed_uint_t len, char* buf, int buflen) {
    char tbuf[100];
    char ubuf[100];
    char* x=ubuf;
    xed_uint_t tlen;
    int i,plen;
    xed_bool_t leading_zeros = 1;
    int blen = buflen;
    blen = xed_strncpy(buf,"0x",blen);
    (void)xed_itoa_hex_zeros(tbuf, d64, len*8 , leading_zeros,100);
    tlen = xed_strlen(tbuf);
    plen = len - tlen; // how much to pad
    if (plen>0) {
        for(i=0;i<plen;i++)
            *x++='0';
        *x=0;
        blen = xed_strncat(buf,ubuf, blen);
    }
    blen = xed_strncat(buf,tbuf,blen);
    return blen;
}
int xed_immdis_print_value_signed(const xed_immdis_t* p, char* buf, int buflen) {
    xed_int64_t d64;
    xed_uint64_t u64;
    int blen = buflen;
    xed_uint_t len = xed_immdis_get_bytes(p);
    if (len != 1 && len != 2 && len != 4 && len != 8) {
        return xed_immdis__print_ptr(p,buf,buflen);
    }

    d64 = xed_immdis_get_signed64(p);
    if (d64<0) {
        blen  = xed_strncpy(buf,"-",blen);
        u64 = -d64;
    }
    else {
        buf[0] = 0;
        u64 = d64;
    }
    blen = xed_immdis_print_helper(u64, len, buf+xed_strlen(buf), blen);
    return blen;
}


int xed_immdis_print_value_unsigned(const xed_immdis_t* p, char* buf, int buflen) {
    xed_uint64_t d64 = xed_immdis_get_unsigned64(p);
    xed_uint_t len = xed_immdis_get_bytes(p);
    if (len != 1 && len != 2 && len != 4 && len != 8) {
        return xed_immdis__print_ptr(p,buf,buflen);
    }
    return xed_immdis_print_helper(d64, len, buf, buflen);
}



void xed_immdis_add_byte(xed_immdis_t* p, xed_uint8_t b) {
    // add them byte by byte
    p->present  = 1;
    if (p->currently_used_space >= p->max_allocated_space)     {
        XED2DIE((xed_log_file, 
                 "adding too many bytes to immdis. max_allocated_space=%d currently_used_space=%d\n",p->max_allocated_space , p->currently_used_space));
    }
    p->value.x[ p->currently_used_space++ ] = b;
}

void xed_immdis_add_byte_array(xed_immdis_t* p, int nb, xed_uint8_t* ba) {
    int i;
    XED2VMSG((xed_log_file,"nb= %d\n", nb));
    for(i=0; i < nb; i++ ) {
        xed_immdis_add_byte(p,ba[i]);
    }
    XED2VMSG((xed_log_file, "Set %d bytes\n", (int)p->currently_used_space));
}



