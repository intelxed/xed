/* BEGIN_LEGAL 

Copyright (c) 2024 Intel Corporation

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
#include "xed-decode.h"       // external interface to decoder
#include "xed-error-enum.h"
#include "xed-decoded-inst.h"
#include "xed-operand-storage.h"
#include "xed-tables-extern.h"
#include "xed-internal-header.h"
#include "xed-isa-set.h"
#include "xed-ild-private.h"
#include "xed3-static-decode.h"
#include "xed3-dynamic-decode.h"
#include "xed3-dynamic-part1-capture.h"  //FIXME fix filename
#include "xed-chip-features.h"
#include "xed-chip-features-private.h" // for xed_test_features()
#include "xed-chip-features-table.h"
#include "xed-chip-modes.h"
#include "xed-reg-class.h"

//////////////////////////////////////////////////////////////////////////////

#if defined(XED_AVX)
static xed_uint_t reg_id_avx2(xed_reg_enum_t r) {
    xed_reg_class_enum_t reg_class =  xed_reg_class(r);
    if (reg_class == XED_REG_CLASS_YMM)
        return r - XED_REG_YMM0;
    return r - XED_REG_XMM0;
}
 
static void check_avx2_gathers(xed_decoded_inst_t* xds) {
    // compare by register id because reg width (ymm vs xmm) can vary.
    xed_uint_t indx_id = reg_id_avx2(xed3_operand_get_index(xds));
    xed_uint_t dest_id = reg_id_avx2(xed3_operand_get_reg0(xds));
    xed_uint_t mask_id = reg_id_avx2(xed3_operand_get_reg1(xds));
    // the 3 regs (dest, mask and index) cannot be the same.
    if (indx_id == mask_id ||
        indx_id == dest_id ||
        mask_id == dest_id )
    {
        xed3_operand_set_error(xds,XED_ERROR_GATHER_REGS);
    }
}
# if defined(XED_SUPPORTS_AVX512)
static xed_uint_t reg_id_avx512(xed_reg_enum_t r) {
    xed_reg_class_enum_t reg_class =  xed_reg_class(r);
    if (reg_class == XED_REG_CLASS_ZMM)
        return r - XED_REG_ZMM0;
    if (reg_class == XED_REG_CLASS_YMM)
        return r - XED_REG_YMM0;
    return r - XED_REG_XMM0;
}
static void check_avx512_gathers(xed_decoded_inst_t* xds) {
    // compare by register id because reg width (ymm vs xmm) can vary.
    // index cannot be same as dest on avx512 gathers
    xed_uint_t indx_id = reg_id_avx512(xed3_operand_get_index(xds));
    xed_uint_t dest_id = reg_id_avx512(xed3_operand_get_reg0(xds));
    if (indx_id == dest_id)
        xed3_operand_set_error(xds,XED_ERROR_GATHER_REGS);

}
# endif
#endif
#if defined(XED_ATTRIBUTE_NO_SRC_DEST_MATCH_DEFINED)
static void check_src2_dest_match(xed_decoded_inst_t* xds) {
    xed_reg_enum_t srcx; 
    xed_reg_enum_t dest = xed3_operand_get_reg0(xds);
    xed_reg_enum_t srcy = xed3_operand_get_reg2(xds);
    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_MASKOP_EVEX)) 
        srcx = xed3_operand_get_reg3(xds); 
    else 
        srcx = xed3_operand_get_reg1(xds);
    // works fine if 2nd src is a memop
    if (dest == srcx || dest == srcy)
        xed3_operand_set_error(xds,XED_ERROR_BAD_REG_MATCH);
}
#endif

#if defined(XED_ATTRIBUTE_NO_REG_MATCH_DEFINED)
/* this is essentially targeted at AMX instructions but applies to others (e.g. POP2{,P})
   The check could be more robust to allow ignoring even more registers or by allowing
   compares exclusively to type-exact registers
*/
static XED_INLINE void check_all_regs_match(xed_decoded_inst_t* xds) {
    /* Check that the first, second and third registers do not match */
    xed_reg_enum_t reg1;
    xed_reg_enum_t reg0 = xed3_operand_get_reg0(xds);
    xed_reg_enum_t reg2 = xed3_operand_get_reg2(xds);

    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_MASKOP_EVEX)) 
        reg1 = xed3_operand_get_reg3(xds); 
    else
        reg1 = xed3_operand_get_reg1(xds);

    if (reg0 == reg1 || reg1 == reg2 || reg0 == reg2)
        xed3_operand_set_error(xds,XED_ERROR_BAD_REG_MATCH);
}
#endif

static XED_INLINE void
xed_decode_finalize_operand_storage_fields(xed_decoded_inst_t* xds)
{
    // if something is found to be in-error, you must set xed3_operand_get_error(xds)!

    if ( xed3_operand_get_lock(xds) &&
         !xed_decoded_inst_get_attribute(xds,XED_ATTRIBUTE_LOCKED)) {
        // operation cannot take a LOCK prefix, but one was found.
        xed3_operand_set_error(xds,XED_ERROR_BAD_LOCK_PREFIX);
        return;
    }

    /* We only keep real reps, MPX reps, HLE reps. Refining reps can just
     mess up subsequent encodes if the iclass or operands get changed by
     the user. */

#if 0 // FIXME: Do we want this?
    if (xed3_operand_get_rep(xds) &&
        !xed_decoded_inst_get_attribute(xds,XED_ATTRIBUTE_REP))
    {
        if (!xed_decoded_inst_has_mpx_prefix(xds) &&
            !xed_decoded_inst_is_xrelease(xds) &&
            !xed_decoded_inst_is_xacquire(xds) )
        {
            xed3_operand_set_rep(xds,0); // clear refining REP
        }
    }
#endif

#if defined(XED_ATTRIBUTE_NO_SRC_DEST_MATCH_DEFINED)
    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_NO_SRC_DEST_MATCH)) {
        check_src2_dest_match(xds);
    }
#endif
#if defined(XED_ATTRIBUTE_NO_REG_MATCH_DEFINED)
    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_NO_REG_MATCH)) {
        check_all_regs_match(xds);
    }
#endif
    
#if defined(XED_AVX)        
    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_GATHER))
    {
        if (xed_decoded_inst_get_extension(xds) == XED_EXTENSION_AVX2GATHER)
            check_avx2_gathers(xds);
# if defined(XED_SUPPORTS_AVX512)  
        else if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_MASKOP_EVEX))
            check_avx512_gathers(xds);
# endif // XED_SUPPORTS_AVX512
    }
#endif // XED_AVX

#if defined(XED_MPX)
    // BNDLDX/BNDSTX disallow RIP-relative operation in 64b mode.
    //
    // FIXME: Expressing this in the grammar causes the NOP hashtable to be
    // too big.
    if (xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_NO_RIP_REL))
        if (xed3_operand_get_rm(xds) == 5 && xed3_operand_get_mod(xds) == 0)
            if (xed3_operand_get_mode(xds)==2)  // 64b mode
                xed3_operand_set_error(xds,XED_ERROR_GENERAL_ERROR);
#endif
    if (xed3_operand_get_realmode(xds)!=0) {
        // Illegal for VEX/EVEX or PROTECTED_MODE instructions
        if (xed3_operand_get_vexvalid(xds) || 
            xed_decoded_inst_get_attribute(xds, XED_ATTRIBUTE_PROTECTED_MODE)) {
            // SEP/SMX legality is also CPL-dependent -> Skip check.
            if (xed_decoded_inst_get_isa_set(xds) != XED_ISA_SET_SEP &&
                xed_decoded_inst_get_isa_set(xds) != XED_ISA_SET_SMX) {
                    xed3_operand_set_error(xds,XED_ERROR_INVALID_MODE);
            }
        }
    }
}




xed_error_enum_t 
xed_decode_with_features(xed_decoded_inst_t* xedd, 
                         const xed_uint8_t* itext, 
                         const unsigned int bytes,
                         xed_chip_features_t* chip_features)
{
    xed_error_enum_t error;
    unsigned int tbytes = bytes;
    xed_chip_enum_t chip = xed_decoded_inst_get_input_chip(xedd);
    xed_features_elem_t const* features = 0;
    if (chip_features) {
        features = chip_features->f;
    }
    else if (chip != XED_CHIP_INVALID) {
        features = xed_get_features(chip);
    }

    set_chip_modes(xedd, chip, features);

    xedd->_byte_array._dec = itext;
    
    /* max_bytes says ILD how many bytes it can read */    
    if (tbytes > XED_MAX_INSTRUCTION_BYTES)
        tbytes = XED_MAX_INSTRUCTION_BYTES;
    xed3_operand_set_max_bytes(xedd, tbytes);

    
    /* Do the instruction length decode*/
    xed_instruction_length_decode(xedd);
    
    /* check ILD-specific decoding errors */
    if (xed3_operand_get_error(xedd)) 
        return xed3_operand_get_error(xedd);

    /* part1 is the NTs that come before the INSTRUCTIONS NT (OSZ, ASZ
     * nonterminals)*/
    xed3_dynamic_decode_part1(xedd);
    if (xed3_operand_get_error(xedd)) 
        return xed3_operand_get_error(xedd);
    
    /* lookup the xed_inst_t */
    xed3_static_decode(xedd);

    if (xed_decoded_inst_get_iform_enum(xedd) == XED_IFORM_INVALID)
        return XED_ERROR_GENERAL_ERROR;

    /* capture all the Nts that come in patterns */
    xed3_dynamic_decode_part2(xedd);
    if (xed3_operand_get_error(xedd)) 
        return xed3_operand_get_error(xedd);

    /* capture the operands */
    xed3_decode_operands(xedd);
    if (xed3_operand_get_error(xedd)) 
        return xed3_operand_get_error(xedd);
    
    xed_decode_finalize_operand_storage_fields(xedd);

    error = xed3_operand_get_error(xedd);
    if (error == XED_ERROR_NONE && features)
    {
        const xed_isa_set_enum_t isa_set = xed_decoded_inst_get_isa_set(xedd);
        if (!xed_test_features(features, isa_set))
        {
            return XED_ERROR_INVALID_FOR_CHIP;
        }
#if defined(XED_APX)
        // Check legacy instructions with APX repurposed prefix bits
        if (!decoder_supports_apx(xedd) && xed_classify_apx(xedd))
        {
            return XED_ERROR_INVALID_FOR_CHIP;
        }
#endif
    }
    return error;
}

xed_error_enum_t 
xed_decode(xed_decoded_inst_t* xedd, 
           const xed_uint8_t* itext, 
           const unsigned int bytes)
{
    return xed_decode_with_features(xedd, itext, bytes, 0);
}
