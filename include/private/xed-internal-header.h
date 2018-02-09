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
/// @file xed-internal-header.h
/// 



#if !defined(XED_INTERNAL_HEADER_H)
# define XED_INTERNAL_HEADER_H


#if defined(_WIN32) && defined(_MANAGED)
#pragma unmanaged
#endif

#include "xed-internal-header-2.h"

#include "xed-decoded-inst.h"
#include "xed-decoded-inst-api.h"
#include "xed-decoded-inst-private.h"
#include "xed-decode-supp.h"
#if defined(XED_ENCODER)
# include "xed-encode-isa-functions.h"
#endif

#endif
