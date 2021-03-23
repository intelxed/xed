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

#include "xed-interface.h"
#include "xed-isa-set.h"
#include "xed-chip-features-private.h"

#include "xed-chip-modes-override.h"

static void
xed_chip_modes_wbnoinvd_cldemote(xed_decoded_inst_t* xedd,
                                 xed_chip_enum_t chip,
                                 xed_chip_features_t* features)
{
    // WBNOINVD repurposes an existing encoding (prefixed WBINVD) so we
    // need to rely on the xed chip to tell us which semantics are associated
    // with that encoding.
    
    xed_chip_features_t* f = features;
    xed_chip_features_t loc_features;
    if (f==0) {
        // if no features supplied, get default features for specified chip.
        xed_get_chip_features(&loc_features, chip);
        f = &loc_features;
    }
#if defined(XED_SUPPORTS_WBNOINVD)
    if (xed_test_chip_features(f, XED_ISA_SET_WBNOINVD)) 
        xed3_operand_set_wbnoinvd(xedd,1);
#endif
    if (xed_test_chip_features(f, XED_ISA_SET_CLDEMOTE))  
        xed3_operand_set_cldemote(xedd,1);
}


void
set_chip_modes(xed_decoded_inst_t* xedd,
               xed_chip_enum_t chip,
               xed_chip_features_t* features)
{
    xed_bool_t first_prefix = 0;
    xed_uint_t p4, lzcnt, tzcnt;

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
        first_prefix = 1;
        break;
        
      case XED_CHIP_QUARK:
        // Quark is PENTIUM ISA but not PENTIUM implementation
        first_prefix = 1;
        break;
        
      case XED_CHIP_PENTIUM:
      case XED_CHIP_PENTIUMREAL:
        xed3_operand_set_modep5(xedd,1);
        first_prefix = 1;
        break;
      case XED_CHIP_PENTIUMMMX:
      case XED_CHIP_PENTIUMMMXREAL:
        xed3_operand_set_modep5(xedd,1);
        xed3_operand_set_modep55c(xedd,1);
        first_prefix = 1;
        break;

      default:
        break;
    }

    xed_chip_modes_override(xedd, chip, features);  //replaceable function
    xed_chip_modes_wbnoinvd_cldemote(xedd, chip, features); 
    
    if (first_prefix)
        xed3_operand_set_mode_first_prefix(xedd,1);

    /* set the P4-ness for ISA-set rejection */
    p4 = 1;
    if (chip != XED_CHIP_INVALID)
        if ( xed_isa_set_is_valid_for_chip(XED_ISA_SET_PAUSE, chip) == 0 )
            p4 = 0;
    xed3_operand_set_p4(xedd,p4);

#if defined(XED_SUPPORTS_LZCNT_TZCNT)
    /* LZCNT / TZCNT show up on HSW. LZCNT has its own CPUID bit, TZCNT is on
     * BMI1.  */
    lzcnt = 1;
    tzcnt = 1;
    if (chip != XED_CHIP_INVALID) {
        if ( xed_isa_set_is_valid_for_chip(XED_ISA_SET_LZCNT, chip) == 0 )
            lzcnt = 0;
        if ( xed_isa_set_is_valid_for_chip(XED_ISA_SET_BMI1, chip) == 0 )
            tzcnt = 0;
    }
    if (features) {
        lzcnt = xed_test_chip_features(features, XED_ISA_SET_LZCNT);
        tzcnt = xed_test_chip_features(features, XED_ISA_SET_BMI1);
    }
    xed3_operand_set_lzcnt(xedd,lzcnt);
    xed3_operand_set_tzcnt(xedd,tzcnt);
#endif
    (void) lzcnt; (void) tzcnt; //pacify compiler

    if (chip != XED_CHIP_INVALID)  {
        if ( xed_isa_set_is_valid_for_chip(XED_ISA_SET_PPRO_UD0_SHORT, chip)  ) {
            xed3_operand_set_mode_short_ud0(xedd, 1);
        }
    }

}
