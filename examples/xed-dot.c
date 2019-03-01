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
/*
  take xed_decoded_inst_t* and add it to a graph.
  The input operands are input edges.
  The output operands are output edges.
  Careful with "special" operands in new technologies
 */

#include "xed-dot.h"
#include "xed-examples-util.h"
#include <assert.h>
#include <stdlib.h>

xed_dot_graph_t* xed_dot_graph(void) {
    xed_dot_graph_t* g = 0;
    g = (xed_dot_graph_t*)malloc(sizeof(xed_dot_graph_t));
    assert(g != 0);
    g->edges = 0;
    g->nodes = 0;
    return g;
}
static void delete_nodes(xed_dot_graph_t* g) {
    xed_dot_node_t* p = g->nodes;
    while(p) {
        xed_dot_node_t* t = p;
        p = p->next;
        free(t);
    }
}
static void delete_edges(xed_dot_graph_t* g) {
    xed_dot_edge_t* p = g->edges;
    while(p) {
        xed_dot_edge_t* t = p;
        p = p->next;
        free(t);
    }
}
void xed_dot_graph_deallocate(xed_dot_graph_t* g)
{
    delete_nodes(g);
    delete_edges(g);
    free(g);
}

xed_dot_node_t* xed_dot_node(xed_dot_graph_t* g,
                             char const* const name) {
    xed_dot_node_t* n = 0;
    n = (xed_dot_node_t*)malloc(sizeof(xed_dot_node_t));
    assert(n != 0);
    n->name = xed_strdup(name);
    
    n->next = g->nodes;
    g->nodes = n;
    return n;
}


void xed_dot_edge(xed_dot_graph_t* g,
                  xed_dot_node_t* src,
                  xed_dot_node_t* dst,
                  xed_dot_edge_style_t style)
{
    xed_dot_edge_t* e = 0;
    e = (xed_dot_edge_t*)malloc(sizeof(xed_dot_edge_t));
    assert(e != 0);
    e->src = src;
    e->dst = dst;
    e->style = style;

    e->next = g->edges;
    g->edges = e;
}



void xed_dot_dump(FILE* f, xed_dot_graph_t* g) {
    xed_dot_edge_t* p = g->edges;
    fprintf(f,"digraph {\n");
    while(p) {
        fprintf(f, "\"%s\" -> \"%s\"",
                p->src->name,
                p->dst->name);
        
        switch(p->style) {
          case XED_DOT_EDGE_SOLID:
            break; /* nothing required */
          case XED_DOT_EDGE_DASHED:
            fprintf(f, "[ style = dashed ]");
            break;
          case XED_DOT_EDGE_DOTTED:
            fprintf(f, "[ style = dotted ]");
            break;
          default:
            break;
        }
        
        fprintf(f, ";\n");

        p = p->next;
    }
    fprintf(f,"}\n");
}
