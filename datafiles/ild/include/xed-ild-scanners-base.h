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

/// @file xed-ild-scanners.h
/// instruction length decoder scanners 
    
#if !defined(XED_ILD_SCANNERS_BASE_H)
# define XED_ILD_SCANNERS_BASE_H
#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-types.h"

void xed_ild_scanners_init(void) {
    xed_ild_operator_init(&prefix_op,"prefix", prefix_scanner);

#if defined(XED_AVX) 
    xed_ild_operator_init(&vex_op,"vex", vex_scanner);
       
    xed_ild_operator_init(&vex_opcode_op, "vex_opcode", vex_opcode_scanner);
#  if defined(XED_AMD_ENABLED)
    xed_ild_operator_init(&xop_op,    "xop_opcode",    xop_scanner);
#  endif
    xed_ild_operator_init(&vex_c4_op, "vex_c4_opcode", vex_c4_scanner);
    xed_ild_operator_init(&vex_c5_op, "vex_c5_opcode", vex_c5_scanner);
#endif    
    
    xed_ild_operator_init(&opcode_op,"opcode", opcode_scanner);
    xed_ild_operator_init(&modrm_op,"modrm", modrm_scanner);
    xed_ild_operator_init(&sib_op,"sib", sib_scanner);
    xed_ild_operator_init(&disp_op,"disp", disp_scanner);
    xed_ild_operator_init(&imm_op,"imm", imm_scanner);

    xed_add_ild_operator(&prefix_op);
#if defined(XED_AVX) 
    xed_add_ild_operator(&vex_op);
#endif
    xed_add_ild_operator(&opcode_op);
    xed_add_ild_operator(&modrm_op);
    xed_add_ild_operator(&sib_op);
    xed_add_ild_operator(&disp_op);
    xed_add_ild_operator(&imm_op);
}


#endif

