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
/// @file disas-raw.c

#include "xed/xed-interface.h" 
#if defined(XED_DECODER)
#include "xed-examples-util.h"
#include "xed-disas-raw.h"

void xed_disas_raw(xed_disas_info_t* fi)
{
    void* region = 0;
    unsigned int len = 0;
    xed_map_region(fi->input_file_name, &region, &len);
 
    fi->s =  (unsigned char*)region;
    fi->a = (unsigned char*)region;
    fi->q = (unsigned char*)(region) + len; // end of region
    fi->runtime_vaddr = fi->fake_base;
    fi->runtime_vaddr_disas_start = 0;
    fi->runtime_vaddr_disas_end = 0;
    fi->symfn = 0;
    fi->caller_symbol_data = 0;
    fi->line_number_info_fn = 0;
    xed_disas_test(fi);
    if (fi->xml_format == 0)
        xed_print_decode_stats(fi);
}

#endif
