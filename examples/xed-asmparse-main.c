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

// more natural assembly language parser

#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#include "xed-asmparse.h"

#include "xed/xed-interface.h"
#include "xed-examples-util.h"

static xed_uint_t intel_asm_emits=0;

static xed_bool_t test_has_relbr(const xed_inst_t* p);
static xed_bool_t has_relbr(xed_iclass_enum_t iclass);

static void delete_string_list(xed_str_list_t* h) {
    // clean up memory allocated
    xed_str_list_t* p=h;
    while(p) {
        xed_str_list_t* t=0;
        free(p->s); // free the string content
        t = p->next;
        free(p);  // free the node itself
        p = t;
    }
}
    

static char* duplicate(char const* const s) {
    return xed_strdup(s);
}

static xed_str_list_t* split_string(const char* p)
{
    xed_str_list_t* q = xed_tokenize(p,";");
    // the strings returned from xed_tokenize are all part of the original
    // string. we duplicate them for easier cleanup later
    xed_str_list_t* a = q;
    while(a) {
        a->s = duplicate(a->s);
        a = a->next;
    }
    return q;
}
    
static xed_str_list_t* process_args(int argc, char** argv,
                                    xed_uint_t* mode,
                                    int* verbose)
{
    // sets mode, verbose and fills in a linked list of strings as the
    // return value.  Also sets intel_asm_emits.
    
    const char* usage = "Usage: %s [-16|-32|-64] [--emit] [-v|-q] <assembly line>\n" 
                        "\tThe assembly line can have semicolon separators " 
                        "to allow for multiple instructions.\n"
                        "\tThe --emit option changes output to Intel compiler __emit lines.\n"
                        "\n\n";
    
    xed_str_list_t* string_list;
    int i = 0;
    unsigned int len = 0;
    char* s = 0;
    char* p = 0;
    char* q = 0;
    int keep_going = 1;
    int mode_found = 0;
    int first_arg = 1;
    if (argc<=1) {
        asp_error_printf(usage, argv[0]);
        exit(1);
    }
    *mode = 32;
    while(keep_going) {
        keep_going = 0;
        if (first_arg >= argc)
            break;
        if (strcmp("-32",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            *mode = 32;
            first_arg++;
        }
        else if (strcmp("-16",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            *mode = 16;
            first_arg++;
        }
        else if (strcmp("-64",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            *mode = 64;
            first_arg++;
        }
        else if (strcmp("-v",argv[first_arg])==0) {
            keep_going = 1;
            (*verbose)++;
            first_arg++;
        }
        else if (strcmp("-q", argv[first_arg])== 0) {
            keep_going = 1;
            *verbose = 0;
            first_arg++;
        }
        else if (strcmp("--emit", argv[first_arg])== 0) {
            intel_asm_emits=1;
            keep_going = 1;
            first_arg++;
        }

    }
    for(i=first_arg;i<argc;i++) {
        // add one for trailing space or null at end
        len = len + xed_strlen(argv[i]) + 1;
    }
    
    if (len == 0) {
        asp_error_printf("Need a command line to parse\n");
        exit(1);
    }

    
    p = s = (char*) malloc(len);
    assert(p!=0);
    for(i=first_arg;i<argc;i++) {
        if (i>first_arg) // spaces between secondary args
           *p++ = ' ';
        q = argv[i];
        while(*q)  // copy argument
            *p++ = *q++;
    }
    *p = 0;  // null terminate

    string_list = split_string(s);
    free(s);
    return string_list;
}

static void set_state(xed_state_t* dstate, xed_enc_line_parsed_t* v) {
    xed_state_zero(dstate);
        
    if (v->mode == 16) {
        dstate->stack_addr_width=XED_ADDRESS_WIDTH_16b;
        dstate->mmode=XED_MACHINE_MODE_LEGACY_16;
    }
    else if (v->mode == 32) {
        dstate->stack_addr_width=XED_ADDRESS_WIDTH_32b;
        dstate->mmode=XED_MACHINE_MODE_LEGACY_32;
    }
    else if (v->mode == 64) {
        dstate->stack_addr_width=XED_ADDRESS_WIDTH_64b;
        dstate->mmode=XED_MACHINE_MODE_LONG_64;
    }
    else {
        asp_error_printf("Invalid mode: %d\n", v->mode);
        exit(1);
    }

}

/* Make string p1 + "_" + p2, put it into result
   Check if matching iclass exists.
   If it exists, return true, otherwise false */
static xed_bool_t probe_iclass_string(const char *p1, const char *p2, 
                                      char *result, int maxlen) {
    xed_strncpy(result, p1, maxlen);
    xed_strncat(result, "_", maxlen);
    xed_strncat(result, p2, maxlen);
    xed_iclass_enum_t valid_iclass = str2xed_iclass_enum_t(result);
    return (valid_iclass != XED_ICLASS_INVALID);
}

static void process_prefixes(xed_enc_line_parsed_t* v,
                             xed_encoder_instruction_t* inst)
{
    slist_t* q = v->prefixes;
    while(q) {
        if (strcmp(q->s, "LOCK") == 0) {
            /* nothing required */
        }
        else if (strcmp(q->s, "REP") == 0 || 
                 strcmp(q->s, "REPE") == 0) {
            xed_rep(inst); 
        }
        else if (strcmp(q->s, "XRELEASE") == 0) {
            xed_rep(inst);
        }
        else if (strcmp(q->s, "XACQUIRE") == 0) {
            xed_repne(inst);
        }
        else if (strcmp(q->s, "REPNE") == 0) {
            xed_repne(inst); 
        }
        else if (strcmp(q->s, "DATA16") == 0) {
            //FIXME: data16
        }
        else if (strcmp(q->s, "DATA32") == 0) {
            //FIXME: data32
        }
        else if (strcmp(q->s, "ADDR16") == 0) {
            //FIXME: addr16
        }
        else if (strcmp(q->s, "ADDR32") == 0) {
            //FIXME: addr32
        }
        else if (strcmp(q->s, "REX") == 0) {
            //FIXME: rex
        }
        else if (strcmp(q->s, "REXW") == 0) {
            //FIXME: rexw
        }
        else {
            asp_error_printf("Unhandled prefix: %s\n", q->s);
            exit(1);
        }
        q = q->next;
    }
}

typedef struct {
    const char* s;
    xed_uint_t src;
    xed_uint_t dst;
} bcast_info_t;

static const bcast_info_t bcast[] = {
    { "{1TO2}",  1,  2 },
    { "{1TO4}",  1,  4 },
    { "{1TO8}",  1,  8 },
    { "{1TO16}", 1, 16 },
    { "{1TO32}", 1, 32 },
    { "{1TO64}", 1, 64 },
    { 0, 0, 0} 
};

static void process_mem_decorator(slist_t* decos, xed_encoder_operand_t* operand, xed_uint_t* pos)
{

    slist_t* d = decos;
    xed_uint_t  i = *pos;
    int found_a_bcast_decorator = 0;
    while(d && !found_a_bcast_decorator) {
        xed_uint_t j=0;
        for(j=0;bcast[j].s;j++) {
            if (strcmp(bcast[j].s,d->s)==0) {
                //FIXME: RECORD WHICH DECORATOR IS FOUND SO WE CAN COMPUTE
                //       THE VL FOR FPCLASS AND VCMP TYPE INSTR.
                operand[i++] = xed_other(XED_OPERAND_BCAST,1);
                found_a_bcast_decorator = 1;
                break;
            }
        }
        d = d->next;
    }
    *pos = i;
    
    if (decos && !found_a_bcast_decorator) {
        asp_error_printf("Bad memory decorator: ");
        d = decos;
        while (d) {
            asp_error_printf("%s ", d->s);
            d = d->next;
        }
        exit(1);
    }
}

static void check_too_many_operands(int op_pos) {
    if (op_pos >= XED_ENCODER_OPERANDS_MAX) {
        asp_error_printf("Too many operands\n");
        exit(1);
    }
}

static int process_rc_sae(char const* s,xed_encoder_operand_t* operand, xed_uint_t* pos)
{
#if defined(XED_SUPPORTS_AVX512)
    xed_uint_t i = *pos;
    if (strcmp("{RNE-SAE}",s)==0) {
        check_too_many_operands(i+1);
        operand[i++] = xed_other(XED_OPERAND_ROUNDC,1);
        operand[i++] = xed_other(XED_OPERAND_SAE,1);
        *pos = i;
        return 1;
    }
    else if (strcmp("{RD-SAE}",s)==0) {
        check_too_many_operands(i+1);
        operand[i++] = xed_other(XED_OPERAND_ROUNDC,2);
        operand[i++] = xed_other(XED_OPERAND_SAE,1);
        *pos = i;
        return 1;
    }
    else if (strcmp("{RU-SAE}",s)==0) {
        check_too_many_operands(i+1);
        operand[i++] = xed_other(XED_OPERAND_ROUNDC,3);
        operand[i++] = xed_other(XED_OPERAND_SAE,1);
        *pos = i;
        return 1;
    }
    else if (strcmp("{RZ-SAE}",s)==0) {
        check_too_many_operands(i+1);
        operand[i++] = xed_other(XED_OPERAND_ROUNDC,4);
        operand[i++] = xed_other(XED_OPERAND_SAE,1);
        *pos = i;
        return 1;
    }
    else if (strcmp("{SAE}",s)==0) {
        check_too_many_operands(i);
        operand[i++] = xed_other(XED_OPERAND_SAE,1);
        *pos = i;
        return 1;
    }
#endif
    asp_error_printf("Unhandled decorator: %s\n",s);
    exit(1);
    return 0;
    (void) operand; (void) pos;
}


static xed_uint_t get_nbits_signed(xed_int64_t imm_val) {
    xed_uint_t nbits = 0;
    xed_uint8_t legal_widths = 1|2|4|8;  // bytes
    xed_uint_t nbytes = 0;
    nbytes = xed_shortest_width_signed(imm_val, legal_widths);
    nbits = 8 * nbytes;
    return nbits;
}
static xed_uint_t get_nbits_unsigned(xed_uint64_t imm_val) {
    xed_uint_t nbits = 0;
    xed_uint8_t legal_widths = 1|2|4|8;  // bytes
    xed_uint_t nbytes = 0;
    nbytes = xed_shortest_width_unsigned(imm_val, legal_widths);
    nbits = 8 * nbytes;
    return nbits;
}

static xed_uint_t get_nbits_signed_disp(xed_int64_t disp_val) {
    // displacements are 1 or 4 bytes in 32/64b addressing.
    // FIXME: In 16b addressing one can have 16b displacements.
    xed_uint_t nbits = 0;
    xed_uint8_t legal_widths = 1|4;  // bytes
    xed_uint_t nbytes = 0;
    if (disp_val == 0) // FIXME: how to force nonzero displacement?
        return 0;
    nbytes = xed_shortest_width_signed(disp_val, legal_widths);
    nbits = 8 * nbytes;
    return nbits;
}

static xed_reg_class_enum_t get_gpr_reg_class(xed_reg_enum_t reg) {
    xed_reg_class_enum_t rc = xed_reg_class(reg);
    if (rc == XED_REG_CLASS_GPR)    {
        rc = xed_gpr_reg_class(reg);
        return rc;
    }
    return XED_REG_CLASS_INVALID;
}

static void set_eosz(xed_reg_enum_t reg,
                     xed_uint_t* eosz)
{
    xed_reg_class_enum_t rc = get_gpr_reg_class(reg);
    if (rc == XED_REG_CLASS_GPR16) {
        if (*eosz < 16)
            *eosz = 16;
    }
    else if (rc == XED_REG_CLASS_GPR32) {
        if (*eosz < 32)
            *eosz = 32;
        }
    else if (rc == XED_REG_CLASS_GPR64) {
        asp_dbg_printf("#SET EOSZ 64\n");
        *eosz=64;
    }
}


static void set_mode(xed_reg_enum_t reg,
                     int* mode)
{
    // only set mode if it is set to something too narrow.  Note: instead
    // we could simply only infer mode if the mode is not set explicitly
    // (==0) which would facilitate some error checking.
    
    xed_reg_class_enum_t rc = get_gpr_reg_class(reg);
    if (rc == XED_REG_CLASS_GPR16) {
        if (*mode < 16)
            *mode = 16;
        if (reg >= XED_REG_R8W)
            *mode = 64;
    }
    else if (rc == XED_REG_CLASS_GPR32) {
        if (*mode < 32)
            *mode = 32;
        if (reg >= XED_REG_R8D)
            *mode = 64;
    }
    else if (rc == XED_REG_CLASS_GPR64) {
        *mode=64;
    }
}


static void set_mode_vec(xed_reg_enum_t reg,
                         int* mode)
{
    //if using simd (xmm/ymm/zmm) regs > 7, then set 64b mode
    xed_reg_class_enum_t rc = xed_reg_class(reg);
    xed_uint_t regid = 0;
    if (rc == XED_REG_CLASS_XMM) {
        regid = reg - XED_REG_XMM0;
    }
    else if (rc == XED_REG_CLASS_YMM) {
        regid = reg - XED_REG_YMM0;
    }
#if defined(XED_SUPPORTS_AVX512)
    else if (rc == XED_REG_CLASS_ZMM) {
        regid = reg - XED_REG_ZMM0;
    }
#endif
    if (regid > 7 && *mode != 64) {
        asp_printf("Forcing mode to 64b based on regs used\n");
        *mode = 64;
    }
}

static xed_bool_t string_number_is_signed(const char* s)
{
    if (*s == '+' || *s == '-') 
        return 1;
    return 0;
}

/* Return true for e.g. strings "0x0123", "-0123"
   Return false if no padding zeroes */
static xed_bool_t string_has_padding_zeroes(const char* s)
{
    if (*s == '+' || *s == '-') /* skip leading sign */
        s++;
    if (*s == '0' && *(s + 1) == 'X') /* skip hexadecimal prefix */
        s += 2;
    return (*s == '0');
}

/* A nibble is a 4 bits wide hexadecimal digit.
   Note that decimal digits are not nibbles but
   the difference is ignored for the purposes of detecting
   the literal's width */
static xed_uint_t count_nibbles(const char *s)
{
    if (*s == '+' || *s == '-') /* skip leading sign */
        s++;
    if (*s == '0' && *(s + 1) == 'X') /* skip hexadecimal prefix */
        s += 2;
    return xed_strlen(s);
 }

static char const*  const kmasks[] = { "{K0}","{K1}","{K2}","{K3}","{K4}","{K5}","{K6}","{K7}", 0 };

/* If user padded the number with leading zeroes, consider this to be
   an attempt to precisely control the width of the literal. Otherwise,
   choose a width that is just wide enough to fit the value */
static int get_constant_width(char *text, int64_t val) {
    if (string_has_padding_zeroes(text)) 
        return 4 * count_nibbles(text);
    if (string_number_is_signed(text))
        return get_nbits_signed(val);
    return get_nbits_unsigned((xed_uint64_t)val);
}

static void process_operand(xed_enc_line_parsed_t* v,
                            opnd_list_t* q,
                            xed_uint_t* noperand,
                            xed_encoder_operand_t* operands,
                            xed_uint_t* has_imm0,
                            xed_uint_t* eosz)
{
    slist_t* d = 0;
    int found_a_kmask = 0;
    
    xed_uint_t i = *noperand;

    switch (q->type) {
    case OPND_REG: {
        xed_reg_enum_t reg = q->reg;
        if (reg == XED_REG_INVALID) {
            asp_error_printf("Bad register: %s\n", q->s);
            exit(1);
        }

        check_too_many_operands(i);
        operands[i++] = xed_reg(reg);
        set_eosz(reg, eosz);
        set_mode_vec(reg, &(v->mode));
    }
        break;
    case OPND_DECORATOR: {
        if (process_rc_sae(q->s, operands, &i))  {
            check_too_many_operands(i);
        }
        else {
            asp_error_printf("Bad decorator: %s\n", q->s);
            exit(1);
        }
    }
        break;
    case OPND_IMM: {
        xed_uint_t nbits = get_constant_width(q->s, q->imm);
        uint64_t literal_val = (uint64_t)q->imm;

        if (has_relbr(v->iclass_e)) {
            asp_dbg_printf("The literal is treated as relbranch\n");
            check_too_many_operands(i);
            operands[i++] = xed_relbr(literal_val, nbits);
        }
        else { // literal immediate
            if (*has_imm0 == 0) {
                check_too_many_operands(i);
                operands[i++] = xed_imm0(literal_val, nbits); //FIXME: cast or make imm0 signed?
                *has_imm0 = 1;
            }
            else {
                if (nbits != 8) {
                    asp_error_printf(
                        "The second literal constant can only be 8 bit wide\n");
                    exit(1);
                }
                check_too_many_operands(i);
                operands[i++] = xed_imm1(XED_STATIC_CAST(xed_uint8_t, q->imm));
            }
        }
    }
        break;
    case OPND_MEM: {
        xed_reg_enum_t seg = XED_REG_INVALID;
        xed_reg_enum_t base = XED_REG_INVALID;
        xed_reg_enum_t indx = XED_REG_INVALID;
        xed_uint_t scale = q->mem.nscale;
        xed_uint_t displacement_bits = get_nbits_signed_disp(q->mem.ndisp);
        xed_enc_displacement_t disp = xed_disp(q->mem.ndisp, displacement_bits); 
        xed_uint_t width_bits = q->mem.mem_bits;

        if (q->mem.base) 
            base = str2xed_reg_enum_t(q->mem.base);
        if (q->mem.index) 
            indx = str2xed_reg_enum_t(q->mem.index);
        if (q->mem.seg) 
            seg = str2xed_reg_enum_t(q->mem.seg);
        
        set_mode(base, &(v->mode));
        set_mode(indx, &(v->mode));
        set_mode_vec(indx, &(v->mode)); // for AVX512 gathers, scatters
        check_too_many_operands(i);
        operands[i++] = xed_mem_gbisd(seg, base, indx, scale, disp, width_bits);
        process_mem_decorator(q->decorators, operands, &i);
    }
        break;
    case OPND_FARPTR: {
        if (*has_imm0) {
            asp_error_printf(
                "Long pointer cannot follow immediate operand\n");
            exit(1);
        }
        xed_uint16_t seg = (xed_uint16_t)q->farptr.seg_value;
        xed_uint32_t offset = (xed_uint32_t)q->farptr.offset_value;
        xed_uint_t seg_bits = get_constant_width(q->farptr.seg,
                                                 q->farptr.seg_value);
        xed_uint_t offset_bits = get_constant_width(q->farptr.offset,
                                                    q->farptr.offset_value);

        seg_bits = seg_bits < 16 ? 16 : seg_bits;
        if (seg_bits != 16) {
            asp_error_printf(
                "Segment value in far pointer must be 16 bits\n");
            exit(1);
        }
        
        if (offset_bits > 32) {
            asp_error_printf(
                "Far pointer offset must be either 16 or 32 bits");
            exit(1);
        }

        if (offset_bits <= 16) 
            offset_bits = 16;
        else 
            offset_bits = 32;
        *eosz = offset_bits;
        
        check_too_many_operands(i);
        operands[i++] = xed_ptr(offset, offset_bits);

        /* segment is encoded as immediate and must follow offset */
        check_too_many_operands(i);
        operands[i++] = xed_imm0(seg, seg_bits);
        *has_imm0 = 1;
    }
        break;
    default:
        asp_error_printf("Bad operand encountered: %s", q->s);
        exit(1);
    } // switch (q->type)

    //Add k-mask decorators as operands.
    //Not checking for multiple k-masks - Let XED do it; that would not encode.
    d = q->decorators;
    while(d && !found_a_kmask) {
        xed_uint_t j;
        for(j=0;kmasks[j];j++) {
            if (strcmp(kmasks[j],d->s)==0) {
                xed_reg_enum_t kreg = XED_REG_K0 + j;
                check_too_many_operands(i);
                operands[i++] = xed_reg(kreg);
                found_a_kmask = 1;
                break;
            }
        }
        d = d->next;
    }
    *noperand = i;
}



static xed_uint_t encode(xed_encoder_instruction_t* inst)
{
    xed_error_enum_t xed_error = XED_ERROR_NONE;
    xed_bool_t convert_ok = 0;
    xed_encoder_request_t enc_req;
    xed_uint8_t itext[XED_MAX_INSTRUCTION_BYTES];
    unsigned int ilen = XED_MAX_INSTRUCTION_BYTES;
    unsigned int olen = 0;


    xed_encoder_request_zero_set_mode(&enc_req, &(inst->mode));
    convert_ok = xed_convert_to_encoder_request(&enc_req, inst);
    if (!convert_ok) {
        asp_error_printf("Conversion to encode request failed\n");
        exit(1);
    }
    xed_error = xed_encode(&enc_req, itext, ilen, &olen);
    if (xed_error != XED_ERROR_NONE) {
        asp_error_printf("Failed to encode input: %s\n",
                xed_error_enum_t2str(xed_error));
        exit(1);
    }

    if (intel_asm_emits)
        xed_print_intel_asm_emit(itext,olen);
    else 
        xed_print_bytes_pseudo_op(itext,olen);
    return olen;
}

static void process_other_decorator(char const* s,
                                    xed_uint_t* noperand,
                                    xed_encoder_operand_t* operands)

{
    // handle zeroing.
    // allow but ignore k-masks and broadcasts decorators.
    
    // rounding/sae indicators are required to be indepdent operands (at
    // least for now)

#if defined(XED_SUPPORTS_AVX512)
    xed_uint_t i = *noperand;
    
    if (strcmp("{Z}",s) == 0) {
        check_too_many_operands(i);
        operands[i++] = xed_other(XED_OPERAND_ZEROING,1);
    }
    else {

        // allow kmasks, but nothing else
        int j=0;
        int found = 0;
        for (j=0;kmasks[j];j++) {
            if (strcmp(kmasks[j],s) == 0) {
                found = 1;
                break;
            }
        }

        if (!found) {
            for(j=0;bcast[j].s;j++) {
                if (strcmp(bcast[j].s,s)==0) {
                    found = 1;
                    break;
                }
            }
        }

        if (!found)  {
            asp_error_printf("Unhandled decorator: %s\n",s);
            exit(1);
        }
    }

    *noperand = i;
#else
    (void) s; (void) noperand; (void)operands;    
#endif

}

typedef struct {
    const char *from;
    const char *to;
} iclass_name_aliases_t;


static const iclass_name_aliases_t cmovcc_aliases[] = {
       {"CMOVNAE" , "CMOVB"},
       {"CMOVC"   , "CMOVB"},
       {"CMOVNA"  , "CMOVBE"},
       {"CMOVNGE" , "CMOVL"},
       {"CMOVNG"  , "CMOVLE"},
       {"CMOVAE"  , "CMOVNB"},
       {"CMOVNC"  , "CMOVNB"},
       {"CMOVA"   , "CMOVNBE"},
       {"CMOVGE"  , "CMOVNL"},
       {"CMOVG"   , "CMOVNLE"},
       {"CMOVPO"  , "CMOVNP"},
       {"CMOVNE"  , "CMOVNZ"},
       {"CMOVPE"  , "CMOVP"},
       {"CMOVE"   , "CMOVZ"},
};
static const iclass_name_aliases_t setcc_aliases[] = {
       {"SETNAE" , "SETB"},
       {"SETC"   , "SETB"},
       {"SETNA"  , "SETBE"},
       {"SETNGE" , "SETL"},
       {"SETNG"  , "SETLE"},
       {"SETAE"  , "SETNB"},
       {"SETNC"  , "SETNB"},
       {"SETA"   , "SETNBE"},
       {"SETGE"  , "SETNL"},
       {"SETG"   , "SETNLE"},
       {"SETPO"  , "SETNP"},
       {"SETNE"  , "SETNZ"},
       {"SETPE"  , "SETP"},
       {"SETE"   , "SETZ"},
};

static const iclass_name_aliases_t jcc_aliases[] = {
       {"JNAE" , "JB"},
       {"JC"   , "JB"},
       {"JNA"  , "JBE"},
       {"JNGE" , "JL"},
       {"JNG"  , "JLE"},
       {"JAE"  , "JNB"},
       {"JNC"  , "JNB"},
       {"JA"   , "JNBE"},
       {"JGE"  , "JNL"},
       {"JG"   , "JNLE"},
       {"JPO"  , "JNP"},
       {"JNE"  , "JNZ"},
       {"JPE"  , "JP"},
       {"JE"   , "JZ"},
};

static xed_bool_t find_alias(const char* orig,
                             char* result,
                             int maxlen,
                             iclass_name_aliases_t const* const aliases,
                             size_t n_aliases) 
{
    /* Internally, xed uses only one variant per each alias,
       others have to be converted to it */

    size_t i = 0;
    for (i = 0; i < n_aliases; i++) {
        const char *from = aliases[i].from;
        const char *to = aliases[i].to;
        if (!strncmp(orig, from, maxlen)) {
            xed_strncpy(result, to, maxlen);
            return 1;
        }
    }
    return 0;
}

/* Change result to alias mnemonic that is accepted by xed, return true
   Otherwise keep it unchanged and return false */
/* Internally, xed uses only one variant per each alias,
   others have to be converted to it */
static xed_bool_t find_jcc_alias(const char* orig, char* result, int maxlen) {
    const size_t n_aliases = sizeof(jcc_aliases) / sizeof(jcc_aliases[0]);
    return find_alias(orig, result, maxlen, jcc_aliases, n_aliases);
}
static xed_bool_t find_cmovcc_alias(const char* orig, char* result, int maxlen) {
    const size_t n_aliases = sizeof(cmovcc_aliases) / sizeof(cmovcc_aliases[0]);
    return find_alias(orig, result, maxlen, cmovcc_aliases, n_aliases);
}
static xed_bool_t find_setcc_alias(const char* orig, char* result, int maxlen) {
    const size_t n_aliases = sizeof(setcc_aliases) / sizeof(setcc_aliases[0]);
    return find_alias(orig, result, maxlen, setcc_aliases, n_aliases);
}


/* Try all known suffixes and prefixes with the original mnemonic if 
   certain operands or prefixes were seen.
   Put (un)modified iclass string into result */
static void revise_mnemonic(xed_enc_line_parsed_t *v, char* result, int maxlen) {
    const char *orig = v->iclass_str;
    assert(xed_strlen(orig) > 0);

    /* Try _NEAR and _FAR variants for "call" and "ret" */
    if (!v->seen_far_ptr && probe_iclass_string(orig, "NEAR", result, maxlen)) {
        return;
    }
    else if (v->seen_far_ptr && probe_iclass_string(orig, "FAR", result, maxlen)) {
        return;
    }
    /* all aliases for conditional jumps start with 'J' */
    if (orig[0] == 'J' && find_jcc_alias(orig,result, maxlen)) {
        return;
    }
    if (strncmp(orig,"CMOV",4)==0 && find_cmovcc_alias(orig,result, maxlen)) {
        return;
    }
    if (strncmp(orig,"SET",3)==0 && find_setcc_alias(orig,result, maxlen)) {
        return;
    }

    if (v->seen_cr && probe_iclass_string(orig, "CR", result, maxlen)) // mov_cr
        return;
    if (v->seen_dr && probe_iclass_string(orig, "DR", result, maxlen)) // mov_dr
        return;

    /* iclasses contain all three forms: REP_, REPE_ and REPNE_ */
    if (v->seen_repne && probe_iclass_string("REPNE", orig, result, maxlen)) {
        return;
    } 
    else if (v->seen_repe && probe_iclass_string("REPE", orig, result, maxlen)) {
        return;
    }
    else if (v->seen_repe && probe_iclass_string("REP", orig, result, maxlen)) {
        return;
    }

    if (v->seen_lock && probe_iclass_string(orig, "LOCK", result, maxlen)) {
        return;
    }

    /* string vs SSE instructions with similar mnemonics */
    if ((v->deduced_vector_length > 0) 
        && probe_iclass_string(orig, "XMM", result, maxlen))
        return;

    /* TODO handle remaining cases:
        FXRSTOR vs FXRSTOR64 and other *SAVE/ *RSTR(64)
        PEXTRW PEXTRW_SSE4
        VPEXTRW VPEXTRW_c5
        Long NOPs: XED_ICLASS_NOP2 - NOP9 */

    /* Reaching the end of the function means no modifications */
    xed_strncpy(result, orig, maxlen);
}

static xed_uint_t encode_with_xed(xed_enc_line_parsed_t* v)
{
    xed_encoder_instruction_t inst;
    xed_state_t dstate;
    xed_uint_t eosz=0; 
    xed_uint_t noperand=0;
    xed_encoder_operand_t operand_array[XED_ENCODER_OPERANDS_MAX];
    opnd_list_t* q=0;
    xed_uint_t has_imm0 = 0;

    if (v->iclass_str == 0) {
        asp_error_printf("Did not find an instruction\n");
        exit(1);
    }

    process_prefixes(v, &inst);

    /* Instruction's mnemonic is not always unambiguous;
       iclass is sometimes affected by arguments and prefixes.
       Use operand knowledge to adjust the mnemonic if needed */
    char revised_mnemonic[100] = { 0 };
    revise_mnemonic(v, revised_mnemonic, sizeof(revised_mnemonic));
    v->iclass_e = str2xed_iclass_enum_t(revised_mnemonic);

    // handle operands
    q = v->opnds;
    while(q) {
        process_operand(v, q, &noperand, operand_array, &has_imm0, &eosz);
        check_too_many_operands(noperand);
        q = q->next;
    }

    if (v->iclass_e == XED_ICLASS_INVALID) {
        asp_error_printf("Bad instruction name: '%s'\n", revised_mnemonic);
        exit(1);
    }

    asp_dbg_printf("ICLASS [%s]\n", xed_iclass_enum_t2str(v->iclass_e));

    // handle other operand decorators (zeroing, kmasks, broadcast masks)
    q = v->opnds;
    while(q) {
        slist_t* r = q->decorators;
        while(r) {
            process_other_decorator(r->s, &noperand, operand_array);
            check_too_many_operands(noperand);
            r = r->next;
        }
        q = q->next;
    }
    if (eosz == 0) {
        eosz = 32;
        asp_dbg_printf("#Guessing 32b EOSZ\n");
    }

    if (eosz == 64) {
        if (v->mode != 64) {
            asp_dbg_printf("#Changing to 64b mode\n");
        }
        v->mode = 64;
    }
    asp_dbg_printf("#MODE=%d, EOSZ=%d\n", v->mode, eosz);
    set_state(&dstate, v);
    xed_inst(&inst, dstate, v->iclass_e, eosz, noperand, operand_array);
    return encode(&inst);
}

/* Return true if the instruction accepts relative branch as an operand */
static xed_bool_t test_has_relbr(const xed_inst_t* p) {
    const unsigned noperands = xed_inst_noperands(p);
    for (unsigned i = 0; i < noperands; i++) {
        const xed_operand_t* o = xed_inst_operand(p, i);
        if (xed_operand_name(o) == XED_OPERAND_RELBR) {
            return 1;
        }
    }
    return 0;
}

/* relbr_table is an array initialized at startup that tells us if we have
 * a relative branch displacement */
static xed_bool_t relbr_table[XED_ICLASS_LAST];

static xed_bool_t has_relbr(xed_iclass_enum_t iclass) {
    assert(iclass < XED_ICLASS_LAST);
    return relbr_table[iclass];
}
static void setup(void) {
    memset(relbr_table, 0, sizeof(xed_bool_t)*XED_ICLASS_LAST);
    
    for (unsigned i = 0; i < XED_MAX_INST_TABLE_NODES; i++) {
        const xed_inst_t *inst = xed_inst_table_base() + i;
        xed_iclass_enum_t ic = xed_inst_iclass(inst);
        assert(ic < XED_ICLASS_LAST);
        relbr_table[ic] =  test_has_relbr(inst);
    }
}

int main(int argc, char** argv)
{
    int verbose  = 1;
    xed_str_list_t* string_list = 0;
    xed_str_list_t* p = 0;
    xed_uint_t mode=0;
    xed_uint_t length = 0;
    
    setup();
    xed_tables_init();

    p = string_list = process_args(argc, argv, &mode, &verbose);
    asp_set_verbosity(verbose);

    while(p) {
        xed_uint_t olen = 0;
        xed_enc_line_parsed_t* v = 0;

        v = asp_get_xed_enc_node();
        v->mode = mode;
        
        // we duplicate because the asp_delete_xed_enc_line_parsed_line_t
        // will delete the string if still present when we call it.
        v->input = duplicate(p->s);

        if (verbose > 0)
            printf("#Assembling [%s]\n",v->input);

        asp_parse_line(v);

        if (verbose > 1)
            asp_print_parsed_line(v);

        olen = encode_with_xed(v);
        length += olen;

        asp_delete_xed_enc_line_parsed_t(v);
        v = 0;
        p = p->next;
    }
    
    if (verbose > 0) 
        printf("#nbytes = %d\n",length);

    delete_string_list(string_list);
    string_list = 0;

    return 0;
}
