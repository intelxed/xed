/* BEGIN_LEGAL 

Copyright (c) 2025 Intel Corporation

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

#include "xed-interface.h"
#include "xed-isa-set.h"
#include "xed-chip-features-private.h"
#include "xed-chip-features-table.h"
#include "xed-chip-modes.h"
#include "xed-chip-modes-override.h"


void
set_chip_modes(xed_decoded_inst_t* xedd,
               xed_chip_enum_t chip,
               xed_features_elem_t const*const features)
{
    /* Initializes chip-specific decoder behavior, independent of ISA-SETs */
    switch(chip) {
      case XED_CHIP_INVALID:
        break;
      case XED_CHIP_I86:
      case XED_CHIP_I86FP:
      case XED_CHIP_I186:
      case XED_CHIP_I186FP:
      case XED_CHIP_I286REAL:
      case XED_CHIP_I286:
      case XED_CHIP_I2186FP:
      case XED_CHIP_I386REAL:
      case XED_CHIP_I386:
      case XED_CHIP_I386FP:
      case XED_CHIP_I486REAL:
      case XED_CHIP_I486:
      case XED_CHIP_QUARK: // Quark is PENTIUM ISA but not PENTIUM implementation
        xed3_operand_set_mode_first_prefix(xedd, 1);
        break;

      case XED_CHIP_PENTIUM:
      case XED_CHIP_PENTIUMREAL:
      case XED_CHIP_PENTIUMMMX:
      case XED_CHIP_PENTIUMMMXREAL:
        xed3_operand_set_modep5(xedd, 1);
        xed3_operand_set_mode_first_prefix(xedd, 1);
        break;

      default:
        break;
    }

    /* Initializes decoder according to supported ISA-SETs */
    if (features)
    {
        xed_bool_t support;
        /* List of dual encoding instructions: depending on the host, a given encoding can be
        * interpreted as two different instructions.
        * For those, XED sets internal operands to support the matching ISA-SETs.
        */
        static const isa2op_t isa2op[] = {
            // `MODE_SHORT_UD0`: Control the `UD0` instruction length
            {XED_ISA_SET_PPRO_UD0_SHORT, XED_OPERAND_MODE_SHORT_UD0},
            // `P4`: Enables the `PAUSE` instruction (replacing a previous `NOP`)
            {XED_ISA_SET_PAUSE, XED_OPERAND_P4},
#if defined(XED_ISA_SET_ICACHE_PREFETCH_DEFINED)
            // `PREFETCHIT`: Enables the `PREFETCHIT{0,1}` instruction (replacing a previous `NOP`)
            {XED_ISA_SET_ICACHE_PREFETCH, XED_OPERAND_PREFETCHIT},
#endif
#if defined(XED_ISA_SET_MOVRS_DEFINED)
            // `PREFETCHRST`: Enables the `PREFETCHRST2` instruction (replacing a previous `NOP`)
            {XED_ISA_SET_MOVRS, XED_OPERAND_PREFETCHRST},
#endif
#if defined(XED_ISA_SET_WBNOINVD_DEFINED)
            // `WBNOINVD`: Enables the `WBNOINVD` instruction (replacing a previous `WBINVD`)
            {XED_ISA_SET_WBNOINVD, XED_OPERAND_WBNOINVD},
#endif
#if defined(XED_ISA_SET_CLDEMOTE_DEFINED)
            // `CLDEMOTE`: Enables the `CLDEMOTE` instruction (replacing a previous `NOP`)
            {XED_ISA_SET_CLDEMOTE, XED_OPERAND_CLDEMOTE},
#endif
#if defined(XED_SUPPORTS_LZCNT_TZCNT)
            // `LZCNT`: Enables the `LZCNT` instruction (replacing a previous `BSR`)
            {XED_ISA_SET_LZCNT, XED_OPERAND_LZCNT},
            // `TZCNT`: Enables the `TZCNT` instruction (replacing a previous `BSF`)
            {XED_ISA_SET_BMI1, XED_OPERAND_TZCNT},
#endif
#if defined(XED_MPX)
            // `MPXMODE`: Enables the `MPX` ISA-SET instructions (replacing a previous `NOP`)
            {XED_ISA_SET_MPX, XED_OPERAND_MPXMODE},
#endif
#if defined(XED_CET)
            // `CET`: Enables the `CET` ISA-SET instructions (replacing a previous `NOP`)
            {XED_ISA_SET_CET, XED_OPERAND_CET},
#endif
            // EO isa2op
            {XED_ISA_SET_INVALID, XED_OPERAND_INVALID}
        };

        set_decoder_control_ops(xedd, isa2op, features);

        /* set support of major architectures (mainly affects the XED ILD) */
        // AVX2
#if defined(XED_AVX)
        support = xed_test_features(features, XED_ISA_SET_AVX);
        xed3_operand_set_no_vex(xedd, !support);
#endif
        // AVX512
#if defined(XED_ISA_SET_AVX512F_SCALAR_DEFINED)
        support = xed_test_features(features, XED_ISA_SET_AVX512F_SCALAR); // Catches both SKX and KNL
#if defined(XED_ISA_SET_AVX512F_128_DEFINED)
        support |= xed_test_features(features, XED_ISA_SET_AVX512F_128); // For backwards compatibility (SKX only)
#endif
        xed3_operand_set_no_evex(xedd, !support);
#endif
#if defined(XED_APX)
        // APX
        support = xed_test_features(features, XED_ISA_SET_APX_F);
        xed3_operand_set_no_apx(xedd, !support);
#endif

        /* replaceable functions */
        xed_chip_modes_override1(xedd, chip, features);
        xed_chip_modes_override2(xedd, chip, features);
    }
}

