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

// This is an example of how to use the encoder from scratch in the context
// of parsing a string from the command line.  

#include <assert.h>
#include <string.h>
#include <stdlib.h>  // strtol, ...
#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include "xed-enc-lang.h"


static void upcase(char* s) {
    (void)xed_upcase_buf(s);
}

xed_str_list_t* 
tokenize(char const* const s,
         char const* const delimiter)
{
    xed_str_list_t* slist = xed_tokenize(s, delimiter);
    return slist;
}

void slash_split(char const* const src,
                 char** first, // output
                 char** second) //output
{
    xed_str_list_t* sv = tokenize(src, "/");
    xed_str_list_t* p = sv;
    xed_uint_t i=0;
    for(; p ; i++, p=p->next)
    {
        if (i==0) {
            *first = p->s;
            *second = 0;
        }
        else if (i==1)
            *second = p->s;
    }
}



typedef struct {
    xed_bool_t valid;
    unsigned int width_bits;
    xed_uint64_t immed_val;
} immed_parser_t;

static void immed_parser_init(immed_parser_t* self,
                       char const* const s, 
                       char const* const tok0) 
{
    xed_str_list_t* sv = tokenize(s,":");
    xed_uint_t sz = xed_str_list_size(sv);
    self->valid = 0;
    if (sz==2) {
        xed_str_list_t* p = sv;
        xed_uint_t i = 0;
        for(; p ; i++, p=p->next)
        {
            if (i == 0 && strcmp(p->s,tok0) != 0)
                return;
            else if (i == 1) {
                self->immed_val = convert_ascii_hex_to_int(p->s);
                // nibbles to bits
                self->width_bits = XED_CAST(unsigned int,strlen(p->s)*4);
                self->valid = 1;
            }
        }
    }
}


typedef struct {
    xed_bool_t valid;
    xed_reg_enum_t segment_reg;
    xed_uint_t segno;
} seg_parser_t;

static void seg_parser_init(seg_parser_t* self,
                            char const* const s)
{
    xed_str_list_t* sv = tokenize(s,":");
    xed_uint_t ntokens = xed_str_list_size(sv);

    self->valid=0;
    self->segment_reg= XED_REG_INVALID;
    self->segno=0;

    if (ntokens == 2)
    {
        xed_str_list_t* p = sv;
        xed_uint_t i = 0;
        xed_uint_t segid = 99;
        for(; p ; i++, p=p->next)
        {
            if (i == 0)
            {
                if (strcmp(p->s,"SEG")==0 || strcmp(p->s,"SEG0")==0)
                    segid = 0;
                else if (strcmp(p->s,"SEG1")==0)
                    segid = 1;
            }
            else if (i == 1 && segid < 2)
            {
                self->segno = segid;
                self->segment_reg = str2xed_reg_enum_t(p->s);

                if (self->segment_reg != XED_REG_INVALID &&
                    xed_reg_class(self->segment_reg) == XED_REG_CLASS_SR)
                {
                    self->valid=1;
                }
            }
        }
    }
        
}


static void
list2array(char** array, xed_str_list_t* sl, xed_uint_t n)
{
    xed_uint_t i=0;
    xed_str_list_t* p = sl;
    for( ; p && i < n ; i++, p=p->next) 
        array[i] = p->s;
}

static xed_uint_t match(char const* const s, char const* const b)
{
    if (strcmp(s,b)==0)
        return 1;
    return 0;
}
static xed_uint_t skip(char const* const s)
{
    if (match(s,"-") || match(s,"NA"))
        return 1;
    return 0;
}
            
typedef struct
{
    xed_bool_t valid;
    xed_bool_t mem;
    xed_bool_t agen;
    xed_bool_t disp_valid;
    char const* segment;
    char const* base;
    char const* indx;
    char const* scale;
    char const* disp; //displacement
    xed_reg_enum_t segment_reg;
    xed_reg_enum_t base_reg;
    xed_reg_enum_t index_reg;
    xed_uint8_t scale_val;

    xed_int64_t disp_val;
    unsigned int disp_width_bits;

    xed_uint_t mem_len;
} mem_bis_parser_t;  
    // parse: MEMlength:[segment:]base,index,scale[,displacement]
    // parse: AGEN:base,index,scale[,displacement]
    // The displacement is optional

    // split on colons first
    // MEM4:FS:EAX,EBX,4,223344   mem4 fs eax,ebx,4,22334455  -> 3 tokens
    // MEM4:FS:EAX,EBX,4          mem4 fs eax,ebx,4   -> 3 tokens
    // MEM4:EAX,EBX,4,223344      mem4 eax,ebx,4,223344..  -> 2 tokens
    // MEM4:FS:EAX,EBX,4          mem4 fs  eas,ebx,4     -> 3 tokens
static void mem_bis_parser_init(mem_bis_parser_t* self, char* s)
{
    xed_str_list_t* sv=0;
    xed_uint_t ntokens=0;
    xed_uint_t n_addr_tokens=0;
    char* addr_token=0;
    char* main_token=0;
    xed_uint_t i=0;
    xed_str_list_t* p = 0;
    xed_str_list_t* sa = 0;
    char* astr[4];


    self->valid = 0;
    self->mem = 0;
    self->agen = 0;
    self->disp_valid = 0;
    self->segment = "INVALID";
    self->base = "INVALID";
    self->indx = "INVALID";
    self->scale = "1";
    self->segment_reg = XED_REG_INVALID;
    self->base_reg = XED_REG_INVALID;
    self->index_reg = XED_REG_INVALID;
    self->disp_val = 0;
    self->disp_width_bits = 0;
    self->mem_len = 0;

    upcase(s);
    // split on colon first
    sv = tokenize(s,":");
    ntokens = xed_str_list_size(sv);
        
    i=0;
    p = sv;
    if (ntokens !=2 && ntokens != 3) // 3 has segbase
        return;
    for( ; p ; i++, p=p->next) {
        if (i==0)
            main_token = p->s;
        else if (i==1 && ntokens == 3)
            self->segment = p->s;
        else if (i==1 && ntokens == 2)
            addr_token = p->s;
        else if (i==2)
            addr_token = p->s;
    }
    assert(main_token != 0);
    if (strcmp(main_token,"AGEN")==0)
        self->agen=1;
    else if (strncmp(main_token,"MEM",3)==0) {
        self->mem = 1;
    }
    else 
        return;
    if (self->mem && strlen(main_token) > 3) {
        char* mlen = main_token+3;
        self->mem_len = XED_STATIC_CAST(xed_uint_t,strtol(mlen,0,0));
    }

    if (self->agen && strcmp(self->segment,"INVALID")!=0)
        xedex_derror("AGENs cannot have segment overrides");

    sa = tokenize(addr_token,",");
    n_addr_tokens = xed_str_list_size(sa);

    if (n_addr_tokens == 0 || n_addr_tokens > 4)
        xedex_derror("Bad addressing mode syntax for memop");

    list2array(astr, sa, n_addr_tokens);

    if (!skip(astr[0]))
        self->base = astr[0];

    if (n_addr_tokens >= 2)
        if (!skip(astr[1]))
            self->indx = astr[1];

    if (n_addr_tokens > 2) 
        self->scale = astr[2];
    if (skip(self->scale))
        self->scale = "1";
    if (match(self->scale,"1") || match(self->scale,"2") ||
        match(self->scale,"4") || match(self->scale,"8") ) {
        self->valid=1;
        self->scale_val = XED_CAST(xed_uint8_t,strtol(self->scale, 0, 10));
        self->segment_reg = str2xed_reg_enum_t(self->segment);
        self->base_reg = str2xed_reg_enum_t(self->base);
        self->index_reg = str2xed_reg_enum_t(self->indx);

        // look for a displacement
        if (n_addr_tokens == 4 && strcmp(astr[3], "-") != 0) {
            xed_uint64_t unsigned64_disp=0;
            unsigned int nibbles = 0;
            self->disp = astr[3];
            self->disp_valid = 1;
            nibbles = xed_strlen(self->disp);
            if (nibbles & 1) 
                xedex_derror("Displacement must have an even number of nibbles");
            unsigned64_disp = convert_ascii_hex_to_int(self->disp);
            self->disp_width_bits = nibbles*4; // nibbles to bits
            switch (self->disp_width_bits){
              case 8:  self->disp_val = xed_sign_extend8_64((xed_int8_t)unsigned64_disp);
                break;
              case 16: self->disp_val = xed_sign_extend16_64((xed_int16_t)unsigned64_disp);
                break;
              case 32: self->disp_val = xed_sign_extend32_64((xed_int32_t)unsigned64_disp);
                break;
              case 64: self->disp_val = (xed_int64_t)unsigned64_disp;
                break;
            }               
        }
    }
}

static void find_vl(xed_reg_enum_t reg, xed_int_t* vl)
{
    // This will "grow" bad user settings. So if you try to specify /128 on
    // the instruction and it sees a YMM or ZMM register operand, then
    // it'll grow the VL to the right observed size. The right observed
    // size might still be wrong, that is too small (as it can be for
    // "shrinking" converts (PD2PS, PD2DQ, etc.).
    xed_int_t nvl = *vl;
    xed_reg_class_enum_t rc = xed_reg_class(reg);
    if (rc == XED_REG_CLASS_XMM && nvl == -1)  // not set and see xmm
        *vl = 0;
    else if (rc == XED_REG_CLASS_YMM && nvl < 1) // not set, set to xmm and then see ymm
        *vl = 1;
#if defined(XED_SUPPORTS_AVX512)
    else if (rc == XED_REG_CLASS_ZMM && nvl < 2) // not set, set to xmm or ymm and then see zmm
        *vl = 2;
#endif
}


xed_encoder_request_t
parse_encode_request(ascii_encode_request_t areq)
{
    unsigned int i;
    xed_encoder_request_t req;
    char* cfirst=0;
    char* csecond=0;
    xed_str_list_t* tokens = 0;
    unsigned int token_index = 0;
    xed_str_list_t* p = 0;
    xed_uint_t memop = 0;
    xed_uint_t regnum = 0;
    xed_uint_t operand_index = 0;
    xed_iclass_enum_t iclass = XED_ICLASS_INVALID;
    xed_int_t vl = -1;
    xed_int_t uvl = -1;
    
    
    
    // this calls xed_encoder_request_zero()
    xed_encoder_request_zero_set_mode(&req,&(areq.dstate));

    /* This is the important function here. This encodes an instruction
       from scratch.
       
    You must set:
    the machine mode (machine width, addressing widths)
    the iclass
    for some instructions you need to specify prefixes (like REP or LOCK).
    the operands:
    
           operand kind (XED_OPERAND_{AGEN,MEM0,MEM1,IMM0,IMM1,
           RELBR,PTR,REG0...REG15}
           
           operand order
           
              xed_encoder_request_set_operand_order(&req,operand_index,
                                                       XED_OPERAND_*);
              where the operand_index is a sequential index starting at zero.

           operand details 
                     FOR MEMOPS: base,segment,index,scale,
                                         displacement for memops, 
                  FOR REGISTERS: register name
                 FOR IMMEDIATES: immediate values
     */

    tokens = tokenize(areq.command," ");
    p = tokens;

    for ( ; p ; token_index++, p=p->next ) {
        slash_split(p->s, &cfirst, &csecond);
        assert(cfirst);
        upcase(cfirst);
        if (CLIENT_VERBOSE3)
            printf( "[%s][%s][%s]\n", p->s,
                    (cfirst?cfirst:"NULL"),
                    (csecond?csecond:"NULL"));

        // consumed token, advance & exit
        p = p->next;
        break;
    }

    // we can attempt to override the mode
    if (csecond)
    {
        if (strcmp(csecond,"8")==0) 
            xed_encoder_request_set_effective_operand_width(&req, 8);
        else if (strcmp(csecond,"16")==0) 
            xed_encoder_request_set_effective_operand_width(&req, 16);
        else if (strcmp(csecond, "32")==0) 
            xed_encoder_request_set_effective_operand_width(&req, 32);
        else if (strcmp(csecond,"64")==0)
            xed_encoder_request_set_effective_operand_width(&req, 64);
        
        else if (strcmp(csecond,"128")==0)
            uvl = 0;
        else if (strcmp(csecond,"256")==0)
            uvl = 1;
        else if (strcmp(csecond,"512")==0)
            uvl = 2;
    }

    assert(cfirst != 0);
    iclass =  str2xed_iclass_enum_t(cfirst);
    if (iclass == XED_ICLASS_INVALID) {
        fprintf(stderr,"[XED CLIENT ERROR] Bad instruction name: %s\n",
                cfirst);
        exit(1);
    }
    xed_encoder_request_set_iclass(&req, iclass );


    // put the operands in the request. Loop through tokens 
    // (skip the opcode iclass, handled above)
    for( i=token_index; p ; i++, operand_index++, p=p->next ) {
        mem_bis_parser_t mem_bis;
        seg_parser_t seg_parser;
        immed_parser_t imm;
        immed_parser_t simm;
        immed_parser_t imm2;
        immed_parser_t disp;
        immed_parser_t ptr_disp;
        xed_reg_enum_t reg = XED_REG_INVALID;
        xed_operand_enum_t r;
                    
        char* cres_reg=0;
        char* csecond_x=0; //FIXME: not used
        slash_split(p->s, &cres_reg, &csecond_x);
        upcase(cres_reg);
        // prune the AGEN or MEM(base,index,scale[,displacement]) text from
        // cres_reg
        
        // FIXME: add MEM(immed) for the OC1_A and OC1_O types????
        mem_bis_parser_init(&mem_bis,cres_reg);
        if (mem_bis.valid) {
            xed_reg_class_enum_t rc = XED_REG_CLASS_INVALID;
            xed_reg_class_enum_t rci = XED_REG_CLASS_INVALID;
            

            if (mem_bis.mem) {
                if (memop == 0) {
                    // Tell XED that we have a memory operand
                    xed_encoder_request_set_mem0(&req);
                    // Tell XED that the mem0 operand is the next operand:
                    xed_encoder_request_set_operand_order(
                        &req,operand_index, XED_OPERAND_MEM0);
                }
                else {
                    xed_encoder_request_set_mem1(&req);
                    // Tell XED that the mem1 operand is the next operand:
                    xed_encoder_request_set_operand_order(
                        &req,operand_index, XED_OPERAND_MEM1);
                }
                memop++;
            }
            else if (mem_bis.agen) {
                // Tell XED we have an AGEN
                xed_encoder_request_set_agen(&req);
                // The AGEN is the next operand
                xed_encoder_request_set_operand_order(
                    &req,operand_index, XED_OPERAND_AGEN);
            }
            else 
                assert(mem_bis.agen || mem_bis.mem);

            
            rc = xed_gpr_reg_class(mem_bis.base_reg);
            rci = xed_gpr_reg_class(mem_bis.index_reg);
            if (mem_bis.base_reg == XED_REG_EIP)
                xed_encoder_request_set_effective_address_size(&req, 32);
            else if (rc == XED_REG_CLASS_GPR32 || rci == XED_REG_CLASS_GPR32)
                xed_encoder_request_set_effective_address_size(&req, 32);
            else if (rc == XED_REG_CLASS_GPR16 || rci == XED_REG_CLASS_GPR16) 
                xed_encoder_request_set_effective_address_size(&req, 16);

            // fill in the memory fields
            xed_encoder_request_set_base0(&req, mem_bis.base_reg);
            xed_encoder_request_set_index(&req, mem_bis.index_reg);
            xed_encoder_request_set_scale(&req, mem_bis.scale_val);
            xed_encoder_request_set_seg0(&req, mem_bis.segment_reg);
            find_vl(mem_bis.index_reg, &vl); // for scatter/gather
            if (mem_bis.mem_len) 
                xed_encoder_request_set_memory_operand_length(
                    &req,
                    mem_bis.mem_len ); // BYTES
            if (mem_bis.disp_valid)
                xed_encoder_request_set_memory_displacement(
                    &req,
                    mem_bis.disp_val,
                    mem_bis.disp_width_bits/8);
            continue;
        }


        seg_parser_init(&seg_parser,cres_reg);
        if (seg_parser.valid) {
            if (CLIENT_VERBOSE3) 
                printf("Setting segment to %s\n",
                       xed_reg_enum_t2str(seg_parser.segment_reg));
            if (seg_parser.segno == 0)
                xed_encoder_request_set_seg0(&req, seg_parser.segment_reg);
            else
                /*  need SEG1 for MOVS[BWDQ]*/
                xed_encoder_request_set_seg1(&req, seg_parser.segment_reg);

            /* SEG/SEG0/SEG1 is NOT a normal operand. It is a setting, like
             * the lock prefix. Normally the segment will be specified with
             * normal memory operations. With memops without MODRM, or
             * impliclit memops, we need a way of specifying the segment
             * when it is not the default. This is the way. it does not
             * change encoding forms. (When segments are "moved", they are
             * REG operands, not SEG0/1, and are specified by name like EAX
             * is.) */
            continue;
        }


        immed_parser_init(&imm,cres_reg, "IMM");
        
        if (imm.valid) {
            if (CLIENT_VERBOSE3) 
                printf("Setting immediate value to " XED_FMT_LX "\n",
                       imm.immed_val);
            xed_encoder_request_set_uimm0_bits(&req, 
                                               imm.immed_val,
                                               imm.width_bits);
            xed_encoder_request_set_operand_order(&req,
                                                  operand_index,
                                                  XED_OPERAND_IMM0);
            continue;
        }
        immed_parser_init(&simm,cres_reg, "SIMM");
        if (simm.valid) {
            if (CLIENT_VERBOSE3) 
                printf("Setting immediate value to " XED_FMT_LX "\n",
                       simm.immed_val);
            xed_encoder_request_set_simm(
                &req, 
                XED_STATIC_CAST(xed_int32_t,simm.immed_val),
                simm.width_bits/8); //FIXME
            xed_encoder_request_set_operand_order(&req,
                                                  operand_index,
                                                  XED_OPERAND_IMM0);
            continue;
        }

        immed_parser_init(&imm2,cres_reg, "IMM2");
        if (imm2.valid) {
            if (imm2.width_bits != 8)
                xedex_derror("2nd immediate must be just 1 byte long");
            xed_encoder_request_set_uimm1(&req, (xed_uint8_t)imm2.immed_val);
            xed_encoder_request_set_operand_order(&req,
                                                  operand_index,
                                                  XED_OPERAND_IMM1);
            continue;
        }


        immed_parser_init(&disp,cres_reg, "BRDISP");
        if (disp.valid) {
            if (CLIENT_VERBOSE3) 
                printf("Setting  displacement value to " XED_FMT_LX "\n",
                       disp.immed_val);
            xed_encoder_request_set_branch_displacement(
                &req,
                XED_STATIC_CAST(xed_int32_t,disp.immed_val),
                disp.width_bits/8); //FIXME
            xed_encoder_request_set_operand_order(&req,
                                                  operand_index,
                                                  XED_OPERAND_RELBR);
            xed_encoder_request_set_relbr(&req);
            continue;
        }


        immed_parser_init(&ptr_disp,cres_reg, "PTR");
        if (ptr_disp.valid) {
            if (CLIENT_VERBOSE3) 
                printf("Setting pointer displacement value to " XED_FMT_LX "\n",
                       ptr_disp.immed_val);
            xed_encoder_request_set_branch_displacement(
                &req,
                XED_STATIC_CAST(xed_int32_t,ptr_disp.immed_val),
                ptr_disp.width_bits/8); //FIXME
            xed_encoder_request_set_operand_order(&req,
                                                  operand_index,
                                                  XED_OPERAND_PTR);
            xed_encoder_request_set_ptr(&req);
            continue;
        }

        reg = str2xed_reg_enum_t(cres_reg);
        if (reg == XED_REG_INVALID) {
            fprintf(stderr,
                    "[XED CLIENT ERROR] Bad register name: %s on operand %u\n",
                    cres_reg, i);
            exit(1);
        }

        if (areq.dstate.mmode != XED_MACHINE_MODE_LONG_64)
            if (reg == XED_REG_DIL || reg == XED_REG_SPL ||  reg == XED_REG_BPL ||  reg == XED_REG_SIL)
            {
                fprintf(stderr,
                        "[XED CLIENT ERROR] Cannot use DIL/SPL/BPL/SIL outside of 64b mode\n");
                exit(1);
            }
        // The registers operands are numbered starting from the first one
        // as XED_OPERAND_REG0. We increment regnum (below) every time we
        // add a register operands.
        r = XED_CAST(xed_operand_enum_t,XED_OPERAND_REG0 + regnum);
        // store the register identifier in the operand storage field
        xed_encoder_request_set_reg(&req, r, reg);
        // store the operand storage field name in the encode-order array
        xed_encoder_request_set_operand_order(&req, operand_index, r);

        find_vl(reg, &vl);
        
        regnum++;
    } // for loop

    if (uvl == -1)
    {
        // no user VL setting, so use our observation-based guess.
        if (vl>=0) 
            xed3_operand_set_vl(&req,(xed_uint_t)vl);
    }
    else
    {
        if (vl >= 0 && uvl < vl)
            xedex_derror("User specified VL is smaller than largest observed register.");
        // go with the user value. The encoder still might increase it
        // based on observed values. But we test for that above so they'll
        // get the feedback.
        xed3_operand_set_vl(&req,(xed_uint_t)uvl);
    }
    return req;
}
