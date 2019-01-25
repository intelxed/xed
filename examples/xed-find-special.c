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

/// @file xed-tables.c
/// @brief a minimal example of accessing the XED internal tables

#include <stdio.h>
#include <string.h>
#include "xed/xed-interface.h"
static char const* suffix_name(char const* s) {
    char* p = strchr(s,'_');
    return p+1;
}

typedef enum {
    reptype_invalid,
    reptype_rep,
    reptype_repe,
    reptype_repne
} reptype_enum_t;

static reptype_enum_t get_reptype(char const* s) {
    if (strncmp("REPNE",s,5) == 0)
        return reptype_repne;
    if (strncmp("REPE",s,4) == 0)
        return reptype_repe;
    if (strncmp("REP",s,3) == 0)
        return reptype_rep;
    return reptype_invalid;
}

static char const* reptype_enum_t2str(reptype_enum_t r) {
    switch(r) {
      case reptype_repne: return "REPNE";
      case reptype_repe: return "REPE";
      case reptype_rep: return "REP";
      default: return "INVALID";
    }
}

static void scan_inst(const xed_inst_t* p) {
    xed_iclass_enum_t ic = xed_inst_iclass(p);
    xed_category_enum_t cat = xed_inst_category(p);
    if (xed_inst_get_attribute(p,XED_ATTRIBUTE_LOCKABLE)) {
        char const* ics = xed_iclass_enum_t2str(ic);
        printf("LOCKABLE %s\n", ics);
    }
    if (xed_inst_get_attribute(p,XED_ATTRIBUTE_REP)) {
        char const* ics = xed_iclass_enum_t2str(ic);
        reptype_enum_t rt = get_reptype(ics);
        printf("REP* %s  --> %s + %s\n", ics, reptype_enum_t2str(rt), suffix_name(ics));
    }
    if (cat == XED_CATEGORY_STRINGOP || cat == XED_CATEGORY_IOSTRINGOP) {
        char const* ics = xed_iclass_enum_t2str(ic);
        printf("STRINGOP: %s\n", ics);
    }
    
}

static void scan_insts(void) {
    unsigned int i;
    for(i=0;i<XED_MAX_INST_TABLE_NODES;i++)  {
        scan_inst(xed_inst_table_base()+i);
    }
}

int main(int argc, char** argv) {
    
    // initialize the XED tables -- one time.
    xed_tables_init();

    scan_insts();


    return 0;
    (void) argc; (void) argv; //pacify compiler
}
