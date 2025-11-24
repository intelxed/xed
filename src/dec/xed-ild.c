/* BEGIN_LEGAL 

Copyright (c) 2025 Intel Corporation

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
/// @file xed-ild.c
/// instruction length decoder

#include "xed-internal-header.h"
#include "xed-ild.h"
#include "xed-util-private.h"
#include <string.h> // strcmp

#include "xed-ild-modrm.h"
#include "xed-ild-disp-bytes.h"
#include "xed-ild-imm-bytes.h"
#include "xed-operand-accessors.h"
#include "xed-ild-enum.h"
#include "xed-map-feature-tables.h"
#include "xed-chip-features-private.h"
#include "xed-chip-features-table.h"
#include "xed-ild-extension.h"

static void set_has_modrm(xed_decoded_inst_t* d);

static XED_INLINE xed_uint8_t
decoded_inst_get_byte(const xed_decoded_inst_t* p, xed_uint_t byte_index)
{
    /// Read a whole byte from the normal input bytes.
    xed_uint8_t out = p->_byte_array._dec[byte_index];
    return out; 
}

static XED_INLINE void too_short(xed_decoded_inst_t* d)
{
    xed3_operand_set_out_of_bytes(d, 1);
    if ( xed3_operand_get_max_bytes(d) >= XED_MAX_INSTRUCTION_BYTES)
        xed3_operand_set_error(d,XED_ERROR_INSTR_TOO_LONG);
    else
        xed3_operand_set_error(d,XED_ERROR_BUFFER_TOO_SHORT);
}

static XED_INLINE void bad_map(xed_decoded_inst_t* d)
{
    xed3_operand_set_map(d,XED_ILD_MAP_INVALID);
    xed3_operand_set_error(d,XED_ERROR_BAD_MAP);
}

// We set the hints to the values {1,2} here but later move the values to
// {3,4} if the prefixes are actually used for a Jcc branch.  If 3e is used
// as a CET no-track indicator, it remains as the value 2.
static  XED_INLINE void set_hint_3e(xed_decoded_inst_t* d) {
    xed3_operand_set_hint(d,2);
}
static  XED_INLINE void set_hint_2e(xed_decoded_inst_t* d) {
    xed3_operand_set_hint(d,1);
}
static  XED_INLINE xed_bool_t get_hint_3e(xed_decoded_inst_t const* d) {
    return xed3_operand_get_hint(d)==2;
}
static  XED_INLINE void clear_hint(xed_decoded_inst_t* d) {
    xed3_operand_set_hint(d,0);
}

// conservative filter table for fast prefix checking
// 2014-07-30:
// Timing perftest: 2-6% gain
// Without the filter:
//   Average: 384.08s  Minimum: 352.74s
// With the filter:
//   Average: 362.97s  Minimum: 346.26s
//
// The filter includes the 16 values of the REX prefix even in 32b mode.
// If we had a separate filter for 64b mode we could omit the REX prefixes
// from the 32b mode table.
// Could use 2x the space and the 64b mode thing to pick the right table.
// That would speed up 32b prefix decodes.

#define XED_PREFIX_TABLE_SIZE 8
static xed_uint32_t prefix_table[XED_PREFIX_TABLE_SIZE];  // 32B=256b 32*8=2^5*2^3

static void set_prefix_table_bit(xed_uint8_t a)
{
    xed_uint32_t x = a >> 5;
    xed_uint32_t y = a & 0x1F;
    prefix_table[x] |= (1<<y);
}

static XED_INLINE xed_uint_t get_prefix_table_bit(xed_uint8_t a)
{
    // return 1 if the bit is set in the table
    xed_uint32_t x = a >> 5;
    xed_uint32_t y = a & 0x1F;
    return (prefix_table[x] >> y ) & 1;
}

static void init_prefix_table(void)
{
    xed_uint_t i;
    static xed_uint8_t legacy_prefixes[] = {
        0xF0, // lock
        0x66, // osz
        0x67, // asz
        
        0xF2, 0xF3, // rep/repne
        
        0x2E, 0x3E, // 6 segment prefixes
        0x26, 0x36,
        0x64, 0x65,
        
        0 // sentinel
    };

    for (i=0;i<XED_PREFIX_TABLE_SIZE;i++)
        prefix_table[i]=0;
    
    for (i=0;legacy_prefixes[i];i++)
        set_prefix_table_bit(legacy_prefixes[i]);

    // add the 16 values of the REX prefixes even for 32b mode
    for(i=0x40;i<0x50;i++)
        set_prefix_table_bit(XED_CAST(xed_uint8_t,i));
}

#if defined(XED_SUPPORTS_AVX512)
static void XED_NOINLINE bad_v4(xed_decoded_inst_t* d)
{
    xed3_operand_set_error(d,XED_ERROR_BAD_EVEX_V_PRIME);
}
static void XED_NOINLINE bad_z_aaa(xed_decoded_inst_t* d)
{
    xed3_operand_set_error(d,XED_ERROR_BAD_EVEX_Z_NO_MASKING);
}
#endif

static void prefix_scanner(xed_decoded_inst_t* d)
{
    xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
    unsigned char length = xed_decoded_inst_get_length(d);
    xed_uint8_t nprefixes = 0;
    xed_uint8_t nseg_prefixes = 0;
    xed_uint8_t nrexes = 0;
    unsigned char rex = 0;

    while(length < max_bytes)
    {
        xed_uint8_t b = decoded_inst_get_byte(d, length);
        
        // fast check to see if something might be a prefix
        // includes REX prefixes in 32b mode
        if (get_prefix_table_bit(b)==0)
            goto out;
        
        switch(b) {
          case 0x66:
            xed3_operand_set_osz(d, 1);
            xed3_operand_set_prefix66(d, 1);
            /*ignore possible REX prefix encoutered earlier */
            rex = 0;
            break;

          case 0x67:
            xed3_operand_set_asz(d, 1);
            rex = 0;
            break;
            
          /* segment prefixes */
          case 0x2E: //CS
            if (mode_64b(d)==0)  { // 16/32b  mode
                set_hint_2e(d);
                xed3_operand_set_ild_seg(d, b);
            }
            else if (get_hint_3e(d)==0)  {
                // only set 2e hint in 64b mode  if no prior 3e hint (CET's new rule)
                set_hint_2e(d);
            }
            nseg_prefixes++;
            /*ignore possible REX prefix encountered earlier */
            rex = 0;
            break;
            
          case 0x3E: //DS (& CET no-track on indirect call/jmp)

            if (mode_64b(d)==0) { //16/32b mode
                set_hint_3e(d);                
                xed3_operand_set_ild_seg(d, b);
            }
            else //64b mode
            {
                //CET's new rule...
                if (xed3_operand_get_ild_seg(d) != 0x64 &&
                    xed3_operand_get_ild_seg(d) != 0x65 )
                {
                    set_hint_3e(d);
                }
            }
            nseg_prefixes++;
            /*ignore possible REX prefix encountered earlier */
            rex = 0;
            break;
            
          case 0x26: //ES
          case 0x36: //SS
            if (mode_64b(d)==0)  {
                xed3_operand_set_ild_seg(d, b);
                clear_hint(d);
            }

            nseg_prefixes++;
            /*ignore possible REX prefix encountered earlier */
            rex = 0;
            break;
            
          case 0x64: //FS
          case 0x65: //GS
            //for 64b mode we are ignoring non valid segment prefixes
            //only FS=0x64 and GS=0x64 are valid for 64b mode
            xed3_operand_set_ild_seg(d, b);
            clear_hint(d);
            
            nseg_prefixes++;
            /*ignore possible REX prefix encountered earlier */
            rex = 0;
            break;
            
          case 0xF0:
            xed3_operand_set_lock(d, 1);
            rex = 0;
            break;

          case 0xF3:
            xed3_operand_set_ild_f3(d, 1);
            xed3_operand_set_last_f2f3(d, 3);
            if (xed3_operand_get_first_f2f3(d) == 0)
                xed3_operand_set_first_f2f3(d, 3);
            
            rex = 0;
            break;
            
          case 0xF2:
            xed3_operand_set_ild_f2(d, 1);
            xed3_operand_set_last_f2f3(d, 2);
            if (xed3_operand_get_first_f2f3(d) == 0)
                xed3_operand_set_first_f2f3(d, 2);
            
            rex = 0;
            break;
            
          default:
             /*Take care of REX prefix */
            if (mode_64b(d)  &&
                (b & 0xf0) == 0x40) {
                    nrexes++;
                    rex = b;
            }
            else
                goto out;
        }
        length++;
        nprefixes++;
    }
out:
    //set counts
    xed_decoded_inst_set_length(d, length);
    xed3_operand_set_nprefixes(d, nprefixes);
    xed3_operand_set_nseg_prefixes(d, nseg_prefixes);
    xed3_operand_set_nrexes(d, nrexes);

    //set REX, REXW, etc.
    if (rex) {
        xed3_operand_set_rexw(d, (rex>>3) & 1);
        xed3_operand_set_rexr(d, (rex>>2) & 1);
        xed3_operand_set_rexx(d, (rex>>1) & 1);
        xed3_operand_set_rexb(d,  (rex) & 1);
        xed3_operand_set_rex(d, 1);
    }

    //set REP and REFINING
    if (xed3_operand_get_mode_first_prefix(d))
        xed3_operand_set_rep(d, xed3_operand_get_first_f2f3(d));
    else
        xed3_operand_set_rep(d, xed3_operand_get_last_f2f3(d));

    //set SEG_OVD
    /*FIXME: lookup table for seg_ovd ? */
    /*FIXME: make the grammar use the raw byte value instead of the 1..6
     * recoding */
    switch(xed3_operand_get_ild_seg(d)) {
    case 0x2e:
        xed3_operand_set_seg_ovd(d, 1);
        break;
    case 0x3e:
        xed3_operand_set_seg_ovd(d, 2);
        break;
    case 0x26:
        xed3_operand_set_seg_ovd(d, 3);
        break;
    case 0x64:
        xed3_operand_set_seg_ovd(d, 4);
        break;
    case 0x65:
        xed3_operand_set_seg_ovd(d, 5);
        break;
    case 0x36:
        xed3_operand_set_seg_ovd(d, 6);
        break;
    default:
        break;
    }

    //check max bytes
    if (length >= max_bytes) {
        /* all available length was taken by prefixes, but we for sure need
         * at least one additional byte for an opcode, hence we are out of
         * bytes.         */
        too_short(d);
        return;
    }
}

#if defined(XED_AVX)
typedef union { // C4 payload 1
    struct {
        xed_uint32_t map:5;
        xed_uint32_t b_inv:1;
        xed_uint32_t x_inv:1;
        xed_uint32_t r_inv:1;
        xed_uint32_t pad:24; 
    } s;
    struct {
        xed_uint32_t map:5;
        xed_uint32_t b_inv:1;
        xed_uint32_t rx_inv:2;
        xed_uint32_t pad:24; 
    } coarse;
    xed_uint32_t u32;
} xed_avx_c4_payload1_t;

typedef union { // C4 payload 2
    struct {
        xed_uint32_t pp:2;
        xed_uint32_t l:1;
        xed_uint32_t vvv210:3;
        xed_uint32_t v3:1;
        xed_uint32_t w:1;
        xed_uint32_t pad:24; 
    } s;
    xed_uint32_t u32;
} xed_avx_c4_payload2_t;

typedef union { // C5 payload 1
    struct {
        xed_uint32_t pp:2;
        xed_uint32_t l:1;
        xed_uint32_t vvv210:3;
        xed_uint32_t v3:1;
        xed_uint32_t r_inv:1;
        xed_uint32_t pad:24; 
    } s;
    struct {
        xed_uint32_t pp:2;
        xed_uint32_t l:1;
        xed_uint32_t vvv210:3;
        xed_uint32_t rv3_inv:2;
        xed_uint32_t pad:24; 
    } coarse;
    xed_uint32_t u32;
} xed_avx_c5_payload_t;

static void evex_vex_opcode_scanner(xed_decoded_inst_t* d); //prototype

static void set_vl(xed_decoded_inst_t* d, xed_uint_t vl) {
    xed3_operand_set_vl(d, vl);
}

static void vex_c4_scanner(xed_decoded_inst_t* d)
{
    // assumption: length < max_bytes. This is checked in prefix_scanner.
    // c4 is  the byte at 'length'
    xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
    unsigned char length  = xed_decoded_inst_get_length(d);
    xed_avx_c4_payload1_t c4byte1;    
    if (length+1 < max_bytes)   {
        length++;
        c4byte1.u32 = decoded_inst_get_byte(d, length);
        // in 16/32b modes, the MODRM.MOD field MUST be 0b11
        if (!mode_64b(d) && c4byte1.coarse.rx_inv != 3) {
            // this is not a vex prefix, go to next scanner
            return;
        }
    }
    else {
        // not enough bytes to check vex prefix validity
        xed_decoded_inst_set_length(d, max_bytes);
        too_short(d);
        return ;
    }

    //      c4  xx yy opc
    //          ^          
    // length is set to the position of the first payload byte.
    // we need 2 more: 2nd payload byte and opcode.
    if (length + 2 < max_bytes) {
      xed_avx_c4_payload2_t c4byte2;
      xed_uint_t eff_map;

      c4byte2.u32 = decoded_inst_get_byte(d, length+1);
      length += 2;
      xed_decoded_inst_set_length(d, length); // now point at opcode

      xed3_operand_set_rexr(d, ~c4byte1.s.r_inv&1);
      xed3_operand_set_rexx(d, ~c4byte1.s.x_inv&1);
      xed3_operand_set_rexb(d, (mode_64b(d) & ~c4byte1.s.b_inv)&1);
      xed3_operand_set_rexw(d, c4byte2.s.w);

      xed3_operand_set_vexdest3(d,   c4byte2.s.v3);
      xed3_operand_set_vexdest210(d, c4byte2.s.vvv210);

      set_vl(d, c4byte2.s.l);

      xed_ild_set_pp_vex_prefix(d, c4byte2.s.pp);

      xed3_operand_set_map(d,c4byte1.s.map);

      eff_map = c4byte1.s.map;
      if (xed_ild_map_valid_vex(eff_map) == 0) {
          bad_map(d);
          return; 
      }
      // this is a success indicator for downstreaam decoding
      xed3_operand_set_vexvalid(d, 1); // AVX1/2
      evex_vex_opcode_scanner(d);
      return;
    }
    else {
      /* We don't have 3 bytes available for reading, but we for sure
       * need to read them - for 2 vex payload bytes and opcode byte,
       * hence we are out of bytes.
       */
        xed_decoded_inst_set_length(d, max_bytes);
        too_short(d);
        return;
    }
}

static void vex_c5_scanner(xed_decoded_inst_t* d)
{
    // assumption: length < max_bytes. This is checked in prefix_scanner.
    // c5 is the byte at 'length'
    xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
    unsigned char length  = xed_decoded_inst_get_length(d);
    xed_avx_c5_payload_t c5byte1;
    if (length + 1 < max_bytes)   {
        length++;
        c5byte1.u32 = decoded_inst_get_byte(d, length);
        // in 16/32b modes, the MODRM.MOD field MUST be 0b11
        if (!mode_64b(d) && c5byte1.coarse.rv3_inv != 3) {
            // this is not a vex prefix, go to next scanner
            return;
        }
    }
    else {
        // not enough bytes to check vex prefix validity
        xed_decoded_inst_set_length(d, max_bytes);
        too_short(d);
        return ;
    }
    //      c5  xx  opc
    //          ^          
    // length is set to the position of the first payload byte.
    // we need 1 more: opcode.
    if (length + 1 < max_bytes) {

        xed3_operand_set_rexr(d, ~c5byte1.s.r_inv&1);
        xed3_operand_set_vexdest3(d,   c5byte1.s.v3);
        xed3_operand_set_vexdest210(d, c5byte1.s.vvv210);

        set_vl(d,   c5byte1.s.l);        
        xed_ild_set_pp_vex_prefix(d, c5byte1.s.pp);

        /* Implicitly map1. We use map later in the ILD - for modrm, imm
         * and disp. */
        xed3_operand_set_map(d, XED_ILD_VEX_MAP1);

        // this is a success indicator for downstreaam decoding
        xed3_operand_set_vexvalid(d, 1); // AVX1/2

        length++;  /* eat the vex opcode payload */
        xed_decoded_inst_set_length(d, length);
        
        evex_vex_opcode_scanner(d);  //eats opcode byte
        return;
    }
    else {
        /* We don't have 2 bytes available for reading, but we need to read
         * them - for vex payload byte and opcode bytes, hence we are out
         * of bytes.
         */
        xed_decoded_inst_set_length(d, max_bytes);
        too_short(d);
        return ;
    }
}


#if defined(XED_EXTENSION_XOP_DEFINED)

static XED_INLINE xed_uint_t get_modrm_reg_field(xed_uint8_t b) {
  return (b & 0x38) >> 3;
}

static void xop_scanner(xed_decoded_inst_t* d)
{
    // assumption: length < max_bytes. This is checked in prefix_scanner.
    xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
    unsigned char length = xed_decoded_inst_get_length(d);
    
    if (length + 1 < max_bytes)   {
        xed_uint8_t n = decoded_inst_get_byte(d, length+1);
        /* in all modes, the MODRM.REG field MUST NOT be 0b000.
           mm-rrr-nnn -> mmrr_rnnn
         */
         
        if ( get_modrm_reg_field(n) != 0 ) {
            length++; /* eat the 0x8f */
        }
        else   {
            /* A little optimization: this is not an xop prefix, we can
             * proceed to next scanner */
            return;
        }
    }
    else  {
        /* don't have enough bytes to check if it's an xop prefix, we
         * are out of bytes */
        too_short(d);
        return ;
    }

    /* pointing at the first xop payload byte. we want to make sure, that
     * we have additional 2 bytes available for reading - for 2nd xop payload
     * byte and opcode */
    if (length + 2 < max_bytes)
    {
      xed_avx_c4_payload1_t xop_byte1;
      xed_avx_c4_payload2_t xop_byte2;
      xed_uint8_t map;
      xop_byte1.u32 = decoded_inst_get_byte(d, length);
      xop_byte2.u32 = decoded_inst_get_byte(d, length + 1);
      length += 2; /* eat the 8f xop 2B payload */
      xed_decoded_inst_set_length(d, length);
      
      map = xop_byte1.s.map;
      if (map == 0x9) { 
          xed3_operand_set_map(d,XED_ILD_AMD_XOP9);
      }
      else if (map == 0x8){
          xed3_operand_set_map(d,XED_ILD_AMD_XOP8);
      }
      else if (map == 0xA){
          xed3_operand_set_map(d,XED_ILD_AMD_XOPA);
      }
      else 
          bad_map(d);

      
      xed3_operand_set_rexr(d, ~xop_byte1.s.r_inv&1);
      xed3_operand_set_rexx(d, ~xop_byte1.s.x_inv&1);
      xed3_operand_set_rexb(d, (mode_64b(d) & ~xop_byte1.s.b_inv)&1);

      xed3_operand_set_rexw(d, xop_byte2.s.w);

      xed3_operand_set_vexdest3(d, xop_byte2.s.v3);
      xed3_operand_set_vexdest210(d, xop_byte2.s.vvv210);

      set_vl(d, xop_byte2.s.l);
      xed_ild_set_pp_vex_prefix(d, xop_byte2.s.pp);
      
      xed3_operand_set_vexvalid(d, 3);

      /* using the VEX opcode scanner for xop opcodes too. */
      evex_vex_opcode_scanner(d);
      return;
    }
    else {
      /* We don't have 3 bytes available for reading, but we for sure
       * need to read them - for 2 vex payload bytes and opcode byte,
       * hence we are out of bytes.
       */
        xed_decoded_inst_set_length(d, max_bytes);
        too_short(d);
      return;
    }
}
#endif
#endif     

#if defined(XED_AVX) // for vex_scanner


#if defined(XED_EXTENSION_XOP_DEFINED)

static xed_uint8_t could_support_xop_instr[XED_CHIP_LAST];
static void xed_ild_chip_init(void) {
    // used to quickly check for the AMD (0x8F) XOP extension
    xed_uint_t i;
    for(i=0;i<XED_CHIP_LAST;i++) {
        could_support_xop_instr[i]=0;
    }
    could_support_xop_instr[XED_CHIP_INVALID]=1;
    could_support_xop_instr[XED_CHIP_ALL]=1;
    could_support_xop_instr[XED_CHIP_AMD_BULLDOZER]=1;
}

static XED_INLINE xed_uint_t chip_could_support_xop(xed_decoded_inst_t* d)
{
    xed_chip_enum_t chip = xed_decoded_inst_get_input_chip(d);
    if (chip < XED_CHIP_LAST)
        return could_support_xop_instr[chip];
    return 0;
}
#  endif


static void vex_scanner(xed_decoded_inst_t* d)
{
    /* this handles the AVX C4/C5 VEX prefixes and also the AMD XOP 0x8F
     * prefix */
    unsigned char length = xed_decoded_inst_get_length(d);
    xed_uint8_t b;
    
    // assumption: length < max_bytes (checked in prefix_scanner)
    xed_assert(length < xed3_operand_get_max_bytes(d));
    b = decoded_inst_get_byte(d, length);

    if (b == 0xC5) {
        if (!xed3_operand_get_out_of_bytes(d)) 
            vex_c5_scanner(d);
        return;
    }
    else if (b == 0xC4) {
        if (!xed3_operand_get_out_of_bytes(d)) 
            vex_c4_scanner(d);
        return;
    }
#if defined(XED_EXTENSION_XOP_DEFINED) 
    else if (b == 0x8f && chip_could_support_xop(d) )  {
        if (!xed3_operand_get_out_of_bytes(d)) 
            xop_scanner(d);   
        return;
    }
#endif
}
#endif

static void get_next_as_opcode(xed_decoded_inst_t* d) {
    unsigned char length = xed_decoded_inst_get_length(d);
    if (length < xed3_operand_get_max_bytes(d)) {     
        xed_uint8_t b = decoded_inst_get_byte(d, length);
        xed3_operand_set_nominal_opcode(d, b);
        xed3_operand_set_pos_nominal_opcode(d, length);
        xed_decoded_inst_inc_length(d);
        //set SRM (partial opcode instructions need it)
        xed3_operand_set_srm(d, xed_modrm_rm(b));
    }
    else {
        too_short(d);
    }
}


// has_disp_regular[eamode][modrm.mod][modrm.rm]
static xed_uint8_t has_disp_regular[3][4][8];

static void init_has_disp_regular_table(void) {
    xed_uint8_t eamode;
    xed_uint8_t rm;
    xed_uint8_t mod;

    for (eamode = 0; eamode <3; eamode++)
        for (mod=0; mod < 4; mod++)
            for (rm=0; rm<8; rm++)
                has_disp_regular[eamode][mod][rm] = 0;
    
    //fill the eamode16
    has_disp_regular[0][0][6] = 2;
    for (rm = 0; rm < 8; rm++) {
        for (mod = 1; mod <= 2; mod++)
            has_disp_regular[0][mod][rm] = mod;
    }

    //fill eamode32/64
    for(eamode = 1; eamode <= 2; eamode++) {
        for (rm = 0; rm < 8; rm++) {
            has_disp_regular[eamode][1][rm] = 1;
            has_disp_regular[eamode][2][rm] = 4;
        };
        has_disp_regular[eamode][0][5] = 4;

    }
}

// eamode_table[asz][mmode]
static xed_uint8_t eamode_table[2][XED_GRAMMAR_MODE_64+1];

static void init_eamode_table(void) {
    xed_uint8_t mode;
    xed_uint8_t asz;

    for (asz=0; asz<2; asz++)
        for (mode=0; mode<XED_GRAMMAR_MODE_64+1; mode++)
            eamode_table[asz][mode] = 0;
    

    for (mode = XED_GRAMMAR_MODE_16; mode <= XED_GRAMMAR_MODE_64; mode ++) {
        eamode_table[0][mode] = mode;
    }

    eamode_table[1][XED_GRAMMAR_MODE_16] = XED_GRAMMAR_MODE_32;
    eamode_table[1][XED_GRAMMAR_MODE_32] = XED_GRAMMAR_MODE_16;
    eamode_table[1][XED_GRAMMAR_MODE_64] = XED_GRAMMAR_MODE_32;
}


// has_sib_table[eamode][modrm.mod][modrm.rm]
static xed_uint8_t has_sib_table[3][4][8];

static void init_has_sib_table(void) {
    xed_uint8_t eamode;
    xed_uint8_t mod;
    xed_uint8_t rm;
    
    for (eamode = 0; eamode <3; eamode++)
        for (mod=0; mod < 4; mod++)
            for (rm=0; rm<8; rm++)
                has_sib_table[eamode][mod][rm] = 0;

    //for eamode32/64 there is sib byte for mod!=3 and rm==4
    for(eamode = 1; eamode <= 2; eamode++) {
        for (mod = 0; mod <= 2; mod++) {
            has_sib_table[eamode][mod][4] = 1;
        }
    }
}


#if defined(XED_SUPPORTS_AVX512)
static void bad_ll(xed_decoded_inst_t* d) {
    xed3_operand_set_error(d,XED_ERROR_BAD_EVEX_LL);
}


static void bad_ll_check(xed_decoded_inst_t* d)
{
    if (xed3_operand_get_llrc(d) == 3)  {
        // we have a potentially bad EVEX.LL field.
        if (xed3_operand_get_mod(d) != 3) // memop
            bad_ll(d);
        else if (xed3_operand_get_bcrc(d)==0) // reg-reg but not rounding
            bad_ll(d);
    }
}
#endif

void xed_modrm_scanner(xed_decoded_inst_t* d)
{
    xed_uint8_t b;
    xed_uint8_t has_modrm;
    set_has_modrm(d);

    has_modrm = xed3_operand_get_has_modrm(d);

    if (has_modrm) {
        unsigned char length = xed_decoded_inst_get_length(d);
        if (length < xed3_operand_get_max_bytes(d)) {
            xed_uint8_t eamode;
            xed_uint8_t mod;
            xed_uint8_t rm;

            b = decoded_inst_get_byte(d, length);
            xed3_operand_set_modrm_byte(d, b);
            xed3_operand_set_pos_modrm(d, length);
            xed_decoded_inst_inc_length(d); /* eat modrm */

            mod = xed_modrm_mod(b);
            rm = xed_modrm_rm(b);
            xed3_operand_set_mod(d, mod);
            xed3_operand_set_rm(d, rm);
            xed3_operand_set_reg(d, xed_modrm_reg(b));
            
#if defined(XED_SUPPORTS_AVX512)
            bad_ll_check(d);
#endif
            /*This checks that we are not in MOV_DR or MOV_CR instructions
            that ignore MODRM.MOD bits and don't have DISP and SIB */
            if (has_modrm != XED_ILD_HASMODRM_IGNORE_MOD) {
                xed_uint8_t asz = xed3_operand_get_asz(d);
                xed_uint8_t mode = xed3_operand_get_mode(d);
                // KW complains here but it is stupid. Code is fine.
                eamode = eamode_table[asz][mode];

                xed_assert(eamode <= 2); 

                /* opcode scanner (and prefix scanner) doesn't set
                disp_bytes, hence we can set it to 0  without worrying about
                overriding a value that was set earlier. */
                
                xed3_operand_set_disp_width(
                    d,
                    bytes2bits(has_disp_regular[eamode][mod][rm]));
      
                /*same with sib, we will not override data set earlier here*/
                xed3_operand_set_has_sib(d, has_sib_table[eamode][mod][rm]);
                
                
            }
            return;
        }
        else { 
            /*need modrm, but length >= max_bytes, and we are out of bytes*/
            too_short(d);
            return;
        }
          
    }
    /*no modrm, set RM from nominal_opcode*/
    //rm = xed_modrm_rm(xed3_operand_get_nominal_opcode(d));
    //xed3_operand_set_rm(d, rm);

    /* a little optimization: we don't have modrm and hence don't have sib.
     * Hence we don't need to call sib scanner and can go straight to disp*/
    /*FIXME: Better to call next scanner anyway for better modularity?*/
}

static void sib_scanner(xed_decoded_inst_t* d)
{
    
  if (xed3_operand_get_has_sib(d)) {
      unsigned char length = xed_decoded_inst_get_length(d);
      if (length < xed3_operand_get_max_bytes(d)) {
          xed_uint8_t b;
          b = decoded_inst_get_byte(d, length); 

          xed3_operand_set_pos_sib(d, length);
          xed3_operand_set_sibscale(d, xed_sib_scale(b));
          xed3_operand_set_sibindex(d, xed_sib_index(b));
          xed3_operand_set_sibbase(d, xed_sib_base(b));

          xed_decoded_inst_inc_length(d); /* eat sib */
  
          if (xed_sib_base(b) == 5) {
              /* other mod values are set by modrm processing */
              if (xed3_operand_get_mod(d) == 0)
                  xed3_operand_set_disp_width(d, bytes2bits(4));
          }
      }
      else { /*has_sib but not enough length -> out of bytes */
          too_short(d);
          return;
      }
  }
}


static void disp_scanner(xed_decoded_inst_t* d)
{
    /*                                   0   1  2  3   4  5   6   7   8 */
    static const xed_uint8_t ilog2[] = { 99 , 0, 1, 99, 2, 99, 99, 99, 3 };

    xed_uint8_t disp_bytes;
    xed_uint8_t length = xed_decoded_inst_get_length(d);
    xed_uint_t yes_no_var = xed_ild_get_has_disp(d);
    if (yes_no_var == 2) {
        xed_ild_map_enum_t map = (xed_ild_map_enum_t)xed3_operand_get_map(d);
        xed_uint8_t opcode     = xed3_operand_get_nominal_opcode(d);
        xed_uint_t               vv = xed3_operand_get_vexvalid(d);

        xed_assert(map < XED_MAP_ROW_LIMIT);
        xed_assert(vv < XED_VEXVALID_LIMIT);

        xed_ild_l1_func_t const* fptr_tbl = xed_ild_disp_width_table[vv][map];
        xed_ild_l1_func_t      fptr = 0;
        xed_assert(fptr_tbl); // fptr_tbl guaranteed to be valid by construction

        fptr = fptr_tbl[opcode];
        xed_assert(fptr); // fptr guaranteed to be valid by construction
        (*fptr)(d);
    }
    /*All other maps should have been set earlier*/
    disp_bytes = bits2bytes(xed3_operand_get_disp_width(d));
    if (disp_bytes) {
        xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
        if ((length + disp_bytes) <= max_bytes) {

            //set disp value
            const xed_uint8_t* itext = d->_byte_array._dec;
            xed_uint8_t* disp_ptr = (xed_uint8_t*)(itext + length);
          
            // sign extend the displacement to 64b while passing to accessor
          
            switch(ilog2[disp_bytes]) { 
              case 0: { // 1B=8b. ilog2(1) = 0
                  xed_int8_t disp = 0;
                  memcpy(&disp, disp_ptr, sizeof(disp));
                  xed3_operand_set_disp(d, disp);
                  break;
              }
              case 1: { // 2B=16b ilog2(2) = 1
                  xed_int16_t disp = 0;
                  memcpy(&disp, disp_ptr, sizeof(disp));
                  xed3_operand_set_disp(d, disp);
                  break;
              }
              case 2: { // 4B=32b ilog2(4) = 2
                  xed_int32_t disp = 0;
                  memcpy(&disp, disp_ptr, sizeof(disp));
                  xed3_operand_set_disp(d, disp);
                  break;
              }
              case 3: {// 8B=64b ilog2(8) = 3
                  xed_int64_t disp = 0;
                  memcpy(&disp, disp_ptr, sizeof(disp));
                  xed3_operand_set_disp(d, disp);
                  break;
              }
              default:
                xed_assert(0);
            }

            xed3_operand_set_pos_disp(d, length);
            xed_decoded_inst_set_length(d, length + disp_bytes);
        }
        else {
            too_short(d);
            return;
        }
    }
}



static void set_has_modrm(xed_decoded_inst_t* d) {
    xed_uint_t yes_no_var = xed_ild_get_has_modrm(d);
    if (yes_no_var == 1) {
        xed3_operand_set_has_modrm(d, XED_ILD_HASMODRM_TRUE);
    }
    else if (yes_no_var == 2) {
        xed_uint8_t opcode = xed3_operand_get_nominal_opcode(d);
        xed_uint_t      vv = xed3_operand_get_vexvalid(d);
        xed_uint_t     map = xed3_operand_get_map(d);
        xed_uint8_t const* modrm_for_vv_map = xed_ild_has_modrm_table[vv][map];
        xed_assert(modrm_for_vv_map!=0);
        xed_uint8_t has_modrm = modrm_for_vv_map[opcode];
        if (has_modrm == XED_ILD_HASMODRM_UD0) {
            has_modrm = !xed3_operand_get_mode_short_ud0(d);
        }
        xed3_operand_set_has_modrm(d,has_modrm);

    }
}


static void set_imm_bytes(xed_decoded_inst_t* d) {
    xed_uint8_t imm_bits = xed3_operand_get_imm_width(d);
    if (!imm_bits) {
        xed_uint_t var_or_bytes = xed_ild_get_has_imm(d); 
        if (var_or_bytes < 7) // fixed 0,1,2,4 bytes handled here
            xed3_operand_set_imm_width(d,bytes2bits(var_or_bytes));
        else { // var_or_bytes == 7 denotes that a complex length determination is reqd
            xed_uint_t               vv = xed3_operand_get_vexvalid(d);
            xed_ild_map_enum_t      map = (xed_ild_map_enum_t)xed3_operand_get_map(d);
            xed_uint8_t          opcode = xed3_operand_get_nominal_opcode(d);

            xed_assert(map < XED_MAP_ROW_LIMIT);
            xed_assert(vv < XED_VEXVALID_LIMIT);

            xed_ild_l1_func_t const* fptr_tbl = xed_ild_imm_width_table[vv][map];
            xed_ild_l1_func_t      fptr = 0;
            xed_assert(fptr_tbl); // fptr_tbl guaranteed to be valid by construction

            fptr = fptr_tbl[opcode];
            xed_assert(fptr); // fptr guaranteed to be valid by construction
            (*fptr)(d);
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
void xed_set_downstream_info(xed_decoded_inst_t* d, xed_uint_t vv) {
    xed_uint_t mapno = xed3_operand_get_map(d);

    // copy the codes from the map_info_t tables for later procsssing
    xed_ild_set_has_modrm(d, xed_ild_has_modrm(vv,mapno));
    xed_ild_set_has_disp(d,  xed_ild_has_disp(vv,mapno));
    xed_ild_set_has_imm(d,  xed_ild_has_imm(vv,mapno));
}

#if defined(XED_AVX)
static void catch_invalid_rex_or_legacy_prefixes(xed_decoded_inst_t* d)
{
    // REX, F2, F3, 66 are not allowed before VEX or EVEX prefixes
    if ( mode_64b(d) && xed3_operand_get_rex(d) )
        xed3_operand_set_error(d,XED_ERROR_BAD_REX_PREFIX);
    else if ( xed3_operand_get_prefix66(d) ||
              xed3_operand_get_ild_f3(d) ||
              xed3_operand_get_ild_f2(d) )
        xed3_operand_set_error(d,XED_ERROR_BAD_LEGACY_PREFIX);
}


static void evex_vex_opcode_scanner(xed_decoded_inst_t* d)
{
    /* no need to check max_bytes here, it was checked in previous
    scanner */
    unsigned char length = xed_decoded_inst_get_length(d);
    xed_uint8_t b = decoded_inst_get_byte(d, length);

    xed3_operand_set_nominal_opcode(d, b);
    xed3_operand_set_pos_nominal_opcode(d, length);
    xed_decoded_inst_inc_length(d);
    xed_set_downstream_info(d,xed3_operand_get_vexvalid(d));
}
#endif

// indicate whether a decoded instruction should be fed to the opcode scanner
// as instructions with the REX2 prefix should be fed to a dedicated REX2 scanner
static XED_INLINE xed_bool_t opcode_scanner_needed(xed_decoded_inst_t *d)
{
    // FIXME: Consider skipping error check here — already validated earlier
#if defined(XED_APX)
    return (xed3_operand_get_error(d) == XED_ERROR_NONE) && (xed3_operand_get_rex2(d) == 0);
#else
    return (xed3_operand_get_error(d) == XED_ERROR_NONE);
#endif
}


static void opcode_scanner(xed_decoded_inst_t* d)
{
    unsigned char length = xed_decoded_inst_get_length(d);
    xed_uint8_t b;
    xed_uint64_t i;
    
    // assumption: length < max_bytes (checked in prefix_scanner)
    xed_assert(length < xed3_operand_get_max_bytes(d));
    b = decoded_inst_get_byte(d, length);


    // matching maps vs having a summary of which opcodes are definately map0.
    // Common case is map 0, but the loop would check them all and deduce map 0, slowly.
    // Could just hardcode 0x0F for map escapes loop scan
    // Or I hard code the known maps and handle "extra maps" with a loop
    if (b != 0x0F) {
        xed3_operand_set_map(d, XED_ILD_LEGACY_MAP0);
        xed3_operand_set_nominal_opcode(d, b);
        xed3_operand_set_pos_nominal_opcode(d, length);
        xed3_operand_set_srm(d, xed_modrm_rm(b));
        xed_decoded_inst_inc_length(d);
        xed_set_downstream_info(d,0);
        return;
    }
    // things that start with 0x0F are escape maps...

    length++; /* eat the 0x0F */
    if (length >= xed3_operand_get_max_bytes(d)) {
        too_short(d);
        return;
    }

    b = decoded_inst_get_byte(d, length); // get next byte

    //FIXME: could split into two loops and have the map1-like loop first..

    // map 0 was removed from the static list of maps for this loop
    for(i=0;i<sizeof(xed_legacy_maps)/sizeof(xed_map_info_t);i++) {
        xed_map_info_t const* m = xed_legacy_maps+i;
        // if no secondary map, or we match the secondary map, we are set.
        if (m->legacy_escape == 0x0F) {
            if (m->has_legacy_opcode==0) {
                xed3_operand_set_nominal_opcode(d, b);
                xed3_operand_set_pos_nominal_opcode(d, length);
                length++; /* eat the 2nd  opcode byte */
                xed3_operand_set_map(d, m->map_id);
                xed_decoded_inst_set_length(d, length);
                //set SRM (partial opcode instructions need it)
                xed3_operand_set_srm(d, xed_modrm_rm(b));
                xed_set_downstream_info(d,0);
                return;
            }
            else if (m->legacy_opcode == b) {
                length++; /* eat the secondary map byte */
                xed3_operand_set_map(d, m->map_id);
                xed_decoded_inst_set_length(d, length);
#if defined(XED_EXTENSION_3DNOW_DEFINED)
                if (m->opc_pos == -1) 
                    xed3_operand_set_amd3dnow(d, m->opc_pos == -1);
                else
#endif
                    get_next_as_opcode(d);
                xed_set_downstream_info(d,0);
                return;
            }
        }
    }
    // handle no map found... FIXME
    bad_map(d);
}

//////////////////////////////////////////////////////////////////////////
// AVX512 EVEX and EVEX-IMM8 scanners

#if defined(XED_SUPPORTS_AVX512)

// a union defining the first payload byte of the EVEX prefix
// different features have different bit interpretations
// APX for instance, allocates 3 bits for map and 1 bit each for
// R3, X3, B3, R4 and B4
typedef union { 
    struct {  // AVX512
        xed_uint32_t map:4;
        xed_uint32_t rr_inv:1;
        xed_uint32_t b_inv:1;
        xed_uint32_t x_inv:1;
        xed_uint32_t r_inv:1;
    } s;
    struct {  // AVX512 coarse
        xed_uint32_t map:4;
        xed_uint32_t rr_inv:1;
        xed_uint32_t b_inv:1;
        xed_uint32_t rx_inv:2;  
    } coarse;
#if defined(XED_APX)
    struct {  // APX
        xed_uint32_t map:3;
        xed_uint32_t rexb4:1;
        xed_uint32_t rr_inv:1;
        xed_uint32_t b_inv:1;
        xed_uint32_t x_inv:1;
        xed_uint32_t r_inv:1;
    } apx;
#endif // XED_APX
    xed_uint8_t u8;
} xed_evex_payload1_t;

// a union defining the second payload byte of the EVEX prefix
// APX reinterprets the ubit field as X4
typedef union {
    struct {  // AVX512
        xed_uint32_t pp:2;
        xed_uint32_t ubit:1;
        xed_uint32_t vexdest210:3;
        xed_uint32_t vexdest3:1;
        xed_uint32_t rexw:1;
    } s;
    xed_uint8_t u8;
} xed_evex_payload2_t;

// a union defining the third payload byte of the EVEX prefix
// APX extends the capability of the EVEX prefix by providing an NF bit
// and an ND bit (no-flags and new-data-destination respectively).
// with special CCMP/CTEST instructions, APX provides yet another different
// bit interpretation, where the four least significant bits represent SCC
typedef union{
    xed_uint8_t u8;
    struct  {    // AVX512
        xed_uint32_t mask:3;
        xed_uint32_t vexdest4p:1;
        xed_uint32_t bcrc:1;
        xed_uint32_t llrc:2;
        xed_uint32_t z:1;
    } s;
#if defined(XED_APX)
    struct {   // APX standard EVEX encoding
        xed_uint32_t mask_zero:2;
        xed_uint32_t nf:1;
        xed_uint32_t vexdest4p:1;
        xed_uint32_t nd:1;
        xed_uint32_t llrc:2;
        xed_uint32_t zeroing:1;
    } apx;
    struct {  // APX CCMP/CTEST reinterpretation
        xed_uint32_t scc:4;
        xed_uint32_t nd:1;
        xed_uint32_t llrc:2;
        xed_uint32_t zeroing:1;
    } apx_scc; 
#endif // XED_APX
} xed_evex_payload3_t;

// indicate whether the current decoder features/chip supports AVX512 architecture
static XED_INLINE xed_bool_t 
decoder_supports_avx512(xed_decoded_inst_t *d)
{
    if (xed3_operand_get_no_vex(d) || xed3_operand_get_no_evex(d))
        return 0;
    return 1;
}

static XED_INLINE xed_uint8_t set_evex_map(xed_decoded_inst_t *d, xed_evex_payload1_t evex1)
{
    xed_uint8_t map = evex1.s.map; // 4 bits map
#if defined(XED_APX)
    if (decoder_supports_apx(d))
    {
        map = evex1.apx.map;       // 3 bits map
        xed3_operand_set_rexb4(d, evex1.apx.rexb4);
    }
#endif // XED_APX
    xed3_operand_set_map(d, map);
    return map;
}

static void evex_scanner(xed_decoded_inst_t* d)
{
    unsigned char length = xed_decoded_inst_get_length(d);
    xed_uint8_t b;

    // assumption: length < max_bytes (checked in prefix_scanner)
    xed_assert(length < xed3_operand_get_max_bytes(d));
    b = decoded_inst_get_byte(d, length);
    
    if (b == 0x62)
    {
        xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
        xed_evex_payload1_t evex1;
        xed_uint_t eff_map;
        // check that it is not a BOUND instruction
        if (length + 1 < max_bytes) {
            evex1.u8 = decoded_inst_get_byte(d, length+1);
            if (!mode_64b(d) && evex1.coarse.rx_inv != 3) {
                /*this is a BOUND instruction */
                return;
            }
        }
        else {
            xed_decoded_inst_set_length(d, max_bytes);
            too_short(d);
            return;
        }
        
        // Link to the EVEX encoding space
        xed3_operand_set_vexvalid(d, 2);

        eff_map = set_evex_map(d, evex1);
        if (eff_map == 0) {
            xed_decoded_inst_set_length(d, length+2);
            bad_map(d);
            return; 
        }

        /*Unlike the vex and xop prefix scanners, here length is pointing
        at the evex 0x62 prefix byte.  We want to ensure that we have
        enough bytes available to read 4 bytes for evex prefix and 1 byte
        for an opcode */
        if (length + 4 < max_bytes) {
            xed_evex_payload2_t evex2;

            evex2.u8 = decoded_inst_get_byte(d, length+2);

            // above check guarantees that r and x are 1 in 16/32b mode.
            if (mode_64b(d)) {
                xed3_operand_set_rexr(d,  ~evex1.s.r_inv&1);
                xed3_operand_set_rexx(d,  ~evex1.s.x_inv&1);
                xed3_operand_set_rexb(d,  ~evex1.s.b_inv&1);
                xed3_operand_set_rexr4(d, ~evex1.s.rr_inv & 1);
            }

            if (xed_ild_map_valid_evex(eff_map) == 0) {
                xed_decoded_inst_set_length(d, length+4);    // we saw 62 xx xx xx opc
                bad_map(d);
                return;
            }

            xed3_operand_set_rexw(d,   evex2.s.rexw);
            xed3_operand_set_vexdest3(d,  evex2.s.vexdest3);
            xed3_operand_set_vexdest210(d, evex2.s.vexdest210);
            xed3_operand_set_ubit(d, evex2.s.ubit);
            xed_ild_set_pp_vex_prefix(d, evex2.s.pp);

            if(evex2.s.pp == 1) { // Compacted 0x66 prefix
                // Affect the instruction's effective OSZ (EOSZ). 
                // Used by EVEX instructions with GPR scalable operand size (GPRv/GPRy/...)
                xed3_operand_set_osz(d, 1);
            }

            if (!xed3_operand_get_error(d))
            {
                xed_evex_payload3_t evex3;
                evex3.u8 = decoded_inst_get_byte(d, length+3);

                xed3_operand_set_zeroing(d, evex3.s.z);
                
                // llrc is still required for rounding fixup much later
                // during decode.
                xed3_operand_set_llrc(d, evex3.s.llrc);
                
                set_vl(d, evex3.s.llrc);
                xed3_operand_set_bcrc(d, evex3.s.bcrc);
                xed3_operand_set_vexdest4(d, ~evex3.s.vexdest4p&1);
                if (!mode_64b(d) && evex3.s.vexdest4p==0)
                    bad_v4(d);

                xed3_operand_set_mask(d, evex3.s.mask);
                if (evex3.s.mask == 0 && evex3.s.z == 1)
                    bad_z_aaa(d);
            
#if defined(XED_APX)
                if (decoder_supports_apx(d))
                {
                    /* Set the APX reinterpreted EVEX bits */
                    // APX promoted instruction's NT will clear the MASK and BCRC XED operands, 
                    // but all other non-APX EVEX instructions won't clear the NF/ND operands.
                    xed3_operand_set_nf(d, evex3.apx.nf);  // EVEX.mask[2] -> APX.NF
                    xed3_operand_set_nd(d, evex3.apx.nd);  // EVEX.bcrc    -> APX.ND
                    if (xed3_operand_get_map(d) == 4) {
                        // For CCMP/CTEST (currently MAP4 only). 
                        // ILD has no mapping for opcode to CCMP/CTEST instructions. 
                        // Therefore, always set the SCC operand. 
                        // Note, APX pattern's NTs will clear it later if needed.
                        xed3_operand_set_scc(d, evex3.apx_scc.scc);
                    }
                }
#endif // XED_APX
            }

            length += 4;
            xed_decoded_inst_set_length(d, length);
            /* vex opcode scanner fits for evex instructions too: it just reads
             * one byte as nominal opcode, this is exactly what we want for 
             * evex*/
            evex_vex_opcode_scanner(d);
            
            /* identify the instruction as EVEX (will be used in the encoder to force
             * re-encoding in the EVEX space).
             * This will prevent cases where EVEX input will be re-encoded to VEX space */
            xed3_operand_set_must_use_evex(d, 1);
        }
        else {
            /*there is no enough bytes, hence we are out of bytes */
            xed_decoded_inst_set_length(d, max_bytes);    // we saw 62 0b11xx.xxxx        
            too_short(d);
        }
    }
}

void late_evex_scanner(xed_decoded_inst_t *d)
{
    /* Reinterpret the EVEX prefix bits.
     * Due to ModRM.mod dependency and performance in mind, do it as a late scanner */
#if defined(XED_APX)
    xed_uint_t mod3 = xed3_operand_get_mod3(d);
    xed_assert(xed3_operand_get_vexvalid(d)==2);
    if (!mod3 && decoder_supports_apx(d))
    {
        // [APX] Reinterpret the Ubit with memory index fourth EGPR bit.
        // Pacify the iPattern's UBIT condition and set the X4 inverted value.
        xed_uint_t ubit = xed3_operand_get_ubit(d);
        xed3_operand_set_ubit(d, 1);  // Needed for non-APX EVEX instructions
        xed3_operand_set_rexx4(d, ~ubit & 1);
    }
#endif // XED_APX
    (void) d; // Pacify compiler
}
#endif // defined(XED_SUPPORTS_AVX512)

#if defined(XED_APX)
// process the REX2 prefix if exists.
// This function checks for the existence of REX2 prefix (starting with xD5)
// and sets the first and second payload bytes accordingly (B3,X3,R3,B4...)
// then scans the instructions' opcode
static XED_INLINE void rex2_scanner(xed_decoded_inst_t *d)
{
    xed_uint8_t length = xed_decoded_inst_get_length(d);
    xed_uint8_t b;
    
    // assumption: length < max_bytes (checked in prefix_scanner)
    xed_assert(length < xed3_operand_get_max_bytes(d));
    b = decoded_inst_get_byte(d, length);

    /* REX2 Prefix */
    if (b == 0xD5)
    {
        xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);

        if (xed3_operand_get_rex(d))
        {
            xed3_operand_set_error(d, XED_ERROR_BAD_REX_PREFIX);
            // Keep parsing to provide a richer content of error...
        }
        
        /* Eat REX2 prefix byte and start the payload parser */
        // D5  rex2  opc
        // ^
        if (length + 1 < max_bytes)
        {
            // D5  rex2  opc
            //     ^
            static const xed_ild_map_enum_t rex2_bit_to_map[] = {
                XED_ILD_LEGACY_MAP0, XED_ILD_LEGACY_MAP1};
            xed_uint8_t map_bit = 0;
            xed_uint8_t rex2 = decoded_inst_get_byte(d, length + 1);
            xed3_operand_set_rex2(d, 1);

            map_bit = (rex2>>7) & 1;
            xed3_operand_set_map(d, rex2_bit_to_map[map_bit]);

            xed3_operand_set_rexr4(d, (rex2>>6) & 1);
            xed3_operand_set_rexx4(d, (rex2>>5) & 1);
            xed3_operand_set_rexb4(d, (rex2>>4) & 1);
            // Lower nibble - REX like
            xed3_operand_set_rexw(d, (rex2>>3) & 1);
            xed3_operand_set_rexr(d, (rex2>>2) & 1);
            xed3_operand_set_rexx(d, (rex2>>1) & 1);
            xed3_operand_set_rexb(d, (rex2)    & 1);


            // d5  rex2  opc
            //           ^
            if (length + 2 >= max_bytes) 
            {
                xed_decoded_inst_set_length(d, max_bytes); // We saw D5 xx
                too_short(d);
                return;
            }

            /* REX2 Opcode scanner */
            length += 2;
            b = decoded_inst_get_byte(d, length);
            xed3_operand_set_nominal_opcode(d, b);
            xed3_operand_set_pos_nominal_opcode(d, length);
            xed3_operand_set_srm(d, xed_modrm_rm(b));
            xed_decoded_inst_set_length(d, length+1); // We saw D5 xx opc
            xed_set_downstream_info(d,0);
        }
        else
        {
            xed_decoded_inst_set_length(d, max_bytes); // We saw D5
            too_short(d);
        }
    }
}
#endif // XED_APX

static void imm_scanner(xed_decoded_inst_t* d)
{
  xed_uint8_t imm_bytes;
  xed_uint8_t imm1_bytes;
  xed_uint8_t max_bytes = xed3_operand_get_max_bytes(d);
  unsigned char length = xed_decoded_inst_get_length(d);
  unsigned int pos_imm = 0;
  const xed_uint8_t* itext = d->_byte_array._dec;
  const xed_uint8_t* imm_ptr = 0;

  // Figure out how many imm bytes we need to collect, if any
  set_imm_bytes(d);
    
#if defined(XED_CATEGORY_3DNOW_DEFINED)
  if (xed3_operand_get_amd3dnow(d)) {
      if (length < max_bytes) {
          /*opcode is in immediate*/
          xed3_operand_set_pos_nominal_opcode(d, length);

          xed3_operand_set_nominal_opcode(d, 
                                          decoded_inst_get_byte(d, length));
          /*count the pseudo immediate byte, which is opcode*/
          xed_decoded_inst_inc_length(d); 
          /*imm_bytes == imm_bytes1 == 0 for amd3dnow */
          return;
      }
      else {
          too_short(d);
          return;
      }
  }
#endif


  // Denote location of the imm byte(s) from the byte stream
  // (consume imm1 if present)
  
  imm_bytes = bits2bytes(xed3_operand_get_imm_width(d));
  imm1_bytes = xed3_operand_get_imm1_bytes(d);
  if (imm_bytes)  {

      if (length + imm_bytes <= max_bytes) {
          xed3_operand_set_pos_imm(d, length);
          /* eat imm */
          length += imm_bytes;
          xed_decoded_inst_set_length(d, length); 

          if (imm1_bytes)  {
              if (length + imm1_bytes <= max_bytes) {
                  xed3_operand_set_pos_imm1(d, length);
                  imm_ptr = itext + length;
                  length += imm1_bytes; /* eat imm1 */
                  xed_decoded_inst_set_length(d, length);
                  //set uimm1 value
                  xed3_operand_set_uimm1(d, *imm_ptr);
              }
              else {/* Ugly code */
                    too_short(d);
                    return;
              }
            }
      }
      else {
          too_short(d);
          return;
      }
  }

  // Store the imm byte(s)
  
  /* FIXME: setting UIMM chunks. This can be done better, 
   * for example special capturing function in ILD, like for imm_bytes*/
  pos_imm = xed3_operand_get_pos_imm(d);
  imm_ptr = itext + pos_imm;
  switch(imm_bytes)  {
  case 0:
      break;
  case 1: {
      xed_uint8_t esrc, uimm0 = 0;
      memcpy(&uimm0, imm_ptr, sizeof(uimm0));
      esrc = uimm0 >> 4;
      xed3_operand_set_uimm0(d, uimm0);
      xed3_operand_set_esrc(d, esrc);
      break;
  }
  case 2: {
      xed_uint16_t uimm0 = 0;
      memcpy(&uimm0, imm_ptr, sizeof(uimm0));
      xed3_operand_set_uimm0(d, uimm0);
      break;
  }
  case 4: {
      xed_uint32_t uimm0 = 0;
      memcpy(&uimm0, imm_ptr, sizeof(uimm0));
      xed3_operand_set_uimm0(d, uimm0);
      break;
  }
  case 8: {
      xed_uint64_t uimm0 = 0;
      memcpy(&uimm0, imm_ptr, sizeof(uimm0));
      xed3_operand_set_uimm0(d, uimm0);
      break;
  }
  default:
      /*Unexpected immediate width, this should never happen*/
      xed_assert(0);
  }

  /* uimm1 is set earlier */
}


////////////////////////////////////////////////////////////////////////////////

void xed_ild_lookup_init(void) {
    xed_ild_eosz_init();
    xed_ild_easz_init();

    xed_ild_imm_l3_init();
    xed_ild_disp_l3_init();

    init_has_disp_regular_table();
    init_eamode_table();
    init_has_sib_table();

}


void xed_ild_init(void) {
    init_prefix_table();
    xed_ild_lookup_init();
    xed_init_chip_model_info();
#if defined(XED_EXTENSION_XOP_DEFINED) 
    xed_ild_chip_init();
#endif
}




void
xed_instruction_length_decode(xed_decoded_inst_t *ild)
{
    prefix_scanner(ild);
#if defined(XED_AVX) 
    if (xed3_operand_get_out_of_bytes(ild))
        return;
    if (!xed3_operand_get_no_vex(ild))
        vex_scanner(ild);
#endif
#if defined(XED_SUPPORTS_AVX512)
    // evex scanner assumes it can read bytes so we must check for limit first.
    if (xed3_operand_get_out_of_bytes(ild) ||
        xed3_operand_get_error(ild))
        return;

    // if we got a vex prefix (which also sucks down the opcode),
    // then we do not need to scan for evex prefixes.
    if (!xed3_operand_get_vexvalid(ild)) {
        if (decoder_supports_avx512(ild)) {
            // Scan EVEX prefixes only if chip supports AVX512
            evex_scanner(ild);
        }
    }
#endif
    // scanner assumes it can read bytes so we must check for limit first.
    if (xed3_operand_get_out_of_bytes(ild))
        return;    
    
    if (xed3_operand_get_vexvalid(ild)) {
        catch_invalid_rex_or_legacy_prefixes(ild);
    }

    if (!xed3_operand_get_vexvalid(ild)) {
        // Scan the legacy encoding space
#if defined(XED_APX)
        if (decoder_supports_apx(ild)) {
            rex2_scanner(ild);
        }
#endif // XED_APX
        if (opcode_scanner_needed(ild)) {
            opcode_scanner(ild);
        }
    }
    
    if (xed3_operand_get_out_of_bytes(ild))
        return;        
    
    xed_modrm_scanner(ild);
    sib_scanner(ild);
    disp_scanner(ild);
    imm_scanner(ild);
#if defined(XED_SUPPORTS_AVX512)
    if (xed3_operand_get_vexvalid(ild) == 2) { // EVEX
        late_evex_scanner(ild);
    }
#endif
}

#include "xed-chip-modes.h"

/// This is the second main entry point for the decoder
/// used for new xed3 decoding.
XED_DLL_EXPORT xed_error_enum_t 
xed_ild_decode(xed_decoded_inst_t* xedd, 
           const xed_uint8_t* itext, 
           const unsigned int bytes)
{
    xed_uint_t tbytes;
    xed_features_elem_t const *features = 0;
    xed_chip_enum_t chip = xed_decoded_inst_get_input_chip(xedd);
    if (chip != XED_CHIP_INVALID)
        features = xed_get_features(chip);
    set_chip_modes(xedd, chip, features); // FIXME: add support for cpuid features

    xedd->_byte_array._dec = itext;

    tbytes =  bytes;
    if (bytes > XED_MAX_INSTRUCTION_BYTES)
        tbytes = XED_MAX_INSTRUCTION_BYTES;
    xed3_operand_set_max_bytes(xedd, tbytes);
    xed_instruction_length_decode(xedd);
    
    if (xed3_operand_get_out_of_bytes(xedd))
        return XED_ERROR_BUFFER_TOO_SHORT;
    return xed3_operand_get_error(xedd);
}


// xed-ild-private.h
xed_bits_t 
xed_ild_cvt_mode(xed_machine_mode_enum_t mmode) {

    xed_bits_t result = 0;
    switch(mmode)
    {
      case XED_MACHINE_MODE_LONG_64:
        result = XED_GRAMMAR_MODE_64;

        break;
      case XED_MACHINE_MODE_LEGACY_32:
      case XED_MACHINE_MODE_LONG_COMPAT_32:
      case XED_MACHINE_MODE_REAL_32:
        result = XED_GRAMMAR_MODE_32;
        break;

      case XED_MACHINE_MODE_REAL_16:
      case XED_MACHINE_MODE_LEGACY_16:
      case XED_MACHINE_MODE_LONG_COMPAT_16:
        result = XED_GRAMMAR_MODE_16;
        break;
      default:
        xed_derror("Bad machine mode in xed_ild_cvt_mode() call");
    }
    return result;
}
