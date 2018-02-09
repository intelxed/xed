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

#if !defined(XED_VERSION_H)
# define XED_VERSION_H
#include "xed-common-hdrs.h"

///@ingroup INIT
/// Returns a string representing XED svn commit revision and time stamp.
XED_DLL_EXPORT char const* xed_get_version(void);
///@ingroup INIT
/// Returns a copyright string.
XED_DLL_EXPORT char const* xed_get_copyright(void);
#endif
