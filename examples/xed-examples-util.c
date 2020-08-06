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

#include "xed/xed-interface.h"
#include "xed/xed-get-time.h"
#include "xed-examples-util.h"
#include <string.h> //strlen, memcmp, memset
#include <stddef.h> //ptrdiff_t
#if defined(XED_MAC) || defined(XED_LINUX) || defined(XED_BSD)
# include <unistd.h>
# include <sys/mman.h>
# include <sys/types.h>
# include <sys/stat.h>
# include <fcntl.h>
#endif
#include <ctype.h>
#include <stdlib.h>
#include <assert.h>
#include "xed-dot-prep.h"


#include "xed/xed-ild.h"
#if defined(PTI_XED_TEST)
#include "pti-xed-test.h"
#endif

#define DCAST(x) XED_STATIC_CAST(double,(x))
#define XCAST(x) XED_STATIC_CAST(xed_int64_t,(x))
#define U64CAST(x) XED_STATIC_CAST(xed_uint64_t,(x))
#define ICAST(x) XED_STATIC_CAST(xed_int_t,(x))
#define UCAST(x) XED_STATIC_CAST(xed_uint_t,(x))


#define XED_TMP_BUF_LEN (1024*4)


#define XED_HISTO_MAX_CYCLES 10000 // must be divisible by cycles/bin
#define XED_HISTO_CYCLES_PER_BIN 50 
#define XED_HISTO_BINS (XED_HISTO_MAX_CYCLES/XED_HISTO_CYCLES_PER_BIN)

typedef struct {
    xed_uint64_t  total_time ;
    xed_uint64_t  total_insts ;
    xed_uint64_t  total_ilen ;
    xed_uint64_t  total_olen ;
    xed_uint64_t  total_shorter ;
    xed_uint64_t  total_longer ;
    xed_uint64_t  bad_times ;
    xed_uint64_t  reset_counter;

    xed_uint64_t  total_insts_tail;
    xed_uint64_t  total_time_tail;
    xed_uint64_t  perf_tail;

    xed_uint64_t histo[XED_HISTO_BINS];
} xed_stats_t;

#if defined(XED_DECODER)
static void
update_histogram(xed_stats_t* p,
                 xed_uint64_t delta)
{
    xed_uint32_t bin;
    if (delta  < XED_HISTO_MAX_CYCLES)
        bin = XED_STATIC_CAST(xed_uint32_t, delta / XED_HISTO_CYCLES_PER_BIN);
    else
        bin = XED_HISTO_BINS-1;
    p->histo[bin]++;
}

static void
init_histogram(xed_stats_t* p)
{
    memset(p->histo, 0,
           sizeof(xed_uint64_t)*XED_HISTO_BINS);
}


static void
xed_stats_update(xed_stats_t* p,
                 xed_uint64_t t1, 
                 xed_uint64_t t2)
{
    if (t2 > t1)
    {
        xed_uint64_t delta = t2-t1;
        p->total_time += delta;
        update_histogram(p,delta);
    }
    else
        p->bad_times++;
    p->total_insts++;
    p->reset_counter++;
    if (p->reset_counter == 50) {
        if (CLIENT_VERBOSE1) 
            printf("\n\nRESETTING STATS\n\n");
        // to ignore startup transients paging everything in.
        init_histogram(p);
        p->total_insts=0;
        p->total_time=0;
    }
    //these guys count average on tail instructions -
    //when all cpu caches and tables are full
    if (p->total_insts >= p->perf_tail) {
        p->total_insts_tail++;
        p->total_time_tail += (t2-t1);
    }
}

static void
xed_stats_zero(xed_stats_t* p,
               xed_disas_info_t* di)
{
    p->total_time = 0;
    p->total_insts = 0;
    p->total_ilen = 0;
    p->total_olen = 0;
    p->total_shorter = 0;
    p->total_longer = 0;
    p->bad_times = 0;
    p->reset_counter = 0;

    p->total_time_tail = 0;
    p->total_insts_tail = 0;
    p->perf_tail = di->perf_tail_start;

    init_histogram(p);
}
#endif

static xed_stats_t xed_dec_stats; 
static xed_stats_t xed_enc_stats;

void xed_disas_info_init(xed_disas_info_t* p)
{
    memset(p,0,sizeof(xed_disas_info_t));
}

xed_syntax_enum_t global_syntax = XED_SYNTAX_INTEL;
int client_verbose=0; 

////////////////////////////////////////////////////////////////////////////

static char xed_toupper(char c) {
    if (c >= 'a' && c <= 'z') {
        int t = c - 'a';
        char u = (char)(t+'A');
        return u;
    }
    return c;
}

char* xed_upcase_buf(char* s) {
    xed_uint_t len = XED_STATIC_CAST(xed_uint_t,strlen(s));
    xed_uint_t i;
    for(i=0 ; i < len ; i++ ) 
        s[i] = xed_toupper(s[i]);
    return s;
}

static xed_uint8_t letter_cvt(char a, char base) {
    return (xed_uint8_t)(a-base);
}

static xed_uint8_t convert_nibble(char x) {
    // convert ascii nibble to hex
    xed_uint8_t rv = 0;
    if (x >= '0' && x <= '9') 
        rv = letter_cvt(x, '0');
    else if (x >= 'A' && x <= 'F') 
        rv = (xed_uint8_t)(letter_cvt(x,'A') + 10U);
    else if (x >= 'a' && x <= 'f') 
        rv = (xed_uint8_t)(letter_cvt(x,'a') + 10U);
    else    {
        printf("Error converting hex digit. Nibble value 0x%x\n", x);
        exit(1);
    }
    return rv;
}


xed_int64_t xed_atoi_hex(char* buf) {
    xed_int64_t o=0;
    xed_uint_t i;
    xed_uint_t len = XED_STATIC_CAST(xed_uint_t,strlen(buf));
    for(i=0; i<len ; i++) 
        o = o*16 + convert_nibble(buf[i]);
    return o;
}

xed_int64_t xed_atoi_general(char* buf, int mul) {
    /*      mul should be 1000 or 1024     */
    char* q;
    xed_int64_t b;

    char* p = buf;
    while(*p && isspace((unsigned char)*p))
    {
        p++;
    }
    // exclude hex; octal works just fine
    q = p;
    if (*q == '-' || *q == '+')
    {
        q++;
    }
    if (*q=='0' && (q[1]=='x' || q[1]=='X'))
    {
        return xed_strtoll(buf,0);
    }

    b = xed_strtoll(buf,0);
    if (*p)
    {
        while(*p && (*p == '-' || *p == '+'))
        {
            p++;
        }
        while(*p && isdigit((unsigned char)*p))
        {
            p++;
        }

        if (*p != 0)
        {
            if (*p == 'k' || *p == 'K')
            {
                b = b * mul;
            }
            else if (*p == 'm' || *p == 'M')
            {
                b = b * mul * mul;
            }
            else if (*p == 'g' || *p == 'G' || *p == 'b' || *p == 'B')
            {
                b = b * mul * mul * mul;
            }
        }
    }
    return b;
}


static char nibble_to_ascii_hex(xed_uint8_t i) {
    if (i<10) return (char)(i+'0');
    if (i<16) return (char)(i-10+'A');
    return '?';
}

void xed_print_hex_line(char* buf,
                        const xed_uint8_t* array,
                        const unsigned int length, 
                        const unsigned int buflen)
{
  unsigned int n = length;
  unsigned int i = 0;
  if (length == 0)
      n = XED_MAX_INSTRUCTION_BYTES;
  assert(buflen >= (2*n+1)); /* including null */
  for( i=0 ; i< n; i++)     {
      buf[2*i+0] = nibble_to_ascii_hex(array[i]>>4);
      buf[2*i+1] = nibble_to_ascii_hex(array[i]&0xF);
  }
  buf[2*i]=0;
}



void XED_NORETURN xedex_derror(const char* s) {
    printf("[XED CLIENT ERROR] %s\n",s);
    exit(1);
}

void xedex_dwarn(const char* s) {
    printf("[XED CLIENT WARNING] %s\n",s);
}


////////////////////////////////////////////////////////////////////////////

#if defined(XED_DECODER)
//#define BINARY_DUMP

#if defined (BINARY_DUMP)
int fd = 0;
void open_binary_output_file(void);
void open_binary_output_file(void)
{
    fd = open("output", O_WRONLY|O_CREAT|O_TRUNC, S_IRWXU);
    if (fd == -1) {
        fprintf(stderr,"Could not open binary output file\n");
        exit(1);
    }
}
#endif

static XED_INLINE xed_error_enum_t
decode_internal(xed_decoded_inst_t* xedd,
                const xed_uint8_t* itext,
                xed_uint_t max_bytes)
{
    xed_error_enum_t err =  xed_decode(xedd,itext,max_bytes);

#if defined (BINARY_DUMP)
    if (err == XED_ERROR_NONE)
        write(fd, itext, xed_decoded_inst_get_length(xedd));
#endif
    
    return err;
}
#endif

void init_xedd(xed_decoded_inst_t* xedd,
               xed_disas_info_t* di)
{


#if defined(XED_DECODER)
    xed_decoded_inst_zero_set_mode(xedd, &(di->dstate));
#endif
    xed_decoded_inst_set_input_chip(xedd, di->chip);
#if defined(XED_MPX)
    xed3_operand_set_mpxmode(xedd, di->mpx_mode);
#endif
#if defined(XED_CET)
    xed3_operand_set_cet(xedd, di->cet_mode);
#endif
    if (di->operand != XED_OPERAND_INVALID) 
        xed3_set_generic_operand(xedd, di->operand, di->operand_value);
}

////////////////////////////////////////////////////////////////////////////

static void
dump_histo(xed_uint64_t* histo,
           xed_uint32_t bins,
           xed_uint32_t cycles_per_bin)
{
    xed_uint32_t i=0;
    xed_uint64_t total=0;
    double cdf = 0;
    for(i=0;i<bins;i++) 
        total += histo[i];

    if (total == 0)
        return;
    
    for(i=0;i<bins;i++)
    {
        double pct = 100.0*DCAST(histo[i])/DCAST(total);
        cdf += pct;
        printf("[ %4u ... %4u ]  " XED_FMT_LU12 "  %7.2lf%%  %7.2lf%%\n",
               i*cycles_per_bin,
               (i+1)*cycles_per_bin-1,
               histo[i],
               pct,
               cdf);
    }
}


static void
print_decode_stats_internal( xed_disas_info_t*di,
                             xed_stats_t* p, 
                             const char* sname,
                             const char* dec_enc  ) 
{
    double cpi;
    double cpi_tail;
    printf("#%s %s STATS\n", sname, dec_enc);
    printf("#Total %s cycles:        " XED_FMT_LU "\n", dec_enc,
           p->total_time);
    printf("#Total instructions %s: " XED_FMT_LU "\n", dec_enc,
           p->total_insts);
    printf("#Total tail %s cycles:        " XED_FMT_LU "\n", dec_enc,
           p->total_time_tail);
    printf("#Total tail instructions %s: " XED_FMT_LU "\n", dec_enc,
           p->total_insts_tail);

    cpi  =  1.0 * DCAST(p->total_time) / DCAST(p->total_insts);
    printf("#Total cycles/instruction %s: %.2f\n" , dec_enc, cpi);

    cpi_tail = 1.0 * DCAST(p->total_time_tail) /
               DCAST(p->total_insts_tail);
    printf("#Total tail cycles/instruction %s: %.2f\n" , dec_enc, cpi_tail);

    if (p->bad_times)
        printf("#Bad times: " XED_FMT_LU "\n", p->bad_times);

    if (di->histo)
        dump_histo(p->histo, XED_HISTO_BINS, XED_HISTO_CYCLES_PER_BIN);
}

void xed_print_decode_stats(xed_disas_info_t* di)
{
    print_decode_stats_internal(di, &xed_dec_stats, "XED3", "DECODE");
}

void xed_print_encode_stats(xed_disas_info_t* di)
{
    print_decode_stats_internal(di, &xed_enc_stats, "XED3", "ENCODE");
}



void
xed_map_region(const char* path,
               void** start,
               unsigned int* length)
{
#if defined(_WIN32) 
    FILE* f;
    size_t t,ilen;
    xed_uint8_t* p;
#if defined(XED_MSVC8_OR_LATER) && !defined(PIN_CRT)
    errno_t err;
    fprintf(stderr,"#Opening %s\n", path);
    err = fopen_s(&f,path,"rb");
#else
    int err=0;
    fprintf(stderr,"#Opening %s\n", path);
    f = fopen(path,"rb");
    err = (f==0);
#endif
    if (err != 0) {
        fprintf(stderr,"ERROR: Could not open %s\n", path);
        exit(1);
    }
    err =  fseek(f, 0, SEEK_END);
    if (err != 0) {
        fprintf(stderr,"ERROR: Could not fseek %s\n", path);
        exit(1);
    }
    ilen = ftell(f);
    fprintf(stderr,"#Trying to read " XED_FMT_SIZET "\n", ilen);
    p = (xed_uint8_t*)malloc(ilen);
    assert(p!=0);
    t=0;
    err = fseek(f,0, SEEK_SET);
    if (err != 0) {
        fprintf(stderr,"ERROR: Could not fseek to start of file %s\n", path);
        exit(1);
    }
    
    while(t < ilen) {
        size_t n;
        if (feof(f)) {
            fprintf(stderr, "#Read EOF. Stopping.\n");
            break;
        }
        n = fread(p+t, 1, ilen-t,f);
        t = t+n;
        fprintf(stderr,"#Read " XED_FMT_SIZET " of " XED_FMT_SIZET " bytes\n", 
                t, ilen);
        if (ferror(f)) {
            fprintf(stderr, "Error in file read. Stopping.\n");
            break;
        }
    }
    fclose(f);
    *start = p;
    *length = (unsigned int)ilen;
    
#else 
    off_t ilen;
    int fd;
    fd = open(path, O_RDONLY);
    if (fd == -1)   {
        printf("Could not open file: %s\n" , path);
        exit(1);
    }
    ilen = lseek(fd, 0, SEEK_END); // find the size.
    if (ilen == -1)
        xedex_derror("lseek failed");
    else 
        *length = (unsigned int) ilen;

    lseek(fd, 0, SEEK_SET); // go to the beginning
    *start = mmap(0,
                  *length,
                  PROT_READ|PROT_WRITE,
                  MAP_PRIVATE,
                  fd,
                  0);
    if (*start == (void*) -1)
        xedex_derror("could not map region");
#endif
    if (CLIENT_VERBOSE1)
        printf("Mapped " XED_FMT_U " bytes!\n", *length);
}


////////////////////////////////////////////////////////////////////////////

#if defined(XED_DECODER)

static xed_disassembly_callback_fn_t registered_disasm_callback=0;

void
xed_register_disassembly_callback(xed_disassembly_callback_fn_t f)
{
    registered_disasm_callback = f;
}


void disassemble(xed_disas_info_t* di,
                 char* buf,
                 int buflen,
                 xed_decoded_inst_t* xedd,
                 xed_uint64_t runtime_instruction_address,
                 void* caller_data) 
{
    xed_bool_t ok;
    xed_print_info_t pi;
    xed_init_print_info(&pi);
    pi.p = xedd;
    pi.blen = buflen;
    pi.buf = buf;

    // passed back to symbolic disassembly function
    pi.context = caller_data;

    // 0=use the default symbolic disassembly function registered via
    // xed_register_disassembly_callback(). If nonzero, it would be a
    // function pointer to a disassembly callback routine. See xed-disas.h
    pi.disassembly_callback = registered_disasm_callback;
    
    pi.runtime_address = runtime_instruction_address;
    pi.syntax = global_syntax;
    pi.format_options_valid = 1;
    pi.format_options = di->format_options;
    pi.buf[0]=0; //allow use of strcat
    
    ok = xed_format_generic(&pi);
    if (!ok)
    {
        pi.blen = xed_strncpy(pi.buf,"Error disassembling ",pi.blen);
        pi.blen = xed_strncat(pi.buf,
                               xed_syntax_enum_t2str(pi.syntax),
                               pi.blen);
        pi.blen = xed_strncat(pi.buf," syntax.",pi.blen);
    }
}

void xed_decode_error( xed_uint64_t runtime_instruction_address,
                       xed_uint64_t offset, 
                       const xed_uint8_t* ptr, 
                       xed_error_enum_t xed_error,
                       xed_uint_t length)
{
    char buf[XED_HEX_BUFLEN];
    printf("ERROR: %s Could not decode at offset: 0x" 
           XED_FMT_LX " len: %d PC: 0x" XED_FMT_LX ": [", 
           xed_error_enum_t2str(xed_error),
           offset,
           length,
           runtime_instruction_address);

    xed_print_hex_line(buf, ptr, length, XED_HEX_BUFLEN);
    printf("%s]\n",buf);
}

static void
print_hex_line(const xed_uint8_t* p,
               unsigned int length)
{
        char buf[XED_HEX_BUFLEN];
        unsigned int lim = XED_HEX_BUFLEN/2;
        if (length < lim)
            lim = length;
        xed_print_hex_line(buf,p, lim, XED_HEX_BUFLEN); 
        printf("%s\n", buf);
}

static void 
print_attributes(xed_decoded_inst_t* xedd) {
    /* Walk the attributes. Generally, you'll know the one you want to
     * query and just access that one directly. */

    const xed_inst_t* xi = xed_decoded_inst_inst(xedd);

    unsigned int i, nattributes  =  xed_attribute_max();

    printf("ATTRIBUTES: ");
    for(i=0;i<nattributes;i++) {
        xed_attribute_enum_t attr = xed_attribute(i);
        if (xed_inst_get_attribute(xi,attr))
            printf("%s ", xed_attribute_enum_t2str(attr));
    }
    printf("\n");
}


xed_uint_t
disas_decode_binary(xed_disas_info_t* di,
                    const xed_uint8_t* hex_decode_text,
                    const unsigned int bytes,
                    xed_decoded_inst_t* xedd,
                    xed_uint64_t runtime_address)
{
    // decode one instruction
    xed_uint64_t t1,t2;
    xed_error_enum_t xed_error;
    xed_bool_t okay;

    if (CLIENT_VERBOSE) {
        print_hex_line(hex_decode_text, bytes);
    }

    t1 = xed_get_time();
    xed_error = decode_internal(xedd, hex_decode_text, bytes);
    t2 = xed_get_time();
    okay = (xed_error == XED_ERROR_NONE);
    
#if defined(PTI_XED_TEST)
    if (okay)
        pti_xed_test(xedd,hex_decode_text, bytes, runtime_address);
#endif

    if (CLIENT_VERBOSE3) {
        xed_uint64_t delta = t2-t1;
        printf("Decode time = " XED_FMT_LU "\n", delta);
    }
    
    if (okay)     {

        if (CLIENT_VERBOSE1) {
            char tbuf[XED_TMP_BUF_LEN];
            xed_decoded_inst_dump(xedd,tbuf,XED_TMP_BUF_LEN);
            printf("%s\n",tbuf);
        }
        if (CLIENT_VERBOSE) {
            char buf[XED_TMP_BUF_LEN];
            if (xed_decoded_inst_valid(xedd)) 
            {
                printf( "ICLASS:     %s\n"
                        "CATEGORY:   %s\n"
                        "EXTENSION:  %s\n"
                        "IFORM:      %s\n"
                        "ISA_SET:    %s\n", 
                        xed_iclass_enum_t2str(xed_decoded_inst_get_iclass(xedd)),
                        xed_category_enum_t2str(xed_decoded_inst_get_category(xedd)),
                        xed_extension_enum_t2str(xed_decoded_inst_get_extension(xedd)),
                        xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(xedd)),
                        xed_isa_set_enum_t2str(xed_decoded_inst_get_isa_set(xedd)));
                print_attributes(xedd);
            }
            disassemble(di, buf,XED_TMP_BUF_LEN, xedd, runtime_address,0);
            printf("SHORT:      %s\n", buf);
        }
        return 1;
    }
    else {
        xed_uint_t dec_length = xed_decoded_inst_get_length(xedd);
        xed_decode_error(0, 0, hex_decode_text, xed_error, dec_length);
        return 0;
    }
}
#endif  // XED_DECODER

#if defined(XED_ENCODER) && defined(XED_DECODER)
xed_uint_t
disas_decode_encode_binary(xed_disas_info_t* di,
                           const xed_uint8_t* decode_text_binary,
                           const unsigned int bytes,
                           xed_decoded_inst_t* xedd, 
                           xed_uint64_t runtime_address)
{
    // decode then encode one instruction
    unsigned int retval_olen = 0;
    xed_uint64_t dt1, dt2;
    xed_bool_t decode_okay;
    
    // decode it...
    dt1 = xed_get_time();
    decode_okay =  disas_decode_binary(di,
                                       decode_text_binary,
                                       bytes,
                                       xedd, 
                                       runtime_address);
    dt2=xed_get_time();
    xed_stats_update(&xed_dec_stats, dt1, dt2);

    if (decode_okay)     {
        xed_error_enum_t encode_okay;
        xed_uint64_t et1,et2;
        unsigned int enc_olen, ilen = XED_MAX_INSTRUCTION_BYTES;
        xed_uint8_t array[XED_MAX_INSTRUCTION_BYTES];
        // they are basically the same now
        xed_encoder_request_t* enc_req = xedd; 
        // convert decode structure to proper encode structure
        xed_encoder_request_init_from_decode(xedd);
        xed3_operand_set_encode_force(enc_req, di->encode_force);
        
        // encode it again...
        et1 = xed_get_time();
        encode_okay =  xed_encode(enc_req, array, ilen, &enc_olen);
        et2 = xed_get_time();
        xed_stats_update(&xed_enc_stats, et1, et2);
        if (encode_okay != XED_ERROR_NONE) {
            if (CLIENT_VERBOSE) {
                char buf[XED_TMP_BUF_LEN];
                char buf2[XED_TMP_BUF_LEN];
                int blen=XED_TMP_BUF_LEN;
                xed_encode_request_print(enc_req, buf, XED_TMP_BUF_LEN);
                blen = xed_strncpy(buf2,"Could not re-encode: ", blen);
                blen = xed_strncat(buf2, buf, blen);
                blen = xed_strncat(buf2,"\nError code was: ",blen);
                blen = xed_strncat(buf2,
                                   xed_error_enum_t2str(encode_okay),blen);
                blen = xed_strncat(buf2, "\n",blen);
                xedex_dwarn(buf2);
            }
        }
        else         {
            retval_olen = enc_olen;
            // See if it matched the original...
            if (CLIENT_VERBOSE) {
                char buf[XED_HEX_BUFLEN];
                xed_uint_t dec_length; 
                xed_print_hex_line(buf,array, enc_olen, XED_HEX_BUFLEN);
                printf("Encodable! %s\n",buf);
                dec_length = xed_decoded_inst_get_length(xedd);
                if ((enc_olen != dec_length ||
                     memcmp(decode_text_binary, array, enc_olen)  )) {
                    char buf2[XED_TMP_BUF_LEN];
                    char buf3[XED_TMP_BUF_LEN];
                    printf("Discrepenacy after re-encoding. dec_len= " 
                           XED_FMT_U " ", dec_length);
                    xed_print_hex_line(buf, decode_text_binary, 
                                       dec_length,XED_HEX_BUFLEN);
                    printf("[%s] ", buf);
                    printf("enc_olen= " XED_FMT_U "", enc_olen);
                    xed_print_hex_line(buf, array, enc_olen, XED_HEX_BUFLEN);
                    printf(" [%s] ", buf);
                    printf("for instruction: ");
                    xed_decoded_inst_dump(xedd, buf3,XED_TMP_BUF_LEN);
                    printf("%s\n", buf3);
                    printf("vs Encode  request: ");
                    xed_encode_request_print(enc_req, buf2, XED_TMP_BUF_LEN);
                    printf("%s\n", buf2);
                }
                else 
                    printf("Identical re-encoding\n");
            }
        }
    }
    return retval_olen;
}
#endif
///////////////////////////////////////////////////////////////////////////
#if defined(XED_DECODER) && defined(XED_AVX)
typedef enum { XED_AST_INPUT_NOTHING, 
               XED_AST_INPUT_SSE, 
               XED_AST_INPUT_AVX_SCALAR,
               XED_AST_INPUT_AVX128, 
               XED_AST_INPUT_AVX256, 
               XED_AST_INPUT_VZEROALL, 
               XED_AST_INPUT_VZEROUPPER, 
               XED_AST_INPUT_XRSTOR,
               XED_AST_INPUT_EVEX_SCALAR,
               XED_AST_INPUT_EVEX128,
               XED_AST_INPUT_EVEX256,
               XED_AST_INPUT_EVEX512,
               XED_AST_INPUT_LAST }  xed_ast_input_enum_t;

static char const* const xed_ast_input_enum_t_strings[] = {
    "n/a",
    "sse",
    "avx.scalar",
    "avx.128",
    "avx.256",
    "vzeroall",
    "vzeroupper",
    "xrstor",
    "evex.scalar",
    "evex.128",
    "evex.256",
    "evex.512"
};

static xed_uint8_t avx_extensions[XED_EXTENSION_LAST];
static void init_interesting_avx(void) {
    memset(avx_extensions,0,sizeof(xed_uint8_t)*XED_EXTENSION_LAST);
    avx_extensions[XED_EXTENSION_AVX]=1;
    avx_extensions[XED_EXTENSION_FMA]=1;
    avx_extensions[XED_EXTENSION_F16C]=1;
    avx_extensions[XED_EXTENSION_AVX2]=1;
    avx_extensions[XED_EXTENSION_AVX2GATHER]=1;
#if defined(XED_SUPPORTS_AVX512)
    avx_extensions[XED_EXTENSION_AVX512EVEX]=1;
#endif
}
static XED_INLINE int is_interesting_avx(xed_extension_enum_t extension) {
    return avx_extensions[extension];
}
static XED_INLINE xed_ast_input_enum_t avx_type(xed_decoded_inst_t* xedd) {
    xed_uint32_t vl;
#if defined(XED_SUPPORTS_AVX512)
    xed_uint32_t avx512 = (xed_decoded_inst_get_extension(xedd) == XED_EXTENSION_AVX512EVEX);
#else
    xed_uint32_t avx512 = 0;
#endif
    
    // scalar ops are implicitly 128b
    if (xed_decoded_inst_get_attribute(xedd, XED_ATTRIBUTE_SIMD_SCALAR)) 
        return avx512 ? XED_AST_INPUT_EVEX_SCALAR : XED_AST_INPUT_AVX_SCALAR;
    
    // look at the VEX.VL field
    vl = xed3_operand_get_vl(xedd);
    switch(vl) {
      case 0: return avx512 ? XED_AST_INPUT_EVEX128 : XED_AST_INPUT_AVX128;
      case 1: return avx512 ? XED_AST_INPUT_EVEX256 : XED_AST_INPUT_AVX256;
      case 2: return XED_AST_INPUT_EVEX512;
      default: return XED_AST_INPUT_NOTHING;
    }
}
static int is_sse(xed_decoded_inst_t* xedd) {
    const xed_extension_enum_t extension = xed_decoded_inst_get_extension(xedd);
    const xed_category_enum_t category = xed_decoded_inst_get_category(xedd);

    if (extension == XED_EXTENSION_SSE)
    {
        if (category != XED_CATEGORY_MMX  &&
            category != XED_CATEGORY_PREFETCH) /* exclude PREFETCH* insts */
            return 1;
    }
    else if (extension == XED_EXTENSION_SSE2  ||
             extension == XED_EXTENSION_SSSE3 ||
             extension == XED_EXTENSION_SSE4)
    {
        if (category != XED_CATEGORY_MMX)
            return 1;
    }
    else if (extension == XED_EXTENSION_AES ||
             extension == XED_EXTENSION_PCLMULQDQ
#if defined(XED_SUPPORTS_SHA) 
             || extension == XED_EXTENSION_SHA
#endif
    )
    {
        return 1;
    }
    return 0;
}

static char const* xed_ast_input_enum_t2str(xed_ast_input_enum_t e) {
    assert(e < XED_AST_INPUT_LAST);
    return xed_ast_input_enum_t_strings[e];
}
static xed_ast_input_enum_t classify_avx_sse(xed_decoded_inst_t* xedd)
{
    xed_extension_enum_t ext = xed_decoded_inst_get_extension(xedd);
    xed_iclass_enum_t iclass  = xed_decoded_inst_get_iclass(xedd);
    if (iclass == XED_ICLASS_VZEROALL) {
        return XED_AST_INPUT_VZEROALL;
    }
    else if (iclass == XED_ICLASS_VZEROUPPER) {
        return XED_AST_INPUT_VZEROUPPER;
    }
    else if (is_interesting_avx(ext)) {
        return avx_type(xedd);
    }
    else if (is_sse(xedd)) {
        return XED_AST_INPUT_SSE;
    }
    else if (iclass == XED_ICLASS_XRSTOR) {
        return XED_AST_INPUT_XRSTOR;
    }
    return XED_AST_INPUT_NOTHING;
}
#endif // XED_AVX

///////////////////////////////////////////////////////////////////////////
#if defined(XED_DECODER)

static int
all_zeros(xed_uint8_t* p, unsigned int len)
{
    unsigned int i;
    for( i=0;i<len;i++) 
        if (p[i]) 
            return 0;
    return 1;
}

static void
emit_pad(xed_uint32_t dec_len)
{
    // pad out the instruction bytes
    unsigned int sp;
    for ( sp=dec_len; sp < 12; sp++) 
        printf("  ");
    printf(" ");
}

static void
emit_sym(xed_disas_info_t*di,
         xed_uint64_t runtime_instruction_address)
{
    if (di->symfn) {
        char* name = (*di->symfn)(runtime_instruction_address, 
                                  di->caller_symbol_data);
        if (name) {
            if (di->xml_format) 
                printf("\n<SYM>%s</SYM>\n", name);
            else
                printf("\nSYM %s:\n", name);
        }
    }
}

static void
emit_hex(xed_decoded_inst_t* xedd, unsigned char* z)
{
    unsigned int dec_len;
    char buffer[XED_HEX_BUFLEN];
    dec_len = xed_decoded_inst_get_length(xedd);
    xed_print_hex_line(buffer, (xed_uint8_t*) z, 
                       dec_len, XED_HEX_BUFLEN);
    printf("%s",buffer);
    emit_pad(dec_len);
}

static void
emit_cat_ext(xed_decoded_inst_t* xedd,
             xed_disas_info_t* di)
{
    printf("%-9s ",
           xed_category_enum_t2str(
               xed_decoded_inst_get_category(xedd)));
    printf("%-10s ",
           xed_extension_enum_t2str(
               xed_decoded_inst_get_extension(xedd)));
    
    if (di->emit_isa_set)
        printf("%-10s ",
               xed_isa_set_enum_t2str(
                   xed_decoded_inst_get_isa_set(xedd)));

}
static void
emit_resync_msg(unsigned char* z, unsigned int x)
{
    char buf[XED_HEX_BUFLEN];
    printf("ERROR: found symbol in the middle of"
           " an instruction. Resynchronizing...\n");
    printf("ERROR: Rejecting: [");
    xed_print_hex_line(buf, z, x, XED_HEX_BUFLEN);
    printf("%s]\n",buf);
}

static void
emit_dec_sep_msg(unsigned int i) {
    printf("\n==============================================\n");
    printf("Decoding instruction " XED_FMT_U "\n", i);
    printf("==============================================\n");
}

static void
emit_addr_hex(xed_uint64_t runtime_instruction_address,
              unsigned char* z,
              xed_uint_t ilim)
{
    char tbuf[XED_HEX_BUFLEN];
    printf("Runtime Address " XED_FMT_LX ,
           runtime_instruction_address);
    xed_print_hex_line(tbuf, (xed_uint8_t*) z, ilim, XED_HEX_BUFLEN);
    printf(" [%s]\n", tbuf);
}

static void
emit_cat_ext_ast(xed_decoded_inst_t* xedd,
                 xed_disas_info_t* di)
{
#if defined(XED_AVX)
    if (di->ast)
    {
        printf("%-11s ",
               xed_ast_input_enum_t2str(
                   classify_avx_sse(xedd)));
    }
    else
#endif
    {
        emit_cat_ext(xedd,di);
    }
    (void)di; //pacify compiler
}

static void
emit_line_num(xed_disas_info_t* di,
              xed_error_enum_t xed_error,
              xed_uint64_t runtime_instruction_address)
{
    if (di->line_numbers ||
        xed_error == XED_ERROR_INVALID_FOR_CHIP)
    {
        if (di->line_number_info_fn)
            (*di->line_number_info_fn)(
                runtime_instruction_address);
    }
}


static void
emit_xml(xed_decoded_inst_t* xedd,
         xed_uint64_t runtime_instruction_address,
         unsigned char* z,
         xed_disas_info_t* di)
{
    char buffer[XED_TMP_BUF_LEN];
    unsigned int dec_len;

    printf("<ASMLINE>\n"); 
    printf("  <ADDR>" XED_FMT_LX "</ADDR>\n", 
           runtime_instruction_address);
    printf("  <CATEGORY>%s</CATEGORY>\n", 
           xed_category_enum_t2str( xed_decoded_inst_get_category(xedd)));
    printf("  <EXTENSION>%s</EXTENSION>\n",
           xed_extension_enum_t2str(xed_decoded_inst_get_extension(xedd)));
    printf("  <ITEXT>");
    dec_len = xed_decoded_inst_get_length(xedd);
    xed_print_hex_line(buffer, (xed_uint8_t*) z, 
                       dec_len, XED_TMP_BUF_LEN);
    printf("%s</ITEXT>\n",buffer);
    disassemble(di, buffer,XED_TMP_BUF_LEN, 
                xedd, runtime_instruction_address, 
                di->caller_symbol_data);
    printf( "  %s\n",buffer);
    printf("</ASMLINE>\n"); 
}


static void
emit_disasm(xed_disas_info_t* di,
            xed_decoded_inst_t* xedd,
            xed_uint64_t runtime_instruction_address,
            unsigned char* z,
            xed_dot_graph_supp_t* gs,
            xed_error_enum_t xed_error)
{ 
    if (CLIENT_VERBOSE1) {
        char tbuf[XED_TMP_BUF_LEN];
        xed_decoded_inst_dump(xedd,tbuf, XED_TMP_BUF_LEN);
        printf("%s\n",tbuf);
    }
    if (CLIENT_VERBOSE)  {
        emit_sym(di, runtime_instruction_address);
        if (di->xml_format) 
            emit_xml(xedd, runtime_instruction_address, z, di);
        else
        {
            char buffer[XED_TMP_BUF_LEN];
            char const* fmt = "XDIS " XED_FMT_LX ": ";
            if (di->format_options.lowercase_hex==0)
                fmt = "XDIS " XED_FMT_LX_UPPER ": ";
                              
            printf(fmt, runtime_instruction_address);
            emit_cat_ext_ast(xedd,di);
            emit_hex(xedd, z);
            disassemble(di,
                        buffer,XED_TMP_BUF_LEN,
                        xedd, 
                        runtime_instruction_address, 
                        di->caller_symbol_data);
            printf( "%s",buffer);
            if (gs) {
                xed_dot_graph_add_instruction(
                    gs,
                    xedd,
                    runtime_instruction_address,
                    di->caller_symbol_data,
                    registered_disasm_callback);
            }
            
            if (xed_error == XED_ERROR_INVALID_FOR_CHIP) {
                di->errors_chip_check++;
                printf(" # INVALID-FOR-CHIP");
            }
            emit_line_num(di, xed_error,
                          runtime_instruction_address);
            
            printf( "\n");
        }
    }
}
static unsigned int
check_resync(xed_disas_info_t* di,
             xed_uint64_t runtime_instruction_address,
             unsigned int length,
             unsigned char* z)
{
    if (di->resync && di->symfn)
    {
        unsigned int x;
        for ( x=1 ; x<length ; x++ ) 
        {
            char* name = (*di->symfn)(runtime_instruction_address+x, 
                                      di->caller_symbol_data);
            if (name)
            {
                /* bad news. We found a symbol in the middle of an
                 * instruction. That probably means decoding is messed up.
                 * This usually happens because of data-in the code/text
                 * section.  We should reject the current instruction and
                 * pick up at the symbol address. */
                emit_resync_msg(z,x);
                return x;
            }
        }
    }
    return 0;
}
    
static void XED_NORETURN
die_zero_len(
    xed_uint64_t runtime_instruction_address,
    unsigned char* z,
    xed_disas_info_t* di,
    xed_error_enum_t xed_error)
{
    printf("Zero length on decoded instruction!\n");
    xed_decode_error( runtime_instruction_address, 
                      U64CAST(z-di->a), z, xed_error, 15);
    xedex_derror("Dying");
}

void xed_disas_test(xed_disas_info_t* di)
{
    // this decodes are region defined by the input structure.
    
    static int first = 1;
    xed_uint64_t errors = 0;
    unsigned int m;
    unsigned char* z;  // our sliding pointer for decoding
    unsigned char* zlimit;
    unsigned int length;
    int skipping;
    int last_all_zeros;
    unsigned int i;
    int okay;
    xed_decoded_inst_t xedd;
    xed_uint64_t runtime_instruction_address;
    xed_dot_graph_supp_t* gs = 0;
    xed_bool_t graph_empty = 1;
    unsigned int resync;

    if (di->dot_graph_output) {
        xed_syntax_enum_t local_syntax = XED_SYNTAX_INTEL;
        gs = xed_dot_graph_supp_create(local_syntax);
    }

    if (first) {
        xed_stats_zero(&xed_dec_stats, di);
        first = 0;
    }

    m = di->ninst; // number of things to decode
    z = di->a;   // set to start of region
  
    if (di->runtime_vaddr_disas_start) 
        if (di->runtime_vaddr_disas_start > di->runtime_vaddr)
            z = (di->runtime_vaddr_disas_start - di->runtime_vaddr) +
                di->a;

    zlimit = 0;
    if (di->runtime_vaddr_disas_end) {
        if (di->runtime_vaddr_disas_end > di->runtime_vaddr)
            zlimit = (di->runtime_vaddr_disas_end - di->runtime_vaddr) +
                     di->a;
        else  /* end address is before start of this region -- skip it */
            goto finish;
    } 

    if (z >= di->q)   /* start pointer  is after end of section */
        goto finish;

    // for skipping long strings of zeros
    skipping = 0;
    last_all_zeros = 0;
    for( i=0; i<m;i++) 
    {
        xed_uint_t ilim;
        if (zlimit && z >= zlimit) {
            if (di->xml_format == 0)
                printf("# end of range.\n");
            break;
        }
        if (z >= di->q) {
            if (di->xml_format == 0)
                printf("# end of text section.\n");
            break;
        }

        /* if we get near the end of the section, clip the itext length */
        ilim = 15;
        // we know z < di->q due to above if() statement. 
        if (z + ilim > di->q) { 
            // pointer diff is signed, but in this case guaranteed positive and <= ilim.
            ilim = UCAST(di->q - z);
        }

        if (CLIENT_VERBOSE3) 
            emit_dec_sep_msg(i);
    
        // if we get two full things of 0's in a row, start skipping.
        if (all_zeros((xed_uint8_t*) z, ilim)) 
        {
            if (skipping) {
                z = z + ilim;
                continue;
            }
            else if (last_all_zeros) { 
                printf("...\n");
                z = z + ilim;
                skipping = 1;
                continue;
            }
            else
                last_all_zeros = 1;
        }
        else
        {
            skipping = 0;
            last_all_zeros = 0;
        }

        runtime_instruction_address =  U64CAST(z-di->a) + 
                                       di->runtime_vaddr;
         
        if (CLIENT_VERBOSE3) 
            emit_addr_hex(runtime_instruction_address, z, ilim);

        okay = 0;
        length = 0;

        init_xedd(&xedd, di); 
        
        if ( di->decode_only )
        {
            xed_uint64_t t1,t2;
            xed_error_enum_t xed_error = XED_ERROR_NONE;

            t1 = xed_get_time();

            //do the decode
            xed_error = decode_internal(
                &xedd, 
                XED_REINTERPRET_CAST(const xed_uint8_t*,z),
                ilim);
            
            t2 = xed_get_time();

            okay = (xed_error == XED_ERROR_NONE);
#if defined(PTI_XED_TEST)
            if (okay)
                pti_xed_test(&xedd,
                             XED_REINTERPRET_CAST(const xed_uint8_t*,z),
                             ilim,
                             runtime_instruction_address);
#endif
            
            xed_stats_update(&xed_dec_stats, t1, t2);
            length = xed_decoded_inst_get_length(&xedd);

            if (okay && length == 0) 
                die_zero_len(runtime_instruction_address, z, di, xed_error);

            resync = check_resync(di, runtime_instruction_address, length, z);
            if (resync) {
                z += resync;
                continue;
            }

            xed_dec_stats.total_ilen += length;

//we don't want to print out disassembly with ILD perf
#if !defined(XED_ILD_ONLY) && !defined(XED2_PERF_MEASURE)

            if (okay || xed_error == XED_ERROR_INVALID_FOR_CHIP)
            {
                // we still print it out if it is invalid for the chip.
                // so that people can see the problematic instruction
                emit_disasm(di, &xedd,
                            runtime_instruction_address,
                            z, gs, xed_error);
                if (CLIENT_VERBOSE && gs) 
                    graph_empty = 0;
            }
            
            if (okay == 0)
            {
                errors++;
                length = xed_decoded_inst_get_length(&xedd);
                if (length == 0)
                    length = 1;

                xed_decode_error( runtime_instruction_address,
                                  U64CAST(z-di->a),
                                  z, 
                                  xed_error,
                                  length);
                
            }  // okay == 0
        } // decode_only

#    if defined(XED_ENCODER) && defined(XED_DECODER)
        else  // decode->encode
        {
            unsigned int olen  = 0;
            olen  = disas_decode_encode_binary(di,
                                               XED_REINTERPRET_CAST(const xed_uint8_t*,z),
                                               ilim,
                                               &xedd, 
                                               runtime_instruction_address);

            okay = (olen != 0);
            if (!okay)  {
                errors++;
                printf("-- Could not decode/encode at offset: " XED_FMT_LU "\n" ,
                       U64CAST(z-di->a));
                // just give a length of 1B to see if we can restart decode...
                length = 1;
            }        
            else {
                length = xed_decoded_inst_get_length(&xedd);
                xed_dec_stats.total_ilen += length;
                xed_dec_stats.total_olen += olen;
                if (length > olen)
                    xed_dec_stats.total_shorter += (length - olen);
                else
                    xed_dec_stats.total_longer += (olen - length);
            }
        }        
#    endif  // XED_ENCODER & XED_DECODER
#endif //!defined(XED_ILD_ONLY) 
        
        
        z = z + length;
    } //for i
   
    if (di->xml_format == 0) {
        printf( "# Errors: " XED_FMT_LU "\n", errors);
    }
finish:

    if (gs) {
        if (graph_empty ==0 ) 
            xed_dot_graph_dump(di->dot_graph_output, gs);
        xed_dot_graph_supp_deallocate(gs);
    }
    
    di->errors += errors;
}
#endif


xed_uint8_t
convert_ascii_nibble(char c)
{
  if (c >= '0' && c <= '9') {
      return letter_cvt(c,'0');
  }
  else if (c >= 'a' && c <= 'f') {
      return (xed_uint8_t)(letter_cvt(c,'a') + 10U);
  }
  else if (c >= 'A' && c <= 'F') {
      return (xed_uint8_t)(letter_cvt(c,'A') + 10U);
  }
  else {
      char buffer[XED_HEX_BUFLEN];
      char* x;
      xed_strncpy(buffer,"Invalid character in hex string: ", XED_HEX_BUFLEN);
      x= buffer+strlen(buffer);
      *x++ = c;
      *x++ = 0;
      xedex_derror(buffer);
      return 0;
  }
}



xed_uint64_t convert_ascii_hex_to_int(const char* s) {
    xed_uint64_t retval = 0;
    const char* p = s;
    while (*p) {
        retval  =  (retval << 4) + convert_ascii_nibble(*p);
        p++;
    }
    return retval;
}


xed_uint8_t convert_ascii_nibbles(char c1, char c2) {
    xed_uint8_t a = (xed_uint8_t)(convert_ascii_nibble(c1) * 16 + convert_ascii_nibble(c2));
    return a;
}

unsigned int
xed_convert_ascii_to_hex(const char* src, xed_uint8_t* dst, 
                         unsigned int max_bytes)
{
    unsigned int j;
    unsigned int p = 0;
    unsigned int i = 0;

    const unsigned int len = XED_STATIC_CAST(unsigned int,strlen(src));
    if ((len & 1) != 0) 
        xedex_derror("test string was not an even number of nibbles");
    
    if (len > (max_bytes * 2) ) 
        xedex_derror("test string was too long");

    for( j=0;j<max_bytes;j++) 
        dst[j] = 0;

    for(;i<len/2;i++) {
        if (CLIENT_VERBOSE3) 
            printf("Converting %c & %c\n", src[p], src[p+1]);
        dst[i] = convert_ascii_nibbles(src[p], src[p+1]);
        p=p+2;
    }
    return i;
}


static xed_int64_t
convert_base10(const char* buf)
{
    xed_int64_t v = 0;
    xed_int64_t sign = 1;
    int len = XED_STATIC_CAST(int,strlen(buf));
    int i; 
    for(i=0;i<len;i++)
    {
        char c = buf[i];
        if (i == 0 && c == '-')
        {
            sign = -1;
        }
        else if (c >= '0' && c <= '9')
        {
            unsigned int digit = letter_cvt(c,'0');
            v = v*10 + digit;
        }
        else if (c == '_') /* skip underscores */
            continue; 
        else
        {
            break;
        }
    }
    return v*sign;
}

static xed_int64_t
convert_base16(const char* buf)
{
    xed_int64_t v = 0;
    int len = XED_STATIC_CAST(int,strlen(buf));
    int start =0 ;
    int i;
    if (len > 2 && buf[0] == '0' && (buf[1] == 'x' || buf[1] == 'X'))
    {
        start = 2;
    }
    for(i=start;i<len;i++)
    {
        char c = buf[i];
        if (c >= '0' && c <= '9')
        {
            unsigned int digit = letter_cvt(c, '0');
            v = v*16 + digit;
        }
        else if (c >= 'A' && c <= 'F')
        {
            unsigned int digit = letter_cvt(c,'A') + 10U;
            v = v*16 + digit;
        }
        else if (c >= 'a' && c <= 'f')
        {
            unsigned int digit = letter_cvt(c,'a') + 10U;
            v = v*16 + digit;
        }
        else if (c == '_') /* skip underscores */
            continue;
        else
        {
            break;
        }
    }
    return v;
}

static xed_int64_t
xed_internal_strtoll(const char* buf, int base)
{
    switch(base)
    {
      case 0:
        if (strlen(buf) > 2 && buf[0] == '0' && 
            (buf[1] == 'x' || buf[1] == 'X'))
        {
            return convert_base16(buf);
        }
        return convert_base10(buf);
      case 10:
        return convert_base10(buf);
      case 16:
        return convert_base16(buf);
      default:
        assert(0);
    }
    return 0;
}


xed_int64_t xed_strtoll(const char* buf, int base)
{
    xed_int64_t t;
    // strtoll is missing on some compilers and buggy on some platforms
    t =  xed_internal_strtoll(buf,base);
   return t;
}

char* xed_strdup(char const* const src) {
    unsigned int n = (unsigned int)strlen(src)+1; /* plus one for null */
    char* dst = (char*)malloc(n*sizeof(char));
    assert(dst != 0);
    dst[0]=0; /* start w/ a null */
    xed_strncat(dst, src, ICAST(n));
    return dst;
}

void xed_example_utils_init(void) {
#if defined(XED_DECODER)  && defined (BINARY_DUMP)
    open_binary_output_file();
#endif
#if defined(XED_DECODER) && defined(XED_AVX)
    init_interesting_avx();
#endif
}


char const* xedex_append_string(char const* p, // p is free()'d
                                char const* x)
{
    char* m = 0; //returned pointer
    char* n = 0; //temp ptr for copying
    char const* t = 0; //temp ptr for copying
    size_t tl = (p?strlen(p):0) + strlen(x) + 1;
    m = n = (char*) malloc(tl);
    assert(m!=0);
    if (p) {
        t = p;
        while(*t)
            *n++ = *t++;
    }
    
    t = x;
    while(*t)
        *n++ = *t++;
    *n++ = 0; // null terminate
    if (p)
        free((void*)p);
    return m;
}

////
static xed_str_list_t* alloc_str_node(void) {
    xed_str_list_t* p = (xed_str_list_t*)malloc(sizeof(xed_str_list_t));
    assert(p!=0);
    return p;
}

// MS does not have strsep()
static char*
portable_strsep(char** input_string, char const* const sep)
{
    char* p = *input_string;
    if (p)  {
        // find token in input string
        char* t = strpbrk(*input_string, sep);
        if (t) {
            *t = 0; // write a null at sep
            *input_string = t+1; // advance pointer
            return p;
        }
        // no token, just return input string
        *input_string=0; // clear pointer
        return p;
    }
    *input_string = 0;
    return 0;
}

xed_str_list_t* xed_tokenize(char const* const p, char const* const sep)
{
    // return a list of strings with their own storage for the tokens.  if
    // one were to free the list, one would have to just free the first
    // token.  The strsep() puts nulls in to a copy of the input string p
    // replacing the delimiters.
    
    xed_str_list_t* head=0;
    xed_str_list_t* last=0;
    xed_str_list_t* cur=0;
    char* token=0;
    char* tmp_string=0;
    
    tmp_string = xed_strdup(p);
    // puts a null in string at token and returns pointer to first token,
    // updates tmp_string to point after null.
    while(1)
    {
        token = portable_strsep(&tmp_string, sep);
        if (!token)
            break;
        if (token[0]) // we know token is non-null
        {
            cur = alloc_str_node();
            if (!head)  
                head = cur;
            cur->next = 0;
            cur->s = token;
            if (last)
                last->next = cur;
            last = cur;
        }
    }
    return head;
}


xed_uint_t xed_str_list_size(xed_str_list_t* p) { //count chunks
    unsigned int c = 0;
    while(p) {
        c++;
        p = p->next;
    }
    return c;
}

void xed_print_bytes_pseudo_op(const xed_uint8_t* array, unsigned int olen) {
    unsigned int i;
    printf(".byte ");
    for(i=0;i<olen;i++) {
        if (i>0)
            printf(",");
        printf("0x%02x",(xed_uint32_t)(array[i]));
    }
    printf("\n");
}

void xed_print_intel_asm_emit(const xed_uint8_t* array, unsigned int olen) {
    unsigned int i;
    for(i=0;i<olen;i++) 
        printf("     __emit 0x%02x\n",(xed_uint32_t)(array[i]));
}
