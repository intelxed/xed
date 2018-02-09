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

// 2014-11-20: This file has code duplication with other parts of the XED
// code base. It is intended to be the bare minimum required to allow
// clients to use the ILD standalone (libxed-ild) library. Ultimately, I
// should remove the code duplication by splitting a few more of the files.

#include "xed-types.h"
#include "xed-util.h"
#include "xed-portability.h"
#include "xed-portability-private.h"
#include "xed-common-defs.h"
#include "xed-common-hdrs.h"
#include "xed-state.h"
#include "xed-decoded-inst.h"
#include "xed-operand-accessors.h"

#include <stdio.h>  //fprint, stderr
#include <string.h> //memset

#if defined(__linux__) && defined(__STDC_HOSTED__) && __STDC_HOSTED__ == 0
   extern void abort (void)  __attribute__ ((__noreturn__));
#else
#  include <stdlib.h>
#endif

int xed_verbose=2;
#if defined(XED_MESSAGES)
FILE* xed_log_file;
#endif

void xed_derror(const char* s) {
    XED2DIE((xed_log_file,"%s\n", s));
    (void)s; //pacify compiler when msgs are disabled
}

static xed_user_abort_function_t xed_user_abort_function = 0;


static void* xed_user_abort_other = 0;

void xed_register_abort_function(xed_user_abort_function_t fn,
                                 void* other) {
    xed_user_abort_function = fn;
    xed_user_abort_other = other;
}

void xed_internal_assert( const char* msg, const char* file, int line) {
    if (xed_user_abort_function) {
      (*xed_user_abort_function)(msg, file, line, xed_user_abort_other);
    }
    else {
      fprintf(stderr,"ASSERTION FAILURE %s at %s:%d\n", msg, file, line);
    }
    abort();
}




void xed_operand_values_set_mode(xed_operand_values_t* p,
                                 const xed_state_t* dstate)  {

    /* set MODE, SMODE and REALMODE */
    xed3_operand_set_realmode(p,0);
    switch(xed_state_get_machine_mode(dstate))
    {
      case XED_MACHINE_MODE_LONG_64:
        xed3_operand_set_mode(p,2);
        xed3_operand_set_smode(p,2);
        return;
        
      case XED_MACHINE_MODE_LEGACY_32:
      case XED_MACHINE_MODE_LONG_COMPAT_32:
        xed3_operand_set_mode(p,1);
        break;

      case XED_MACHINE_MODE_REAL_16:
        xed3_operand_set_realmode(p,1);
        xed3_operand_set_mode(p,0);
        break;

      case XED_MACHINE_MODE_LEGACY_16:
      case XED_MACHINE_MODE_LONG_COMPAT_16:
        xed3_operand_set_mode(p,0);
        break;
      default:
        xed_derror("Bad machine mode in xed_operand_values_set_mode() call");
    }

    // 64b mode returns above. this is for 16/32b modes only
    switch(xed_state_get_stack_address_width(dstate))    {
      case XED_ADDRESS_WIDTH_16b:
        xed3_operand_set_smode(p,0);
        break;
      case XED_ADDRESS_WIDTH_32b:
        xed3_operand_set_smode(p,1);
        break;
      default:
        break;
    }
}

XED_DLL_EXPORT void
xed_decoded_inst_zero_set_mode(xed_decoded_inst_t* p,
                               const xed_state_t* dstate)
{
    memset(p, 0, sizeof(xed_decoded_inst_t));
    xed_operand_values_set_mode(p,dstate);
}

void xed_set_verbosity(int v) {
    xed_verbose = v;
}

void  xed_set_log_file(void* o) {
#if defined(XED_MESSAGES)
    xed_log_file = (FILE*)o;
#else
    (void)o;
#endif

}

