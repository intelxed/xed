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
/// @file xed-flags-private.H
/// 

#ifndef XED_MAP_INFO_H
# define  XED_MAP_INFO_H

typedef struct {
    xed_uint8_t legacy_escape;
    xed_uint8_t has_legacy_opcode;
    xed_uint8_t legacy_opcode;
    xed_uint8_t map_id;    
    xed_int8_t  opc_pos;
} xed_map_info_t;

#endif
