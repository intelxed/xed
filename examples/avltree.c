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

#include "avltree.h"
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

typedef struct avl_node_s {
    avl_key_t key;
    void* data;
    int32_t balance_factor;
    uint32_t height;
    struct avl_node_s* left;
    struct avl_node_s* right;
} avl_node_t;

static void pad(int d) {
    int i;
    for(i=0;i<d;i++)
        fputs("  ", stdout);
}
static void print_node(avl_node_t* n, int cur_depth) // recursive
{

    pad(cur_depth);
    if (n) {
#if defined(__GNUC__) && defined(__LP64__) && !defined(__APPLE__)
# define AVL_FMT_LU "%lu"
#else
# define AVL_FMT_LU "%llu"
#endif
        fprintf(stdout, "H%u B%d (" AVL_FMT_LU ", %p)\n",
                n->height,
                n->balance_factor,
                (uint64_t) n->key,
                n->data);
        print_node(n->left, cur_depth+1);
        print_node(n->right, cur_depth+1);
    }
    else 
        fprintf(stdout, "*empty*\n");
    
}
#if 0
static void print_tree(avl_tree_t* tree) {
    printf("=============\n");
    if (tree->top)
        print_node(tree->top, 0);
    else
        fprintf(stdout, "*empty tree*\n");
    printf("=============\n");
}
#endif

void  avl_tree_init(avl_tree_t* tree)
{
    tree->top = 0;
}

static void clear(avl_node_t* n, int free_data) // recursive
{
    if (n->left) 
        clear(n->left, free_data);
    if (n->right) 
        clear(n->right, free_data);
    if (free_data && n->data)
        free((void*)n->data);
    free((void*)n);
}
void  avl_tree_clear(avl_tree_t* tree, int free_data)
{
    if (tree->top) {
        clear(tree->top, free_data);
    }
    tree->top = 0;
}

static avl_node_t* find_node(avl_node_t* n, avl_key_t key) //recursive
{
    if (n->key == key)
        return n;
    else if (n->key > key && n->left)
        return find_node(n->left, key);
    else if (n->right)
        return find_node(n->right, key);
    return 0;
}

static void* find(avl_node_t* n, avl_key_t key) //recursive
{
    if (n)
    {
        avl_node_t* x = find_node(n,key);
        if (x)
            return x->data;
    }
    return 0;
}

void* avl_find  (avl_tree_t* tree, avl_key_t key)
{
    return find(tree->top, key);
}










static avl_node_t* find_node_lower_bound(avl_node_t* n, avl_key_t key,
                                         avl_node_t** lb) //recursive
{
    //printf("NODE KEY=%lld\n", n->key);
    if (n->key == key){
        *lb = n;
        return n;
    }
    else if (n->key > key && n->left) {
        //printf("\tGO LEFT\n");
        return find_node_lower_bound(n->left, key, lb);
    }

    if (n->key < key) {
        // store the max lower bound we encounter when node key is < search
        // key.
        if (*lb  && (*lb)->key < n->key)
            *lb = n;
        else if (*lb == 0) 
            *lb = n;
    }
    
    if (n->right) {
        //printf("\tGO RIGHT\n");
        return find_node_lower_bound(n->right, key, lb);
    }
    return *lb;
}

static void* find_lower_bound(avl_node_t* n, avl_key_t key,
                              avl_key_t* lbkey) // output
{
    avl_node_t* lbound = 0;
    if (n)
    {
        (void) find_node_lower_bound(n,key, &lbound);
        if (lbound) {
            *lbkey = lbound->key;
            return lbound->data;
        }
    }
    return 0;
}
void* avl_find_lower_bound  (avl_tree_t* tree, avl_key_t key,
                             avl_key_t* lbkey) // output
{
    return find_lower_bound(tree->top, key, lbkey);
}






static avl_node_t* make_node(avl_key_t key, void* value)
{
    avl_node_t* n = (avl_node_t*) malloc(sizeof(avl_node_t));
    assert(n != 0);
    n->key = key;
    n->data = value;
    n->balance_factor = 0;
    n->height = 1;
    n->left = n->right = 0;
    return n;
}

static uint32_t mmax(uint32_t a, uint32_t b) {
    return (a>b)?a:b;
}

static uint32_t update_height(avl_node_t* n)
{
    avl_node_t* a = n->left;
    avl_node_t* b = n->right;
    return 1 + mmax((a?a->height:0), (b?b->height:0));
}
static int32_t update_balance(avl_node_t* n)
{
    avl_node_t* a = n->left;
    avl_node_t* b = n->right;
    return (int32_t)(a?a->height:0) - (int32_t)(b?b->height:0);
}
static void update_height_and_balance(avl_node_t* n)
{
    n->height = update_height(n);
    n->balance_factor = update_balance(n);
}
static avl_node_t* left_left(avl_node_t* n) // changes top node
{
    // knock the tree over to the right, making n->left in to the new top node.
    // juggle subtrees

    avl_node_t* new_top = n->left;
    avl_node_t* old_top = n;
    old_top->left = new_top->right;
    new_top->right = old_top;
    update_height_and_balance(old_top);
    update_height_and_balance(new_top);
    return new_top;
}
static avl_node_t* left_right(avl_node_t* n)
{
    // replace n->left with n->left->right, juggle subtrees
    avl_node_t* l_node = n->left;
    avl_node_t* lr_node = n->left->right;
    n->left = lr_node;
    l_node->right = lr_node->left;
    lr_node->left = l_node;
    update_height_and_balance(l_node);
    update_height_and_balance(lr_node);
    return n;
}
static avl_node_t* right_left(avl_node_t* n)
{
    // replace n->right with n->right->left, juggle subtrees
    avl_node_t* r_node = n->right;
    avl_node_t* rl_node = n->right->left;
    n->right = rl_node;
    r_node->left = rl_node->right;
    rl_node->right = r_node;
    update_height_and_balance(r_node);
    update_height_and_balance(rl_node);
    return n;
}
static avl_node_t* right_right(avl_node_t* n) // changes top node
{
    // knock the tree over to the left, making n->right in to the new top node.
    // juggle subtrees
    avl_node_t* new_top = n->right;
    avl_node_t* old_top = n;
    old_top->right = new_top->left;
    new_top->left = old_top;
    update_height_and_balance(old_top);
    update_height_and_balance(new_top);
    return new_top;
}

static avl_node_t* insert(avl_node_t* n,
                          avl_key_t key, void* value, int free_data)
{
    if (n->key == key) {
        if (n->data && free_data)
            free((void*)n->data);
        n->data = value;
    }
    else if (n->key > key) {
        if (n->left) {
            n->left = insert(n->left, key, value, free_data);
            update_height_and_balance(n);
        }
        else  {
            n->left = make_node(key,value);
            update_height_and_balance(n);
        }
    }
    else if (n->key < key) {
        if (n->right) {
            n->right = insert(n->right, key, value, free_data);
            update_height_and_balance(n);
        }
        else {
            n->right = make_node(key,value);
            update_height_and_balance(n);
        }
    }
    // rebalancing might change the current node
    if (n->balance_factor >= 2) // heavy on the left
    {
        if (n->left->balance_factor == -1) {
            // subtree is heavy right, make it heavy left, then knock it over
            n = left_right(n);
            n = left_left(n);
        }
        else if (n->left->balance_factor == 1) {
            // subtree is heavy left, knock it over
            n = left_left(n);
        }
    }
    else if (n->balance_factor <= -2) // heavy on the right
    {
        if (n->right->balance_factor == 1) {
            // subtree is heavy left, make it heavy right, then knock it over
            n = right_left(n);
            n = right_right(n);
        }
        else if (n->right->balance_factor == -1) {
            // subtree is heavy right, knock it over
            n = right_right(n);
        }
    }
    update_height_and_balance(n); // FIXME: redundant, remove this
    if  (n->balance_factor <= -2 || n->balance_factor >= 2) {
        printf("FAIL\n");
        print_node(n, 0);
        assert (n->balance_factor < 2 && n->balance_factor > -2);
    }
    return n;
}

void  avl_insert(avl_tree_t* tree, avl_key_t key, void* value, int free_data)
{
    //rebalancing can change what the 'tree' points to as its top node.
    if (tree->top)
        tree->top = insert(tree->top, key, value, free_data);
    else
        tree->top = make_node(key,value);
    //print_tree(tree);
}


typedef struct avl_link_node_s {
    avl_node_t* node;
    struct avl_link_node_s* next;
} avl_link_node_t;

void avl_iter_begin( avl_iter_t* iter, avl_tree_t* tree)
{
    iter->head = 0;
    iter->tail = 0;
    if (tree->top) {
        avl_link_node_t* n = (avl_link_node_t*)malloc(sizeof(avl_link_node_t));
        assert(n != 0);
        n->node = tree->top;
        n->next = 0;
        iter->head = n;
        iter->tail = n;
    }
    
}

void* avl_iter_current(avl_iter_t* iter)
{
    return iter->head->node->data;
}

static void add_link_node(avl_iter_t* iter, avl_node_t* anode)
{
    if (anode)
    {
        avl_link_node_t* n = (avl_link_node_t*)malloc(sizeof(avl_link_node_t));
        assert(n != 0);
        n->next = 0;
        n->node = anode;
        iter->tail->next = n;
        iter->tail = n;
    }
 }
void avl_iter_increment(avl_iter_t* iter)
{
    avl_link_node_t* p;
    add_link_node(iter, iter->head->node->left);
    add_link_node(iter, iter->head->node->right);
    p = iter->head;
    iter->head = p->next;
    free(p);
}
int avl_iter_done(avl_iter_t* iter)
{
    return (iter->head == 0);
}

void avl_iter_cleanup(avl_iter_t* iter) // call if end iteration early
{
    struct avl_link_node_s* p = iter->head;
    while(p) {
        struct avl_link_node_s* t = p;
        p = t->next;
        free(t);
    }
}
