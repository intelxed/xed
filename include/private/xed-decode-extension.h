/* BEGIN_LEGAL 

Copyright (c) 2026 Intel Corporation

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

/// @file xed-decode-extension.h
/// Post-decode extension hook (overrideable by xedext)

#if !defined(XED_DECODE_EXTENSION_H)
# define XED_DECODE_EXTENSION_H

#include "xed-decoded-inst.h"

/// Called after a successful full decode.
/// The default stub is a no-op; xedext can replace xed-decode-extension.c
/// to inject post-decode fixup logic.
void xed_decode_finalize_ext(xed_decoded_inst_t* d);

#endif /* XED_DECODE_EXTENSION_H */
