/* BEGIN_LEGAL 

Copyright (c) 2023 Intel Corporation

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
#include <assert.h>
#include <stdbool.h>
#include "xed/xed-interface.h"

/* Number of indent_tag's used to increase or decrease the value
 * of 'indent' for each change in indent level.
 */
#define INDENT_AMOUNT 4

/* The current indent (INDENT_AMOUNT * indent_tag) */
static int indent = 0;

/* The character(s) used to show an indent */
static const char *indent_tag = " ";

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

/* Increase the indent level (for JSON output) */
void inc_indent(void) {
    indent += INDENT_AMOUNT;
}

/* Decrease the indent level (for JSON output) */
void dec_indent(void) {
    assert(indent);
    assert((indent - INDENT_AMOUNT) >= 0);

    indent -= INDENT_AMOUNT;
}

/* Add (display) indent number of indent_tag characters
 * to stdout for JSON output.
 */
void add_indent(void) {
    printf("%*s", indent, indent_tag);
}

/* Increase the indent level and apply the current indent
 * for JSON output.
 */
void inc_add_indent(void) {
    inc_indent();
    add_indent();
}

/* Decrease the indent level and apply the new indent
 * for JSON output.
 */
void dec_add_indent(void) {
    dec_indent();
    add_indent();
}

/* Display the specified instruction operand to stdout in JSON format. */
void dump_operand_json(const xed_operand_t* op, unsigned num) {
    assert(op);

    /* Start the operand object */
    add_indent();
    printf("{\n");
    inc_indent();

    xed_operand_enum_t operand_name = xed_operand_name(op);
    xed_operand_visibility_enum_t operand_visibility = xed_operand_operand_visibility(op);
    xed_operand_type_enum_t operand_type = xed_operand_type(op);
    xed_operand_element_xtype_enum_t operand_xtype = xed_operand_xtype(op);
    xed_operand_action_enum_t operand_action = xed_operand_rw(op);

    add_indent();
    printf("\"operand-number\": %u,\n", num);

    add_indent();
    printf("\"operand-name\": \"%s\",\n", xed_operand_enum_t2str(operand_name));

    add_indent();
    printf("\"operand-visibility\": \"%s\",\n", xed_operand_visibility_enum_t2str(operand_visibility));

    add_indent();
    printf("\"operand-type\": \"%s\",\n", xed_operand_type_enum_t2str(operand_type));

    add_indent();
    printf("\"operand-xtype\": \"%s\",\n", xed_operand_element_xtype_enum_t2str(operand_xtype));

    if (xed_operand_type(op) == XED_OPERAND_TYPE_NT_LOOKUP_FN) {
        add_indent();
        printf("\"operand-nonterminal-name\": \"%s\",\n",
          xed_nonterminal_enum_t2str(xed_operand_nonterminal_name(op))
        );
    }

    if (xed_operand_type(op) == XED_OPERAND_TYPE_REG) {
        add_indent();
        printf("\"operand-register\": \"%s\",\n",
          xed_reg_enum_t2str(xed_operand_reg(op))
        );
    }

    add_indent();
    printf("\"operand-action\": \"%s\"\n", xed_operand_action_enum_t2str(operand_action));

    /* End the operand object */
    dec_add_indent();
    printf("}");
}

/* Display the specified instruction attributes to stdout in JSON format. */
void print_attributes_json(const xed_inst_t* xi) {
    assert(xi);

    unsigned int nattributes = xed_attribute_max();

    /* Start the attributes array */
    add_indent();
    printf("\"attributes\": [");

    bool shown_an_attrib = false;

    for(unsigned int i=0; i < nattributes; i++) {
        xed_attribute_enum_t attr = xed_attribute(i);

        if (xed_inst_get_attribute(xi, attr)) {
            printf("%s\"%s\"",
                   shown_an_attrib ? ", " : "",
                   xed_attribute_enum_t2str(attr)
               );

            if (! shown_an_attrib) shown_an_attrib = true;
        }
    }

    /* End the attributes array */
    printf("],\n");
}

/* Display the specified instruction in JSON format to stdout.
 *
 * Parameters:
 *
 * p: Instruction.
 * opcode: Name of instruction.
 * form_index: The zero-based form index number.
 */
void
dump_inst_json(const xed_inst_t* p, const char *opcode, unsigned int form_index) {
    assert(p);

    xed_iform_enum_t iform = xed_inst_iform_enum(p);
    xed_category_enum_t category = xed_inst_category(p);
    xed_extension_enum_t extension = xed_inst_extension(p);
    xed_isa_set_enum_t isa = xed_inst_isa_set(p);

    unsigned int operands = xed_inst_noperands(p);

    /* Start the instruction object */
    add_indent();
    printf("{\n");
    inc_indent();

    /* Not strictly required, but potentially useful */
    add_indent();
    printf("\"opcode\": \"%s\",\n", opcode);

    /* Not strictly required, but potentially useful */
    add_indent();
    printf("\"form-index\": %u,\n", form_index);

    add_indent();
    printf("\"iform\": \"%s\",\n", xed_iform_enum_t2str(iform));

    add_indent();
    printf("\"category\": \"%s\",\n", xed_category_enum_t2str(category));

    add_indent();
    printf("\"extension\": \"%s\",\n", xed_extension_enum_t2str(extension));

    add_indent();
    printf("\"isa\": \"%s\",\n", xed_isa_set_enum_t2str(isa));

    print_attributes_json(p);

    /* Start the operands array */
    add_indent();
    printf("\"operands\": [\n");
    inc_indent();

    for(unsigned int i=0; i < operands; i++) {
        dump_operand_json(xed_inst_operand(p, i), i);

        printf("%s\n",
          ((i+1) == operands) ? "" : ",");
    }

    /* End the operands array */
    dec_add_indent();
    printf("]\n");

    /* End the instruction object */
    dec_add_indent();
    printf("}");
}

/* Calculate the number of instruction forms.
 *
 * Parameters:
 *
 * current_index: Current instruction index.
 * current_iclass: Current iclass / instruction.
 *
 * NB: This function assumes that the xed_inst_table is sorted by iclass.
 */
unsigned
get_forms_count(unsigned current_index, xed_iclass_enum_t current_iclass)
{
    unsigned count = 0;

    for(unsigned int i = current_index; i < XED_MAX_INST_TABLE_NODES; i++) {
        const xed_inst_t *p = xed_inst_table_base()+i;
        xed_iclass_enum_t iclass = xed_inst_iclass(p);

        if (iclass != current_iclass) {
            break;
        }

        count++;
    }

    return count;
}

/* Display all instructions to stdout in JSON format. */
void dump_insts_json(void) {
    /* Start the JSON object */
    printf("{\n");

    /* Start the instructions object */
    inc_add_indent();
    printf("\"instructions\": {\n");
    inc_indent();

    xed_iclass_enum_t prev_iclass = XED_ICLASS_INVALID;

    unsigned int forms_count = 0;
    unsigned int iclasses_shown = 0;

    for(int i=0;i < XED_MAX_INST_TABLE_NODES; i++) {
        const xed_inst_t *p = xed_inst_table_base() + i;
        xed_iclass_enum_t iclass = xed_inst_iclass(p);

        if (iclass == XED_ICLASS_INVALID) {
            continue;
        }

        const char *opcode = xed_iclass_enum_t2str(iclass);
        /* We've found a new iclass, so calculate the number
         * of forms for this instruction.
         */
        if (iclass != prev_iclass) {
            forms_count = get_forms_count(i, iclass);
            assert(forms_count >= 1);
        }

        /* Show iclass (aka instruction name / opcode) */
        add_indent();
        printf("\"%s\": {\n", opcode);
        inc_indent();

        /* Start the opcode forms array that shows all the different
         * ways to specify the instruction.
         */
        add_indent();
        printf("\"forms\": [\n");
        inc_indent();

        for (unsigned int form = 0; form < forms_count; form++) {
            const xed_inst_t *p = xed_inst_table_base() + i + form;
            dump_inst_json(p, opcode, form);

            /* Add comma for all but final forms */
            printf("%s\n",
                   ((form+1) < forms_count) ? "," : "");
        }

        i += forms_count;

        /* End of the opcode forms */
        dec_add_indent();
        printf("]\n");

        /* End of opcode */
        dec_add_indent();
         printf("}%s\n",
            ((i+1) < XED_MAX_INST_TABLE_NODES) ? "," : "");

        prev_iclass = iclass;
        iclasses_shown++;
    }

    /* End the instructions object */
    dec_add_indent();
    printf("}\n");

    /* End the JSON object */
    dec_add_indent();
    printf("}\n");
}

void dump_insts_text(void) {
    int i;
    for(i=0;i<XED_MAX_INST_TABLE_NODES;i++)  {
        printf("%d ", i);
        dump_inst(xed_inst_table_base()+i);
    }
}

void dump_insts(bool use_json) {
    if (use_json) {
        dump_insts_json();
    } else {
        dump_insts_text();
    }
}

int main(int argc, char** argv) {
    bool use_json = 0;

    // initialize the XED tables -- one time.
    xed_tables_init();

    for(int i=1; i < argc; i++) {
        if (strcmp(argv[i], "-json") == 0) {
            use_json = true;
            break;
        }
    }

    dump_insts(use_json);

    return 0;
}
