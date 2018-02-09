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
/// @file xed-operand-action.h
/// 

#if !defined(XED_OPERAND_ACTION_H)
# define XED_OPERAND_ACTION_H

#include "xed-types.h"
#include "xed-operand-action-enum.h"

XED_DLL_EXPORT xed_uint_t xed_operand_action_read(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_read_only(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_written(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_written_only(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_read_and_written(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_conditional_read(const xed_operand_action_enum_t rw);
XED_DLL_EXPORT xed_uint_t xed_operand_action_conditional_write(const xed_operand_action_enum_t rw);

#endif

