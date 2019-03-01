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
#include "xed-internal-header.h"
#if defined(XED_MESSAGES)
# include <stdio.h>
#endif

extern void xed_ild_init(void);

XED_DLL_EXPORT void 
xed_tables_init(void)
{
    static int first_time = 1;
    if (first_time == 0)
	return;
    first_time = 0;
#if defined(XED_MESSAGES)
    xed_log_file = stdout;
#endif
    xed_ild_init();
}
