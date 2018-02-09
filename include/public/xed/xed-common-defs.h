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
/// @file xed-common-defs.h 
/// @brief some pervasive defines



#ifndef XED_COMMON_DEFS_H
# define XED_COMMON_DEFS_H

 // for most things it is 4, but one 64b mov allows 8
#define XED_MAX_DISPLACEMENT_BYTES  8

 // for most things it is max 4, but one 64b mov allows 8.
#define XED_MAX_IMMEDIATE_BYTES  8

#define XED_MAX_INSTRUCTION_BYTES  15


#define XED_BYTE_MASK(x) ((x) & 0xFF)
#define XED_BYTE_CAST(x) (XED_STATIC_CAST(xed_uint8_t,x))

#endif









