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
#include <stdarg.h>


/// turn off (or on) argument checking if using the checked encoder interface.
/// values 1, 0
XED_DLL_EXPORT void xed_enc2_check_args_set(xed_bool_t on);

typedef void (xed_user_abort_handler_t)(const char * restrict format, va_list args);

/// Set a function taking a variable-number-of-arguments (stdarg) to handle
/// the errors and die.  The argument are like printf with a format string
/// followed by a varaible number of arguments.

XED_DLL_EXPORT void xed_enc2_set_error_handler(xed_user_abort_handler_t* fn);


#endif
