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

#if !defined(XED_DOT_PREP_H)
# define XED_DOT_PREP_H
#include "xed/xed-interface.h"
#include "xed-dot.h"

typedef struct {
    xed_syntax_enum_t syntax;
    xed_dot_graph_t* g;
    
    // node that is last writer of the register
    xed_dot_node_t* xed_reg_to_node[XED_REG_LAST];
    
    xed_dot_node_t* start;
} xed_dot_graph_supp_t;

xed_dot_graph_supp_t* xed_dot_graph_supp_create(
    xed_syntax_enum_t arg_syntax);

void xed_dot_graph_supp_deallocate(
    xed_dot_graph_supp_t* gg);

void xed_dot_graph_add_instruction(
    xed_dot_graph_supp_t* gg,
    xed_decoded_inst_t* xedd,
    xed_uint64_t runtime_instr_addr,
    void* caller_data,
    xed_disassembly_callback_fn_t disas_symbol_cb);

void xed_dot_graph_dump(
    FILE* f,
    xed_dot_graph_supp_t* gg);

#endif
