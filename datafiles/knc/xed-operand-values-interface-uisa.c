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


/* The code in this file is used to override the corresponding XED library
 * functions in a different file in the main XED sources. This code is for
 * the disp8*N handling used in EVEX encodings.  The files.cfg file
 * controls the file replacement.
 */

#include "xed-internal-header.h"
#include "xed-operand-values-interface.h"
#include "xed-util.h"
#include "xed-init-pointer-names.h"
#include "xed-operand-ctype-enum.h"
#include "xed-operand-ctype-map.h"
#include "xed-reg-class.h"
#include <string.h> //memset



xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits_raw(
    const xed_operand_values_t* p)
{
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    return xed3_operand_get_disp_width(p);
}

xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits(
    const xed_operand_values_t* p)
{
    xed_uint32_t raw_width;
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    raw_width = xed3_operand_get_disp_width(p);
    if (raw_width == 8) {
          xed_int64_t nelem = xed3_operand_get_nelem(p);
          if (nelem) {
              xed_int64_t element_size = xed3_operand_get_element_size(p); 
              if (element_size * nelem  > 1) //FIXME bad test
                  // just double the apparent width because the most UISA
                  // will do is multiply by 64.
                  return 16; 
          }
    }
    return raw_width;
}


xed_int64_t  xed_operand_values_get_memory_displacement_int64(
    const xed_operand_values_t* p)
{
    unsigned int len;
    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    
    len = xed3_operand_get_disp_width(p);
    switch(len) {
      case 8: {
          xed_int64_t odisp;
          xed_int64_t disp = xed3_operand_get_disp(p);
          xed_int64_t nelem = xed3_operand_get_nelem(p);
          
          // converted to bytes
          xed_int64_t element_size = xed3_operand_get_element_size(p)>>3; 


          // the loadunpack & packstore instructions ignore the number of
          // elements
          if (xed3_operand_get_no_scale_disp8(p))
              nelem = 1;
          
          odisp = disp * nelem * element_size;
          /* printf("DISP: " XED_FMT_LX16 " NELEM
                    " XED_FMT_LD " SIZE " XED_FMT_LD
                    " ODISP: " XED_FMT_LX16 "\n",
                         disp ,nelem, element_size , odisp); */
          if (nelem)
              return odisp;
          else
              return disp;
      }
      case 16:
      case 32:
      case 64: return xed3_operand_get_disp(p);
      default:
        return 0;
    }
}

#include "xed-ild.h"

xed_int64_t
xed_operand_values_get_memory_displacement_int64_raw(
    const xed_operand_values_t* p)
{
    unsigned int len;

    if (xed_operand_values_has_memory_displacement(p) == 0)
        return 0;
    
    len = xed3_operand_get_disp_width(p); //bits
    switch(len) {
      case 8: 
      case 16:
      case 32:
      case 64:
        return xed3_operand_get_disp(p);
      default:
        return 0;
    }
}



