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

#include <stdint.h>
#include <stdarg.h>

#include "xed/xed-interface.h"

typedef struct slist_s {
    char* s;
    struct slist_s* next;
} slist_t;

typedef enum {
    OPND_INVALID,
    OPND_REG,
    OPND_IMM, /* Literal that corresponds to immediate or displacement */
    OPND_MEM,
    OPND_DECORATOR,
    OPND_FARPTR
} opnd_type_t;

typedef struct {
    unsigned int len;
    char* seg;
    char* base;
    char* index;
    char* disp;
    int64_t ndisp; // disp converted to a number
    char* scale;
    unsigned int nscale; // 0(invalid), 1,2,4,8
    int minus;
    char const* mem_size;  // NOT allocated; do not free. Pointer to static string
    uint32_t mem_bits;  // mem_size converted to bits
} memparse_rec_t;

typedef struct {
    char* seg;
    char* offset;
    int64_t seg_value;
    int64_t offset_value;
} farptr_rec_t;

typedef struct opnd_list_s {
    char* s;
    opnd_type_t type;
    memparse_rec_t mem;
    farptr_rec_t farptr;
    slist_t* decorators;
    int64_t imm;
    xed_reg_enum_t reg;
    struct opnd_list_s* next;
} opnd_list_t;


typedef struct {
    char* input;
    int valid;
    int mode; // 16/32/64
    char* iclass_str;
    xed_iclass_enum_t iclass_e;
    slist_t* prefixes; // reversed
    slist_t* operands; // reversed
    opnd_list_t* opnds;

    /* parsing state used to resolve ambiguous cases */
    xed_bool_t seen_repe;
    xed_bool_t seen_repne;
    xed_bool_t seen_lock;
    xed_bool_t seen_cr;
    xed_bool_t seen_dr;
    xed_bool_t seen_far_ptr;
    int deduced_vector_length;
} xed_enc_line_parsed_t;

void asp_set_verbosity(int v);
void asp_error_printf(const char* format, ...);
void asp_printf(const char* format, ...);
void asp_dbg_printf(const char* format, ...);

xed_enc_line_parsed_t* asp_get_xed_enc_node(void);
void asp_delete_xed_enc_line_parsed_t(xed_enc_line_parsed_t* v);
void asp_parse_line(xed_enc_line_parsed_t* v);
void asp_print_parsed_line(xed_enc_line_parsed_t* v);


