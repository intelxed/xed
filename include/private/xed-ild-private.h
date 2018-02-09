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

/// @file xed-ild-private.h
/// instruction length decoder private header

#if !defined(XED_ILD_PRIVATE_H)
# define XED_ILD_PRIVATE_H




#include "xed-ild.h"
#include "xed-machine-mode-enum.h"
static XED_INLINE xed_uint_t xed_modrm_mod(xed_uint8_t m) { return m>>6; }
static XED_INLINE xed_uint_t xed_modrm_reg(xed_uint8_t m) { return (m>>3)&7; }
static XED_INLINE xed_uint_t xed_modrm_rm(xed_uint8_t m) { return m&7; }
static XED_INLINE xed_uint_t xed_sib_scale(xed_uint8_t m) { return m>>6; }
static XED_INLINE xed_uint_t xed_sib_index(xed_uint8_t m) { return (m>>3)&7; }
static XED_INLINE xed_uint_t xed_sib_base(xed_uint8_t m) { return m&7; }
static XED_INLINE xed_uint_t bits2bytes(xed_uint_t bits) { return bits>>3; }
static XED_INLINE xed_uint_t bytes2bits(xed_uint_t bytes) { return bytes<<3; }


typedef void(*xed_ild_l1_func_t)(xed_decoded_inst_t*);
typedef xed_uint32_t(*xed3_find_func_t)(const xed_decoded_inst_t*);

typedef struct {xed_uint32_t key; xed_uint32_t value;} lu1_entry_t;
typedef struct {xed_uint32_t key; xed3_find_func_t l2_func;} lu2_entry_t;


typedef enum {
    XED_ILD_MAP0,
    XED_ILD_MAP1, /* 0F */
    XED_ILD_MAP2, /* 0F38 */
    XED_ILD_MAP3, /* 0F3A */
    XED_ILD_MAP4,  /* required placeholders */
    XED_ILD_MAP5,
    XED_ILD_MAP6,
    XED_ILD_MAPAMD,   /* fake map 7 -  amd 3dnow */
    XED_ILD_MAP_XOP8, /* amd xop */
    XED_ILD_MAP_XOP9, /* amd xop */
    XED_ILD_MAP_XOPA, /* amd xop */
    XED_ILD_MAP_LAST,  /* for array sizing */
    XED_ILD_MAP_INVALID /* for error handling */
} xed_ild_map_enum_t;


#define XED_GRAMMAR_MODE_64 2
#define XED_GRAMMAR_MODE_32 1
#define XED_GRAMMAR_MODE_16 0

/*
Double immediate instructions are special. There are only 3 of them
and anyway they require a special care. It seems that the simplest way
is just to define L1 functions for both such map-opcode pairs:
(0x0F,0x78) and (0x0, 0xC8)
*/

/* (0x0f,0x78) map-opcode pair is even more special, because it has a conflict
on imm_bytes between AMD's INSERTQ,EXTRQ and Intel's VMREAD.
We already hardcode L1 functions for double immediate instructions, so we will
hardcode a conflict resolution here too. */
static XED_INLINE void xed_ild_hasimm_map0x0F_op0x78_l1(xed_decoded_inst_t* x) {
    /*FIXME: f3 prefix is not mentioned in INSERTQ or EXTRQ grammar
    definitions, however is forbidden for VMREAD. It seems that it can
    go with INSERTQ and EXTRQ. Right? */
    if (xed3_operand_get_osz(x) ||
        xed3_operand_get_ild_f2(x)
        //    || xed3_operand_get_ild_f3(x)
    ) 
    {
        /*for INSERTQ and EXTRQ*/
        /*straight in bytes*/
        xed3_operand_set_imm_width(x, bytes2bits(1));
        xed3_operand_set_imm1_bytes(x, 1);
        return;
    }
    /* for VMREAD imm_bytes is 0*/
}

/*ENTER instruction has UIMM16 and UIMM8_1 NTs*/
static XED_INLINE void xed_ild_hasimm_map0x0_op0xc8_l1(xed_decoded_inst_t* x) {
    /* for ENTER */
    /*straight in bytes*/
    xed3_operand_set_imm_width(x, bytes2bits(2));
    xed3_operand_set_imm1_bytes(x, 1);
}

/*FIXME: need to put getters in scanners headers to keep layering working*/

/// Convert xed_machine_mode_enum_t to a corresponding xed_bits_t value
/// for MODE operand
///  @param mmode - machine mode in xed_machine_mode_enum_t type
/// @return mode value for MODE operand in xed_bits_t type 
///
/// @ingroup ILD
xed_bits_t xed_ild_cvt_mode(xed_machine_mode_enum_t mmode);

/// Initialize internal data structures of the ILD.
void xed_ild_init_decoder(void);



/* Special getter for RM  */
static XED_INLINE xed_uint_t
xed_ild_get_rm(const xed_decoded_inst_t* ild) {
    /* Sometimes we don't have modrm, but grammar still
     * likes to use RM operand - in this case it is first
     * 3 bits of the opcode.
     */
    xed_uint8_t modrm;
    if (xed3_operand_get_has_modrm(ild))
        return xed3_operand_get_rm(ild);
    modrm = xed3_operand_get_nominal_opcode(ild);
    return xed_modrm_rm(modrm);
}

/* compressed operand getters */
static XED_INLINE xed_uint_t
xed3_operand_get_mod3(const xed_decoded_inst_t* ild) {
    return xed3_operand_get_mod(ild) == 3;
}

static XED_INLINE xed_uint_t
xed3_operand_get_rm4(const xed_decoded_inst_t* ild) {
    return xed3_operand_get_rm(ild) == 4;
}

static XED_INLINE xed_uint_t
xed3_operand_get_uimm0_1(const xed_decoded_inst_t* ild) {
    return xed3_operand_get_uimm0(ild) == 1;
}


#if defined(XED_AVX)
static XED_INLINE xed_uint_t
xed3_operand_get_vexdest210_7(const xed_decoded_inst_t* ild) {
    return xed3_operand_get_vexdest210(ild) == 7; 
}
#endif

#if defined(XED_SUPPORTS_AVX512)
static XED_INLINE
xed_uint32_t xed3_operand_get_mask_not0(const xed_decoded_inst_t *d) {
    /* aaa != 0  */
    return xed3_operand_get_mask(d) != 0;
}
static XED_INLINE
xed_uint32_t xed3_operand_get_mask_zero(const xed_decoded_inst_t *d) {
    /* aaa == 0  */
    return xed3_operand_get_mask(d) == 0;
}
#endif

void
xed_instruction_length_decode(xed_decoded_inst_t* d);


#endif

