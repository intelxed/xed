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

#if !defined(XED_DECODER_MODES)
# define XED_DECODER_MODES

# include "xed-chip-enum.h"
# include "xed-decoded-inst.h"
# include "xed-chip-features.h"

/// Set decoder modes and state which reflect ISA support. This function 
/// sets the decoder state according to the selected ISA variation (given by a chip 
/// or chip_features) for encodings that can translate into different instructions 
/// (e.g., NOP vs. PREFETCH). Additionally, it disables ILD (Instruction Length Decoder) 
/// and decoder support for certain major architectures such as AVX512 and APX.
/// 
/// @param xedd a #xed_decoded_inst_t for a decoded instruction.
/// @param chip An enumeration specifying the target chip.
/// @param chip_features A pointer to a structure defining the chip features.
XED_DLL_EXPORT void 
xed_set_decoder_modes(xed_decoded_inst_t* xedd,
                      xed_chip_enum_t chip,
                      xed_chip_features_t const*const chip_features);

#endif
