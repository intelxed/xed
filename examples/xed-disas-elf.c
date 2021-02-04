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

#include "xed-disas-elf.h"  // early, to get defines

#if defined(XED_DECODER) && defined(XED_ELF_READER)

////////////////////////////////////////////////////////////////////////////


#include "xed-disas-elf.h"
#if defined(XED_PRECOMPILED_ELF_DWARF)
# include <libelf.h>
#else  // system version
# include <elf.h>
# if defined(XED_DWARF)
#   include <libelf.h>
# endif
#endif
#if defined(XED_DWARF)
# include <dwarf.h>
# include <libdwarf.h>
#endif

#include "xed/xed-interface.h"
#include "xed-examples-util.h"
#include "xed-symbol-table.h"
#include "avltree.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>

////////////////////////////////////////////////////////////////////////////


// DWARF HANDLING

#if defined(XED_DWARF)
static void dwarf_handler(Dwarf_Error err, Dwarf_Ptr errarg)
{
    (void)err;
    (void)errarg;
}

/* file 0 does not exist */
typedef struct {
    xed_uint32_t line;
    xed_uint32_t file;
} line_number_entry_t;

void line_number_entry_init(line_number_entry_t*p,
                            xed_uint32_t a_line,
                            xed_uint32_t a_file)
{
    p->line=a_line;
    p->file=a_file;
}

/* addresses  -> line_number_entry_t values */
static avl_tree_t line_number_table; //xed_uint64_t -> line_number_entry_t*

/* start at 1, 0 means no file */
static xed_uint32_t global_file_num = 1;

/* global file num -> string */
static avl_tree_t global_file_name_table; // xed_uint64_t -> char*

/* local file num -> global file num. This one is restarted for each
 * compilation unit. */
static avl_tree_t file_name_table; // xed_uint64_t -> xed_uint64_t

static char const* unknown = "Unknown";

static int find_line_number(xed_uint64_t addr,
                            char** file,
                            xed_uint32_t* line)
{
    line_number_entry_t* p =
        (line_number_entry_t*) avl_find(&line_number_table,
                                        addr);
    if (!p)
        return 0;

    char *q = (char*) avl_find(&global_file_name_table,p->file);
    if (q)
        *file = q;
    else
        *file = (char*)unknown;
    *line = p->line;
    return 1;
}

//external interface, called indirectly
void find_line_number_info(xed_uint64_t addr)
{
    char* file_name;
    xed_uint32_t line_number;
    if (find_line_number(addr,
                         &file_name,
                         &line_number))
    {
        printf("  # %s:%d", file_name, line_number);
    }
}


static void read_dwarf_line_numbers(void* region,
                                    unsigned int region_bytes)
{
    int dres;
    Dwarf_Debug dbg;
    Dwarf_Unsigned next_cu_offset;;
    
    elf_version(EV_CURRENT);

    Elf* elf = elf_memory(XED_STATIC_CAST(char*,region), region_bytes);
    dres = dwarf_elf_init(elf, DW_DLC_READ, dwarf_handler, 0, &dbg, 0);
    if (dres != DW_DLV_OK) 
        return;

    avl_tree_init(&line_number_table);
    avl_tree_init(&global_file_name_table);
    avl_tree_init(&file_name_table);

    while (1)
    {
        int i;
        Dwarf_Die cu_die;
        Dwarf_Half tag;
        Dwarf_Line* line_buf;
        Dwarf_Signed line_count;

        dres = dwarf_next_cu_header(dbg, 0, 0, 0, 0, &next_cu_offset, 0);
        if (dres != DW_DLV_OK) 
            break;
        // Doc says first die is compilation unit
        if (dwarf_siblingof(dbg, 0, &cu_die, 0) != DW_DLV_OK)
            continue;
        if ( (dwarf_tag(cu_die, &tag, 0) != DW_DLV_OK) ||
             (tag != DW_TAG_compile_unit))
        {
            dwarf_dealloc(dbg, cu_die, DW_DLA_DIE);
            continue;
        }
        dres = dwarf_srclines(cu_die, &line_buf, &line_count, 0);
        if (dres != DW_DLV_OK)
        {
            dwarf_dealloc(dbg, cu_die, DW_DLA_DIE);
            continue;
        }
        for (i = 0; i < line_count; i++)
        {
            Dwarf_Addr line_addr;
            Dwarf_Unsigned line_num, file_num;
            Dwarf_Signed line_off;
            Dwarf_Bool line_end;
            char* file_name;
            
            dwarf_lineaddr(line_buf[i], &line_addr, 0);
            dwarf_lineno(line_buf[i], &line_num, 0);
            dwarf_line_srcfileno(line_buf[i], &file_num, 0);
            dwarf_lineoff(line_buf[i], &line_off, 0);
            dwarf_lineendsequence(line_buf[i], &line_end, 0);

            if (file_num)
            {
                dres = dwarf_linesrc(line_buf[i], &file_name, 0);
                if (dres == DW_DLV_OK) {
                    
                    if ( avl_find(&file_name_table, file_num) == 0)
                    {
                        avl_insert(&file_name_table,
                                   file_num,
                                   (void*)(xed_addr_t)global_file_num,0);
                        
                        avl_insert(&global_file_name_table,
                                   global_file_num,
                                   xed_strdup(file_name),1);
                        global_file_num++;
                    }
                    dwarf_dealloc(dbg, file_name, DW_DLA_STRING);
                }
            }
            xed_uint32_t gfn = (xed_uint32_t) (xed_addr_t) avl_find(
                                                  &file_name_table, file_num);
            line_number_entry_t* p =
                 (line_number_entry_t*)malloc(sizeof(line_number_entry_t));
            line_number_entry_init(p, line_num, gfn);
            avl_insert(&line_number_table, line_addr, p, 1);

        } /* for */
        avl_tree_clear(&file_name_table,0);
        dwarf_srclines_dealloc(dbg, line_buf, line_count);
        dwarf_dealloc(dbg, cu_die, DW_DLA_DIE);
    }  /* while */
    dwarf_finish(dbg, 0);
    elf_end(elf);
}

#endif
////////////////////////////////////////////////////////////////////////////


char* 
lookup32(Elf32_Word stoffset,
         void* start,
         unsigned int len,
         Elf32_Off offset)
{
    char* p = (char*)start + offset;
    char* q = p + stoffset;
    if ((unsigned char*)q >= (unsigned char*)start+len)
        return 0;
    if ((unsigned char*)q < (unsigned char*)start)
      return 0;
    return q;
}

char* 
lookup64(Elf64_Word stoffset,
	 void* start,
         unsigned int len,
	 Elf64_Off offset)
{
  char* p = (char*)start + offset;
  char* q = p + stoffset;
  if ((unsigned char*)q >= (unsigned char*)start+len)
      return 0;
  if ((unsigned char*)q < (unsigned char*)start)
      return 0;
  return q;
}

void xed_disas_elf_init(void) {
    xed_register_disassembly_callback(xed_disassembly_callback_function);
}



void
disas_test32(xed_disas_info_t* fi,
	     void* start,
             unsigned int length,
	     Elf32_Off offset,
	     Elf32_Word size, 
             Elf32_Addr runtime_vaddr,
             xed_symbol_table_t* symbol_table)
{
  unsigned char* hard_limit = (unsigned char*)start + length;

  fi->s =  (unsigned char*)start;
  fi->a = (unsigned char*)start + offset;
  if (fi->a >  hard_limit)
      fi->a = hard_limit;
  if ((void*)(fi->a) < start) {
      fprintf(stderr,"# malformed region limit. stopping\n");
      exit(1);
  }
  fi->q = fi->a + size; // end of region
  if (fi->q > hard_limit)
      fi->q = hard_limit;

  fi->runtime_vaddr = runtime_vaddr + fi->fake_base;
  fi->runtime_vaddr_disas_start = fi->addr_start;
  fi->runtime_vaddr_disas_end = fi->addr_end;
  fi->symfn = get_symbol;
  fi->caller_symbol_data = symbol_table;
  fi->line_number_info_fn = 0;
#if defined(XED_DWARF)
  fi->line_number_info_fn = find_line_number_info;
#endif
  // pass in a function to retrieve valid symbol names
  xed_disas_test(fi);
}

static void
disas_test64(xed_disas_info_t* fi,
	     void* start,
             unsigned int length,
	     Elf64_Off offset,
	     Elf64_Xword size,
             Elf64_Addr runtime_vaddr,
             xed_symbol_table_t* symbol_table)
{
  unsigned char* hard_limit = (unsigned char*)start + length;
  fi->s =  (unsigned char*)start;

  fi->a = (unsigned char*)start + offset;
  if (fi->a >  hard_limit)
      fi->a = hard_limit;
  if ((void*)(fi->a) < start) {
      fprintf(stderr,"# malformed region limit. stopping\n");
      exit(1);
  }
  
  fi->q = fi->a + size; // end of region
  if (fi->q > hard_limit)
      fi->q = hard_limit;
  
  fi->runtime_vaddr = runtime_vaddr + fi->fake_base;
  fi->runtime_vaddr_disas_start = fi->addr_start;
  fi->runtime_vaddr_disas_end = fi->addr_end;
  fi->symfn = get_symbol;
  fi->caller_symbol_data = symbol_table;

  fi->line_number_info_fn = 0;
#if defined(XED_DWARF)
  fi->line_number_info_fn = find_line_number_info;
#endif
  // pass in a function to retrieve valid symbol names
  xed_disas_test(fi);
}

#if !defined(EM_IAMCU)  
# define EM_IAMCU 3
#endif

static int check_binary_32b(void* start) {
    Elf32_Ehdr* elf_hdr = (Elf32_Ehdr*) start;
    if ( elf_hdr->e_machine == EM_386   ||
         elf_hdr->e_machine == EM_IAMCU )  
        return 1;
    return 0;
}

static int range_check(void* p, unsigned int esize, void* start, void* end)  {
    if (p < start || (unsigned char*)p+esize > (unsigned char*)end)
        return 1;
    return 0;
}

void
process_elf32(xed_disas_info_t* fi,
              void* start,
	      unsigned int length,
              xed_symbol_table_t* symbol_table)
{
    Elf32_Ehdr* elf_hdr = (Elf32_Ehdr*) start;
    Elf32_Off shoff = elf_hdr->e_shoff;  // section hdr table offset
    Elf32_Shdr* shp = (Elf32_Shdr*) ((char*)start + shoff);
    int sect_strings  = elf_hdr->e_shstrndx;
    xed_uint_t nsect = elf_hdr->e_shnum;
    xed_uint_t i;
    unsigned char* hard_limit = (unsigned char*)start + length;

    if ((void*)shp < start)
        return;
            
    for(i=0;i<nsect;i++) {
        char* name;
        xed_bool_t text = 0;
        
        if (range_check(shp+i, sizeof(Elf32_Shdr), start, hard_limit))
            break;
        if (range_check(shp+sect_strings, sizeof(Elf32_Shdr), start, hard_limit))
            break;
                
        name = lookup32(shp[i].sh_name, start,  length,
                        shp[sect_strings].sh_offset);

        if (shp[i].sh_type == SHT_PROGBITS) {
            if (fi->target_section) {
                if (name && strcmp(fi->target_section, name)==0) 
                    text = 1;
            }
            else if (shp[i].sh_flags & SHF_EXECINSTR)
                text = 1;
        }

        if (text && name) {
            if (fi->xml_format == 0) {
                printf("# SECTION " XED_FMT_D " ", i);
                printf("%25s ", name);
                printf("addr " XED_FMT_LX " ",
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_addr)); 
                printf("offset " XED_FMT_LX " ",
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_offset));
                printf("size " XED_FMT_LU " ", 
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_size));
                printf("type " XED_FMT_LU "\n", 
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_type));
            }

            xst_set_current_table(symbol_table,i);
            disas_test32(fi,
                         start, length,  shp[i].sh_offset, shp[i].sh_size,
                         shp[i].sh_addr,
                         symbol_table);

	}

    }
}

/*-----------------------------------------------------------------*/

int check_binary_64b(void* start) {
#if !defined(EM_X86_64)  /* EM_X86_64 is not present on android */
# define EM_X86_64 62
#endif
#if !defined(EM_L1OM) /* Oh, not zero */
# define EM_L1OM  180
#endif
#if !defined(EM_K1OM) /* Oh, not zero */
# define EM_K1OM  181
#endif

    Elf64_Ehdr* elf_hdr = (Elf64_Ehdr*) start;
    if (elf_hdr->e_machine == EM_X86_64 ||
        elf_hdr->e_machine == EM_L1OM ||
        elf_hdr->e_machine == EM_K1OM) 
        return 1;
    return 0;
}


/*-----------------------------------------------------------------*/
void
process_elf64(xed_disas_info_t* fi,
              void* start,
	      unsigned int length,
              xed_symbol_table_t* symbol_table)
{
    Elf64_Ehdr* elf_hdr = (Elf64_Ehdr*) start;
    Elf64_Off shoff = elf_hdr->e_shoff;  // section hdr table offset
    Elf64_Shdr* shp = (Elf64_Shdr*) ((char*)start + shoff);
    Elf64_Half sect_strings  = elf_hdr->e_shstrndx;
    Elf64_Half nsect = elf_hdr->e_shnum;
    unsigned char* hard_limit = (unsigned char*)start + length;
    unsigned int i;
    xed_bool_t text = 0;

    if (CLIENT_VERBOSE1) 
        printf("# sections %d\n" , nsect);
    
    if ((void*)shp < start)
        return;

    for( i=0;i<nsect;i++)  {
        char* name = 0;
        
        if (range_check(shp+i,sizeof(Elf64_Shdr), start, hard_limit))
            break;
        if (range_check(shp+sect_strings,sizeof(Elf64_Shdr), start, hard_limit))
            break;
        
        name = lookup64(shp[i].sh_name, start, length,
                        shp[sect_strings].sh_offset);
        
        text = 0;
        if (shp[i].sh_type == SHT_PROGBITS) {
            if (fi->target_section) {
                if (name && strcmp(fi->target_section, name)==0) 
                    text = 1;
            }
            else if (shp[i].sh_flags & SHF_EXECINSTR)
                text = 1;
        }

        if (text && name) {
            if (fi->xml_format == 0) {
                printf("# SECTION " XED_FMT_U " ", i);
                printf("%25s ", name);
                printf("addr " XED_FMT_LX " ",
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_addr)); 
                printf("offset " XED_FMT_LX " ",
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_offset));
                printf("size " XED_FMT_LU "\n", 
                       XED_STATIC_CAST(xed_uint64_t,shp[i].sh_size));
            }
            xst_set_current_table(symbol_table,i);
            disas_test64(fi, 
                         start, length, shp[i].sh_offset, shp[i].sh_size, 
                         shp[i].sh_addr, symbol_table);
        }
    }
}


void read_symbols64(void* start,
                    unsigned int len,
                    Elf64_Off offset,
                    Elf64_Xword size,
                    Elf64_Off string_table_offset,
                    xed_symbol_table_t* symtab)
{
    char* a = XED_STATIC_CAST(char*,start);
    Elf64_Sym* p = XED_STATIC_CAST(Elf64_Sym*,a + offset);
    Elf64_Sym* q = XED_STATIC_CAST(Elf64_Sym*,a + offset + size);
    unsigned char* hard_limit = (unsigned char*)start + len;
    if ((void*)p < start)
        return;
    if ((unsigned char*) p + sizeof(Elf64_Sym) > hard_limit)
        p =  (Elf64_Sym*)hard_limit;
    if ((unsigned char*) q > hard_limit)
        q =  (Elf64_Sym*)hard_limit;
    while(p<q) {
        if (ELF64_ST_TYPE(p->st_info) == STT_FUNC) {
            char* name = lookup64(p->st_name, start, len, string_table_offset);
            if (name && xed_strlen(name) > 0) {
                xst_add_local_symbol(
                    symtab,
                    XED_STATIC_CAST(xed_uint64_t,p->st_value), 
                    name, p->st_shndx);
            }
        }
        p++; 
    }
}


/*-----------------------------------------------------------------*/

static void print_comment64(unsigned int i, Elf64_Shdr* shp, char const* const s)
{
    fprintf(stdout,"# Found %s: %u",s, i);
    // NOTE: casts required here because android gcc4.8.0 uses long long
    // int for 64b integer and android-5 gcc490 uses long int.
    fprintf(stdout," offset " XED_FMT_LX, (xed_uint64_t) shp[i].sh_offset);
    fprintf(stdout," size " XED_FMT_LX "\n", (xed_uint64_t) shp[i].sh_size);
}
static void print_comment32(unsigned int i, Elf32_Shdr* shp, char const* const s)
{
    fprintf(stdout,"# Found %s: %u",s,i);
    fprintf(stdout," offset %u",shp[i].sh_offset);
    fprintf(stdout," size %u\n", shp[i].sh_size);
}



static void
symbols_elf64(xed_disas_info_t* fi, 
              void* start,
              unsigned int len,
              xed_symbol_table_t* symtab) {
    Elf64_Ehdr* elf_hdr = (Elf64_Ehdr*) start;
    Elf64_Off shoff = elf_hdr->e_shoff;  // section hdr table offset
    Elf64_Shdr* shp = (Elf64_Shdr*) ((char*)start + shoff);
    Elf64_Half nsect = elf_hdr->e_shnum;
    if (CLIENT_VERBOSE1) 
        printf("# sections %d\n" , nsect);
    unsigned int i;
    Elf64_Half sect_strings  = elf_hdr->e_shstrndx;
    Elf64_Off string_table_offset=0;
    Elf64_Off dynamic_string_table_offset=0;
    unsigned char* hard_limit = (unsigned char*)start + len;

    /* find the string_table_offset and the dynamic_string_table_offset */
    if ((void*)shp < start)
        return;
    
    for( i=0;i<nsect;i++)  {
        if (range_check(shp+i, sizeof(Elf64_Shdr), start, hard_limit)) {
            break;
        }
        if (shp[i].sh_type == SHT_STRTAB) {
            if (range_check(shp+sect_strings, sizeof(Elf64_Shdr),
                            start, hard_limit)) {
                break;
            }
            char* name = lookup64(shp[i].sh_name, start, len,
                                  shp[sect_strings].sh_offset);
            if (name)
            {
                if (strcmp(name,".strtab")==0) {
                    if (fi->xml_format == 0) {
                        print_comment64(i,shp, "strtab");
                    }
                    string_table_offset = shp[i].sh_offset;
                }
                if (strcmp(name,".dynstr")==0) {
                    if (fi->xml_format == 0) {
                        print_comment64(i,shp, "dynamic strtab");
                    }
                    dynamic_string_table_offset = shp[i].sh_offset;
                }
            }
        }
    }
    /* now read the symbols */
    for( i=0;i<nsect;i++)  {
        if (range_check(shp+i, sizeof(Elf64_Shdr), start, hard_limit))
            break;

        if (shp[i].sh_type == SHT_SYMTAB && string_table_offset) {
            if (fi->xml_format == 0) {
                print_comment64(i,shp, "symtab");
            }
            read_symbols64(start, len, shp[i].sh_offset, shp[i].sh_size, 
                           string_table_offset,symtab);
        }
        else if (shp[i].sh_type == SHT_DYNSYM && dynamic_string_table_offset) {
            if (fi->xml_format == 0) {
                print_comment64(i,shp, "dynamic symtab");
            }
            read_symbols64(start, len, shp[i].sh_offset, shp[i].sh_size,
                           dynamic_string_table_offset, symtab);
        }
    }
}



static void
read_symbols32(void* start,
               unsigned int len,
                    Elf32_Off offset,
                    Elf32_Word size,
                    Elf32_Off string_table_offset,
                    xed_symbol_table_t* symtab) {
    char* a = XED_STATIC_CAST(char*,start);
    Elf32_Sym* p = XED_STATIC_CAST(Elf32_Sym*,a + offset);
    Elf32_Sym* q = XED_STATIC_CAST(Elf32_Sym*,a + offset + size);
    
    unsigned char* hard_limit = (unsigned char*)start + len;
    if ((void*)p < start)
        return;
    
    if ((unsigned char*) p + sizeof(Elf32_Sym) > hard_limit)
        p =  (Elf32_Sym*)hard_limit;
    if ((unsigned char*) q > hard_limit)
        q =  (Elf32_Sym*)hard_limit;

    while(p<q) {
        if (ELF32_ST_TYPE(p->st_info) == STT_FUNC) {
            char* name = lookup32(p->st_name, start, len, string_table_offset);
            if (name && xed_strlen(name) > 0) {
                xst_add_local_symbol(
                    symtab,
                    XED_STATIC_CAST(xed_uint64_t,p->st_value), 
                    name, p->st_shndx);
            }
        }
        p++; 
    }
}



static void
symbols_elf32(xed_disas_info_t* fi, 
              void* start,
              unsigned int len,
              xed_symbol_table_t* symtab)
{
    Elf32_Ehdr* elf_hdr = (Elf32_Ehdr*) start;
    Elf32_Off shoff = elf_hdr->e_shoff;  // section hdr table offset
    Elf32_Shdr* shp = (Elf32_Shdr*) ((char*)start + shoff);
    Elf32_Half nsect = elf_hdr->e_shnum;
    if (CLIENT_VERBOSE1) 
        printf("# sections %d\n" , nsect);
    unsigned int i;
    Elf32_Off string_table_offset=0;
    Elf32_Off dynamic_string_table_offset=0;
    int sect_strings  = elf_hdr->e_shstrndx;
    unsigned char* hard_limit = (unsigned char*)start + len;

    if ((void*)shp < start)
        return;

    /* find the string_table_offset and the dynamic_string_table_offset */
    for( i=0;i<nsect;i++)  {
        if (range_check(shp+i, sizeof(Elf32_Shdr), start, hard_limit))
            break;
        if (shp[i].sh_type == SHT_STRTAB) {
            if (range_check(shp+sect_strings, sizeof(Elf32_Shdr),
                            start, hard_limit))
                break;
            char* name = lookup32(shp[i].sh_name, start,  len,
                                  shp[sect_strings].sh_offset);
            if (name)
            {
                if (strcmp(name,".strtab")==0) {
                    if (fi->xml_format == 0) {
                        print_comment32(i,shp, "strtab");
                    }
                    string_table_offset = shp[i].sh_offset;
                }
                if (strcmp(name,".dynstr")==0) {
                    if (fi->xml_format == 0) {
                        print_comment32(i,shp, "dynamic strtab");
                    }
                    dynamic_string_table_offset = shp[i].sh_offset;
                }
            }
        }
    }

    /* now read the symbols */
    for( i=0;i<nsect;i++)  {
        if (range_check(shp+i, sizeof(Elf32_Shdr), start, hard_limit))
            break;
        
        if (shp[i].sh_type == SHT_SYMTAB && string_table_offset) {
            if (fi->xml_format == 0) {
                print_comment32(i,shp, "symtab");
            }
            read_symbols32(start, len, shp[i].sh_offset, shp[i].sh_size, 
                           string_table_offset, symtab);
        } 
        else if (shp[i].sh_type == SHT_DYNSYM && dynamic_string_table_offset)
        {
            if (fi->xml_format == 0) {
                print_comment32(i,shp, "dynamic symtab");
            }
            read_symbols32(start, len, shp[i].sh_offset, shp[i].sh_size,
                           dynamic_string_table_offset, symtab);
        }
    }
}


void
xed_disas_elf(xed_disas_info_t* fi) 
{
    void* region = 0;
    unsigned int len = 0;
    xed_symbol_table_t symbol_table;
    
    xed_disas_elf_init();
    xed_map_region(fi->input_file_name, &region, &len);
    xed_symbol_table_init(&symbol_table);

#if defined(XED_DWARF)
    if (fi->line_numbers)
        read_dwarf_line_numbers(region,len);
#endif
    
    if (check_binary_64b(region)) {
        if (fi->sixty_four_bit == 0 && fi->use_binary_mode) {
            /* modify the default dstate values because we were not expecting a
             * 64b binary */
            fi->dstate.mmode =  XED_MACHINE_MODE_LONG_64;
        }

        symbols_elf64(fi,region, len,  &symbol_table);
        process_elf64(fi, region, len, &symbol_table);
    }
    else if (check_binary_32b(region)) {
        symbols_elf32(fi, region, len,  &symbol_table);
        process_elf32(fi, region, len, &symbol_table);
    }
    else {
        fprintf(stderr,"Not a recognized 32b or 64b ELF binary.\n");
        exit(1);
    }
    if (fi->xml_format == 0){
        xed_print_decode_stats(fi);
        xed_print_encode_stats(fi);
    }
}
 


#endif
////////////////////////////////////////////////////////////////////////////

