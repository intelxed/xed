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
/// @file xed-examples-util.h


#ifndef XED_EXAMPLES_UTIL_H
# define XED_EXAMPLES_UTIL_H

#include <stdio.h>
#include "xed/xed-interface.h"

extern xed_syntax_enum_t global_syntax;
extern int client_verbose;

#define CLIENT_VERBOSE  (client_verbose > 1)
#define CLIENT_VERBOSE0 (client_verbose > 2)
#define CLIENT_VERBOSE1 (client_verbose > 3)
#define CLIENT_VERBOSE2 (client_verbose > 4)
#define CLIENT_VERBOSE3 (client_verbose > 5)

char* xed_upcase_buf(char* s);

/// Accepts K / M / G (or B) qualifiers ot multiply
xed_int64_t xed_atoi_general(char* buf, int mul);
xed_int64_t xed_atoi_hex(char* buf);

/// Converts "112233" in to 0x112233
xed_uint64_t convert_ascii_hex_to_int(const char* s);


unsigned int xed_convert_ascii_to_hex(const char* src, 
                                      xed_uint8_t* dst, 
                                      unsigned int max_bytes);

#define XED_HEX_BUFLEN 200
void xed_print_hex_line(char* buf,
                        const xed_uint8_t* array,
                        const unsigned int length, 
                        const unsigned int buflen); 

void XED_NORETURN xedex_derror(const char* s);
void xedex_dwarn(const char* s);

//////////////////////////////////////////////////////////////////////


typedef struct {
    xed_state_t dstate;
    xed_uint_t ninst;
    xed_bool_t decode_only;
    xed_bool_t sixty_four_bit;
    xed_bool_t mpx_mode;
    xed_bool_t cet_mode;
    char* input_file_name;
    char* symbol_search_path;     // for dbghelp symbol caches
    char* target_section;
    xed_bool_t use_binary_mode; 
    xed_uint64_t addr_start;
    xed_uint64_t addr_end;
    xed_bool_t xml_format;
    xed_uint64_t fake_base;
    xed_bool_t resync; /* turn on/off symbol-based resynchronization */
    xed_bool_t line_numbers; /* control for printing file/line info */
    FILE* dot_graph_output;
    unsigned int perf_tail_start;
    xed_bool_t ast;
    xed_bool_t histo;
    xed_chip_enum_t chip;
    xed_bool_t emit_isa_set;    
    xed_format_options_t format_options;
    xed_operand_enum_t operand;
    xed_uint32_t operand_value;
    xed_bool_t encode_force;
    
    xed_uint64_t errors;
    xed_uint64_t errors_chip_check;
    
    unsigned char* s; // start of image
    unsigned char* a; // start of instructions to decode region
    unsigned char* q; // end of region
    // where this region would live at runtime
    xed_uint64_t runtime_vaddr;
    // where to start in program space, if not zero
    xed_uint64_t runtime_vaddr_disas_start;

    // where to stop in program space, if not zero
    xed_uint64_t runtime_vaddr_disas_end; 

    // a function to convert addresses to symbols
    char* (*symfn)(xed_uint64_t, void*); 
    void* caller_symbol_data;

    void (*line_number_info_fn)(xed_uint64_t addr);

} xed_disas_info_t;

void xed_disas_info_init(xed_disas_info_t* p);

void xed_map_region(const char* path,
                    void** start,
                    unsigned int* length);



void xed_disas_test(xed_disas_info_t* di);



// returns 1 on success, 0 on failure
xed_uint_t disas_decode_binary(xed_disas_info_t* di,
                               const xed_uint8_t* hex_decode_text,
                               const unsigned int bytes,
                               xed_decoded_inst_t* xedd,
                               xed_uint64_t runtime_address);

// returns encode length on success, 0 on failure
xed_uint_t disas_decode_encode_binary(xed_disas_info_t* di,
                                      const xed_uint8_t* decode_text_binary,
                                      const unsigned int bytes,
                                      xed_decoded_inst_t* xedd,
                                      xed_uint64_t runtime_address);


void xed_print_decode_stats(xed_disas_info_t* di);
void xed_print_encode_stats(xed_disas_info_t* di);

void xed_register_disassembly_callback(
                 xed_disassembly_callback_fn_t f);


void disassemble(xed_disas_info_t* di,
                 char* buf,
                 int buflen,
                 xed_decoded_inst_t* xedd,
                 xed_uint64_t runtime_instruction_address,
                 void* caller_data);

// 64b version missing on some MS compilers so I wrap it for portability.
// This function is rather limited and only handles base 10 and base 16.
xed_int64_t xed_strtoll(const char* buf, int base);

char* xed_strdup(char const*  const src);

void xed_example_utils_init(void);

void init_xedd(xed_decoded_inst_t* xedd,
               xed_disas_info_t* di);

char const* xedex_append_string(char const* p, // p is free()'d
                                char const* x);

typedef struct xed_str_list_s {
    char* s;
    struct xed_str_list_s* next;
} xed_str_list_t;

xed_str_list_t* xed_tokenize(char const* const p, char const* const sep);
xed_uint_t xed_str_list_size(xed_str_list_t* p); // counts chunks

void xed_print_intel_asm_emit(const xed_uint8_t* array, unsigned int olen);
void xed_print_bytes_pseudo_op(const xed_uint8_t* array, unsigned int olen);
#endif // file
