/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

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

#if !defined(XED_ENCODE_TABLES_H)
# define XED_ENCODE_TABLES_H

// Some things are "extern const" because they are filled in where they are
// declared in some generated *.c file.

//Table of BIND function per each group
extern const
xed_encode_function_pointer_t xed_encode_groups[XED_ENC_GROUPS];

//mapping from xed iclass to the encoding group
XED_GLOBAL_EXTERN
xed_uint16_t xed_enc_iclass2group[XED_ICLASS_LAST];

//mapping from iclass to it's Id in the group
XED_GLOBAL_EXTERN
xed_uint8_t xed_enc_iclass2index_in_group[XED_ICLASS_LAST];

// The entries of this array are xed_operand_enum_t, but stored as
// xed_uint8_t to save space.  Subverting the type system.
XED_GLOBAL_EXTERN 
xed_uint8_t xed_encode_order[XED_ENCODE_ORDER_MAX_ENTRIES][XED_ENCODE_ORDER_MAX_OPERANDS];
XED_GLOBAL_EXTERN 
xed_uint_t xed_encode_order_limit[XED_ENCODE_ORDER_MAX_ENTRIES];


extern const
xed_ptrn_func_ptr_t xed_encode_fb_lu_table[XED_ENCODE_MAX_FB_PATTERNS];

extern const
xed_ptrn_func_ptr_t xed_encode_emit_lu_table[XED_ENCODE_MAX_EMIT_PATTERNS];

extern const
xed_uint8_t xed_encode_fb_values_table[XED_ENCODE_FB_VALUES_TABLE_SIZE];

extern const
xed_encoder_iform_t xed_encode_iform_db[XED_ENCODE_MAX_IFORMS];

#endif
