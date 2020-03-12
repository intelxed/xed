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
#if !defined(XED_DOT_H)
# define XED_DOT_H

#include "xed/xed-interface.h"
#include <stdio.h>

typedef struct xed_dot_node_s {
    char* name;
    struct xed_dot_node_s* next;
} xed_dot_node_t;

typedef enum {
    XED_DOT_EDGE_SOLID,
    XED_DOT_EDGE_DASHED,
    XED_DOT_EDGE_DOTTED
} xed_dot_edge_style_t;


typedef struct xed_dot_edge_s {
    xed_dot_node_t* src;
    xed_dot_node_t* dst;
    xed_dot_edge_style_t style;
    struct xed_dot_edge_s* next;
} xed_dot_edge_t;

typedef struct {
    xed_dot_edge_t* edges;
    xed_dot_node_t* nodes;
} xed_dot_graph_t;


xed_dot_graph_t* xed_dot_graph(void);
void xed_dot_graph_deallocate(xed_dot_graph_t* gg);

xed_dot_node_t* xed_dot_node(xed_dot_graph_t* g,
                             char const* const name);

void xed_dot_edge(xed_dot_graph_t* g,
                  xed_dot_node_t* src,
                  xed_dot_node_t* dst,
                  xed_dot_edge_style_t style);

void xed_dot_dump(FILE* f, xed_dot_graph_t* g);
#endif
