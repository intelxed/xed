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

/// @file xed-ild-extension.c
/// Default stub for ILD segment extension (overrideable by xedext)

#include "xed-internal-header.h"
#include "xed-ild-extension.h"

/* Default stub does nothing. xedext can override via replace-source. */
void xed_ild_ext_seg_fixup(xed_decoded_inst_t* d,
                           xed_uint8_t last_seg,
                           xed_uint8_t last_seg64)
{
    (void)d; (void)last_seg; (void)last_seg64;
}
