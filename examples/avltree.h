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


#if !defined(_AVL_TREE_H_)
# define _AVL_TREE_H_
            
#include <stdint.h>
#if defined(AVL_KEY_32_BIT)
typedef uint32_t avl_key_t;
#else
typedef uint64_t avl_key_t;
#endif


struct avl_node_s; // fwd decl

typedef struct {
    struct avl_node_s* top;
} avl_tree_t;

void  avl_tree_init(avl_tree_t* tree);

// clear removes the tree nodes, not the data
void  avl_tree_clear(avl_tree_t* tree, int free_data);

void* avl_find(avl_tree_t* tree, avl_key_t key);

// find the node with a key <= the given key. Returns found key value in
// lbkey and the data payoad as a return value.
void* avl_find_lower_bound(avl_tree_t* tree, avl_key_t key,
                           avl_key_t* lbkey); // output


// insert notices  key collisions and will free the associated data if
// free_data is nonzero.
void  avl_insert(avl_tree_t* tree, avl_key_t key, void* value, int free_data);

#if 0 // DELETE not done yet.
// return 1 on failure, 0 on success
int   avl_delete(avl_tree_t* tree, avl_key_t key, int free_data);
#endif


struct avl_link_node_s; // fwd decl

typedef struct avl_iter_s {
    struct avl_link_node_s* head;
    struct avl_link_node_s* tail;    
} avl_iter_t;


void avl_iter_begin( avl_iter_t* iter,avl_tree_t* tree);
void* avl_iter_current(avl_iter_t* iter);
void avl_iter_increment(avl_iter_t* iter);
int avl_iter_done(avl_iter_t* iter);
void avl_iter_cleanup(avl_iter_t* iter); // call if end iteration early

#endif
