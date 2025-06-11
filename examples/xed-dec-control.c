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

/// @file xed-dec-control.c
/// @brief essential decoder example for the XED decode-with-features APIs
/// which can be used for customisable ISA support

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h> // strcmp, memset
#include <assert.h> 

int main(int argc, char** argv);

static xed_bool_t long_mode = 0;

static xed_bool_t check_error(xed_error_enum_t xed_error)
{
    switch (xed_error)
    {
        case XED_ERROR_NONE:
            return 0; // Legal instruction
        case XED_ERROR_INVALID_FOR_CHIP:
            printf("(Instruction is not valid for chip) ");
            return 0; // This instruction is legal in general, return 0 to print it later.
        case XED_ERROR_BUFFER_TOO_SHORT:
            printf("Not enough bytes provided\n");
            return 1;
        case XED_ERROR_GENERAL_ERROR:
            printf("Could not decode given input.\n");
            return 1;
        default:
            printf("Unhandled error code: %s\n", 
                    xed_error_enum_t2str(xed_error));
            return 1;
    }
}

static void print_inst(const xed_decoded_inst_t *xedd, xed_uint_t inst_count)
{
    #define BUFLEN  1000
    char buffer[BUFLEN];
    xed_syntax_enum_t syntax = XED_SYNTAX_INTEL;
    xed_bool_t ok;

    printf("%d: ", inst_count);
    if (check_error(xed3_operand_get_error(xedd)))
        return;

    ok = xed_format_context(syntax, xedd, buffer, BUFLEN, 0, 0, 0);
    if (ok)
        printf("%s\n", buffer);
    else
        printf("Error disassembling %s syntax\n", xed_syntax_enum_t2str(syntax));
}

/**
 * Performs a XED chip-check like validation on a decoded instruction.
 *
 * This function validates the decoded instruction (`xedd`) against the specified
 * chip and chip features. It first checks the instruction validity against the
 * provided chip features. If no chip features are specified, it then checks
 * against the chip. Additionally, it ensures compatibility with legacy instructions
 * that use repurposed prefix bits in the APX architecture.
 */
static xed_bool_t valid_instruction(xed_decoded_inst_t *xedd,
                                    xed_chip_enum_t chip,
                                    const xed_chip_features_t *chip_features)
{
    xed_bool_t valid = 1;
    if (chip_features) {
        valid = xed_decoded_inst_valid_for_features(xedd, chip_features);
    }
    else if (chip != XED_CHIP_INVALID) {
        valid = xed_decoded_inst_valid_for_chip(xedd, chip);
    }
#if defined(XED_APX)
    if (valid) {
        xed_bool_t apx_system = 0;
        if (long_mode == 1 && !xed3_operand_get_no_apx(xedd))
            apx_system = 1;
        // Check legacy instructions with APX repurposed prefix bits
        if (!apx_system && xed_classify_apx(xedd))
        {
            valid = 0;
        }
    }
#endif
    return valid;
}

static void xed_decode_repeatable(xed_decoded_inst_t *xedd, 
                                  const char *decode_text_in, 
                                  xed_chip_enum_t chip,
                                  const xed_chip_features_t *chip_features)
{
    xed_uint8_t hex_decode_text[XED_MAX_INSTRUCTION_BYTES];
    xed_error_enum_t error;
    xed_uint_t inst_count = 0;
    const char *decode_text = decode_text_in;
    unsigned int remaining = (unsigned int)strlen(decode_text) / 2; // 2 bytes per nibble

    // Initialize decoder ISA support based on XED chip features.
    // This setup is performed once during the initialization phase to optimize performance.
    xed_decoded_inst_t init_xedd;
    xed_set_decoder_modes(xedd, chip, chip_features); 
    init_xedd = *xedd;

    do {
        xed_uint_t len;
        xed_uint_t bytes = xed_convert_ascii_to_hex(decode_text, hex_decode_text, XED_MAX_INSTRUCTION_BYTES);
        if (bytes == 0) {
            printf("Invalid hex string\n");
            return;
        }

        error = xed_decode(xedd, hex_decode_text, bytes);  // No decoder ISA init, No chip-check
        if (error == XED_ERROR_NONE && !valid_instruction(xedd, chip, 0))  // self chip-check
            xed3_operand_set_error(xedd, XED_ERROR_INVALID_FOR_CHIP);
        
        print_inst(xedd, inst_count++);

        // prepare for the next decode...
        len = xed_decoded_inst_get_length(xedd);
        decode_text += len * 2;
        if (len < remaining) {
            remaining -= len;
            *xedd = init_xedd;
        }
        else {
            remaining = 0;
        }
    }
    while (remaining > 0);
}

/**
 * Decode without specifying XED chip or features.
 *
 * Decoder ISA support init: No
 * XED Chip-check: No
 * Faster decode: Yes
 *
 * In this method, XED chip/features are not specified, and the user needs to
 * manually set the XED internal operands to initiate decoder ISA support.
 * This method offers maximum control and customizability, but it requires the
 * user to understand and correctly set the internal operands.
 *
 * Note: This method is error-prone and not recommended unless the user has a
 * specific reason to use it.
 */
static void decode_no_chip(xed_decoded_inst_t *xedd, const xed_uint8_t *itext, xed_uint_t bytes)
{
    // Example: Specify decoder support for CET ISA
#if defined(XED_CET)
    xed3_operand_set_cet(xedd, 1);
#endif
    xed_decode(xedd, itext, bytes); // No decoder ISA init, No chip-check
    print_inst(xedd, 0);
}

/**
 * Decode with XED chip.
 *
 * Decoder ISA support init: Yes
 * XED Chip-check: Optional (see below)
 * Faster decode: Optional (see below)
 *
 * When a XED chip is used, the `xed_decode()` API sets the decoder ISA support
 * state according to the chosen chip. 
 * 
 * If the `xed_decode()` API is called multiple times, the user can disable ISA 
 * init execution on each call and instead use the `xed_set_decoder_modes()` 
 * API for on-demand initialization.
 * This approach can enhance decoding performance.
 *
 * This method is simple and recommended for users who find XED's predefined
 * chips sufficient for their needs. To specify support for all the latest ISA,
 * users can use the XED_CHIP_ALL chip.
 */
static void decode_with_chip(xed_decoded_inst_t *xedd, 
                             const char *decode_text, 
                             const xed_uint8_t *hex_decode_text,
                             xed_uint_t bytes,
                             xed_bool_t repeat)
{
#if defined(XED_CHIP_LUNAR_LAKE_DEFINED)
    xed_chip_enum_t chip = XED_CHIP_LUNAR_LAKE; // Example chip
#else
    xed_chip_enum_t chip = XED_CHIP_ALL; // Example chip
#endif
    printf("Using decode_with_chip(), Repeat=%s\n", repeat ? "True" : "False");

    if (repeat)
    {
        // Optimized repeatable version which executes decoder ISA init one time:
        xed_decode_repeatable(xedd, decode_text, chip, 0);
    }
    else {
        // Setting a chip to the xed_decoded_inst_t initiates decoder ISA support on 
        // each call to `xed_decode()`
        xed_decoded_inst_set_input_chip(xedd, chip);
        // Decoder ISA support init -> decode -> chip-check
        xed_decode(xedd, hex_decode_text, bytes);
        print_inst(xedd, 0);
    }
}

/**
 * Decode with XED chip-features.
 *
 * Decoder ISA support init: Yes
 * XED Chip-check: Optional (see below)
 * Faster decode: Optional (see below)
 *
 * XED chip-features is a customizable chip specified by supported XED ISA-SETs.
 * When using the `xed_decode_with_features()` API, the decoder ISA support state
 * is internally initialized according to the given xed_chip_features_t arg.
 *
 * If the `xed_decode_with_features()` API is called multiple times, the user can
 * disable ISA init execution on each call and instead use the `xed_set_decoder_modes()`
 * API for on-demand initialization, and later call the `xed_decode()` decode API.
 * This approach can enhance decoding performance.
 *
 * This method allows easy customization of ISA support using XED ISA-SETs and
 * lets XED set the required internals based on the given xed_chip_features_t list.
 * It is recommended for users who want maximum control with simple and easy-to-use
 * ISA-SET controlled APIs.
 */
static void decode_with_features(xed_decoded_inst_t *xedd, 
                                 const char *decode_text, 
                                 const xed_uint8_t *hex_decode_text, 
                                 xed_uint_t bytes,
                                 xed_bool_t repeat)
{
    xed_chip_features_t chip_features;
    xed_chip_enum_t init_chip = XED_CHIP_ALL;
    xed_uint32_t eax, ebx, ecx, edx;
    printf("Using decode_with_features(), Repeat=%s\n", repeat ? "True" : "False");

    /* Initialize chip_features with support for the latest and newest ISA (XED_CHIP_ALL) */
    xed_get_chip_features(&chip_features, init_chip);

    /* Modify dual-encoding ISA support */
    // Pause is supported since PENTIUM4 - Assume valid
    xed_modify_chip_features(&chip_features, XED_ISA_SET_PAUSE, 1);
#if defined(XED_CET)
    // CET is runtime-dependent - Assume valid
    xed_modify_chip_features(&chip_features, XED_ISA_SET_CET, 1);
#endif

    /* Modify dual-encoding ISA support according to the host CPUID */
#if defined(XED_ISA_SET_LZCNT_DEFINED)
    // XED_ISA_SET_LZCNT : lzcnt.80000001.0.ecx.5
    get_cpuid(0x80000001, 0, &eax, &ebx, &ecx, &edx);
    xed_modify_chip_features(&chip_features, XED_ISA_SET_LZCNT, get_bit32(ecx, 5));
#endif
#if defined(XED_ISA_SET_WBNOINVD_DEFINED)
    // XED_ISA_SET_WBNOINVD : wbnoinvd.80000008.0.ebx.9
    get_cpuid(0x80000008, 0, &eax, &ebx, &ecx, &edx);
    xed_modify_chip_features(&chip_features, XED_ISA_SET_WBNOINVD, get_bit32(ebx, 9));
#endif
    
    /***************************/
    /* Leaf = 0x7, subleaf = 0 */
    get_cpuid(0x7, 0, &eax, &ebx, &ecx, &edx);

#if defined(XED_ISA_SET_BMI1_DEFINED)
    // XED_ISA_SET_BMI1 : bmi1.7.0.ebx.3
    xed_modify_chip_features(&chip_features, XED_ISA_SET_BMI1, get_bit32(ebx, 3));
#endif
#if defined(XED_ISA_SET_CLDEMOTE_DEFINED)
    // XED_ISA_SET_CLDEMOTE : cldemote.7.0.ecx.25
    xed_modify_chip_features(&chip_features, XED_ISA_SET_CLDEMOTE, get_bit32(ecx, 25));
#endif
#if defined(XED_MPX)
    // XED_ISA_SET_MPX : mpx.7.0.ebx.14
    xed_modify_chip_features(&chip_features, XED_ISA_SET_MPX, get_bit32(ebx, 14));
#endif
    /***************************/
    /* Leaf = 0x7, subleaf = 0x1 */
    get_cpuid(0x7, 0x1, &eax, &ebx, &ecx, &edx);
#if defined(XED_ISA_SET_ICACHE_PREFETCH_DEFINED)
    // XED_ISA_SET_ICACHE_PREFETCH : icache_prefetch.7.1.edx.14
    xed_modify_chip_features(&chip_features, XED_ISA_SET_ICACHE_PREFETCH,
                             get_bit32(edx, 14));
#endif
#if defined(XED_ISA_SET_MOVRS_DEFINED)
    // XED_ISA_SET_MOVRS : movrs.7.1.eax.31
    xed_modify_chip_features(&chip_features, XED_ISA_SET_MOVRS, get_bit32(eax, 31));
#endif
    /***************************/

    if (repeat)
    {
        // Specifying chip_features effectively makes XED chip a "don't-care" value.
        // Optimized repeatable version which executes decoder ISA init one time:
        xed_decode_repeatable(xedd, decode_text, XED_CHIP_INVALID, &chip_features);
    }
    else { // No repeat
        // Decoder ISA support init -> decode -> chip-check:
        xed_decode_with_features(xedd, hex_decode_text, bytes, &chip_features);
        print_inst(xedd, 0);
    }
}

int main(int argc, char **argv)
{
    xed_uint_t argcu = (xed_uint_t)argc;
    xed_decoded_inst_t xedd;
    xed_uint8_t hex_decode_text[XED_MAX_INSTRUCTION_BYTES];
    xed_format_options_t format_options;
    xed_machine_mode_enum_t mmode;
    xed_address_width_enum_t stack_addr_width;
    const char *decode_text = 0;
    xed_uint_t i, bytes, len, de_method = 0, repeat = 0;

    // one time initialization 
    xed_tables_init();
    // xed_set_verbosity( 99 );
    memset(&format_options, 0, sizeof(format_options));
    format_options.hex_address_before_symbolic_name = 0;
    format_options.xml_a = 0;
    format_options.omit_unit_scale = 0;
    format_options.no_sign_extend_signed_immediates = 0;
    format_options.emit_ignored_branch_taken_hint = 0;

    for (i = 1; i < argcu; i++)
    {
        if (strcmp(argv[i], "-xml") == 0) 
            format_options.xml_a = 1;
        else if (strcmp(argv[i], "-no-unit-scale") == 0) 
            format_options.omit_unit_scale = 1;
        else if (strcmp(argv[i], "-no-sign-extend") == 0) 
            format_options.no_sign_extend_signed_immediates = 1;
        else if (strcmp(argv[i], "-64") == 0) 
            long_mode = 1;
        else if (strcmp(argv[i], "-de-method") == 0) 
        {
            de_method = xed_atoi_general(argv[i + 1], 1000);
            i++;
        }
        else if (strcmp(argv[i], "-repeat") == 0)
            repeat = 1;
        else 
            break;
    }

    xed_format_set_options(format_options);

    // begin processing of instructions...

    if (long_mode) {
        mmode = XED_MACHINE_MODE_LONG_64;
        stack_addr_width = XED_ADDRESS_WIDTH_64b;
    }
    else {
        mmode = XED_MACHINE_MODE_LEGACY_32;
        stack_addr_width = XED_ADDRESS_WIDTH_32b;
    }

    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);

    // convert ascii hex to hex bytes
    for (; i < argcu; i++) {
        decode_text = xedex_append_string(decode_text, argv[i]);
        if (!decode_text) {
            printf("Failed to allocate memory for decode_text\n");
            exit(1);
        }
    }

    len = (unsigned int)strlen(decode_text);
    if ((len & 1) == 1)
    {
        printf("Must supply even number of nibbles per substring\n");
        exit(1);
    }

    bytes = xed_convert_ascii_to_hex(decode_text,
                                     hex_decode_text,
                                     XED_MAX_INSTRUCTION_BYTES);
    if (bytes == 0)
    {
        printf("Must supply some hex bytes\n");
        exit(1);
    }

    printf("PARSING BYTES: ");
    for (i = 0; i < bytes; i++)
        printf("%02x ", hex_decode_text[i]);
    printf("\n");

    switch (de_method)
    {
    case 0:
        decode_no_chip(&xedd, hex_decode_text, XED_MAX_INSTRUCTION_BYTES);
        break;
    case 1:
        decode_with_chip(&xedd, decode_text, hex_decode_text, XED_MAX_INSTRUCTION_BYTES, repeat);
        break;
    case 2:
        decode_with_features(&xedd, decode_text, hex_decode_text, XED_MAX_INSTRUCTION_BYTES, repeat);
        break;
    default:
        printf("Unsupported decode method (Using \"-de-method\")\n");
        exit(1);
        break;
    }

    free((void*)decode_text); // Free allocated memory
    return 0;
}
