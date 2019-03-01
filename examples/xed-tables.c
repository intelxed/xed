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
#include "xed/xed-interface.h"


void dump_operand(const xed_operand_t* op) {
    printf("%s ", xed_operand_enum_t2str(xed_operand_name(op)));
    printf("%s ", 
      xed_operand_visibility_enum_t2str(xed_operand_operand_visibility(op)));
    printf("%s ", xed_operand_action_enum_t2str(xed_operand_rw(op)));
    printf("%s ", xed_operand_type_enum_t2str(xed_operand_type(op)));
    printf("%s ", xed_operand_element_xtype_enum_t2str(xed_operand_xtype(op)));
    if (xed_operand_type(op) == XED_OPERAND_TYPE_NT_LOOKUP_FN)
        printf("%s ", 
          xed_nonterminal_enum_t2str(xed_operand_nonterminal_name(op)));
    if (xed_operand_type(op) == XED_OPERAND_TYPE_REG)
        printf("%s ", xed_reg_enum_t2str(xed_operand_reg(op)));
}


void print_attributes(const xed_inst_t* xi) {
    /* Walk the attributes. Generally, you'll know the one you want to
     * query and just access that one directly. */

    unsigned int i, nattributes  =  xed_attribute_max();

    printf("ATTRIBUTES: ");
    for(i=0;i<nattributes;i++) {
        xed_attribute_enum_t attr = xed_attribute(i);
        if (xed_inst_get_attribute(xi,attr))
            printf("%s ", xed_attribute_enum_t2str(attr));
    }
    printf("\n");
}


void dump_inst(const xed_inst_t* p) {
    unsigned int j;
    printf("%s ", xed_iclass_enum_t2str(xed_inst_iclass(p)));
    printf("%s ", xed_iform_enum_t2str(xed_inst_iform_enum(p)));
    printf("%s ", xed_category_enum_t2str(xed_inst_category(p)));
    printf("%s ", xed_extension_enum_t2str(xed_inst_extension(p)));
    printf("%s ", xed_isa_set_enum_t2str(xed_inst_isa_set(p)));
    print_attributes(p);
    printf("%2u ", xed_inst_noperands(p));
    printf("\n");
    for(j=0;j<xed_inst_noperands(p);j++) {
        printf("\t%u ", j);
        dump_operand(xed_inst_operand(p,j));
        printf("\n");
    }

}

void dump_insts(void) {
    int i;
    for(i=0;i<XED_MAX_INST_TABLE_NODES;i++)  {
        printf("%d ", i);
        dump_inst(xed_inst_table_base()+i);
    }
}

int main(int argc, char** argv) {
    
    // initialize the XED tables -- one time.
    xed_tables_init();

    dump_insts();


    return 0;
    (void) argc; (void) argv; //pacify compiler
}
