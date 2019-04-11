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
/// @file xed-tables-extern.H
/// 

#if !defined(XED_TABLES_EXTERN_H)
# define XED_TABLES_EXTERN_H

#include "xed-gen-table-defs.h" // a generated file
#if defined(XED_ENCODER)
# include "xed-encoder-gen-defs.h" // a generated file
#endif
#include "xed-inst.h"
#include "xed-reg-class-enum.h" // a generated file
#include "xed-operand-width-enum.h" // a generated file
#include "xed-operand-element-xtype-enum.h" // a generated file
#include "xed-flags.h"
#include "xed-flags-private.h"
#include "xed-operand-element-type-enum.h" // a generated file
#include "xed-operand-type-info.h"
#if defined(XED_ENCODER)
# include "xed-encode-types.h"
#endif
#define XED_GLOBAL_EXTERN extern
#include "xed-tables.h"
#undef  XED_GLOBAL_EXTERN
#if defined(XED_ENCODER)
# include "xed-encode.h"
# include "xed-encode-private.h"
#endif

#endif
