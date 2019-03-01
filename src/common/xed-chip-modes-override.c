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

/* this function is called by set_chip_modes in xed-chip-modes.c to add new
 * functionality in extended builds for setting modes that cannot be placed
 * in the public sources. */

#include "xed-chip-modes-override.h"
void xed_chip_modes_override(xed_decoded_inst_t* xedd,
                             xed_chip_enum_t chip,
                             xed_chip_features_t* features)
{
    // empty function
    (void) xedd; // pacify compiler
    (void) chip;
    (void) features;
}
