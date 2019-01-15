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

// more natural assembly language parser

#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#include "xed-asmparse.h"

#include "xed/xed-interface.h"
#include "xed-examples-util.h"

#define ASP_MAX_OPERANDS (XED_ENCODER_OPERANDS_MAX+3)

static void process_args(int argc, char** argv, xed_enc_line_parsed_t* v,
                         int* verbose) {
    const char* usage = "Usage: %s [-16|-32|-64] [-v|-q] <assembly line>\n";
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
    v->mode = 32;
    while(keep_going) {
        keep_going = 0;
        if (strcmp("-32",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            v->mode = 32;
            first_arg++;
        }
        else if (strcmp("-16",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            v->mode = 16;
            first_arg++;
        }
        else if (strcmp("-64",argv[first_arg])==0) {
            if (mode_found) {
                asp_error_printf("Duplicate mode knob: %s\n", argv[first_arg]);
                exit(1);
            }
            mode_found = 1;
            keep_going = 1;
            v->mode = 64;
            first_arg++;
        }
        else if (strcmp("-v",argv[first_arg])==0) {
            keep_going = 1;
            *verbose = 2;
            first_arg++;
        }
        else if (strcmp("-q", argv[first_arg])== 0) {
            keep_going = 1;
            *verbose = 0;
            first_arg++;
        }
    }
    for(i=first_arg;i<argc;i++) {
        // add one for trailing space or null at end
        len = len + xed_strlen(argv[i]) + 1;
    }
    p = s = (char*) malloc(len);
    for(i=first_arg;i<argc;i++) {
        if (i>first_arg) // spaces between secondary args
           *p++ = ' ';
        q = argv[i];
        while(*q)  // copy argument
            *p++ = *q++;
    }
    *p = 0;  // null terminate
    v->input = s;
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
static void process_prefixes(xed_enc_line_parsed_t* v,
                             xed_encoder_instruction_t* inst)
{
    slist_t* q = v->prefixes;
    while(q) {
        if (strcmp(q->s, "LOCK") == 0) {
            // FIXME: need to change iclass
        }
        else if (strcmp(q->s, "REP") == 0 || 
                 strcmp(q->s, "REPE") == 0 || 
                 strcmp(q->s, "XRELEASE") == 0) {
            // FIXME: *may* need to change iclass for rep-string ops
            xed_rep(inst); 
        }
        else if (strcmp(q->s, "REPNE") == 0 || 
                 strcmp(q->s, "XACQUIRE") == 0) {
            // FIXME: *may* need to change iclass for rep-string ops
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
    if (op_pos >= ASP_MAX_OPERANDS) {
        asp_error_printf("Too many operands\n");
        exit(1);
    }
}

static int process_rc_sae(char const* s,xed_encoder_operand_t* operand, xed_uint_t* pos)
{
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

    asp_error_printf("Unhandled decorator: %s\n",s);
    exit(1);
    return 0;
}


static xed_uint_t get_nbits_signed(xed_int64_t imm_disp_val) {
    xed_uint_t nbits = 0;
    xed_uint8_t legal_widths = 1|2|4|8;  // bytes
    xed_uint_t nbytes = 0;
    nbytes = xed_shortest_width_signed(imm_disp_val, legal_widths); 
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
        asp_printf("SET EOSZ 64\n");
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
    else if (rc == XED_REG_CLASS_ZMM) {
        regid = reg - XED_REG_ZMM0;
    }
    if (regid > 7 && *mode != 64) {
        asp_printf("Forcing mode to 64b based on regs used\n");
        *mode = 64;
    }
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
    if (q->type == OPND_REG) {
        xed_reg_enum_t reg = str2xed_reg_enum_t(q->s);
        if (reg == XED_REG_INVALID) {
            asp_error_printf("Bad register: %s\n", q->s);
            exit(1);
        }
        check_too_many_operands(i);
        operands[i++] = xed_reg(reg);
        set_eosz(reg, eosz);
        set_mode_vec(reg, &(v->mode));
    }
    else if (q->type == OPND_DECORATOR) {
        if (process_rc_sae(q->s, operands, &i))  {
            check_too_many_operands(i);
        }
        else {
            asp_error_printf("Bad decorator: %s\n", q->s);
            exit(1);
        }
    }
    else if (q->type == OPND_IMM) {
        /* If user padded the number with leading zeroes, consider this to be
           an attempt to precisely control the width of the literal. Otherwise,
           choose a width that is just wide enough to fit the value */
        xed_uint_t nbits = 0;
        if (string_has_padding_zeroes(q->s)) {
            nbits = 4 * count_nibbles(q->s);
        }
        else {
            nbits = get_nbits_signed(q->imm);
        }
        if (*has_imm0==0) {
            check_too_many_operands(i);
            operands[i++] = xed_imm0((uint64_t)q->imm, nbits); //FIXME: cast or make imm0 signed?
            *has_imm0=1;
        }
        else {
            if (nbits != 8) {
                asp_error_printf(
                    "The second literal constant can only be 8 bit wide\n");
                exit(1);
            }
            check_too_many_operands(i);
            operands[i++] = xed_imm1(XED_STATIC_CAST(xed_uint8_t,q->imm));
        }
    }
    else if (q->type == OPND_MEM) {
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
    else {
        asp_error_printf("Bad operand encountered: %s", q->s);
        exit(1);
    }

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

static void encode(xed_encoder_instruction_t* inst)
{
    xed_error_enum_t xed_error = XED_ERROR_NONE;
    xed_bool_t convert_ok = 0;
    xed_encoder_request_t enc_req;
    xed_uint8_t itext[XED_MAX_INSTRUCTION_BYTES];
    unsigned int ilen = XED_MAX_INSTRUCTION_BYTES;
    unsigned int olen = 0;
    xed_uint_t j=0;

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
    asp_printf("Result: ");
    for(j=0;j<olen-1;j++) 
        printf("%02x ", itext[j]);
    printf("%02x\n", itext[olen-1]);
}

static void process_other_decorator(char const* s,
                                    xed_uint_t* noperand,
                                    xed_encoder_operand_t* operands)
{
    // handle zeroing.
    // allow but ignore k-masks and broadcasts decrorators.
    
    // rounding/sae indicators are required to be indepdent operands (at
    // least for now)
    
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
}

static void encode_with_xed(xed_enc_line_parsed_t* v)
{
    xed_encoder_instruction_t inst;
    xed_state_t dstate;
    xed_iclass_enum_t iclass=XED_ICLASS_INVALID;
    xed_uint_t eosz=0; 
    xed_uint_t noperand=0;
    xed_encoder_operand_t operand_array[ASP_MAX_OPERANDS];
    opnd_list_t* q=0;
    xed_uint_t has_imm0 = 0;
    
    iclass = str2xed_iclass_enum_t(v->iclass);
    if (iclass == XED_ICLASS_INVALID) {
        asp_error_printf("Invalid iclass: %s\n", v->iclass);
        exit(1);
    }

    process_prefixes(v,&inst);
        
    // handle operands
    q = v->opnds;
    while(q) {
        process_operand(v, q, &noperand, operand_array, &has_imm0, &eosz);
        check_too_many_operands(noperand);
        q = q->next;
    }

    // handle other decorators (zeroing, kmasks, broadcast masks)
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
        asp_printf("Guessing 32b EOSZ\n");
    }

    if (eosz == 64) {
        if (v->mode != 64) {
            asp_printf("Changing to 64b mode\n");
        }
        v->mode = 64;
    }
    asp_printf("MODE=%d, EOSZ=%d\n", v->mode, eosz);
    set_state(&dstate, v);
    xed_inst(&inst, dstate, iclass, eosz, noperand, operand_array);
    encode(&inst);
}

int main(int argc, char** argv)
{
    xed_tables_init();
    int verbose  = 1;

    xed_enc_line_parsed_t* v = asp_get_xed_enc_node();

    process_args(argc, argv, v, &verbose);
    asp_set_verbosity(verbose);
    asp_parse_line(v);

    if (verbose > 1)
        asp_print_parsed_line(v);

    encode_with_xed(v);

    asp_delete_xed_enc_line_parsed_t(v);
    return 0;
}
