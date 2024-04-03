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

/// This is the place to start learning about the decoder APIs. It
/// exercises most of the essential features of the decoder.

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>

int main(int argc, char** argv);


void print_misc(xed_decoded_inst_t* xedd) {
    xed_uint_t i=0, j=0;
    const xed_operand_values_t* ov = xed_decoded_inst_operands_const(xedd);
    const xed_inst_t* xi = xed_decoded_inst_inst(xedd);
    xed_exception_enum_t e = xed_inst_exception(xi);
    xed_uint_t np = xed_decoded_inst_get_nprefixes(xedd);

    xed_isa_set_enum_t isaset = xed_decoded_inst_get_isa_set(xedd);

    if (xed_operand_values_has_real_rep(ov)) {
        xed_iclass_enum_t norep =
            xed_rep_remove(xed_decoded_inst_get_iclass(xedd));
        printf("REAL REP ");
        printf("\tcorresponding no-rep iclass: %s\n" ,
               xed_iclass_enum_t2str(norep));
               
    }
    if (xed_operand_values_has_rep_prefix(ov)) {
        printf("F3 PREFIX\n");
    }
    if (xed_operand_values_has_repne_prefix(ov)) {
        printf("F2 PREFIX\n");
    }
    if (xed_operand_values_has_address_size_prefix(ov)) {
        printf("67 PREFIX\n");
    }
    if (xed_operand_values_has_operand_size_prefix(ov)) {
        /* this 66 prefix is not part of the opcode */
        printf("66-OSZ PREFIX\n");
    }
    if (xed_operand_values_mandatory_66_prefix(ov)) {
        /* this 66 prefix is mandatory */
        printf("MANDATORY 66 PREFIX\n");
    }
    else if (xed_operand_values_has_66_prefix(ov)) {
        /* this is any 66 prefix including the above */
        printf("ANY 66 PREFIX\n");
    }
    if (xed3_operand_get_rex2(xedd)) {
        /* Legacy instructions with REX2 prefix have no new iforms. This function returns a non-zero
        number if REX2 prefix is detected for a Legacy instruction */
        printf("REX2 PREFIX\n");
    }

    if (xed_decoded_inst_get_attribute(xedd, XED_ATTRIBUTE_RING0)) {
        printf("RING0 only\n");
    }

    if (e != XED_EXCEPTION_INVALID) {
        printf("EXCEPTION TYPE: %s\n", xed_exception_enum_t2str(e));
    }
    if (xed_decoded_inst_is_broadcast(xedd))
        printf("BROADCAST\n");
#if defined(XED_APX)
    if (xed_classify_apx(xedd))
    {
        printf("[APX] ");
        if (xed_decoded_inst_get_attribute(xedd, XED_ATTRIBUTE_APX_NDD)) {
            printf("New-Data-Destination ");
        }
        if (xed_decoded_inst_get_attribute(xedd, XED_ATTRIBUTE_APX_NF)) {
            printf("No-Flags ");
        }
        if (xed3_operand_get_has_egpr(xedd)) {
            /* returns a non-zero number if one of the register/memory-structure operands of a decoded
            instruction is an extended GPR(EGPR) (valid for both Legacy and EVEX instructions) */
            printf("Uses-EGPR ");
        }
        if (xed_decoded_inst_is_apx_zu(xedd)) {
            printf("Zero-Upper ");
        }
        printf("\n");
    }
#endif
    
    if (xed_classify_sse(xedd) || xed_classify_avx(xedd) || xed_classify_avx512(xedd) || 
        xed_classify_amx(xedd))
    {
        if (xed_classify_amx(xedd))
            printf("AMX\n");
        else if (xed_classify_avx512_maskop(xedd))
            printf("AVX512 KMASK-OP\n");
        else {
            xed_bool_t sse = 0;
            if (xed_classify_sse(xedd)) {
                sse = 1;
                printf("SSE\n");
            }
            else if (xed_classify_avx(xedd))
                printf("AVX\n");
            else if (xed_classify_avx512(xedd))
                printf("AVX512\n");
            
            if (xed_decoded_inst_get_attribute(xedd, XED_ATTRIBUTE_SIMD_SCALAR))
                printf("SCALAR\n");
            else {
                // xed_decoded_inst_vector_length_bits is only for VEX/EVEX instr.
                // This will print 128 vl for FXSAVE and LD/ST MXCSR which is unfortunate.
                xed_uint_t vl_bits = sse ? 128 : xed_decoded_inst_vector_length_bits(xedd);
                printf("Vector length: %u\n", vl_bits);
            }

            if (xed_classify_avx512(xedd)) {
                xed_uint_t vec_elements  = xed_decoded_inst_avx512_dest_elements(xedd);
                printf( "AVX512 vector elements: %u\n", vec_elements);
            }
        }
    }

    // does not include instructions that have XED_ATTRIBUTE_MASK_AS_CONTROL.
    // does not include vetor instructions that have k0 as a mask register.
    if (xed_decoded_inst_masked_vector_operation(xedd))
        printf("WRITE-MASKING\n");

    if (np) 
        printf("Number of legacy prefixes: %u \n", np);

    printf("ISA SET: [%s]\n", xed_isa_set_enum_t2str(isaset));
    for(i=0; i<XED_MAX_CPUID_GROUPS_PER_ISA_SET; i++)
    {
        xed_cpuid_group_enum_t cpuidgrp;
        cpuidgrp = xed_get_cpuid_group_enum_for_isa_set(isaset,i);
        if (cpuidgrp == XED_CPUID_GROUP_INVALID)
            break;
        printf("%u\tCPUID GROUP NAME: [%s]\n", i, xed_cpuid_group_enum_t2str(cpuidgrp));

        for(j=0; j<XED_MAX_CPUID_RECS_PER_GROUP; j++)
        {
            xed_cpuid_rec_enum_t cpuidrec;
            xed_cpuid_rec_t crec;
            xed_bool_t r;
            cpuidrec = xed_get_cpuid_rec_enum_for_group(cpuidgrp,j);
            if (cpuidrec == XED_CPUID_REC_INVALID)
                break;
            printf("\t%u\tCPUID RECORD NAME: [%s]\n", j, xed_cpuid_rec_enum_t2str(cpuidrec));

            r = xed_get_cpuid_rec(cpuidrec, &crec);
            if (r) {
                printf("\t\t{Leaf 0x%08x, subleaf 0x%08x, %s[%u:%u]} = %u\n",
                    crec.leaf, crec.subleaf, xed_reg_enum_t2str(crec.reg),
                    crec.bit_start, crec.bit_end, crec.value);
            }
            else {
                printf("Could not find cpuid leaf information\n");
            }
        }
    }

    if (xed3_operand_get_sae(xedd))
    {
        static char const* rounding_modes[5] = { "", "rne-sae", "rd-sae", "ru-sae", "rz-sae"};
        int t = xed3_operand_get_roundc(xedd);
        printf("suppress-all-exceptions (SAE) set\n");
        if (t>0 && t<5) 
            printf("rounding mode override = %s\n", rounding_modes[t]);
    }

}

void print_branch_hints(xed_decoded_inst_t* xedd) {
    if (xed_operand_values_branch_not_taken_hint(xedd)) 
        printf("HINT: NOT TAKEN\n");
    else if (xed_operand_values_branch_taken_hint(xedd)) 
        printf("HINT: TAKEN\n");
    else if (xed_operand_values_cet_no_track(xedd)) 
        printf("CET NO-TRACK\n");
}

void print_attributes(xed_decoded_inst_t* xedd) {
    /* Walk the attributes. Generally, you'll know the one you want to
     * query and just access that one directly. */

    const xed_inst_t* xi = xed_decoded_inst_inst(xedd);

    unsigned int i, nattributes  =  xed_attribute_max();

    printf("ATTRIBUTES: ");
    for(i=0;i<nattributes;i++) {
        xed_attribute_enum_t attr = xed_attribute(i);
        if (xed_inst_get_attribute(xi,attr))
            printf("%s ", xed_attribute_enum_t2str(attr));
    }
    printf("\n");
}

void print_reads_zf_flag(xed_decoded_inst_t* xedd) {
    /* example of reading one bit from the flags set */
    if (xed_decoded_inst_uses_rflags(xedd)) {
        xed_simple_flag_t const* rfi = xed_decoded_inst_get_rflags_info(xedd);
        xed_flag_set_t const* read_set = xed_simple_flag_get_read_flag_set(rfi);
        if (read_set->s.zf) {
            printf("READS ZF\n");
        }
    }
}

void print_flags(xed_decoded_inst_t* xedd) {
    unsigned int i, nflags;
    if (xed_decoded_inst_uses_rflags(xedd)) {
        const xed_simple_flag_t* rfi = xed_decoded_inst_get_rflags_info(xedd);
        assert(rfi);
        printf("FLAGS:\n");
        if (xed_simple_flag_reads_flags(rfi)) {
            printf("   reads-rflags ");
        }
        else if (xed_simple_flag_writes_flags(rfi)) {
            //XED provides may-write and must-write information
            if (xed_simple_flag_get_may_write(rfi)) {
                printf("  may-write-rflags ");
            }
            if (xed_simple_flag_get_must_write(rfi)) {
                printf("  must-write-rflags ");
            }
        }
        nflags = xed_simple_flag_get_nflags(rfi);
        for( i=0;i<nflags ;i++) {
            const xed_flag_action_t* fa =
                xed_simple_flag_get_flag_action(rfi,i);
            char buf[500];
            xed_flag_action_print(fa,buf,500);
            printf("%s ", buf);
        }
        printf("\n");
        // or as as bit-union
        {
            xed_flag_set_t const*  read_set =
                xed_simple_flag_get_read_flag_set(rfi);
            /* written set include undefined flags */
            xed_flag_set_t const* written_set =
                xed_simple_flag_get_written_flag_set(rfi);
            xed_flag_set_t const* undefined_set =
                xed_simple_flag_get_undefined_flag_set(rfi);
            char buf[500];
            xed_flag_set_print(read_set,buf,500);
            printf("       read: %30s mask=0x%x\n",
                   buf,
                   xed_flag_set_mask(read_set));
            xed_flag_set_print(written_set,buf,500);
            printf("    written: %30s mask=0x%x\n",
                   buf,
                   xed_flag_set_mask(written_set));
            xed_flag_set_print(undefined_set,buf,500);
            printf("  undefined: %30s mask=0x%x\n",
                   buf,
                   xed_flag_set_mask(undefined_set));
        }
#if defined(XED_APX)
        /* print Default Flags Values based on the DFV pseudo register*/
        xed_reg_enum_t dfv_enum = xed_decoded_inst_get_dfv_reg(xedd);
        if (dfv_enum != XED_REG_INVALID){
            xed_flag_dfv_t dfv_reg;
            xed_bool_t okay = xed_flag_dfv_get_default_flags_values(dfv_enum, &dfv_reg);
            assert(okay);
            printf("    default:%13sof=%u, sf=%u, zf=%u, cf=%u\n",
                    "",
                    dfv_reg.s.of,
                    dfv_reg.s.sf,
                    dfv_reg.s.zf,
                    dfv_reg.s.cf);
        }
#endif
    }
}

void print_memops(xed_decoded_inst_t* xedd) {
    unsigned int i, memops = xed_decoded_inst_number_of_memory_operands(xedd);

    printf("Memory Operands\n");
    
    for( i=0;i<memops ; i++)   {
        xed_bool_t r_or_w = 0;
        xed_reg_enum_t seg;
        xed_reg_enum_t base;
        xed_reg_enum_t indx;
        printf("  %u ",i);
        if ( xed_decoded_inst_mem_read(xedd,i)) {
            printf("   read ");
            r_or_w = 1;
        }
        if (xed_decoded_inst_mem_written(xedd,i)) {
            printf("written ");
            r_or_w = 1;
        }
        if (!r_or_w) {
            printf("   agen "); // LEA instructions
        }
        seg = xed_decoded_inst_get_seg_reg(xedd,i);
        if (seg != XED_REG_INVALID) {
            printf("SEG= %s ", xed_reg_enum_t2str(seg));
        }
        base = xed_decoded_inst_get_base_reg(xedd,i);
        if (base != XED_REG_INVALID) {
            printf("BASE= %3s/%3s ",
                   xed_reg_enum_t2str(base),
                   xed_reg_class_enum_t2str(xed_reg_class(base)));
        }
        indx = xed_decoded_inst_get_index_reg(xedd,i);
        if (i == 0 && indx != XED_REG_INVALID) {
            printf("INDEX= %3s/%3s ",
                   xed_reg_enum_t2str(indx),
                   xed_reg_class_enum_t2str(xed_reg_class(indx)));
            if (xed_decoded_inst_get_scale(xedd,i) != 0) {
                // only have a scale if the index exists.
                printf("SCALE= %u ",
                       xed_decoded_inst_get_scale(xedd,i));
            }
        }

        if (xed_operand_values_has_memory_displacement(xedd))
        {
            xed_uint_t disp_bits =
                xed_decoded_inst_get_memory_displacement_width(xedd,i);
            if (disp_bits)
            {
                xed_int64_t disp;
                printf("DISPLACEMENT_BYTES= %u ", disp_bits);
                disp = xed_decoded_inst_get_memory_displacement(xedd,i);
                printf("0x" XED_FMT_LX16 " base10=" XED_FMT_LD, disp, disp);
            }
        }
        printf(" ASZ%u=%u\n",
               i,
               xed_decoded_inst_get_memop_address_width(xedd,i));
    }
    printf("  MemopBytes = %u\n",
           xed_decoded_inst_get_memory_operand_length(xedd,0));
}


void print_operands(xed_decoded_inst_t* xedd) {
    unsigned int i, noperands;
#define TBUFSZ 90
    char tbuf[TBUFSZ];
    const xed_inst_t* xi = xed_decoded_inst_inst(xedd);
    xed_operand_action_enum_t rw;
    xed_uint_t bits;
    
    printf("Operands\n");
    noperands = xed_inst_noperands(xi);
    printf("#   TYPE               DETAILS        VIS  RW       OC2 BITS BYTES NELEM ELEMSZ   ELEMTYPE   REGCLASS\n");
    printf("#   ====               =======        ===  ==       === ==== ===== ===== ======   ========   ========\n");
    tbuf[0]=0;
    for( i=0; i < noperands ; i++) { 
        const xed_operand_t* op = xed_inst_operand(xi,i);
        xed_operand_enum_t op_name = xed_operand_name(op);
        printf("%u %6s ",
               i,xed_operand_enum_t2str(op_name));

        switch(op_name) {
          case XED_OPERAND_AGEN:
          case XED_OPERAND_MEM0:
          case XED_OPERAND_MEM1:
            // we print memops in a different function
            xed_strcpy(tbuf, "(see below)");
            break;
          case XED_OPERAND_PTR:     // pointer (always in conjunction with a IMM0)
          case XED_OPERAND_ABSBR:   // Absolute branch displacements
          case XED_OPERAND_RELBR: { // Relative branch displacements
              xed_uint_t disp_bytes =
                  xed_decoded_inst_get_branch_displacement_width(xedd);
              if (disp_bytes) {
              char buf[40];
              const unsigned int no_leading_zeros=0;
              const xed_bool_t lowercase = 1;
              xed_uint_t disp_bits =
                  xed_decoded_inst_get_branch_displacement_width_bits(xedd);
                  xed_int64_t disp =
                      xed_decoded_inst_get_branch_displacement(xedd);
                  xed_itoa_hex_ul(buf, disp, disp_bits, no_leading_zeros, 40, lowercase);
#if defined (_WIN32) && !defined(PIN_CRT)
                  _snprintf_s(tbuf, TBUFSZ, TBUFSZ,
                           "BRANCH_DISPLACEMENT_BYTES=%u 0x%s",
                           disp_bytes,buf);
#else
                  snprintf(tbuf, TBUFSZ,
                           "BRANCH_DISPLACEMENT_BYTES=%u 0x%s",
                           disp_bytes,buf);
#endif
              }
            }
            break;

          case XED_OPERAND_IMM0: { // immediates
              char buf[64];
              const unsigned int no_leading_zeros=0;
              xed_uint_t ibits;
              const xed_bool_t lowercase = 1;
              ibits = xed_decoded_inst_get_immediate_width_bits(xedd);
              if (xed_decoded_inst_get_immediate_is_signed(xedd)) {
                  xed_uint_t rbits = ibits?ibits:8;
                  xed_int32_t x = xed_decoded_inst_get_signed_immediate(xedd);
                  xed_uint64_t y = XED_STATIC_CAST(xed_uint64_t,
                                                   xed_sign_extend_arbitrary_to_64(
                                                       (xed_uint64_t)x,
                                                       ibits));
                  xed_itoa_hex_ul(buf, y, rbits, no_leading_zeros, 64, lowercase);
              }
              else {
                  xed_uint64_t x =xed_decoded_inst_get_unsigned_immediate(xedd);
                  xed_uint_t rbits = ibits?ibits:16;
                  xed_itoa_hex_ul(buf, x, rbits, no_leading_zeros, 64, lowercase);
              }
#if defined (_WIN32) && !defined(PIN_CRT)
              _snprintf_s(tbuf, TBUFSZ, TBUFSZ,
                          "0x%s(%ub)",buf,ibits);
#else
              snprintf(tbuf,TBUFSZ,
                       "0x%s(%db)",buf,ibits);
#endif
              break;
          }
          case XED_OPERAND_IMM1: { // 2nd immediate is always 1 byte.
              xed_uint8_t x = xed_decoded_inst_get_second_immediate(xedd);
#if defined (_WIN32) && !defined(PIN_CRT)
              _snprintf_s(tbuf, TBUFSZ, TBUFSZ,
                          "0x%02x",(int)x);
#else
              snprintf(tbuf,TBUFSZ,
                       "0x%02x",(int)x);
#endif

              break;
          }

          case XED_OPERAND_REG0:
          case XED_OPERAND_REG1:
          case XED_OPERAND_REG2:
          case XED_OPERAND_REG3:
          case XED_OPERAND_REG4:
          case XED_OPERAND_REG5:
          case XED_OPERAND_REG6:
          case XED_OPERAND_REG7:
          case XED_OPERAND_REG8:
          case XED_OPERAND_REG9:
          case XED_OPERAND_BASE0:
          case XED_OPERAND_BASE1:
            {

              xed_reg_enum_t r = xed_decoded_inst_get_reg(xedd, op_name);
#if defined (_WIN32)  && !defined(PIN_CRT)
              _snprintf_s(tbuf, TBUFSZ, TBUFSZ,
                       "%s=%s", 
                       xed_operand_enum_t2str(op_name),
                       xed_reg_enum_t2str(r));
#else
              snprintf(tbuf,TBUFSZ,
                       "%s=%s", 
                       xed_operand_enum_t2str(op_name),
                       xed_reg_enum_t2str(r));
#endif
              break;
            }
          default: 
            printf("need to add support for printing operand: %s",
                   xed_operand_enum_t2str(op_name));
            assert(0);      
        }
        printf("%21s", tbuf);
        
        rw = xed_decoded_inst_operand_action(xedd,i);
        
        printf(" %10s %3s %9s",
               xed_operand_visibility_enum_t2str(
                   xed_operand_operand_visibility(op)),
               xed_operand_action_enum_t2str(rw),
               xed_operand_width_enum_t2str(xed_operand_width(op)));

        bits =  xed_decoded_inst_operand_length_bits(xedd,i);
        printf( "  %3u", bits);
        /* rounding, bits might not be a multiple of 8 */
        printf("  %4u", (bits +7) >> 3);

        printf("    %2u", xed_decoded_inst_operand_elements(xedd,i));
        printf("    %3u", xed_decoded_inst_operand_element_size_bits(xedd,i));
        
        printf(" %10s",
               xed_operand_element_type_enum_t2str(
                   xed_decoded_inst_operand_element_type(xedd,i)));
        printf(" %10s\n",
               xed_reg_class_enum_t2str(
                   xed_reg_class(
                       xed_decoded_inst_get_reg(xedd, op_name))));
    }
}

int main(int argc, char** argv) {
    xed_state_t dstate;
    xed_decoded_inst_t xedd;
    xed_uint_t i, bytes = 0;
    xed_uint_t argcu = (xed_uint_t)argc;
    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    xed_uint_t first_argv;
    xed_bool_t already_set_mode = 0;
    xed_chip_enum_t chip = XED_CHIP_INVALID;
    char const* decode_text=0;
    unsigned int len;
    xed_error_enum_t xed_error;
    xed_uint_t operands_index = 0;
    xed_operand_enum_t operands[XED_MAX_INPUT_OPERNADS] = {XED_OPERAND_INVALID};
    xed_uint32_t operands_value[XED_MAX_INPUT_OPERNADS] = {0};
        
#if defined(XED_MPX)
    unsigned int mpx_mode=0;
#endif
#if defined(XED_CET)
    unsigned int cet_mode=0;
#endif
    xed_tables_init();
    xed_state_zero(&dstate);

    first_argv = 1;
    dstate.mmode=XED_MACHINE_MODE_LEGACY_32;
    dstate.stack_addr_width=XED_ADDRESS_WIDTH_32b;

    for(i=1;i< argcu;i++) {
        if (strcmp(argv[i], "-64") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LONG_64;
            first_argv++;
        }
#if defined(XED_MPX)
        else if (strcmp(argv[i], "-mpx") == 0) {
            mpx_mode = 1;
            first_argv++;
        }
#endif
#if defined(XED_CET)
        else if (strcmp(argv[i], "-cet") == 0) {
            cet_mode = 1;
            first_argv++;
        }
#endif
        else if (strcmp(argv[i], "-16") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LEGACY_16;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        }
        else if (strcmp(argv[i], "-s16") == 0) {
            already_set_mode = 1;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        }
        else if (strcmp(argv[i], "-chip") == 0) {
            assert(i+1 < argcu);    
            chip = str2xed_chip_enum_t(argv[i+1]);
            printf("Setting chip to %s\n", xed_chip_enum_t2str(chip));
            assert(chip != XED_CHIP_INVALID);
            first_argv+=2;
        }
        else if (strcmp(argv[i], "-set") == 0) {
            assert(i+2 < argcu);    // needs 2 args
            if (operands_index >= XED_MAX_INPUT_OPERNADS) {
                printf("ERROR: too many -set operands, max is %d\n", XED_MAX_INPUT_OPERNADS);
                exit(1);
            }

            operands[operands_index] = str2xed_operand_enum_t(argv[i+1]);
            if (operands[operands_index] == XED_OPERAND_INVALID){
                printf("ERROR: operand %s doesn't exist\n", argv[i+1]);
                exit(1);
            }
            operands_value[operands_index] = XED_STATIC_CAST(xed_uint8_t, xed_atoi_general(argv[i+2],1000));
            operands_index++;
            first_argv+=3;
        }
    }

    assert(first_argv < argcu);

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    xed_decoded_inst_set_input_chip(&xedd, chip);
#if defined(XED_MPX)
    xed3_operand_set_mpxmode(&xedd, mpx_mode);
#endif
#if defined(XED_CET)
    xed3_operand_set_cet(&xedd, cet_mode);
#endif
    // set the value of operands referenced after '-set'
    for (i = 0; i < operands_index; i++)    
        xed3_set_generic_operand(&xedd, operands[i], operands_value[i]);

    // convert ascii hex to hex bytes
    for(i=first_argv; i< argcu;i++) 
        decode_text = xedex_append_string(decode_text,argv[i]);
    
    len = (unsigned int) strlen(decode_text);
    if ((len & 1) == 1) { 
        printf("Must supply even number of nibbles per substring\n");
        exit(1);
    }
    if (len > XED_MAX_INSTRUCTION_BYTES*2) {
        printf("Must supply at most 30 nibbles (15 bytes)\n");
        exit(1);
    }

    bytes = xed_convert_ascii_to_hex(decode_text,
                                     itext,
                                     XED_MAX_INSTRUCTION_BYTES);
    if (bytes == 0) {
        printf("Must supply some hex bytes\n");
        exit(1);
    }

    printf("Attempting to decode: ");
    for(i=0;i<bytes;i++)
        printf("%02x ", XED_STATIC_CAST(xed_uint_t,itext[i]));
    printf("\n");

    xed_error = xed_decode(&xedd, 
                           XED_REINTERPRET_CAST(const xed_uint8_t*,itext), 
                           bytes);
    
    if (xed_error != XED_ERROR_NONE) {
        xed_uint_t dec_length = xed_decoded_inst_get_length(&xedd);
        xed_decode_error(0, 0, itext, xed_error, dec_length);
        exit(1);
    }
        
    printf("iclass %s\t",
           xed_iclass_enum_t2str(xed_decoded_inst_get_iclass(&xedd)));
    printf("category %s\t" ,
           xed_category_enum_t2str(xed_decoded_inst_get_category(&xedd)));
    printf("ISA-extension %s\t",
           xed_extension_enum_t2str(xed_decoded_inst_get_extension(&xedd)));
    printf("ISA-set %s\n" ,
           xed_isa_set_enum_t2str(xed_decoded_inst_get_isa_set(&xedd)));
    printf("instruction-length %u\n",
           xed_decoded_inst_get_length(&xedd));
    printf("operand-width %u\n",
           xed_decoded_inst_get_operand_width(&xedd));
    printf("effective-operand-width %u\n", 
           xed_operand_values_get_effective_operand_width(
               xed_decoded_inst_operands_const(&xedd)));
    printf("effective-address-width %u\n",
           xed_operand_values_get_effective_address_width(
               xed_decoded_inst_operands_const(&xedd)));
    printf("stack-address-width %u\n",
           xed_operand_values_get_stack_address_width(
               xed_decoded_inst_operands_const(&xedd)));
    printf("iform-enum-name %s\n", 
           xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(&xedd)));
    printf("iform-enum-name-dispatch (zero based) %u\n",
           xed_decoded_inst_get_iform_enum_dispatch(&xedd));
    printf("iclass-max-iform-dispatch %u\n",
           xed_iform_max_per_iclass(xed_decoded_inst_get_iclass(&xedd)));

    printf("Nominal opcode position %u\n",
           xed3_operand_get_pos_nominal_opcode(&xedd));
    printf("Nominal opcode 0x%02x\n",
           xed3_operand_get_nominal_opcode(&xedd));
    
    // operands
    print_operands(&xedd);
    
    // memops
    print_memops(&xedd);
    
    // flags
    print_flags(&xedd);
    print_reads_zf_flag(&xedd);

    // attributes
    print_attributes(&xedd);

    // misc
    print_misc(&xedd);
    print_branch_hints(&xedd);
    
    return 0;
}
