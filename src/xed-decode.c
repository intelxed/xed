/*BEGIN_LEGAL 

Copyright (c) 2016 Intel Corporation

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
#include "xed-chip-features-private.h" // for xed_test_chip_features()
#include "xed-chip-modes.h"

//////////////////////////////////////////////////////////////////////////////

#if defined(XED_ILD_CHECK)
#include "xed-ild.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

#define XED_ILD_CMP_BUFLEN 1024
#define XED_ILD_CHECK_MAX_ERR 1

static void xedex_derror(const char* s) {
    //we want to assert after XED_ILD_CHECK_MAX_ERR divergences
    static unsigned int err_count = 0;
    printf("\n[XED_ILD_CHECK_ERROR] %s\n",s);
    err_count++;
    if (err_count == XED_ILD_CHECK_MAX_ERR) {
        exit(1);
    }
}

static void xed_print_hex_line(char* buf, const xed_uint8_t* array, 
                               const int length, const int buflen) {
  const xed_bool_t uppercase=0;
  int n = length;
  int i=0;
  if (length == 0)
      n = XED_MAX_INSTRUCTION_BYTES;
  assert(buflen >= (2*n+1)); /* including null */
  for( i=0 ; i< n; i++)     {
      buf[2*i+0] = xed_to_ascii_hex_nibble(array[i]>>4, uppercase);
      buf[2*i+1] = xed_to_ascii_hex_nibble(array[i]&0xF, uppercase);
  }
  buf[2*i]=0;
}

static void print_hex_line(const xed_uint8_t* p, unsigned int length) {
    char buf[XED_ILD_CMP_BUFLEN];
    unsigned int lim = XED_ILD_CMP_BUFLEN/2;
    if (length < lim)
        lim = length;
    xed_print_hex_line(buf,p, lim, XED_ILD_CMP_BUFLEN); 
    printf("%s\n", buf);
}

static void xed_ild_inst_dump(const xed_decoded_inst_t* p, char* buf, int buflen)  {
    char* t=buf;
    int blen = buflen;
    blen = xed_strncpy(t, "ILD INST:\n", blen);
    t = buf + xed_strlen(buf);
    xed_operand_values_print_short( xed_decoded_inst_operands_const(p), t, blen);
}

static void xed_ild_error(const xed_decoded_inst_t* xedd, 
                          const xed_decoded_inst_t* ild) {
    char buf[XED_ILD_CMP_BUFLEN] = {0};
    xed_uint_t xed2_length = xed_decoded_inst_get_length(xedd);
    xed_decoded_inst_dump(xedd, buf, XED_ILD_CMP_BUFLEN);
    printf("xedd:\n%s\n",  buf);
    print_hex_line(xedd->_byte_array._dec, xed2_length);
    xed_ild_inst_dump(ild,  buf, XED_ILD_CMP_BUFLEN);
    printf("ild:\n%s\n",  buf);
    print_hex_line(ild->_byte_array._dec, xed2_length);
    xedex_derror("ILD CMP FAILURE");
}

static void xed_ild_cmp_member(xed_uint_t xed2_res, xed_uint_t ild_res,
    const char* format_str, const xed_decoded_inst_t* xedd, 
    const xed_decoded_inst_t* ild) {
    if (ild_res != xed2_res) {
        printf(format_str, xed2_res, ild_res);
        xed_ild_error(xedd, ild);
    }
}

static void xed_ild_cmp(const xed_decoded_inst_t* xedd, 
                        const xed_decoded_inst_t* ild) {
    xed_uint_t ild_res = 0;
    xed_uint_t xed2_res = 0;

    /*FIXME: automate it somehow?*/

    /* check all relevant information */
    ild_res = xed_decoded_inst_get_length(ild);
    xed2_res = xed_decoded_inst_get_length(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "ILD length differs! xed2_length=%d ild_length=%d\n", xedd, ild);
    
    
    ild_res = xed3_operand_get_asz(ild);
    xed2_res = xed3_operand_get_asz(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "ASZ differs! xed2_asz=%d ild_asz=%d\n", xedd, ild);


    ild_res = xed3_operand_get_prefix66(ild);
    xed2_res = xed3_operand_get_prefix66(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "PREFIX66 differs! xed2_res=%d ild_res=%d\n", xedd, ild);

    ild_res = xed3_operand_get_rep(ild);
    xed2_res = xed3_operand_get_rep(xedd);
    if ((ild_res == 1 && xed2_res != 2) ||
        (ild_res == 0 && xed2_res == 2)) {
        printf("F2 differs! xed2_rep=%d ild_rep=%d\n", 
            xed2_res, ild_res);
        xed_ild_error(xedd, ild);
    }

    ild_res = xed3_operand_get_lock(ild);
    xed2_res = xed3_operand_get_lock(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "LOCK differs! xed2_lock=%d ild_lock=%d\n", xedd, ild);

    ild_res = xed3_operand_get_seg_ovd(ild);
    xed2_res = xed3_operand_get_seg_ovd(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "SEG_OVD differs! xed2_res=%d ild_res=%d\n", xedd, ild);

    /* HINT is reassigned sometimes, so we cannot compare it after
     * ILD
     */
    /*
    ild_res = xed3_operand_get_hint(ild);
    xed2_res = xed3_operand_get_hint(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "HINT differs! xed2_res=%d ild_res=%d\n", xedd, ild);
        */

    if (xed3_operand_get_modrm(xedd)) {
        ild_res = xed3_operand_get_mod(ild);
        xed2_res = xed3_operand_get_mod(xedd);
        xed_ild_cmp_member(xed2_res, ild_res, 
            "MOD differs! xed2_res=%d ild_res=%d\n", xedd, ild);

        ild_res = xed3_operand_get_reg(ild);
        xed2_res = xed3_operand_get_reg(xedd);
        xed_ild_cmp_member(xed2_res, ild_res, 
            "REG differs! xed2_res=%d ild_res=%d\n", xedd, ild);

        ild_res = xed_ild_get_rm(ild);
        xed2_res = xed3_operand_get_rm(xedd);
        xed_ild_cmp_member(xed2_res, ild_res, 
            "RM differs! xed2_res=%d ild_res=%d\n", xedd, ild);

    }

    ild_res = xed3_operand_get_sibscale(ild);
    xed2_res = xed3_operand_get_sibscale(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "SIBSCALE differs! xed2_res=%d ild_res=%d\n", xedd, ild);

    ild_res = xed3_operand_get_sibindex(ild);
    xed2_res = xed3_operand_get_sibindex(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "SIBINDEX differs! xed2_res=%d ild_res=%d\n", xedd, ild);

    ild_res = xed3_operand_get_sibbase(ild);
    xed2_res = xed3_operand_get_sibbase(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "SIBBASE differs! xed2_res=%d ild_res=%d\n", xedd, ild);
    
    /*FIXME: VEX operands ? */

    /* displacement width in xed2 has some problems ... 
    ild_res = ild->disp_bytes;
    xed2_res = xed_decoded_inst_get_memory_displacement_width(xedd,0) +
        xed_decoded_inst_get_branch_displacement_width(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "disp_bytes differs! xed2_disp_bytes=%d ild_disp_bytes=%d\n",
        xedd, ild);
        */
    
    /* immediate is tricky since there is implicit IMM0 operand
    ild_res = ild->imm_bytes + ild->imm1_bytes;
    xed2_res = xed_decoded_inst_get_immediate_width(xedd);
    xed_ild_cmp_member(xed2_res, ild_res, 
        "imm_bytes differs! xed2_imm_bytes=%d ild_imm_bytes=%d\n", xedd, ild);
        */
}


static void xed3_static_decode_cmp(const xed_decoded_inst_t* xedd, 
    xed_decoded_inst_t* ild) {

    if (ild->_inst != xedd->_inst) {
        xed_uint32_t xed2_idx = 
            (xed_uint32_t)(xedd->_inst - &xed_inst_table[0]);
        xed_uint32_t xed3_idx = 
            (xed_uint32_t)(ild->_inst - &xed_inst_table[0]);
        printf("_inst differs! xed2_idx=%d xed3_idx=%d\n", 
            xed2_idx, xed3_idx);
        xed_ild_error(xedd, ild);
    }
}


static void check_ild(const xed_decoded_inst_t* xedd, 
                      const xed_uint8_t* itext) {
#if defined(XED_ILD_CHECK_VERBOSE)
    static unsigned int inst_count = 0;
#endif

    xed_decoded_inst_t ild_data;
    
    xed_decoded_inst_zero(&ild_data);

    xed3_operand_set_mode(&ild_data, xed3_operand_get_mode(xedd));
    
    xed_ild_decode(&ild_data, itext, XED_MAX_INSTRUCTION_BYTES);
    xed_ild_cmp(xedd, &ild_data);

    xed3_dynamic_decode_part1(&ild_data);
    xed3_static_decode(&ild_data);
    xed3_static_decode_cmp(xedd, &ild_data);
    xed3_dynamic_decode_part2(&ild_data);
    xed3_decode_operands(&ild_data);


#if defined(XED_ILD_CHECK_VERBOSE)
    inst_count++;
    printf("[XED_ILD_CHECK_LOG] #instructions = %d\n", inst_count);
#endif
}

#endif  // XED_ILD_CHECK

//////////////////////////////////////////////////////////////////////////////



#if defined(XED_AVX)
static void check_avx2_gathers(xed_decoded_inst_t* xds) {
    // the 3 regs (dest, mask and index) cannot be the same.
    if (xed3_operand_get_index(xds) == xed3_operand_get_reg1(xds) ||
        xed3_operand_get_index(xds) == xed3_operand_get_reg0(xds) ||
        xed3_operand_get_reg0(xds)  == xed3_operand_get_reg1(xds)   )
    {
        xed3_operand_set_error(xds,XED_ERROR_GATHER_REGS);
    }
}
# if defined(XED_SUPPORTS_AVX512)
static void check_avx512_gathers(xed_decoded_inst_t* xds) {
    // index cannot be same as dest on avx512 gathers
    if ( xed3_operand_get_index(xds) == xed3_operand_get_reg0(xds))
        xed3_operand_set_error(xds,XED_ERROR_GATHER_REGS);

}
#endif
#endif

static XED_INLINE void
xed_decode_finalize_operand_storage_fields(xed_decoded_inst_t* xds)
{
    // if something is found to be in-error, you must set xed3_operand_get_error(xds)!

    if (xed3_operand_get_lock(xds) && !xed_decoded_inst_get_attribute(xds,XED_ATTRIBUTE_LOCKED)) {
        // operation cannot take a LOCK prefix, but one was found.
        xed3_operand_set_error(xds,XED_ERROR_BAD_LOCK_PREFIX);
        return;
    }

    /* We only keep real reps, MPX reps, HLE reps. Refining reps can just
     mess up subsequent encodes if the iclass or operands get changed by
     the user. */

#if 0 // FIXME: DO NOT COMMIT
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
}




xed_error_enum_t 
xed_decode_with_features(xed_decoded_inst_t* xedd, 
                         const xed_uint8_t* itext, 
                         const unsigned int bytes,
                         xed_chip_features_t* features)
{
    xed_error_enum_t error;
    xed_chip_enum_t chip = xed_decoded_inst_get_input_chip(xedd);

    set_chip_modes(xedd, chip, features);
    xedd->_byte_array._dec = itext;

    /* max_bytes says ILD how many bytes it can read */
    xed3_operand_set_max_bytes(xedd, bytes);
    
    /* Do the instruction length decode*/
    xed_instruction_length_decode(xedd);
    
    /* check ILD-specific decoding errors */
    if (xed3_operand_get_error(xedd)) 
        return xed3_operand_get_error(xedd);

    /* part1 is all the Nts that come before the INSTRUCTIONS NT (OSZ, ASZ
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
    if (error == XED_ERROR_NONE) {
        if (chip != XED_CHIP_INVALID) {
            if (!xed_decoded_inst_valid_for_chip(xedd, chip))  {
                return XED_ERROR_INVALID_FOR_CHIP;
            }
        }
        if (features) {
            const xed_isa_set_enum_t isa_set = xed_decoded_inst_get_isa_set(xedd);
            if (!xed_test_chip_features(features, isa_set)) {
                return XED_ERROR_INVALID_FOR_CHIP;
            }
        }
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
