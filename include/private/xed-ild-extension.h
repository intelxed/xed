/*BEGIN_LEGAL 

Copyright (c) 2022 Intel Corporation

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

/// @file xed-ild-extension.h
/// instruction length decoder extension header

#if !defined(XED_ILD_EXTENSION_H)
# define XED_ILD_EXTENSION_H

#include "xed-decoded-inst.h"

xed_bool_t xed_ild_extension_handle_ubit_avx512(xed_decoded_inst_t *d);

#endif

