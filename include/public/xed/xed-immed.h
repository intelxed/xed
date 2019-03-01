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
/// @file xed-immed.h
/// 

#ifndef XED_IMMED_H
# define XED_IMMED_H

#include "xed-types.h"
#include "xed-common-defs.h"
#include "xed-util.h"

XED_DLL_EXPORT xed_int64_t xed_immed_from_bytes(xed_int8_t* bytes, xed_uint_t n);
    /*
      Convert an array of bytes representing a Little Endian byte ordering
      of a number (11 22 33 44 55.. 88), in to a a 64b SIGNED number. That gets
      stored in memory in little endian format of course. 

      Input 11 22 33 44 55 66 77 88, 8
      Output 0x8877665544332211  (stored in memory as (lsb) 11 22 33 44 55 66 77 88 (msb))

      Input f0, 1
      Output 0xffff_ffff_ffff_fff0  (stored in memory as f0 ff ff ff   ff ff ff ff)

      Input f0 00, 2
      Output 0x0000_0000_0000_00F0 (stored in memory a f0 00 00 00  00 00 00 00)

      Input 03, 1
      Output 0x0000_0000_0000_0030 (stored in memory a 30 00 00 00  00 00 00 00)
    */


#endif
