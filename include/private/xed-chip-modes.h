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

#if !defined(XED_CHIP_MODES)
# define XED_CHIP_MODES

# include "xed-chip-enum.h"
# include "xed-decoded-inst.h"
# include "xed-chip-features.h"

void set_chip_modes(xed_decoded_inst_t* xedd,
                    xed_chip_enum_t chip,
                    xed_features_elem_t const*const features);
#endif
