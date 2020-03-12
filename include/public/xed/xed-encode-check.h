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


#ifndef XED_ENCODE_CHECK_H
# define XED_ENCODE_CHECK_H
#include "xed-common-hdrs.h"
#include "xed-types.h"


/// turn off (or on) argument checking if using the checked encoder interface.
/// values 1, 0
/// @ingroup ENC2
XED_DLL_EXPORT void xed_enc2_set_check_args(xed_bool_t on);

#endif
