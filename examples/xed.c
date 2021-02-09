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
/// @file xed.c


////////////////////////////////////////////////////////////////////////////

#include "xed/xed-interface.h"
#include "xed/xed-immdis.h"
#include "xed-examples-util.h"
#if defined(XED_ENCODER)
# include "xed-enc-lang.h"
#endif
#include "xed-disas-elf.h"
#include "xed-disas-macho.h"
#include "xed-disas-raw.h"
#include "xed-disas-hex.h"
#include "xed-disas-pecoff.h"
#include "xed-disas-filter.h"
#include "xed-symbol-table.h"
#include "xed-nm-symtab.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>

int main(int argc, char** argv);
static int intel_asm_emit = 0;

////////////////////////////////////////////////////////////////////////////
#if defined(XED_DECODER)
static xed_uint_t disas_decode( xed_disas_info_t* di,
                                const char* decode_text,
                                xed_decoded_inst_t* xedd,
                                xed_uint64_t runtime_address)
{
    xed_uint8_t hex_decode_text[XED_MAX_INSTRUCTION_BYTES];
    xed_uint_t bytes = xed_convert_ascii_to_hex(decode_text,
                                                hex_decode_text,
                                                XED_MAX_INSTRUCTION_BYTES);
    return  disas_decode_binary(di,
                                hex_decode_text,
                                bytes,
                                xedd,
                                runtime_address);
}
#endif

#if defined(XED_DECODER) && defined(XED_ENCODER)
static unsigned int disas_decode_encode(xed_disas_info_t* di,
                                        const char* decode_text,
                                        xed_decoded_inst_t* xedd,
                                        xed_uint64_t runtime_address)
{
    xed_uint8_t hex_decode_text[XED_MAX_INSTRUCTION_BYTES];
    xed_uint_t bytes = xed_convert_ascii_to_hex( decode_text,
                                                 hex_decode_text, 
                                                 XED_MAX_INSTRUCTION_BYTES);
    return disas_decode_encode_binary(di,
                                      hex_decode_text,
                                      bytes,
                                      xedd,
                                      runtime_address);
}
#endif

static FILE*
fopen_portable(char const* const file_name,
               char const* const mode)
{
    FILE* f = 0;
#if defined(XED_WINDOWS) && !defined(PIN_CRT)
    errno_t error = fopen_s(&f, file_name, mode);
    if (error != 0)
        return 0;
#else
    f = fopen(file_name, mode);
#endif
    return f;
}



#if defined(XED_ENCODER)

static unsigned int disas_encode(const xed_state_t* dstate,
                                 const char* encode_text,
                                 xed_operand_enum_t operand,
                                 xed_uint32_t operand_value,
                                 xed_bool_t encode_force)
{
    char buf[5000];
    xed_uint8_t array[XED_MAX_INSTRUCTION_BYTES];
    unsigned int ilen = XED_MAX_INSTRUCTION_BYTES;
    unsigned int olen=0;
    ascii_encode_request_t areq;
    xed_encoder_request_t req;
    xed_error_enum_t r;

    areq.dstate = *dstate;
    areq.command = encode_text;
    req = parse_encode_request(areq);

    if (operand != XED_OPERAND_INVALID)
        xed3_set_generic_operand(&req, operand, operand_value);
    
    xed3_operand_set_encode_force(&req, encode_force);

    xed_encode_request_print(&req, buf, 5000);
    printf("Request: %s", buf);

    r = xed_encode(&req, array, ilen, &olen);
    if (r != XED_ERROR_NONE)     {
        printf("Could not encode: %s\n", encode_text);
        printf("Error code was: %s\n", xed_error_enum_t2str(r));
        xedex_derror("Dying");
    }
    else if (CLIENT_VERBOSE)   {
        char buf2[XED_HEX_BUFLEN];
        xed_print_hex_line(buf2,array, olen,XED_HEX_BUFLEN);
        printf("Encodable! %s\n", buf2);
        if (intel_asm_emit) 
            xed_print_intel_asm_emit(array,olen);
        else
            xed_print_bytes_pseudo_op(array,olen);
    }
    return olen;
}

static void no_comments(char* buf) {
    size_t i, len = strlen(buf);
    for(i=0;i<len;i++) {
        if (buf[i] == ';' || buf[i] == '#' ||
            buf[i] == '\r' || buf[i] == '\n')
        {
            buf[i]= 0; // stomp on it
            return;
        }
    }
}

static void xed_assemble(const xed_state_t* dstate,
                         const char* encode_file_name)
{
#define ASM_BUF_SIZE 1024
    const xed_int_t bsize = ASM_BUF_SIZE;
    char buf[ASM_BUF_SIZE];
    FILE* f = fopen_portable(encode_file_name,"r");
    if (!f) {
        printf("Could not open %s\n", encode_file_name);
        xedex_derror("Dying");
    }

    while(!feof(f) && fgets(buf, bsize, f))
    {
        unsigned int olen=0;
        ascii_encode_request_t areq;
        xed_encoder_request_t req;
        xed_uint8_t array[XED_MAX_INSTRUCTION_BYTES];
        const unsigned int ilen = XED_MAX_INSTRUCTION_BYTES;
        xed_error_enum_t r;
        unsigned int i;
        
        printf("; %s\n",buf);
        no_comments(buf);
        if (strlen(buf) == 0)
            continue;
        areq.dstate = *dstate;
        areq.command = buf;
        req = parse_encode_request(areq);
 
        r = xed_encode(&req, array, ilen, &olen);
        if (r != XED_ERROR_NONE)     {
            printf("Could not encode: %s\n", buf);
            printf("Error code was: %s\n", xed_error_enum_t2str(r));
            xedex_derror("Dying");
        }
        printf("      .byte ");
        for(i=0;i<olen;i++) {
            if (i > 0)
                printf(", ");
            printf("0x%02x",array[i]);
        }
        printf("\n");
    }
    fclose(f);
}
#endif

static void emit_version(void) {
    printf("%s\n", xed_get_copyright());
    printf("XED version: [%s]\n\n", xed_get_version());
}

static void usage(char* prog) {
    unsigned int i;
    static const char* usage_msg[] = {
      "One of the following is required:",
#if defined(__APPLE__)
      "\t-i input_file             (decode macho-format file)",
#elif defined(XED_ELF_READER)
      "\t-i input_file             (decode elf-format file)",
#elif defined(_WIN32)
      "\t-i input_file             (decode pecoff-format file)",
#endif
      "\t-ir raw_input_file        (decode a raw unformatted binary file)",
      "\t-ih hex_input_file        (decode a raw unformatted ASCII hex file)",
      "\t-d hex-string             (decode a sequence of bytes, must be last)",
      "\t-j                        (just decode one instruction when using -d)",
      "\t-F prefix                 (decode ascii hex bytes after prefix)",
      "\t                          (running in filter mode from stdin)",
#if defined(XED_ENCODER)
      "\t-ide input_file           (decode/encode file)",
      "\t-e instruction            (encode, must be last)",
      "\t-f                        (encode force, skip encoder chip check)",
      "\t-ie file-to-assemble      (assemble the contents of the file)",
      "\t-de hex-string            (decode-then-encode, must be last)",
#endif
      "",
      "Optional arguments:",
      "",
      "\t-v N          (0=quiet, 1=errors, 2=useful-info, 3=trace,",
      "\t               5=very verbose)",
      "\t-xv N         (XED engine verbosity, 0...99)",
      "",
      "\t-chip-check CHIP   (count instructions that are not valid for CHIP)",
      "\t-chip-check-list   (list the valid chips)",
      "",
      "\t-s section    (target section for file disassembly,",
      "\t               PECOFF and ELF formats only)",
      "",
      "\t-n N          (number of instructions to decode. Default 100M,",
      "\t               accepts K/M/G qualifiers)",
      " ",
      "\t-b addr       (Base address offset, for DLLs/shared libraries.",
      "\t               Use 0x for hex addresses)",
      "\t-as addr      (Address to start disassembling.",
      "\t               Use 0x for hex addresses)",
      "\t-ae addr      (Address to end   disassembling.",
      "\t               Use 0x for hex addresses)",
      "\t-no-resync    (Disable symbol-based resynchronization algorithm",
      "\t               for disassembly)",
      "\t-ast          (Show the AVX/SSE transition classfication)",
      "\t-histo        (Histogram decode times)",
      "",
      "\t-I            (Intel syntax for disassembly)",
      "\t-A            (ATT SYSV syntax for disassembly)",
      "\t-isa-set      (Emit the XED \"ISA set\" in dissasembly)",
      "\t-xml          (XML formatting)",
      "\t-uc           (upper case hex formatting)",
      "\t-pmd          (positive memory displacement formatting)",
      "\t-nwm          (Format AVX512 without curly braces for writemasks, include k0)",
      "\t-emit         (Output __emit statements for the Intel compiler)",
      "\t-S file       Read symbol table in \"nm\" format from file",
#if defined(XED_DWARF) 
      "\t-line         (Emit line number information, if present)",
#endif
      "\t-dot FN       (Emit a register dependence graph file in dot format.",
      "\t               Best used with -as ADDR -ae ADDR to limit graph size.)",
      "",
      "\t-r            (for REAL_16 mode, 16b addressing (20b addresses),",
      "\t               16b default data size)",
      "\t-r32          (for REAL_32 mode, 16b addressing (20b addresses),",
      "\t               32b default data size)",
      "\t-16           (for LEGACY_16 mode, 16b addressing,",
      "\t               16b default data size)",
      "\t-32           (for LEGACY_32 mode, 32b addressing,",
      "\t               32b default data size -- default)",
      "\t-64           (for LONG_64 mode w/64b addressing",
      "\t               Optional on windows/linux)",
#if defined(XED_MPX)
      "\t-mpx          (Turn on MPX mode for disassembly, default is off)",
#endif
#if defined(XED_CET)
      "\t-cet          (Turn on CET mode for disassembly, default is off)",
#endif
      "\t-s32          (32b stack addressing, default, not in LONG_64 mode)",
      "\t-s16          (16b stack addressing, not in LONG_64 mode)",
      "\t-set OP VAL   (Set a XED operand to some integer value)",

#if defined(XED_USING_DEBUG_HELP)
      "",
      "\t-sp           (Search path for windows symbols)",
#endif
      "\t-version      (The version message)",
      "\t-help         (This help message)",
      " ",
      0
    };      

    emit_version();
    printf("Usage: %s [options]\n", prog);
    for(i=0; usage_msg[i]  ; i++)
        printf("%s\n", usage_msg[i]);
}

 

static char const* remove_spaces(char const*  s) { //frees original string
    xed_uint32_t i=0,c=0;
    char* p=0;
    
    if (s == 0)
        return 0;
    
    while(s[i]) {
        if (s[i] != ' ')
            c++;
        i++;
    }
    c++; // add the null
    p = (char*)malloc(c);
    assert(p!=0);
    i=0;
    c=0;
    while(s[i]) {
        if (s[i] != ' ')
            p[c++] = s[i];
        i++;
    }
    p[c]=0;
    free((void*)s);

    return p;
}


static void
test_argc(int i, int argc)
{
    if (i+1 >= argc)
        xedex_derror("Need more arguments. Use \"xed -help\" for usage.");
}




static void list_chips(void)
{
    xed_chip_enum_t c = XED_CHIP_INVALID;
    int i=0;
    for( ; c < XED_CHIP_LAST;  i++ ) {
        if (i > 0 && (i % 3) == 0)
            printf("\n");
        printf("%-25s ", xed_chip_enum_t2str(c));
        c = (xed_chip_enum_t)(c + 1);
    }
    printf("\n");
}


int
main(int argc, char** argv)
{
    xed_bool_t sixty_four_bit = 0;
    xed_bool_t mpx_mode = 0;
    xed_bool_t cet_mode = 0;
    xed_bool_t decode_only = 1;
    char* input_file_name = 0;
    char* symbol_search_path = 0;
    char const* decode_text=0;
    char const* encode_text=0;
    xed_state_t dstate;
    xed_bool_t encode = 0;
    xed_bool_t encode_force = 0;
    xed_uint_t ninst = 100*1000*1000; // FIXME: should use maxint...
    //perf_tail is for skipping first insts in performance measure mode
    unsigned int perf_tail = 0;         
    xed_bool_t decode_encode = 0;
    int i,j;
    unsigned int loop_decode = 0;
    xed_bool_t decode_raw = 0;
    xed_bool_t decode_hex = 0;
    xed_bool_t assemble  = 0;
    char* target_section = 0;
    xed_bool_t use_binary_mode = 1;
    xed_bool_t emit_isa_set = 0;
    xed_uint64_t addr_start = 0;
    xed_uint64_t addr_end = 0;
    xed_uint64_t fake_base = 0;
    xed_bool_t xml_format =0;
    xed_bool_t resync = 0;
    xed_bool_t ast = 0;
    xed_bool_t histo = 0;
    xed_bool_t line_numbers = 0;
    xed_chip_enum_t xed_chip = XED_CHIP_INVALID;
    xed_operand_enum_t operand = XED_OPERAND_INVALID;
    xed_uint32_t operand_value = 0;
    xed_bool_t filter = 0;
    xed_bool_t just_decode_first_pattern=0;
#if defined(XED_LINUX)
    char *prefix = NULL;
#endif

    char* dot_output_file_name = 0;
    xed_bool_t dot = 0;
    xed_decoded_inst_t xedd;
    xed_uint_t retval_okay = 1;
    unsigned int obytes=0;
#if defined(XED_DECODER)
    xed_disas_info_t decode_info;
#endif
#if defined(XED_LINUX)
    char *nm_symtab_fn = NULL;
#endif
    
    /* I have this here to test the functionality, if you are happy with
     * the XED formatting options, then you do not need to set this or call
     * xed_format_set_options() */

    xed_format_options_t format_options;
    memset(&format_options,0,sizeof(xed_format_options_t));
#if defined(XED_NO_HEX_BEFORE_SYMBOLIC_NAMES)
    format_options.hex_address_before_symbolic_name=0;
#else
    format_options.hex_address_before_symbolic_name=1;
#endif
    format_options.write_mask_curly_k0 = 1;
    format_options.lowercase_hex = 1;    

    xed_example_utils_init();

    xed_state_init(&dstate,
                   XED_MACHINE_MODE_LEGACY_32,
                   XED_ADDRESS_WIDTH_32b,  /* 2nd parameter ignored */
                   XED_ADDRESS_WIDTH_32b);

    resync = 1;
    client_verbose = 3;
    xed_set_verbosity( client_verbose );
    for( i=1; i < argc ; i++ )    {
#if defined(XED_LINUX)
        if (strcmp(argv[i], "-F") == 0) {
            test_argc(i, argc);
            filter = 1;
            prefix = argv[++i];
            continue;
        } else if (strcmp(argv[i], "-S") == 0) {
            test_argc(i, argc);
            nm_symtab_fn = argv[++i];
            continue;
        }
#endif
        if (strcmp(argv[i], "-no-resync") ==0)   {
            resync = 0;
            continue;
        }
        if (strcmp(argv[i], "-ast") ==0)   {
            ast = 1;
            continue;
        }
        if (strcmp(argv[i], "-histo") ==0)   {
            histo = 1;
            continue;
        }
        else if (strcmp(argv[i],"-d")==0)         {
            test_argc(i,argc);
            for(j=i+1; j< argc;j++) 
                decode_text = xedex_append_string(decode_text,argv[j]);
            break; // leave the i=1...argc loop
        }
        else if (strcmp(argv[i],"-j")==0) {
            just_decode_first_pattern=1;
            continue;
        }
        else if (strcmp(argv[i],"-i")==0)        {
            test_argc(i,argc);
            input_file_name = argv[i+1];
            i++;
        }
#if defined(XED_USING_DEBUG_HELP)
        else if (strcmp(argv[i],"-sp")==0)        {
            test_argc(i,argc);
            symbol_search_path = argv[i+1];
            i++;
        }
#endif
        else if (strcmp(argv[i],"-s")==0)        {
            test_argc(i,argc);
            target_section = argv[i+1];
            i++;
        }
        else if (strcmp(argv[i],"-xml")==0)      {
            format_options.xml_a = 1;
            format_options.xml_f = 1;
            xml_format = 1;
        }
        else if (strcmp(argv[i],"-pmd")==0)      {
             format_options.positive_memory_displacements=1;
        }
        else if (strcmp(argv[i],"-uc")==0)      {
            format_options.lowercase_hex = 0; // use uppercase hex
        }
        else if (strcmp(argv[i],"-nwm")==0)      {
            format_options.write_mask_curly_k0 = 0;
        }
#if defined(XED_DWARF) 
        else if (strcmp(argv[i],"-line")==0)      {
            line_numbers = 1;
        }
#endif
        else if (strcmp(argv[i],"-dot")==0)      {
            test_argc(i,argc);
            dot_output_file_name = argv[i+1];
            dot = 1;
            i++;
        }
        else if (strcmp(argv[i],"-ir")==0)        {
            test_argc(i,argc);
            input_file_name = argv[i+1];
            decode_raw = 1;
            i++;
        }
        else if (strcmp(argv[i],"-ih")==0)        {
            test_argc(i,argc);
            input_file_name = argv[i+1];
            decode_hex = 1;
            i++;
        }
#if defined(XED_ENCODER)
        else if (strcmp(argv[i],"-f") == 0) {
            encode_force = 1;
            continue;
        }
        else if (strcmp(argv[i],"-e") == 0) {
            encode = 1;
            test_argc(i,argc);
            // merge the rest of the args in to the encode_text string.
            for( j = i+1; j< argc; j++ )  {
                encode_text = xedex_append_string(encode_text, argv[j]);
                encode_text = xedex_append_string(encode_text, " ");
            }
            break;  // leave the loop
        }
        else if (strcmp(argv[i],"-de")==0)        {
            test_argc(i,argc);
            decode_encode = 1;
            for(j=i+1; j< argc;j++) 
                decode_text = xedex_append_string(decode_text,argv[j]);
            break; // leave the i=1...argc loop
        }
        else if (strcmp(argv[i],"-ie")==0)        {
            test_argc(i,argc);
            input_file_name = argv[i+1];
            assemble = 1;
            i++;
        }
        else if (strcmp(argv[i],"-ide")==0)        {
            test_argc(i,argc);
            input_file_name = argv[i+1];
            decode_only = 0;
            i++;
        }
#endif
        else if (strcmp(argv[i],"-n") ==0)         {
            test_argc(i,argc);
            ninst = XED_STATIC_CAST(xed_uint_t,
                xed_atoi_general(argv[i+1],1000));
            i++;
        }
        else if (strcmp(argv[i],"-perftail") ==0)         {
            // undocumented. not an interesting knob for most users.
            test_argc(i,argc);
            perf_tail = XED_STATIC_CAST(unsigned int,
                xed_atoi_general(argv[i+1],1000));
            i++;
        }
        else if (strcmp(argv[i],"-b") ==0)         {
            test_argc(i,argc);
            fake_base = (xed_uint64_t)xed_atoi_general(argv[i+1],1000);
            printf("ASSUMED BASE = " XED_FMT_LX "\n",fake_base);
            i++;
        }
        else if (strcmp(argv[i],"-as") == 0 || strcmp(argv[i],"-sa") == 0)    {
            test_argc(i,argc);
            addr_start = XED_STATIC_CAST(xed_uint64_t,
                                         xed_atoi_general(argv[i+1],1000));
            i++;
        }
        else if (strcmp(argv[i],"-ae") == 0 || strcmp(argv[i],"-ea") == 0)    {
            test_argc(i,argc);
            addr_end = XED_STATIC_CAST(xed_uint64_t,
                                       xed_atoi_general(argv[i+1],1000));
            i++;
        }

        else if (strcmp(argv[i],"-loop") ==0)         {
            test_argc(i,argc);
            loop_decode = XED_STATIC_CAST(unsigned int,
                                          xed_atoi_general(argv[i+1],1000));
            i++;
        }
        else if (strcmp(argv[i],"-v") ==0)         {
            test_argc(i,argc);
            client_verbose = XED_STATIC_CAST(int,xed_atoi_general(argv[i+1],1000));
            xed_set_verbosity(client_verbose);

            i++;
        }
        else if (strcmp(argv[i],"-xv") ==0)        {
            int xed_engine_verbose;
            test_argc(i,argc);
            xed_engine_verbose = XED_STATIC_CAST(xed_int_t,
                                                 xed_atoi_general(argv[i+1],1000));
            xed_set_verbosity(xed_engine_verbose);
            i++;
        }
        else if (strcmp(argv[i],"-chip-check")==0)        {
            test_argc(i,argc);
            xed_chip = str2xed_chip_enum_t(argv[i+1]);
            printf("Setting chip to %s\n", xed_chip_enum_t2str(xed_chip));
            if (xed_chip == XED_CHIP_INVALID) {
                printf("Invalid chip name specified. Use -chip-check-list to "
                       "see the valid chip names.\n");
                exit(1);
            }
            i++;
        }
        else if (strcmp(argv[i],"-chip-check-list")==0)        {
            list_chips();
            exit(0);
        }
        else if (strcmp(argv[i],"-A")==0)        {
            global_syntax = XED_SYNTAX_ATT;
        }
        else if (strcmp(argv[i],"-I")==0)        {
            global_syntax = XED_SYNTAX_INTEL;
        }
        else if (strcmp(argv[i],"-X")==0)        { // undocumented
            global_syntax = XED_SYNTAX_XED;
        }
        else if (strcmp(argv[i],"-isa-set")==0)   {
            emit_isa_set = 1;
        }
        else if (strcmp(argv[i],"-r32")==0)         {
            sixty_four_bit = 0;
            dstate.mmode = XED_MACHINE_MODE_REAL_32;
            dstate.stack_addr_width = XED_ADDRESS_WIDTH_16b;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-r")==0)         {
            sixty_four_bit = 0;
            dstate.mmode = XED_MACHINE_MODE_REAL_16;
            dstate.stack_addr_width = XED_ADDRESS_WIDTH_16b;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-16")==0)         {
            sixty_four_bit = 0;
            dstate.mmode = XED_MACHINE_MODE_LEGACY_16;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-32")==0) { // default
            sixty_four_bit = 0;
            dstate.mmode = XED_MACHINE_MODE_LEGACY_32;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-64")==0)         {
            sixty_four_bit = 1;
            dstate.mmode = XED_MACHINE_MODE_LONG_64;
            use_binary_mode = 0;
        }
#if defined(XED_MPX)
        else if (strcmp(argv[i],"-mpx")==0)         {
            mpx_mode = 1;
        }
#endif
#if defined(XED_CET)
        else if (strcmp(argv[i],"-cet")==0)         {
            cet_mode = 1;
        }
#endif
        else if (strcmp(argv[i],"-s32")==0) {
            dstate.stack_addr_width = XED_ADDRESS_WIDTH_32b;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-s16")==0) {
            dstate.stack_addr_width = XED_ADDRESS_WIDTH_16b;
            use_binary_mode = 0;
        }
        else if (strcmp(argv[i],"-set")==0) {
            test_argc(i+1,argc); // need 2 args
            operand = str2xed_operand_enum_t(argv[i+1]);
            operand_value = XED_STATIC_CAST(xed_uint32_t,
                                            xed_atoi_general(argv[i+2],1000));
            i += 2;
        }
#if 0
        else if (strcmp(argv[i],"-ti") ==0)        {
            client_verbose = 5;
            xed_set_verbosity(5);
            test_immdis();
            exit(1);
        }
#endif
        else if (strcmp(argv[i],"-emit") ==0) {
            intel_asm_emit = 1;
        }
        else if (strcmp(argv[i],"-version") == 0 ) {
            emit_version();
            exit(0);
        }
        else   {
            usage(argv[0]);
            exit(1);
        }
    }
    if (!encode)     {
        if (input_file_name == 0 &&
            (decode_text == 0 ||
             strlen(decode_text) == 0) && !filter)
        {
            printf("ERROR: required argument(s) were missing\n");
            usage(argv[0]);
            exit(1);
        }
    }

#if defined(XED_LINUX)
    if (nm_symtab_fn) {
        if (!filter) {
            printf("ERROR: -S only support with -F for now\n");
            exit(1);
        }
        xed_read_nm_symtab(nm_symtab_fn);
    }
#endif

    if (CLIENT_VERBOSE2)
        printf("Initializing XED tables...\n");

    xed_tables_init();

    if (CLIENT_VERBOSE2)
        printf("Done initialing XED tables.\n");

    if (decode_text) {
        decode_text = remove_spaces(decode_text);
        assert(decode_text);
    }
    
#if defined(XED_DECODER)
    xed_format_set_options(format_options);
#endif

    if (CLIENT_VERBOSE1) 
        printf("#XED version: [%s]\n", xed_get_version());

    retval_okay = 1;
    obytes=0;

#if defined(XED_DECODER)
    xed_disas_info_init(&decode_info);
    decode_info.input_file_name  = input_file_name;
    decode_info.symbol_search_path = symbol_search_path;
    decode_info.dstate           = dstate;
    decode_info.ninst            = ninst;
    decode_info.decode_only      = decode_only;
    decode_info.sixty_four_bit   = sixty_four_bit;
    decode_info.target_section   = target_section;
    decode_info.use_binary_mode  = use_binary_mode;
    decode_info.addr_start       = addr_start;
    decode_info.addr_end         = addr_end;
    decode_info.xml_format       = xml_format;
    decode_info.fake_base        = fake_base;
    decode_info.resync           = resync;
    decode_info.line_numbers     = line_numbers;
    decode_info.perf_tail_start  = perf_tail;
    decode_info.ast              = ast;
    decode_info.histo            = histo;
    decode_info.chip             = xed_chip;
    decode_info.mpx_mode         = mpx_mode;
    decode_info.cet_mode         = cet_mode;
    decode_info.emit_isa_set     = emit_isa_set;
    decode_info.format_options   = format_options;
    decode_info.operand          = operand;
    decode_info.operand_value    = operand_value;
    decode_info.encode_force     = encode_force;
    
    if (dot)
    {
        decode_info.dot_graph_output = fopen_portable(dot_output_file_name,"w");
        if (!decode_info.dot_graph_output) {
            printf("Could not open %s\n", dot_output_file_name);
            xedex_derror("Dying");
        }
    }
    
    init_xedd(&xedd, &decode_info);
    
#endif

#if defined(XED_LINUX)
    if (filter)
    {
#if defined(XED_DECODER)
        retval_okay = disas_filter(&xedd, prefix, &decode_info);
#endif
    } else
#endif

    if (assemble)
    {
#if defined(XED_ENCODER)
        xed_assemble(&dstate, input_file_name);
#endif
    }
    else if (decode_encode)
    {
#if defined(XED_DECODER) && defined(XED_ENCODER)
        assert(decode_text);
        obytes = disas_decode_encode(&decode_info,
                                     decode_text,
                                     &xedd,
                                     fake_base);
#endif
        retval_okay = (obytes != 0) ? 1 : 0;
    }
    else if (encode)
    {
#if defined(XED_ENCODER)
        assert(encode_text != 0);
        obytes = disas_encode(&dstate,
                              encode_text,
                              operand,
                              operand_value,
                              encode_force);
#endif
    }
    else if (decode_text && strlen(decode_text) != 0)
    {
#if defined(XED_DECODER)
        if (loop_decode)
        {
            unsigned int k;
            for(k=0;k<loop_decode;k++) {
                retval_okay = disas_decode(&decode_info,
                                           decode_text,
                                           &xedd,
                                           fake_base);
                init_xedd(&xedd, &decode_info);
            }
        }
        else
        {
            char const* p = decode_text;
            // 2 bytes per nibble
            unsigned int remaining = (unsigned int)strlen(decode_text) / 2; 
            do {
                unsigned int len;
                retval_okay = disas_decode(&decode_info, p, &xedd, fake_base);
                len = xed_decoded_inst_get_length(&xedd);
                p+=len*2;
                if (len < remaining) {
                    remaining -= len;
                    init_xedd(&xedd, &decode_info);
                }
                else {
                    remaining = 0;
                }
            }
            while(just_decode_first_pattern==0 && retval_okay && remaining > 0);
        }
#endif
    }
    else
    {
#if defined(XED_DECODER)
        if (xml_format) {
            printf("<?xml version=\"1.0\"?>\n");
            printf("<XEDDISASM>\n");
            printf("<XEDFORMAT>1</XEDFORMAT>\n");
        }
        if (decode_raw) {
            xed_disas_raw(&decode_info);
        }
        else if (decode_hex) {
            xed_disas_hex(&decode_info);
        }
        else
        {
#if defined(__APPLE__)
            xed_disas_macho(&decode_info);
#elif defined(XED_ELF_READER)
            xed_disas_elf(&decode_info);
#elif defined(_WIN32)
            xed_disas_pecoff(&decode_info);
#else
            xedex_derror("No PECOFF, ELF or MACHO support compiled in");
#endif
            printf("# Total Errors: " XED_FMT_LU "\n", decode_info.errors);
            if (decode_info.chip)
                printf("# Total Chip Check Errors: " XED_FMT_LU "\n",
                       decode_info.errors_chip_check);
        }
#endif // XED_DECODER
    }
    
    if (xml_format) 
        printf("</XEDDISASM>\n");


    if (retval_okay==0) 
        exit(1);
    return 0;
    (void) obytes;
    (void) encode_text;
#if !defined(XED_DECODER)
    // pacify the compiler for encoder-only builds:
    (void) xedd;
    (void) sixty_four_bit;
    (void) decode_only;
    (void) symbol_search_path;
    (void) ninst;
    (void) perf_tail;
    (void) loop_decode;
    (void) decode_raw;
    (void) decode_hex;
    (void) target_section;
    (void) addr_start;
    (void) addr_end;
    (void) resync;
    (void) ast;
    (void) histo;
    (void) line_numbers;
    (void) dot_output_file_name;
    (void) dot;
    (void) use_binary_mode;
    (void) emit_isa_set;
#endif
}
 

////////////////////////////////////////////////////////////////////////////
