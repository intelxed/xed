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
#include <string.h>
#include <stdlib.h>
#include "xed-symbol-table.h"
#include "xed-nm-symtab.h"

xed_symbol_table_t nm_symtab;
xed_bool_t nm_symtab_init;

void xed_read_nm_symtab(char *fn)
{
    char line[1024];
    FILE *f = fopen(fn, "r");
    if (!f)
	    return;

    xed_symbol_table_init(&nm_symtab);
    nm_symtab_init = 1;
    while (fgets(line, sizeof line, f)) {
	unsigned long long adr;
	char type, name[512+1];
	char *s;

	if (sscanf(line, "%llx %c %512s", &adr, &type, name) != 3)
		continue;
	s = malloc(strlen(name) + 1);
	if (!s)
		break;
	strcpy(s, name);
	xst_add_global_symbol(
		&nm_symtab,
		XED_STATIC_CAST(xed_uint64_t, adr),
		s);
    }
    fclose(f);
}
