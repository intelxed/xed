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
/// @file xed-encode.c

////////////////////////////////////////////////////////////////////////////
// This file contains the public interface to the encoder. 
////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-encode-private.h"
#include "xed-operand-accessors.h"
#include "xed-reg-class.h"

#include "xed-encoder.h" // a generated file of prototypes

//FIXME just need one proto from the above file: xed_bool_t
//xed_encode_nonterminal_ISA_ENCODE(xed_encoder_request_t& xes);


const xed_operand_values_t*
xed_encoder_request_operands_const(const xed_encoder_request_t* p) {
    return p;
}
xed_operand_values_t*
xed_encoder_request_operands(xed_encoder_request_t* p) {
    return p;
}

// Emitting the legacy map bytes.
// Need to convert from xed_ild_map_enum_t to the actual bytes.
// called from generated code (in OBJDIR/xed-enc-patterns.c)
void xed_encoder_request_emit_legacy_map(xed_encoder_request_t* q)
{
    xed_uint8_t bits;
    xed_uint16_t value;
    xed_ild_map_enum_t map;
    map = XED_STATIC_CAST(xed_ild_map_enum_t,xed_encoder_get_map(q));

    switch(map) {
    case XED_ILD_MAP0:
      return;
      
    case XED_ILD_MAP1:
      value = 0x0F;
      bits = 8;
      break;
      
    case XED_ILD_MAP2:
      value = 0x380F; //need to convert big to little endian
      bits = 16;
      break;
      
    case XED_ILD_MAP3:
      value = 0x3A0F; //need to convert big to little endian
      bits = 16;
      break;
      
    case XED_ILD_MAPAMD:
      value = 0x0F0F;
      bits = 16;
      break;
      
    default:
      xed3_operand_set_error(q,XED_ERROR_GENERAL_ERROR);
      return;
    
    } 
    xed_encoder_request_emit_bytes(q,bits,value);
}

void xed_encoder_request_emit_bytes(xed_encoder_request_t* q,
                                   const xed_uint8_t bits,
                                   const xed_uint64_t value){
    
    xed_uint32_t byte_offset;
    xed_uint8_t* p;
    xed_uint32_t bit_offset = xed_encoder_request_bit_offset(q);
   
    //verify that we are aligned on byte
    xed_assert((bit_offset & 7) == 0);
    if ( bit_offset + bits > 8 * xed_encoder_request_ilen(q)) {
        xed3_operand_set_error(q,XED_ERROR_BUFFER_TOO_SHORT);
        return;
    }

    byte_offset = bit_offset >> 3;    

    xed_encoder_request_update_bit_offset(q, bits);
    p = q->_byte_array._enc+byte_offset;

    switch(bits){
    case 8:
        *p = XED_STATIC_CAST(xed_uint8_t,value);
        break;
    case 16:
        *XED_REINTERPRET_CAST(xed_uint16_t*,p) = 
                        XED_STATIC_CAST(xed_uint16_t,value);
        break;
    case 32:
        *XED_REINTERPRET_CAST(xed_uint32_t*,p)= 
                        XED_STATIC_CAST(xed_uint32_t,value);
        break;
    case 64:
        *XED_REINTERPRET_CAST(xed_uint64_t*,p)= value;
        break;
    default:
        xed_assert(0); 
    }
    return;
}


void xed_encoder_request_encode_emit(xed_encoder_request_t* q,
                                     const unsigned int bits,
                                     const xed_uint64_t value) {
    xed_uint32_t nbits;
    xed_uint32_t byte_offset;
    xed_uint32_t bit_in_byte;
    xed_uint32_t processed_bits;
    xed_uint32_t t_bit_offset = xed_encoder_request_bit_offset(q);
    if ( t_bit_offset + bits > 8 * xed_encoder_request_ilen(q)) {
        xed3_operand_set_error(q,XED_ERROR_BUFFER_TOO_SHORT);
        return;
    }

    nbits = bits;
    byte_offset = t_bit_offset >> 3;
    bit_in_byte = t_bit_offset & 7;
    processed_bits = 0;

    // looking for multiples of 8 on the input and when we are at natural
    // byte boundaries in the output.
    if ((bits&7) == 0 && bit_in_byte == 0)    {
        xed_uint8_t* p;
        //int shift;
        
        // the value to encode is a multiple of 8 bits and the current bit
        // pointer is aligned on an 8b boundary, then we can jam in the
        // bytes efficiently using 8/16/32/64b stores.
        xed_encoder_request_update_bit_offset(q, bits);
        p = q->_byte_array._enc+byte_offset;

        switch(bits)        {
          case 8:
            *p = XED_STATIC_CAST(xed_uint8_t,value);
            break;
          case 16:
            *XED_REINTERPRET_CAST(xed_uint16_t*,p) = XED_STATIC_CAST(xed_uint16_t,value);
            break;
          case 32:
            *XED_REINTERPRET_CAST(xed_uint32_t*,p)= XED_STATIC_CAST(xed_uint32_t,value);
            break;
          case 64:
            *XED_REINTERPRET_CAST(xed_uint64_t*,p)= value;
            break;
          default:
            xed_assert(0); 
        }
        return;
    }

    // for inputs that are not multiples of 8-bits:
    while (nbits > 0) {
        xed_uint64_t tvalue; // value we'll shift to get to the right bits
        xed_uint32_t tbits; // # of bits we are taking in this iteraation
        xed_uint32_t bits_remaining_in_byte = 8 - bit_in_byte; 


        if (bits_remaining_in_byte >= nbits) {
            // What's left fits in the current byte.
            tbits  = nbits;
            nbits  = 0;
            tvalue = value;
        }
        else {
            xed_uint32_t vshift;
            
            // we have more bits than fit in what remains of this
            // byte. split it up and take just what remains in this byte.
            tbits  = bits_remaining_in_byte;
            nbits  = nbits - tbits;
            vshift = bits - processed_bits - tbits;
            tvalue = value >> vshift;
            processed_bits += tbits;
        }
        
        if (tbits == 8)
            q->_byte_array._enc[byte_offset] = XED_STATIC_CAST(xed_uint8_t,tvalue);
        else {
            xed_uint64_t mask;
            xed_uint32_t shift;
 
            // we will be OR'ing bits in to this byte so it had better
            // start off as zero.
            if (bit_in_byte == 0)
                q->_byte_array._enc[byte_offset] = 0;

            mask = (1<<tbits)-1;
            shift = bits_remaining_in_byte - tbits;
            q->_byte_array._enc[byte_offset] |= XED_STATIC_CAST(xed_uint8_t,(tvalue & mask) << shift);
        }
        byte_offset++;
        bit_in_byte = 0;
    }
    xed_encoder_request_update_bit_offset(q,bits);
}



xed_bool_t
xed_encoder_request__memop_compatible(const xed_encoder_request_t* p,
                                      xed_operand_width_enum_t operand_width) {
    // return 1 if the memop specified in the operand storage is
    // compatible with the argument operand_width.
    xed_uint16_t operand_width_bytes;
    xed_uint16_t request_width_bytes = xed3_operand_get_mem_width(p);

    // figure out the width, in bytes, of the specified operand
    xed_uint8_t eosz  = xed3_operand_get_eosz(p);
    xed_assert(operand_width < XED_OPERAND_WIDTH_LAST);
    xed_assert(eosz < 4);
    operand_width_bytes = xed_width_bits[operand_width][eosz]>>3;
    //variable sized stuff we punt on the width
    if (operand_width_bytes == 0 || operand_width_bytes == request_width_bytes)
        return 1;
    return 0;
}


void xed_encoder_request_zero_set_mode(xed_encoder_request_t* p,
                                        const xed_state_t* dstate) {
    memset(p, 0, sizeof(xed_encoder_request_t));
    xed_operand_values_set_mode(p,dstate);
}

void xed_encoder_request_zero(xed_encoder_request_t* p)    {
    memset(p, 0, sizeof(xed_encoder_request_t));
}

xed_iclass_enum_t
xed_encoder_request_get_iclass( const xed_encoder_request_t* p)
{
    return XED_STATIC_CAST(xed_iclass_enum_t,xed3_operand_get_iclass(p));
}
void   xed_encoder_request_set_iclass( xed_encoder_request_t* p, 
                                       xed_iclass_enum_t iclass) {
    xed3_operand_set_iclass(p,iclass);
}
void xed_encoder_request_set_repne(xed_encoder_request_t* p) {
    xed3_operand_set_rep(p,2);
}
void xed_encoder_request_set_rep(xed_encoder_request_t* p) {
    xed3_operand_set_rep(p,3);
}
void xed_encoder_request_clear_rep(xed_encoder_request_t* p) {
    xed3_operand_set_rep(p,0);
}


void
xed_encoder_request_set_effective_operand_width( xed_encoder_request_t* p, 
                                                 xed_uint_t width_bits) {
    switch(width_bits) {
      // x87 memops use the width.
      case 8:      xed3_operand_set_eosz(p,0); break;
        
      case 16:     xed3_operand_set_eosz(p,1); break;
      case 32:     xed3_operand_set_eosz(p,2); break;
      case 64:     xed3_operand_set_eosz(p,3); break;
      default:
        xed_assert( width_bits == 8 ||
                    width_bits == 16 ||
                    width_bits == 32 ||
                    width_bits == 64 );
        break;
    }
}
void
xed_encoder_request_set_effective_address_size( xed_encoder_request_t* p, 
                                                xed_uint_t width_bits) {
    switch(width_bits) {
      case 16:     xed3_operand_set_easz(p,1); break;
      case 32:     xed3_operand_set_easz(p,2); break;
      case 64:     xed3_operand_set_easz(p,3); break;
      default:
        xed_assert( width_bits == 16 ||
                    width_bits == 32 ||
                    width_bits == 64 );
        break;
    }
}

void xed_encoder_request_set_branch_displacement(xed_encoder_request_t* p,
                                                 xed_int32_t brdisp,
                                                 xed_uint_t nbytes) {
    xed_operand_values_set_branch_displacement(p, brdisp, nbytes);
}

void xed_encoder_request_set_relbr(xed_encoder_request_t* p) {
    xed3_operand_set_relbr(p,1);
}
void xed_encoder_request_set_ptr(xed_encoder_request_t* p) {
    xed3_operand_set_ptr(p,1);
}

void xed_encoder_request_set_memory_displacement(xed_encoder_request_t* p,
                                                 xed_int64_t memdisp,
                                                 xed_uint_t nbytes) {
    xed_operand_values_set_memory_displacement(p, memdisp, nbytes);
}

void xed_encoder_request_set_uimm0(xed_encoder_request_t* p,
                                   xed_uint64_t uimm,
                                   xed_uint_t nbytes) {
    xed_operand_values_set_immediate_unsigned(p, uimm, nbytes);
    xed3_operand_set_imm0(p,1);
}

void xed_encoder_request_set_uimm0_bits(xed_encoder_request_t* p,
                                        xed_uint64_t uimm,
                                        xed_uint_t nbits) {
    xed_operand_values_set_immediate_unsigned_bits(p, uimm, nbits);
    xed3_operand_set_imm0(p,1);
}
void xed_encoder_request_set_uimm1(xed_encoder_request_t* p,
                                   xed_uint8_t uimm) {
    xed3_operand_set_imm1(p,1);
    xed3_operand_set_uimm1(p,uimm);
}

void xed_encoder_request_set_simm(xed_encoder_request_t* p,
                                  xed_int32_t simm,
                                  xed_uint_t nbytes) {

    xed_operand_values_set_immediate_signed(p, simm, nbytes);
    xed3_operand_set_imm0(p,1);
}

void xed_encoder_request_set_agen(xed_encoder_request_t* p) {
    xed3_operand_set_agen(p,1);
}
void xed_encoder_request_set_mem0(xed_encoder_request_t* p) {
    xed3_operand_set_mem0(p,1);
}
void xed_encoder_request_set_mem1(xed_encoder_request_t* p) {
    xed3_operand_set_mem1(p,1);
}
void xed_encoder_request_set_memory_operand_length(xed_encoder_request_t* p,
                                                   xed_uint_t nbytes) {
    xed3_operand_set_mem_width(p,nbytes);
}
void xed_encoder_request_set_seg0(xed_encoder_request_t* p,
                                  xed_reg_enum_t seg_reg) {
    xed3_operand_set_seg0(p,seg_reg);
}
void xed_encoder_request_set_seg1(xed_encoder_request_t* p,
                                  xed_reg_enum_t seg_reg) {
    xed3_operand_set_seg1(p,seg_reg);
}
void xed_encoder_request_set_base0(xed_encoder_request_t* p,
                                  xed_reg_enum_t base_reg) {
    xed3_operand_set_base0(p,base_reg);
}
void xed_encoder_request_set_base1(xed_encoder_request_t* p,
                                  xed_reg_enum_t base_reg) {
    xed3_operand_set_base1(p,base_reg);
}
void xed_encoder_request_set_index(xed_encoder_request_t* p,
                                  xed_reg_enum_t index_reg) {
    xed3_operand_set_index(p,index_reg);
}
void xed_encoder_request_set_scale(xed_encoder_request_t* p,
                                   xed_uint_t scale) {
    xed3_operand_set_scale(p,scale);
}

void xed_encoder_request_set_operand_order(xed_encoder_request_t* p,
                                           xed_uint_t operand_index, 
                                           xed_operand_enum_t name) {
    xed_assert(operand_index < XED_ENCODE_ORDER_MAX_OPERANDS);
    p->_operand_order[operand_index] = name;

    /* track the maximum number of operands */
    if (operand_index+1 > p->_n_operand_order)
        p->_n_operand_order = operand_index + 1;
}

xed_operand_enum_t
xed_encoder_request_get_operand_order(xed_encoder_request_t* p,
                                      xed_uint_t operand_index) {
    xed_assert(operand_index < XED_ENCODE_ORDER_MAX_OPERANDS &&
               operand_index < p->_n_operand_order);
    return XED_STATIC_CAST(xed_operand_enum_t,p->_operand_order[operand_index]);
}


void xed_encoder_request_zero_operand_order(xed_encoder_request_t* p) {
    p->_n_operand_order = 0;
}

void xed_encoder_request_set_reg(xed_encoder_request_t* p,
                                 xed_operand_enum_t operand,
                                 xed_reg_enum_t reg) {
    xed_assert(operand < XED_OPERAND_LAST);
    xed_operand_values_set_operand_reg(p,operand,reg);
}

void
xed_encode_request_print(const xed_encoder_request_t* p,
                         char* buf,
                         xed_uint_t buflen)  {
    char* t;
    xed_uint_t i;
    xed_uint_t blen = buflen;
    if (buflen < 1000) {
        (void)xed_strncpy(buf,
                          "Buffer passed to xed_encode_request_print is "
                          "too short. Try 1000 bytes",
                          buflen);
        return;
    }
    blen = xed_strncpy(buf,
                      xed_iclass_enum_t2str(xed_encoder_request_get_iclass(p)),
                      blen);
    blen = xed_strncat(buf, " ",blen);
    t = buf + xed_strlen(buf);
    xed_operand_values_print_short( p, t, blen);
    blen = buflen  - xed_strlen(buf);

    if (p->_n_operand_order) {
        blen = xed_strncat(buf,"\nOPERAND ORDER: ",blen);
        for(i=0;i<p->_n_operand_order;i++) { 
            const char*  s = xed_operand_enum_t2str(XED_STATIC_CAST(xed_operand_enum_t,p->_operand_order[i]));
            blen = xed_strncat(buf, s, blen);
            blen = xed_strncat(buf, " ", blen);
        }
    }
    (void) xed_strncat(buf, "\n", blen);
}


//////////////////////////////////////////////////////////////////////////////////////////////
//FIXME: I am not fond of this fixed table, since it is a testament to
//how difficult it is to encode instructions. One day, I'll make this
//use the XED encoding engine.
#define XED_MAX_FIXED_NOPS 9
static const xed_uint8_t xed_nop_array[XED_MAX_FIXED_NOPS][XED_MAX_FIXED_NOPS] = {
    /*1B*/  { 0x90 },
    /*2B*/  { 0x66, 0x90},
    /*3B*/  { 0x0F, 0x1F, 0x00},
    /*4B*/  { 0x0F, 0x1F, 0x40, 0x00},
    /*5B*/  { 0x0F, 0x1F, 0x44, 0x00, 0x00},
    /*6B*/  { 0x66, 0x0F, 0x1F, 0x44, 0x00, 0x00},
    /*7B*/  { 0x0F, 0x1F, 0x80, 0x00, 0x00,0x00, 0x00},
    /*8B*/  { 0x0F, 0x1F, 0x84, 0x00, 0x00, 0x00,0x00, 0x00},
    /*9B*/  { 0x66, 0x0F, 0x1F, 0x84, 0x00, 0x00, 0x00,0x00, 0x00},
};

XED_DLL_EXPORT xed_error_enum_t
xed_encode_nop(xed_uint8_t* array,
               const unsigned int ilen)
{
    if (ilen >= 1 && ilen <= XED_MAX_FIXED_NOPS)  {
        // subtract one from the requested length to get the array index.
        memcpy(array, xed_nop_array[ilen-1], ilen);
        return XED_ERROR_NONE;
    }
    return XED_ERROR_GENERAL_ERROR;
}


#if defined(XED_AVX) || defined(XED_SUPPORTS_AVX512)        
static void set_vl(xed_reg_enum_t reg, xed_uint_t* vl)
{
    xed_uint_t nvl = *vl;
    xed_reg_class_enum_t rc = xed_reg_class(reg);
    // ignore XMM class becaues *vl is either 0 or set by user.

    if (rc == XED_REG_CLASS_YMM && nvl < 1)
        nvl = 1;
#  if defined(XED_SUPPORTS_AVX512)
    else if (rc == XED_REG_CLASS_ZMM && nvl < 2)
        nvl = 2;
#  endif

    *vl = nvl;
}


// uvl= 0,    1,    2
// vl=  012   012   012
//      xgg   txt   ttx
//
// x=match
// t=trust
// g=grow (using observed guess)

static void xed_encode_precondition_vl(xed_encoder_request_t* req)
{
    xed_uint_t vl;
    vl = xed3_operand_get_vl(req);
    // If user set nonzero value, respect it.  If user set vl=0, we cannot
    // tell so we try to override.  Note: It would be very wrong to
    // override incoming nonzero VL values because the observed register
    // sizes represent a MINIMUM valid VL. The actual VL can be larger for
    // "shrinking" converts (PD2PS, PD2DQ, PD2UQQ, etc.). 
    if (vl == 0)  
    {
        xed_operand_enum_t i;
        xed_reg_enum_t r;

        r = xed3_operand_get_index(req);
        // set VL based on index reg if vector reg as it would be for VSIB.
        set_vl(r,&vl);  

        // set VL based on REG any operands
        for (i=XED_OPERAND_REG0;i<=XED_OPERAND_REG8;i++)
        {
            xed3_get_generic_operand(req, i, &r);
            if (r == XED_REG_INVALID)
                break;
            set_vl(r,&vl);
        }
        xed3_operand_set_vl(req,vl);
    }
}

#endif

static void xed_encode_precondition(xed_encoder_request_t* r) {
    /* If the base is RIP, then we help the encoder users by adjusting or
     * supplying a memory displacement. It must be 4B, even if it is zero.
     *
     * This ignores the case of a 2B displacement. No one should do that as
     * it is not legal in 64b mode.
     */
    xed_int64_t t;
    if (xed3_operand_get_base0(r)==XED_REG_RIP) {
        if (xed3_operand_get_disp_width(r) == 0) {
            xed3_operand_set_disp_width(r,32);
            xed3_operand_set_disp(r,0);
        }
        else if (xed3_operand_get_disp_width(r) == 8) {  
           xed3_operand_set_disp_width(r,32);
            /* sign extend the current value to 64b and then pick off the
             * correct part of it */
            t = xed3_operand_get_disp(r);
            xed_operand_values_set_memory_displacement_bits(r,
                                                            t, 32);
        }
    }
#if defined(XED_AVX) || defined(XED_SUPPORTS_AVX512)        
    xed_encode_precondition_vl(r);
#endif
}

XED_DLL_EXPORT xed_error_enum_t xed_encode(xed_encoder_request_t* r,
                                           xed_uint8_t* array, 
                                           const unsigned int ilen,
                                           unsigned int* olen) {
    xed_iclass_enum_t iclass = xed_encoder_request_get_iclass(r);
    if (iclass != XED_ICLASS_INVALID && 
        iclass < XED_ICLASS_LAST && 
        ilen > 0 &&
        array != 0)
    {
        xed_bool_t okay;
        xed_encoder_vars_t xev;
        r->_byte_array._enc = array;

        // FIRST THING: set up the ephemeral storage for the encoder
        xed_encoder_request_set_encoder_vars(r,&xev);

        xed_encoder_request_set_ilen(r,ilen);
        xed_encode_precondition(r);
        okay = xed_encode_nonterminal_ISA_ENCODE(r);

        if (okay) {
            xed_uint32_t t_bit_offset = xed_encoder_request_bit_offset(r);
            xed_assert((t_bit_offset & 7) == 0); // no partial bytes
            *olen = (t_bit_offset >> 3); // offset points to the 1st bit of next byte
            xed_assert(ilen >= *olen);
            xed_encoder_request_vars_remove(r);
            return XED_ERROR_NONE;
        }
        xed_encoder_request_vars_remove(r);
        if (xed3_operand_get_error(r) != XED_ERROR_NONE)
            return xed3_operand_get_error(r);
        return XED_ERROR_GENERAL_ERROR;
    }
    return XED_ERROR_GENERAL_ERROR; 
}




