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

#include <assert.h>
#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include "xed-symbol-table.h"

//////////////////////////////////////////////////////////////////////
void xed_local_symbol_table_init(xed_local_symbol_table_t* p)
{
    avl_tree_init(&p->atree);
}

void xed_symbol_table_init(xed_symbol_table_t* p) {
    p->curtab = 0;
    xed_local_symbol_table_init(&p->gtab);
    avl_tree_init(&p->avl_lmap);
}

xed_local_symbol_table_t* xst_get_local_map(xed_symbol_table_t* p,
                                            xed_uint32_t section)
{
        xed_local_symbol_table_t* v =
            (xed_local_symbol_table_t*) avl_find(&p->avl_lmap, section);
        return v;
}

xed_local_symbol_table_t* xst_make_local_map(xed_symbol_table_t* p,
                                             xed_uint32_t section)
{
    xed_local_symbol_table_t* n =
        (xed_local_symbol_table_t*) malloc(sizeof(xed_local_symbol_table_t));
    assert(n!=0);
    xed_local_symbol_table_init(n);
    avl_insert(&p->avl_lmap, section, n, 0);
    return n;
}
    
void xst_set_current_table(xed_symbol_table_t* p,
                           xed_uint32_t section)
{
    p->curtab = xst_get_local_map(p,section);
}

void xst_add_local_symbol(xed_symbol_table_t* p,
                          xed_uint64_t addr, char* name,
                          xed_uint32_t section)
{
    xed_local_symbol_table_t* ltab = xst_get_local_map(p,section);
    if (ltab == 0) 
        ltab = xst_make_local_map(p,section);
    avl_insert(&ltab->atree,addr, name, 0);
}

void xst_add_global_symbol(xed_symbol_table_t* p,
                           xed_uint64_t addr, char* name) {
    avl_insert(&p->gtab.atree,addr, name, 0);
}



//////////////////////////////////////////////////////////////////////
static xed_bool_t
find_symbol_address(xed_local_symbol_table_t* ltab,
                    xed_uint64_t tgt,
                    xed_uint64_t* sym_addr)
{
    uint64_t lbkey=0;
    void* sym = avl_find_lower_bound(&ltab->atree, tgt, &lbkey);
    if (sym) {
        *sym_addr = lbkey;
        return 1;
    }
    return 0;
}

static xed_bool_t
find_symbol_address_global(xed_uint64_t tgt,
                           xed_symbol_table_t* symbol_table,
                           xed_uint64_t* sym_addr) /* output*/
{
    xed_bool_t r = 0;
    if (symbol_table) {
        /* look global and then local */
        r = find_symbol_address(&symbol_table->gtab, tgt, sym_addr);
        if (r == 0 && symbol_table->curtab) {
            r = find_symbol_address(symbol_table->curtab, tgt, sym_addr);
        }
    }
    return r;
}


char* get_symbol(xed_uint64_t a, void* caller_data) {
    xed_symbol_table_t* symbol_table = (xed_symbol_table_t*)caller_data;
    /* look in the global symbol table  first */
    char* name = (char*)avl_find(&symbol_table->gtab.atree, a);
    if (name)
        return name;
    /* look in the local symbol table if present */
    if (symbol_table->curtab) {
        name = (char*)avl_find(&symbol_table->curtab->atree, a);
        return name;
    }
    return 0;
}


int xed_disassembly_callback_function(
    xed_uint64_t address,
    char* symbol_buffer,
    xed_uint32_t buffer_length,
    xed_uint64_t* offset,
    void* caller_data) 
{
    xed_uint64_t symbol_address;
    xed_symbol_table_t* symbol_table = (xed_symbol_table_t*)caller_data;
    xed_bool_t found = find_symbol_address_global(address, 
                                                  symbol_table, 
                                                  &symbol_address);
    if (found) {
        char* symbol  = get_symbol(symbol_address, caller_data);
        if (symbol) {
            if (xed_strlen(symbol) < buffer_length)
                xed_strncpy(symbol_buffer, symbol, (int)buffer_length);
            else {
                xed_strncpy(symbol_buffer, symbol, (int)(buffer_length-1));
                symbol_buffer[buffer_length-1]=0;
            }
            *offset = address - symbol_address;
            return 1;
        }
    }
    return 0;
}
