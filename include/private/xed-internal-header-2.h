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
/// @file xed-internal-header-2.h
/// 


#if !defined(XED_INTERNAL_HEADER2_H)
# define XED_INTERNAL_HEADER2_H
#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-util.h"
#include "xed-types.h"
#include "xed-operand-ctype-enum.h" // a generated file
#include "xed-reg-enum.h" // a generated file
#include "xed-reg-class-enum.h" // a generated file
#include "xed-operand-enum.h" // a generated file
#include "xed-operand-storage.h" // a generated file
#include "xed-operand-visibility-enum.h" // a generated file
#include "xed-operand-action-enum.h" // a generated file
#include "xed-nonterminal-enum.h" // a generated file
#include "xed-operand-width-enum.h" // a generated file
#include "xed-iform-enum.h" // a generated file
#include "xed-operand-element-xtype-enum.h" // a generated file
#include "xed-inst.h"
#include "xed-inst-private.h"
#include "xed-ild-private.h"
#if defined(XED_ENCODER)
# include "xed-encode.h"
#endif
#include "xed-tables-extern.h"
#include "xed-error-enum.h"
#include "xed-flags.h"
#include "xed-operand-action.h"
#include "xed-cpuid-rec.h"
#include "xed-cpuid-bit-enum.h"

struct xed_decoded_inst_s; //fwd-decl

typedef void (*xed_lookup_function_pointer_t)(struct xed_decoded_inst_s* xds);

#endif
