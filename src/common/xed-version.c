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

#include "xed-version.h"

char const* const xed_copyright =
  "Copyright (C) 2017, Intel Corporation. All rights reserved.";

/* need two levels of macros to expand and stringify the CPP macro arg. */
#define XED_STR1(x) #x
#define XED_STR2(a) XED_STR1(a)
char const* const xed_version = XED_STR2(XED_GIT_VERSION) ;

char const* xed_get_version(void) {
    return xed_version;
}

char const* xed_get_copyright(void) {
    return xed_copyright;
}

