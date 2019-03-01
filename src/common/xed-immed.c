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
/// @file xed-immed.c
/// 

#include "xed-immed.h"
#include "xed-portability.h"

xed_int64_t xed_immed_from_bytes(xed_int8_t* bytes, xed_uint_t n) {
    /*
      See the header file.
    */

    xed_int64_t r;
    xed_union64_t m1, m2;
    int i;
    xed_uint8_t* ub = (xed_uint8_t*) bytes;
    m1.s.hi32 = 0xFFFFFFFF;
    m1.s.lo32 = 0;
    m2.s.hi32 = 0xFFFFFFFF;
    m2.s.lo32 = 0xFFFF0000;
    if (n == 0) 
        return 0;
    else if (n == 4) {
        r = (ub[3]<<24) | (ub[2]<<16) | (ub[1] << 8) | ub[0];
        if (bytes[3] < 0) {
            r = r | m1.i64;
        }
        return r;
    }
    else if (n == 1) 
        return bytes[0];
    else if (n == 8) {
        r = 0;
        for(i=n-1;i>=0;i--)
            r = (r << 8) |  ub[i];
        return r;
    }
    else if (n == 2) {
        r =  (ub[1] << 8) | ub[0];
        /*printf("(%x)", r); */
        if (bytes[1] < 0) {
            r = r | m2.i64;
        }
        return r;
    }
    xed_assert(n==0||n==1||n==2||n==4||n==8);
    return 0;
}
