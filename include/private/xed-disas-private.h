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
/// @file xed-disas.h
/// 

#if !defined(XED_DISAS_PRIVATE_H)
# define XED_DISAS_PRIVATE_H

#include "xed-disas.h"
#include "xed-print-info.h"

int xed_get_symbolic_disassembly(xed_print_info_t* pi,
                                 xed_uint64_t address, 
                                 char* buffer, 
                                 unsigned int buffer_length,
                                 xed_uint64_t* offset);


#endif
