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

/// @file xed-disas-extension.h
/// disassembly extension header

#if !defined(XED_DISAS_EXTENSION_H)
# define XED_DISAS_EXTENSION_H

#include "xed-print-info.h"
#include "xed-util.h"

/// @brief Extension hook called before mnemonic is printed
/// @param pi Print info structure containing decoded instruction, buffer, and state
///
/// Default implementation does nothing. Overriden by xedext.
void xed_disas_ext_pre_mnemonic(xed_print_info_t* pi);

static XED_INLINE void xed_pi_strcat(xed_print_info_t* pi,
                                     char const* str)
{
    xed_assert(pi != NULL && pi->buf != NULL);
    xed_assert(str != NULL);
    pi->blen = xed_strncat(pi->buf, str, pi->blen);
}

static XED_INLINE void xed_prefixes(xed_print_info_t* pi,
                                    char const* prefix)
{
    xed_assert(pi != NULL && prefix != NULL);
    if (pi->emitted == 0 && pi->format_options.xml_a)
        xed_pi_strcat(pi,"<PREFIXES>");
    if (pi->emitted)
        xed_pi_strcat(pi," ");
    xed_pi_strcat(pi,prefix);
    pi->emitted=1;
}

#endif
