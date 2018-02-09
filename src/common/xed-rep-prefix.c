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
/// @file xed-decode.c

////////////////////////////////////////////////////////////////////////////
// This file contains the public interface to the decoder. Related code for
// decoded instructions is in xed-decoded-inst.cpp and xed-decode-impl.cpp
////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-rep-prefix.h"

xed_iclass_enum_t xed_rep_remove(xed_iclass_enum_t x)
{
    xed_iclass_enum_t norep = xed_norep_map(x);
    if (norep == XED_ICLASS_INVALID)
        return x;
    return norep;
}
