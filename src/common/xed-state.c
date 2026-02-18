/* BEGIN_LEGAL 

Copyright (c) 2026 Intel Corporation

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
/// @file xed-state.c
/// 



#include "xed-state.h"
#include "xed-portability.h"
#include "xed-util.h"




int   xed_state_print(const xed_state_t* p, char* buf, int buflen)  {
    if (buflen <= 0)
        return 0;
    xed_assert(p != NULL);
    api_check(buf != NULL);
    int blen = buflen;
    blen = xed_strncpy(buf,"MachineMode: ",blen);
    blen = xed_strncat(buf, xed_machine_mode_enum_t2str(p->mmode),blen);
    blen = xed_strncat(buf," AddrWidth: ",blen);
    blen = xed_strncat(buf, 
            xed_address_width_enum_t2str(xed_state_get_address_width(p)),blen);
    blen = xed_strncat(buf," StackAddrWidth: ",blen);
    blen = xed_strncat(buf,
               xed_address_width_enum_t2str(p->stack_addr_width),blen);
    return blen;
}


