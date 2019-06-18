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

/// @file xed-min.cpp
/// @brief how to discover enum names for xed_iclass_enum_t

/*************************************************************************
   When using XED as a DLL or shared object, the enumerations can change
   from one version of XED to another if instructions (or features) are
   added. Each XED enumeration must be mapped to something your XED client
   can use for indepedent compilation.  This example shows how to discover
   the XED values for the xed_iclass_enum_t and construct a mapping from
   names that are constant to your tool to names that can vary.  You would
   need to this for each XED enumeration that your XED client uses.

   This builds a one map so that you can map things from your clients code
   to XED's names as would be required for an encoder. For a decoder you'd
   also need to invert the mapping so that you can mape from XED names to
   your client's names.
**************************************************************************/

#include "xed/xed-interface.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>

int main(int argc, char** argv);


typedef enum {  /* these are the names that'll use in my code */
    MY_ICLASS_ADD, 
    MY_ICLASS_SUB,
    MY_ICLASS_LAST
} my_iclass_enum_t;

/* A mapping from my (simple) client names to the XED names which can
 * vary. */
typedef struct {
    char const* const string_name;
    int xed_name; /* discovered  and passed to XED n*/
} iclass_interface_t;


iclass_interface_t xed_iclass_interface[] = {
    { "ADD", -1},
    { "SUB", -1}
};

void dump_inst(const xed_inst_t* p) {
    /* N-squared maching... */
    xed_iclass_enum_t ic = xed_inst_iclass(p);
    char const* const xed_name = xed_iclass_enum_t2str(ic);
    iclass_interface_t* table_base = xed_iclass_interface;
    int j=0;

    while( j < MY_ICLASS_LAST) {
        if (strcmp(table_base[j].string_name, xed_name) == 0) {
            if (table_base[j].xed_name == -1) {
                printf("%s maps to %d\n", xed_name, (int)ic);
                table_base[j].xed_name = ic;
            }
            break;
        }
        j++;
    }
}

void build_map_to_xed(void) {
    int i;
    for(i=0;i<XED_MAX_INST_TABLE_NODES;i++)  {
        dump_inst(xed_inst_table_base()+i);
    }
}

/* map from xed values to values I know about  - dynamically allocated */
unsigned int* xed2my_enum = 0;

void invert_map(void) {
    unsigned int n = xed_iclass_enum_t_last();
    unsigned int i;
    
    xed2my_enum = malloc(sizeof(unsigned int)*n);
    assert(xed2my_enum!=0);
    
    for(i=0;i<n;i++) {
        xed2my_enum[i] = 0; // invalid
    }
    for (i=0;i<MY_ICLASS_LAST;i++) {
        xed2my_enum[ xed_iclass_interface[i].xed_name ] = i;
        printf("%s xed=%d client=%d\n", xed_iclass_interface[i].string_name,
               xed_iclass_interface[i].xed_name,
               i);
    }
}

int main(int argc, char** argv) {
    // initialize the XED tables -- one time.
    xed_tables_init();

    build_map_to_xed();
    invert_map();

    return 0;
    (void) argc; (void) argv; //pacify compiler
}
