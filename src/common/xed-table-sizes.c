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


#include <stdio.h>
#include "xed-interface.h"
#include "xed-tables-extern.h"

#define XED_PRINT_TSZ(x) \
    do { \
          bytes += sizeof(x) ; \
          printf("%8ld : " #x "\n", sizeof(x)); \
    } while(0)

void xed_table_sizes(void) {
#if defined(XED_INTROSPECTIVE)
    xed_uint32_t bytes = 0;
    printf("Tables:\n");
    XED_PRINT_TSZ( xed_inst_table );
    XED_PRINT_TSZ( xed_operand );
    XED_PRINT_TSZ( xed_operand_sequences );
    XED_PRINT_TSZ( xed_iform_db );
    XED_PRINT_TSZ( xed_decode_graph );
    XED_PRINT_TSZ( xed_attributes_table );
    XED_PRINT_TSZ( xed_iform_first_per_iclass_table );
    XED_PRINT_TSZ( xed_iform_max_per_iclass_table );
    XED_PRINT_TSZ( xed_enc_func );
    XED_PRINT_TSZ( xed_encode_order );
    XED_PRINT_TSZ( xed_encode_order_limit );
    XED_PRINT_TSZ( xed_reg_class_array );
    XED_PRINT_TSZ( xed_gpr_reg_class_array );
    XED_PRINT_TSZ( xed_reg_width_bits );
    XED_PRINT_TSZ( xed_largest_enclosing_register_array );
    XED_PRINT_TSZ( xed_width_bits );
    XED_PRINT_TSZ( xed_operand_type_table );
    XED_PRINT_TSZ( xed_operand_xtype_info );
    XED_PRINT_TSZ( xed_operand_element_width );
    XED_PRINT_TSZ( xed_width_is_bytes );
    XED_PRINT_TSZ( xed_flags_simple_table );
    XED_PRINT_TSZ( xed_flags_complex_table );
    XED_PRINT_TSZ( xed_flag_action_table );

    printf("%8d : Total\n", bytes);

    printf("\nUnderlying Data structures:\n");
    XED_PRINT_TSZ( xed_simple_flag_t );
    XED_PRINT_TSZ( xed_decoded_inst_t );
    XED_PRINT_TSZ( xed_graph_node_t );
    XED_PRINT_TSZ( xed_inst_t );
    XED_PRINT_TSZ( xed_operand_t );
    XED_PRINT_TSZ( xed_decode_cache_entry_t );
    XED_PRINT_TSZ( xed_decode_cache_t );

    printf("\nFlags Data structures:\n");
    
    XED_PRINT_TSZ( xed_flag_action_t );
    XED_PRINT_TSZ( xed_flag_set_t );
#endif
}
