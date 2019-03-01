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

#if !defined(XED_SYMBOL_TABLE_H)
#define XED_SYMBOL_TABLE_H

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include "avltree.h"
#include <stdlib.h>

typedef struct  {
    avl_tree_t atree;
} xed_local_symbol_table_t;

void xed_local_symbol_table_init(xed_local_symbol_table_t* p);

typedef struct  {
    xed_local_symbol_table_t gtab;
    /* section number maps to a local symbol table */
    avl_tree_t avl_lmap;
    /* the symbol table for the current section */
    xed_local_symbol_table_t* curtab;

} xed_symbol_table_t;

void xed_symbol_table_init(xed_symbol_table_t* p);

xed_local_symbol_table_t* xst_get_local_map(xed_symbol_table_t* p,
                                            xed_uint32_t section);

xed_local_symbol_table_t* xst_make_local_map(xed_symbol_table_t* p,
                                             xed_uint32_t section);
    
void xst_set_current_table(xed_symbol_table_t* p,
                           xed_uint32_t section);

void xst_add_local_symbol(xed_symbol_table_t* p,
                          xed_uint64_t addr, char* name,
                          xed_uint32_t section);

void xst_add_global_symbol(xed_symbol_table_t* p,
                           xed_uint64_t addr, char* name);

////////////////////////////////////////////////////////////////

char* get_symbol(xed_uint64_t a, void* symbol_table);

int xed_disassembly_callback_function(
    xed_uint64_t address,
    char* symbol_buffer,
    xed_uint32_t buffer_length,
    xed_uint64_t* offset,
    void* caller_data);
#endif
