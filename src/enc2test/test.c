/*BEGIN_LEGAL 

nCopyright (c) 2019 Intel Corporation

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

#include "xed-interface.h"
#include "xed-get-time.h"
#if defined(XED_ENC2_CONFIG_M64_A64)
# include "enc2-m64-a64/hdr/xed/xed-enc2-m64-a64.h"
#elif defined(XED_ENC2_CONFIG_M32_A32)
#include "enc2-m32-a32/hdr/xed/xed-enc2-m32-a32.h"
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "xed-histogram.h"

typedef xed_uint32_t (*test_func_t)(xed_uint8_t* output_buffer);
#if defined(XED_ENC2_CONFIG_M64_A64)
extern test_func_t test_functions_m64_a64[];
extern char const* test_functions_m64_a64_str[];
extern const xed_iclass_enum_t test_functions_m64_a64_iclass[];
#elif  defined(XED_ENC2_CONFIG_M32_A32)
extern test_func_t test_functions_m32_a32[];
extern char const* test_functions_m32_a32_str[];
extern const xed_iclass_enum_t test_functions_m32_a32_iclass[];
#endif

static xed_state_t dstate;

static xed_histogram_t histo;

static int enable_emit=0;
static int enable_emit_byte=0;
static int enable_emit_main=0;
static int enable_emit_gnu_asm=0;
static int enable_emit_test_name=0;

static void dump_comment(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    printf("// ");
    for(i=0;i<len;i++) {
        printf("%02x ",buf[i]);
    }
    printf("\n");
}

static void dump_emit_byte(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    dump_comment(buf,len);
    if (enable_emit_gnu_asm)
        printf("  asm(\"");
    printf(".byte ");
    for(i=0;i<len;i++) {
        if (i>0)
            printf(", ");
        printf("0x%02x", buf[i]);
    }
    if (enable_emit_gnu_asm)
        printf("\\n\");");

    printf("\n");
}

static void dump_emit(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    dump_comment(buf,len);
    for(i=0;i<len;i++) {
        printf("__emit 0x%02x\n", buf[i]);
    }
    printf("\n");
}

xed_uint64_t total = 0;
xed_uint_t reps = 100;
int execute_test(int test_id, test_func_t* base, char const* fn_name, xed_iclass_enum_t ref_iclass) {
    xed_decoded_inst_t xedd;
    xed_uint32_t enclen=0;
    xed_error_enum_t err;
    xed_uint8_t output_buffer[2*XED_MAX_INSTRUCTION_BYTES];
    xed_uint64_t t1, t2, delta;
    xed_uint_t i;

    if (enable_emit_test_name)
        printf("//\ttest id %d  iclass: %s (%s)\n",
               test_id, xed_iclass_enum_t2str(ref_iclass), fn_name);
    for(i=0;i<reps;i++)    {
        t1 = xed_get_time();
        //printf("Calling test function %d\n",test_id);
        enclen = (*base[test_id])(output_buffer);
        t2 = xed_get_time();
        if (t2>t1) {
            delta = t2-t1;
            total += delta;
        }
        if (i > 3)
            xed_histogram_update(&histo, t1, t2);
    }
            
    
    // This stuff should problably move in to the individual tests so
    // that we can do more validation about the iclass and operands.
    
    if (enclen > XED_MAX_INSTRUCTION_BYTES) {
        printf("//\ttest id %d ERROR: %s (%s)\n", test_id, "ENCODE TOO LONG", fn_name);
        dump_comment(output_buffer,enclen);
        return 1;
    }
    
    
    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    // set some modern decode mode behavior
    xed3_operand_set_cet(&xedd, 1);
    xed3_operand_set_cldemote(&xedd, 1);
    xed3_operand_set_wbnoinvd(&xedd, 1);
    err = xed_decode(&xedd, output_buffer, enclen);
    if (err == XED_ERROR_NONE) {
        xed_iclass_enum_t observed_iclass = xed_decoded_inst_get_iclass(&xedd);
        xed_uint_t declen = xed_decoded_inst_get_length(&xedd);
        if (enclen != xed_decoded_inst_get_length(&xedd)) {
               printf("//\ttest id %d LENGTH MISMATCH: encode: %d decode: %d iclass: %s (%s)\n", test_id,
                      enclen, declen,
                      xed_iclass_enum_t2str( observed_iclass ),
                      fn_name);
               dump_comment(output_buffer,enclen);
               return 1;
        }
        else if (observed_iclass == XED_ICLASS_NOP &&
            ref_iclass == XED_ICLASS_XCHG &&
            output_buffer[enclen-1] == 0x90) {
            // allow variants of 0x90 to masquerade as NOPs
        }
        else if (observed_iclass != ref_iclass) {
            printf("//\ttest id %d ICLASS MISMATCH: observed: %s expected: %s (%s)\n", test_id,
                   xed_iclass_enum_t2str( observed_iclass ),
                   xed_iclass_enum_t2str( ref_iclass ),
                   fn_name);
            dump_comment(output_buffer,enclen);
            return 1;
        }

        if (enable_emit) {
            dump_emit(output_buffer, enclen);
        }
        else if (enable_emit_byte) {
            dump_emit_byte(output_buffer, enclen);
        }
    }
    else {
        printf("//\ttest id %d ERROR: %s (%s)\n", test_id, xed_error_enum_t2str(err), fn_name);
        dump_comment(output_buffer,enclen);
        return 1;
    }

    return 0;
}


int test_all(test_func_t* base, const char** str_table, const xed_iclass_enum_t* iclass_table) {
    xed_uint32_t test_id=0;
    xed_uint32_t errors = 0;
    xed_uint64_t t1, t2, delta;
    test_func_t* p = base;
    
    t1 = xed_get_time();
    while(*p) {
        char const* fn_name = str_table[test_id];
        const xed_iclass_enum_t ref_iclass = iclass_table[test_id];
        if (execute_test(test_id, base, fn_name, ref_iclass)) {
            printf("//test %d failed\n", test_id);
            errors++;
        }
        p++;
        test_id++;
    }
    t2 = xed_get_time();
    delta = t2-t1;


    printf("//Tests:   %6d\n", test_id);
    printf("//Repeats: %6d\n", reps);
    printf("//Errors:  %6d\n", errors);
    printf("//Cycles: " XED_FMT_LU "\n", delta);
    printf("//Cycles/(enc+dec) : %7.1lf\n", 1.0*delta/(reps*test_id));
    printf("//Cycles/encode    : %7.1lf\n", 1.0*total/(reps*test_id));
    return errors;
}


int main(int argc, char** argv) {
    int i=0, m=0, test_id=0, errors=0,specific_tests=0, enable_histogram=0;
#if defined(XED_ENC2_CONFIG_M64_A64)
    test_func_t* base = test_functions_m64_a64;
    const char** str_table = test_functions_m64_a64_str;
    xed_iclass_enum_t const* iclass_table = test_functions_m64_a64_iclass;
#elif defined(XED_ENC2_CONFIG_M32_A32)
    test_func_t* base = test_functions_m32_a32;
    const char** str_table = test_functions_m32_a32_str;
    xed_iclass_enum_t const* iclass_table = test_functions_m32_a32_iclass;
#endif
    
    xed_tables_init();    
    xed_state_zero(&dstate);
#if defined(XED_ENC2_CONFIG_M64_A64)
    dstate.mmode=XED_MACHINE_MODE_LONG_64;
#elif defined(XED_ENC2_CONFIG_M32_A32)
    dstate.mmode=XED_MACHINE_MODE_LEGACY_32;
    dstate.stack_addr_width=XED_ADDRESS_WIDTH_32b;
#endif
    //dstate.mmode=XED_MACHINE_MODE_LEGACY_16;
    //dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
    
    xed_histogram_initialize(&histo);

    // count tests
    test_func_t* p = base;
    while (*p) {
        i++;
        p++;
    }


    m = i;
    printf("//Total tests %d\n",m);
    for(i=1;i<argc;i++) {
        if (strcmp(argv[i],"--reps")==0) {
            assert( i+1 < argc );
            reps = atoi(argv[i+1]);
            i = i + 1;
        }
        else if (strcmp(argv[i],"--histo")==0) {
            enable_histogram = 1;
        }
        else if (strcmp(argv[i],"--emit")==0) {
            enable_emit = 1;
        }
        else if (strcmp(argv[i],"--byte")==0) {
            enable_emit_byte = 1;
        }
        else if (strcmp(argv[i],"--main")==0) {
            enable_emit_main = 1;
        }
        else if (strcmp(argv[i],"--gnuasm")==0) {
            enable_emit_gnu_asm = 1;
            enable_emit_byte = 1;
        }
        else if (strcmp(argv[i],"--info")==0) {
            enable_emit_test_name = 1;
            enable_emit_byte = 1;
        }
        else if ( strcmp(argv[i],"-h")==0 ||
                  strcmp(argv[i],"--help")==0 )  {
            fprintf(stderr,"%s [-h|--help] [--histo] [--info] [--byte|--emit] [--main] [--gnuasm] [--reps N] [test_id ...]\n",
                    argv[0]);
            exit(0);
        }
        else {
            specific_tests = 1;
            test_id = (int)strtol(argv[i], (char **)NULL, 10);
            if (test_id >=  m) {
                printf("Test ID too large (range: 0...%d)\n",m-1);
                return 1;
            }
        
            char const* fn_name = str_table[test_id];
            xed_iclass_enum_t ref_iclass = iclass_table[test_id];
            if (execute_test(test_id, base, fn_name, ref_iclass)) {
                printf("//test id %d failed\n", test_id);
                errors++;
            }
            else {
                printf("//test id %d success\n", test_id);
            }
        }
    }

    if (enable_emit_byte && enable_emit) {
        printf("Cannot specify --byte and --emit in the same run\n");
        exit(1);
    }
    if (enable_emit_main) {
        if (enable_emit)
            printf("//Compile this with -fasm-blocks using icc\n\n");
        if (enable_emit_gnu_asm)
            printf("//Compile this with gcc\n\n");
        printf("int main(int argc, char** argv) {\n");
        if (enable_emit)
            printf("  __asm {\n");
    }
    if (specific_tests==0) {
        printf("//Testing all...\n");
        errors = test_all(base, str_table, iclass_table);
    }
    if (enable_emit_main) {
        if (enable_emit)
            printf("   }\n"); // end __asm block
        printf("   return 0;\n");
        printf(" }\n");
    }
    if (enable_histogram)
        xed_histogram_dump(&histo, 1);
    return errors>0;
}
