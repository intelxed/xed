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
/// @file xed-init.c



// This declares the major tables used by XED
#include "xed-tables-decl.h"

#include "xed-internal-header.h"

#include "xed-init.h"

extern void xed_init_inst_table(void);
extern void xed_init_pointer_names(void);
extern void xed_init_operand_ctypes(void);
extern void xed_init_width_mappings(void);
extern void xed_init_reg_mappings(void);
extern void xed_init_chip_model_info(void);
extern void xed_init_convert_tables(void);
extern void xed_ild_init(void);
#if defined(XED_MESSAGES)
# include <stdio.h>
#endif
#include "xed-ild.h"

static void 
xed_common_init(void)
{
    static int first_time = 1;
    if (first_time == 0)
	return;
    first_time = 0;
#if defined(XED_MESSAGES)
    xed_log_file=stdout;
#endif
}

static void 
xed_decode_init(void)
{
    static int first_time = 1;
    if (first_time == 0)
	return;
    first_time = 0;
    xed_common_init();
    xed_init_width_mappings();
    xed_init_reg_mappings();

    xed_init_pointer_names(); // generated function
    xed_init_operand_ctypes(); // generated function
    xed_init_inst_table(); // generated function
    xed_init_chip_model_info();
    xed_init_convert_tables();
}

#if defined(XED_ENCODER)
extern void xed_init_encode_table(void);
extern void xed_init_encoder_order(void);

static void
xed_encode_init(void) {
    static int first_time = 1;
    if (first_time == 0)
	return;
    first_time = 0;
    xed_common_init();
    // must have the decoder to use the encoder because of the
    // init-from-decode stuff
    xed_decode_init();
    xed_init_encode_table(); // generated function
    xed_init_encoder_order(); // generated function
}

#endif

extern void xed_table_sizes(void);

XED_DLL_EXPORT void 
xed_tables_init(void)
{
    static int first_time = 1;
    if (first_time == 0)
	return;
    first_time = 0;

    xed_table_sizes();

    xed_common_init();
    xed_decode_init();
#if defined(XED_ENCODER)
    xed_encode_init();
#endif
#if defined(XED_DECODER)
    xed_ild_init();
#endif
}


