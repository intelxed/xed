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
/// @file xed-tables.H
/// 

#if !defined(XED_TABLES_H)
# define XED_TABLES_H


#if !defined(XED_MAX_INST_TABLE_NODES)
# error "Need to include the generated definition for XED_MAX_INST_TABLE_NODES"
#endif


#if !defined(XED_GLOBAL_EXTERN)
# error "Need to define XED_GLOBAL_EXTERN"
#endif

// Some things are "extern const" because they are filled in where they are
// declared in some generated *.c file.

/**************************************************************************/
/* stuff needed for the decoder */
#if defined(XED_DECODER)

XED_DLL_EXPORT extern 
const xed_inst_t       xed_inst_table[XED_MAX_INST_TABLE_NODES];
XED_DLL_EXPORT extern 
const xed_operand_t    xed_operand[XED_MAX_OPERAND_TABLE_NODES];
XED_DLL_EXPORT extern 
const xed_uint16_t     xed_operand_sequences[XED_MAX_OPERAND_SEQUENCES];
XED_DLL_EXPORT extern 
const xed_iform_info_t xed_iform_db[XED_IFORM_LAST];

extern const xed_attribute_enum_t xed_attributes_table[XED_MAX_ATTRIBUTE_COUNT];
extern const xed_operand_convert_enum_t
 xed_operand_convert[XED_MAX_CONVERT_PATTERNS][XED_MAX_DECORATIONS_PER_OPERAND];

extern const xed_uint32_t xed_iform_first_per_iclass_table[XED_ICLASS_LAST];
extern const xed_uint32_t xed_iform_max_per_iclass_table[XED_ICLASS_LAST];

#endif 
/**************************************************************************/





/**************************************************************************/
/* stuff needed for the encoder */
#if defined(XED_ENCODER)
#include "xed-encode-tables.h"
#endif

/**************************************************************************/


/* more miscellaneous stuff */

/* names for each over-ridden iclass.  Even entries are Intel. The subsquent odd
   entry is the ATTY SYSV name. */
XED_DLL_EXPORT extern 
char const* const xed_iclass_string[XED_ICLASS_NAME_STR_MAX];

// the high level reg class for each register.
XED_GLOBAL_EXTERN xed_reg_class_enum_t xed_reg_class_array[XED_REG_LAST];
// for just the GPR types: refines to REG8,16,32,64
XED_GLOBAL_EXTERN xed_reg_class_enum_t xed_gpr_reg_class_array[XED_REG_LAST];

// the width in bits for each register.
// 2nd index 0=32b and 1=64b
XED_GLOBAL_EXTERN xed_uint_t xed_reg_width_bits[XED_REG_LAST][2];

// map each register to the largest enclosing register (for nested
// registers) or back to itself if there is no outer nesting.
XED_GLOBAL_EXTERN xed_reg_enum_t xed_largest_enclosing_register_array[XED_REG_LAST];
XED_GLOBAL_EXTERN xed_reg_enum_t xed_largest_enclosing_register_array_32[XED_REG_LAST];

// OC2 width codes. The 2nd index is the effective operand size (1,2, or 3)
XED_GLOBAL_EXTERN xed_uint16_t xed_width_bits[XED_OPERAND_WIDTH_LAST][4];

// the default type of the operand elements 
XED_GLOBAL_EXTERN 
xed_operand_element_type_enum_t xed_operand_type_table[XED_OPERAND_WIDTH_LAST];

// the xtype -> dtype, # bits per element map
extern const xed_operand_type_info_t xed_operand_xtype_info[XED_OPERAND_XTYPE_LAST];


// number of elements per operand
XED_GLOBAL_EXTERN 
xed_uint32_t xed_operand_element_width[XED_OPERAND_WIDTH_LAST];

// Returns 1 if the corresponding value in xed_width_bits is a multiple of
// 8 bits
XED_GLOBAL_EXTERN xed_uint8_t xed_width_is_bytes[XED_OPERAND_WIDTH_LAST][4];

// FIXME: Could make the flags info  decoder-only.
// Flags tables. The top table points to the flag-actions. The
// complex table points to the simple flags table entries.

extern const xed_simple_flag_t
xed_flags_simple_table[XED_MAX_REQUIRED_SIMPLE_FLAGS_ENTRIES];
extern const xed_complex_flag_t
xed_flags_complex_table[XED_MAX_REQUIRED_COMPLEX_FLAGS_ENTRIES];
extern const xed_flag_action_t
xed_flag_action_table[XED_MAX_GLOBAL_FLAG_ACTIONS];

#endif
