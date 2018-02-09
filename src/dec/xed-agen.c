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
/// @file xed-agen.c
#include "xed-agen.h"
#include "xed-decoded-inst-api.h"

static xed_register_callback_fn_t     register_callback = 0;
static xed_segment_base_callback_fn_t segment_callback = 0;

void xed_agen_register_callback(xed_register_callback_fn_t register_fn,
                                xed_segment_base_callback_fn_t segment_fn) {
    register_callback = register_fn;
    segment_callback = segment_fn;
}

xed_error_enum_t xed_agen(xed_decoded_inst_t* xedd,
                          unsigned int memop_index,
                          void* context,
                          xed_uint64_t* out_address) {
    xed_uint64_t out = 0;
    // Normal memops: BASE+INDEX*SCALE+DISPLACMENT
    xed_uint64_t base_value = 0;
    xed_uint64_t index_value = 0;
    xed_uint64_t segment_base = 0;
    xed_uint64_t scale  = 0;
    xed_int64_t displacement = 0;
    xed_operand_values_t* xedv =  0;
    xed_uint32_t addr_width =  0;
    xed_uint32_t opnd_width =  0;
    xed_bool_t real_mode = 0;
    xed_bool_t error=0;
    xed_reg_enum_t base_reg = XED_REG_INVALID;
    xed_reg_enum_t seg_reg = XED_REG_INVALID;
    xed_attribute_enum_t attr;

    if (xedd == 0)
        return XED_ERROR_GENERAL_ERROR;
    if (memop_index != 0 &&  memop_index != 1)
        return XED_ERROR_BAD_MEMOP_INDEX;
    if (register_callback == 0) 
        return XED_ERROR_NO_AGEN_CALL_BACK_REGISTERED;
    if (segment_callback == 0) 
        return XED_ERROR_NO_AGEN_CALL_BACK_REGISTERED;


    xedv = xed_decoded_inst_operands(xedd);

    addr_width =  xed_operand_values_get_effective_address_width(xedv);

    //16,32,64
    opnd_width =  xed_operand_values_get_effective_operand_width(xedv); 
    real_mode  =  xed_operand_values_get_real_mode(xedv);

    base_reg = xed_decoded_inst_get_base_reg(xedd,memop_index);
    if (base_reg != XED_REG_INVALID)
        base_value = (*register_callback)(base_reg, context, &error);
    if (error)
        return XED_ERROR_CALLBACK_PROBLEM;

    if (memop_index == 1) 
        attr = XED_ATTRIBUTE_STACKPUSH1;
    else
        attr = XED_ATTRIBUTE_STACKPUSH0;
    if (xed_decoded_inst_get_attribute(xedd,attr)) {
        base_value = base_value - (opnd_width>>3);
    }

    seg_reg  = xed_decoded_inst_get_seg_reg(xedd,memop_index);
    if (seg_reg != XED_REG_INVALID) {
        if (real_mode) {
            // selectors are values in real mode 
            segment_base = (*register_callback)(seg_reg, context, &error);
            segment_base <<= 4;
        }
        else {
            segment_base = (*segment_callback)(seg_reg, context, &error); 
        }
        if (error)
            return XED_ERROR_CALLBACK_PROBLEM;
    }

    if (memop_index == 0) {
        xed_reg_enum_t index_reg;
        index_reg = xed_decoded_inst_get_index_reg(xedd,memop_index);
        if (index_reg != XED_REG_INVALID) {
            index_value = (*register_callback)(index_reg, context, &error);
            if (error)
                return XED_ERROR_CALLBACK_PROBLEM;

            scale = xed_decoded_inst_get_scale(xedd,0); 
        }
        displacement = xed_decoded_inst_get_memory_displacement(xedd,0);
    }

    if (addr_width == 64) {
        xed_int64_t base64 = base_value;
        xed_int64_t index64 = index_value;
        xed_int64_t disp64 = displacement;
        xed_int64_t ea64 = base64  + index64 * scale + disp64;
        xed_int64_t lin64 = segment_base + ea64;
        out = lin64;
    }
    else if (addr_width == 32) {
        xed_int32_t base32 = base_value;
        xed_int32_t index32 = index_value;
        xed_int32_t disp32 = displacement;
        xed_int32_t ea32 = base32  + index32 * scale + disp32;
        xed_int32_t lin32 = segment_base + ea32;
        out = lin32;
        // FIXME: big real mode!
    }
    else if (addr_width == 16) {
        xed_int16_t base16 = base_value;
        xed_int16_t index16 = index_value;
        xed_int16_t disp16 = displacement;
        xed_int16_t ea16 = base16  + index16 * scale + disp16;
        xed_int32_t lin32 = segment_base + ea16;
        if (real_mode) {
            xed_uint32_t masked20 = lin32 & 0x000FFFFF;
            out = masked20;
        }
        else 
            out = lin32;
    }

    // RIP-rel 32b -- 67 prefixed rip-rel stuff in 64b mode. FIXME
    
    if (out_address)
        *out_address = out;
    else
        return XED_ERROR_NO_OUTPUT_POINTER;
    return XED_ERROR_NONE;
}

