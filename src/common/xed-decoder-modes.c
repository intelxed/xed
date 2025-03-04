/* BEGIN_LEGAL 

Copyright (c) 2024 Intel Corporation

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

#include "xed-chip-features-table.h"
#include "xed-chip-modes.h"
#include "xed-decoder-modes.h"

void xed_set_decoder_modes(xed_decoded_inst_t *xedd,
                           xed_chip_enum_t chip,
                           xed_chip_features_t const*const chip_features)
{
    xed_features_elem_t const* features = 0;
    if (chip_features) {
        features = chip_features->f;
    }
    else if (chip != XED_CHIP_INVALID) {
        features = xed_get_features(chip);
    }

    set_chip_modes(xedd, chip, features);
}
