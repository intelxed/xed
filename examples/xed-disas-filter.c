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

#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>

#include <xed/xed-interface.h>
#include "xed-examples-util.h"
#include "xed-disas-filter.h"
#include "xed-symbol-table.h"
#include "xed-nm-symtab.h"

#define IMAX 32
#define LINELEN 1024

static int len_hex(char *s)
{
    char *p = s;
    while (isxdigit(*p))
	p++;
    return (int)(p - s);
}

static unsigned long get_ip(char *line)
{
    char *num;
    for (num = line; *num; num++) {
	int l;
	if (isxdigit(*num) && (l = len_hex(num)) >= 8 && isspace(num[l])) {
	    return strtoul(num, NULL, 16);
	}
    }
    return 0;
}

/* Decode fields in lines of the form

   prefix hexbytes ...

   and replace it in the output with the decoded instruction. Each line
   is assumed to be a single instruction for now.

   Optionally we look for a another hex address before prefix that gives
   the IP. */

xed_uint_t disas_filter(xed_decoded_inst_t *inst, char *prefix, xed_disas_info_t *di)
{
    char line[LINELEN];

    di->symfn = get_symbol;
    xed_register_disassembly_callback(xed_disassembly_callback_function);
    while (fgets(line, LINELEN, stdin)) {
	xed_error_enum_t err;
	char *insn = strstr(line, prefix), *ip;
	xed_uint_t ilen;
	char out[256];
	unsigned long val;
	char *endp;
	xed_uint8_t insnbuf[IMAX];

	if (!insn) {
	    fputs(line, stdout);
	    continue;
	}

	ip = insn + strlen(prefix);
	ilen = 0;
	do {
	    val = strtoul(ip, &endp, 16);
	    if (insn == endp)
		    break;
	    insnbuf[ilen++] = (xed_uint8_t)val;
	    ip = endp;
	} while (ilen < IMAX);
	xed_state_t state;
	xed_state_zero(&state);
	xed_state_set_machine_mode(&state, di->dstate.mmode);
	xed_decoded_inst_zero_set_mode(inst, &state);
	if ((err = xed_decode(inst, insnbuf, ilen)) != XED_ERROR_NONE) {
	    snprintf(out, sizeof out, "%s" , xed_error_enum_t2str(err));
	} else {
	    disassemble(di, out, sizeof out, inst, get_ip(line),
			    nm_symtab_init ? &nm_symtab : NULL);
	}
	printf("%.*s\t\t%s%s", (int)(insn - line), line, out, endp);
    }
    return 0;
}
