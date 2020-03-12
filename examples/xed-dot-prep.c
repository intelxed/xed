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

#include "xed-dot-prep.h"
#include <string.h>
#include <assert.h>
#include <stdlib.h>

/* each write replaces the last node for that input */


xed_dot_graph_supp_t* xed_dot_graph_supp_create(
    xed_syntax_enum_t arg_syntax)
{
    xed_dot_graph_supp_t* gs = 0;
    
    gs = (xed_dot_graph_supp_t*)malloc(sizeof(xed_dot_graph_supp_t));
    assert( gs != 0 );
    gs->g = xed_dot_graph();
    gs->syntax = arg_syntax;
    memset(gs->xed_reg_to_node,
           0,
           sizeof(xed_dot_node_t*)*XED_REG_LAST);
    
    gs->start = xed_dot_node(gs->g, "start");
    return gs;
}

void xed_dot_graph_supp_deallocate(xed_dot_graph_supp_t* gg)
{
    if (!gg)
        return;
    xed_dot_graph_deallocate(gg->g);
}


static xed_bool_t add_edge(xed_dot_graph_supp_t* gg,
                           xed_dot_node_t* n,
                           xed_reg_enum_t r,
                           xed_dot_edge_style_t s)
{
    xed_reg_enum_t r_enclosing;
    xed_bool_t found = 0;
    xed_dot_node_t* src = 0;
    /* add edge to n */
    r_enclosing = xed_get_largest_enclosing_register(r);
    src = gg->xed_reg_to_node[r_enclosing];
    if (src) {
        xed_dot_edge(gg->g,src,n,s);
        found = 1;
    }
    return found;
}

static void add_read_operands(xed_dot_graph_supp_t* gg,
                              xed_decoded_inst_t* xedd,
                              xed_dot_node_t* n)
{
    xed_uint_t i, noperands;
    xed_reg_enum_t r;
    const xed_inst_t* xi =  0;
    xed_bool_t found = 0;
    xi = xed_decoded_inst_inst(xedd);
    noperands = xed_inst_noperands(xi);
    
    for( i=0; i < noperands ; i++) {
        const unsigned int no_memop = 99;
        unsigned int memop = no_memop;
        const xed_operand_t* op = xed_inst_operand(xi,i);
        xed_operand_enum_t opname = xed_operand_name(op);
        if (xed_operand_is_register(opname) ||
            xed_operand_is_memory_addressing_register(opname)) {

             if (xed_operand_read(op)) {
                 /* add edge to n */
                 r = xed_decoded_inst_get_reg(xedd, opname);
                 found |= add_edge(gg, n, r, XED_DOT_EDGE_SOLID);
             }
             continue;
        }
        if (opname == XED_OPERAND_MEM0) 
            memop = 0;
        else if (opname == XED_OPERAND_MEM1 ) 
            memop = 1;

        if (memop != no_memop) {
            /* get reads of base/index regs,  if any */
            xed_reg_enum_t base, indx;
            
            base = xed_decoded_inst_get_base_reg(xedd,memop);
            indx = xed_decoded_inst_get_index_reg(xedd,memop);
            if (base != XED_REG_INVALID) 
                found |= add_edge(gg, n, base, XED_DOT_EDGE_SOLID);

            indx = xed_decoded_inst_get_index_reg(xedd,memop);
            if (indx != XED_REG_INVALID) 
                found |= add_edge(gg, n, indx, XED_DOT_EDGE_SOLID);
        }
    } /* for */
    if (!found) {
        /* add an edge from start */
        xed_dot_edge(gg->g, gg->start, n, XED_DOT_EDGE_SOLID);
    }
}

static void add_write_operands(xed_dot_graph_supp_t* gg,
                               xed_decoded_inst_t* xedd,
                               xed_dot_node_t* n)
{
    xed_uint_t i, noperands;
    xed_reg_enum_t r, r_enclosing;
    const xed_inst_t* xi =  0; 
    xi = xed_decoded_inst_inst(xedd);
    noperands = xed_inst_noperands(xi);

    for( i=0; i < noperands ; i++) {
        const xed_operand_t* op = xed_inst_operand(xi,i);
        xed_operand_enum_t opname = xed_operand_name(op);
        if (xed_operand_is_register(opname) ||
            xed_operand_is_memory_addressing_register(opname)) {

             if (xed_operand_written(op)) {
                 /* set n as the source of the value. */
                 /* ignoring partial writes */
                 r = xed_decoded_inst_get_reg(xedd, opname);

                 /* output dependences */
                 (void) add_edge(gg,n,r,XED_DOT_EDGE_DASHED);
                 
                 r_enclosing = xed_get_largest_enclosing_register(r);
                 gg->xed_reg_to_node[r_enclosing] = n;
             }
        }
    } /* for */
}


#define XED_DOT_TMP_BUF_LEN (1024U)

void xed_dot_graph_add_instruction(
    xed_dot_graph_supp_t* gg,
    xed_decoded_inst_t* xedd,
    xed_uint64_t runtime_instr_addr,
    void* caller_data,
    xed_disassembly_callback_fn_t disas_symbol_cb)
{
    /*
      make a new node
      
      for each operand:
        if read:
          make edge from src node for that reg to the new node
      for each operand:
        if write:
          install this node as the writer

      what about partial writes?
      what about register nesting?
     */
    char disasm_str[XED_DOT_TMP_BUF_LEN];
    char* p = 0;
    size_t alen = 0;
    int ok;
    xed_bool_t ok2;
    xed_dot_node_t* n = 0;
    xed_uint32_t remaining_buffer_bytes = XED_DOT_TMP_BUF_LEN;
    
    // put addr on separate line in node label
#if defined(XED_WINDOWS) && !defined(PIN_CRT)
    ok = sprintf_s(disasm_str,
                   XED_DOT_TMP_BUF_LEN,
                   XED_FMT_LX "\\n",
                   runtime_instr_addr);
#else
    ok = sprintf(disasm_str,
                 XED_FMT_LX "\\n",
                 runtime_instr_addr);

#endif
    assert(ok > 0);
    alen = strlen(disasm_str);
    p = disasm_str + alen;
    remaining_buffer_bytes -= XED_CAST(xed_uint32_t, alen);

    ok2 = xed_format_context(gg->syntax,
                            xedd, 
                            p,
                             (int)remaining_buffer_bytes,
                            runtime_instr_addr,
                            caller_data,
                            disas_symbol_cb);
    if (!ok2) {
        (void)xed_strncpy(disasm_str,"???", XED_DOT_TMP_BUF_LEN);
    }
    
    n = xed_dot_node(gg->g, disasm_str);
    add_read_operands(gg,xedd,n);
    add_write_operands(gg,xedd,n);    
}

void xed_dot_graph_dump(
    FILE* f,
    xed_dot_graph_supp_t* gg)
{
    xed_dot_dump(f, gg->g);
}
