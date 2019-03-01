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
/// @file xed-operand-action.c
/// 


#include "xed-operand-action.h"

static const xed_uint8_t xed_read_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 1,
  /* XED_OPERAND_ACTION_R       */ 1,
  /* XED_OPERAND_ACTION_W       */ 0,
  /* XED_OPERAND_ACTION_RCW     */ 1,
  /* XED_OPERAND_ACTION_CW      */ 0,
  /* XED_OPERAND_ACTION_CRW     */ 1,
  /* XED_OPERAND_ACTION_CR      */ 1,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_read_only_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 0,
  /* XED_OPERAND_ACTION_R       */ 1,
  /* XED_OPERAND_ACTION_W       */ 0,
  /* XED_OPERAND_ACTION_RCW     */ 0,
  /* XED_OPERAND_ACTION_CW      */ 0,
  /* XED_OPERAND_ACTION_CRW     */ 0,
  /* XED_OPERAND_ACTION_CR      */ 1,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_written_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 1,
  /* XED_OPERAND_ACTION_R       */ 0,
  /* XED_OPERAND_ACTION_W       */ 1,
  /* XED_OPERAND_ACTION_RCW     */ 1,
  /* XED_OPERAND_ACTION_CW      */ 1,
  /* XED_OPERAND_ACTION_CRW     */ 1,
  /* XED_OPERAND_ACTION_CR      */ 0,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_written_only_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 0,
  /* XED_OPERAND_ACTION_R       */ 0,
  /* XED_OPERAND_ACTION_W       */ 1,
  /* XED_OPERAND_ACTION_RCW     */ 0,
  /* XED_OPERAND_ACTION_CW      */ 1,
  /* XED_OPERAND_ACTION_CRW     */ 0,
  /* XED_OPERAND_ACTION_CR      */ 0,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_read_and_written_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 1,
  /* XED_OPERAND_ACTION_R       */ 0,
  /* XED_OPERAND_ACTION_W       */ 0,
  /* XED_OPERAND_ACTION_RCW     */ 1,
  /* XED_OPERAND_ACTION_CW      */ 0,
  /* XED_OPERAND_ACTION_CRW     */ 1,
  /* XED_OPERAND_ACTION_CR      */ 0,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_conditional_read_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 0,
  /* XED_OPERAND_ACTION_R       */ 0,
  /* XED_OPERAND_ACTION_W       */ 0,
  /* XED_OPERAND_ACTION_RCW     */ 0,
  /* XED_OPERAND_ACTION_CW      */ 0,
  /* XED_OPERAND_ACTION_CRW     */ 1,
  /* XED_OPERAND_ACTION_CR      */ 1,
  /* XED_OPERAND_ACTION_LAST    */ 0
};
static const xed_uint8_t xed_conditional_write_action[] = {
  /* XED_OPERAND_ACTION_INVALID */ 0,
  /* XED_OPERAND_ACTION_RW      */ 0,
  /* XED_OPERAND_ACTION_R       */ 0,
  /* XED_OPERAND_ACTION_W       */ 0,
  /* XED_OPERAND_ACTION_RCW     */ 1,
  /* XED_OPERAND_ACTION_CW      */ 1,
  /* XED_OPERAND_ACTION_CRW     */ 0,
  /* XED_OPERAND_ACTION_CR      */ 0,
  /* XED_OPERAND_ACTION_LAST    */ 0
};


xed_uint_t xed_operand_action_read(const xed_operand_action_enum_t rw) {
    return xed_read_action[rw];
}
xed_uint_t xed_operand_action_read_only(const xed_operand_action_enum_t rw) {
    return xed_read_only_action[rw];
}
xed_uint_t xed_operand_action_written(const xed_operand_action_enum_t rw) {
    return xed_written_action[rw];
}
xed_uint_t xed_operand_action_written_only(const xed_operand_action_enum_t rw) {
    return xed_written_only_action[rw];
}
xed_uint_t xed_operand_action_read_and_written(const xed_operand_action_enum_t rw) {
    return xed_read_and_written_action[rw];
}
xed_uint_t xed_operand_action_conditional_read(const xed_operand_action_enum_t rw) {
    return xed_conditional_read_action[rw];
}
xed_uint_t xed_operand_action_conditional_write(const xed_operand_action_enum_t rw) {
    return xed_conditional_write_action[rw];
}

