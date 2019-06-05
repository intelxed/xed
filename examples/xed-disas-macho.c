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
/// @file xed-disas-macho.cpp

#include "xed/xed-interface.h" // to get defines
#if defined(__APPLE__) && defined(XED_DECODER)

// mac specific headers
#include <mach-o/fat.h>
#include <mach-o/loader.h>
#include <mach-o/stab.h>
#include <mach-o/nlist.h>

#include "xed-disas-macho.h"
#include "xed-examples-util.h"
#include "xed-symbol-table.h"

#include <string.h>

////////////////////////////////////////////////////////////////////////////

xed_uint32_t 
swap_endian(xed_uint32_t x)
{
    xed_uint32_t r = 0;
    xed_uint32_t t = x;
    xed_uint_t i; 
    for(i=0;i<4;i++)
    {
        xed_uint8_t b = (xed_uint8_t) (t&0xFF);
        r =(r << 8)  | b;
        t = t >> 8;
    }
    return r;
}

xed_uint32_t
read_fat_header_narch(xed_uint8_t const* const current_position)
{
    struct fat_header* fh =
        XED_CAST(struct fat_header*,current_position);
    
    // we are little endian looking at big endian data
    if (fh->magic == FAT_CIGAM)
    {
        xed_uint32_t narch = swap_endian(fh->nfat_arch);
        return narch;
    }
    return 0;
}

xed_bool_t
read_fat_header(xed_uint8_t const* const current_position,
                xed_uint32_t fat_arch_slot,
                xed_uint32_t* offset,
                xed_uint32_t* size)
{
    struct fat_header* fh =
        XED_CAST(struct fat_header*,current_position);
    
    // we are little endian looking at big endian data
    if (fh->magic == FAT_CIGAM)
    {
        struct fat_arch* fa = 
            XED_CAST(struct fat_arch*,current_position + 
                                 sizeof(struct fat_header) + 
                                 fat_arch_slot*sizeof(struct fat_arch) );
        const cpu_type_t cpu_type = (cpu_type_t) swap_endian((xed_uint32_t)fa->cputype);
        
        if ((cpu_type & CPU_TYPE_I386) != 0)
        {
            if ((cpu_type & CPU_ARCH_ABI64) != 0)
                printf ("# x86 64b\n");
            else
                printf ("# x86 32b\n");
            *offset = swap_endian(fa->offset);   
            *size   = swap_endian(fa->size);   
            return 1;
        }
    }
    return 0;
}


static xed_bool_t 
executable(xed_uint32_t flags)
{
    return ( (flags & S_ATTR_PURE_INSTRUCTIONS) !=0  || 
             (flags & S_ATTR_SOME_INSTRUCTIONS) !=0  );
}

void
process_segment32( xed_uint_t* sectoff,
                   xed_disas_info_t* decode_info,
                   xed_uint8_t* start,
                   xed_uint8_t* segment_position,
                   unsigned int bytes,
                   xed_symbol_table_t* symbol_table,
                   xed_uint64_t vmaddr)
{
    struct segment_command* sc =
        XED_CAST(struct segment_command*,segment_position);
    xed_uint8_t* start_of_section_data =
        segment_position + sizeof(struct segment_command);
    unsigned int i;
    // look through the array of section headers for this segment.
    for( i=0; i< sc->nsects;i++)
    {
        struct section* sp = 
            XED_CAST(struct section*,
                         start_of_section_data + i *sizeof(struct section));
        
        if (executable(sp->flags))
        {
            // this section is executable. Go get it and process it.
            xed_uint8_t* section_text = start + sp->offset;
            xed_uint32_t runtime_vaddr = sp->addr;

          decode_info->s = start;
          decode_info->a = section_text;
          decode_info->q = section_text + sp->size;
          decode_info->runtime_vaddr = runtime_vaddr + decode_info->fake_base;
          decode_info->runtime_vaddr_disas_start = (xed_uint64_t)decode_info->addr_start;
          decode_info->runtime_vaddr_disas_end = (xed_uint64_t)decode_info->addr_end;
          decode_info->symfn = get_symbol;
          decode_info->caller_symbol_data = symbol_table;
          decode_info->input_file_name   = decode_info->input_file_name;
          decode_info->line_number_info_fn = 0;
          xst_set_current_table(symbol_table,i+1 + *sectoff);
          xed_disas_test(decode_info);

        }
    }
    *sectoff += sc->nsects;
    (void) bytes; (void) vmaddr;
}


void
process_segment64( xed_uint_t* sectoff,
                   xed_disas_info_t* decode_info,
                   xed_uint8_t* start,
                   xed_uint8_t* segment_position,
                   unsigned int bytes,
                   xed_symbol_table_t* symbol_table,
                   xed_uint64_t vmaddr)
{
    struct segment_command_64* sc = 
        XED_CAST(struct segment_command_64*,segment_position);
    xed_uint8_t* start_of_section_data = 
        segment_position + sizeof(struct segment_command_64);
    unsigned int i;
    /* modify the default dstate values because we were not expecting a
     * 64b binary */
    decode_info->dstate.mmode = XED_MACHINE_MODE_LONG_64;
    // look through the array of section headers for this segment.
    for( i=0; i< sc->nsects;i++)
    {
        struct section_64* sp = 
            XED_CAST(struct section_64*,
                    start_of_section_data + i *sizeof(struct section_64));
        if (executable(sp->flags))
        {

            // this section is executable. Go get it and process it.
            xed_uint8_t* section_text = start + sp->offset;
            xed_uint64_t runtime_vaddr = sp->addr;

          decode_info->s = start;
          decode_info->a = section_text;
          decode_info->q = section_text + sp->size;
          decode_info->runtime_vaddr = runtime_vaddr + decode_info->fake_base;
          decode_info->runtime_vaddr_disas_start = (xed_uint64_t)decode_info->addr_start;
          decode_info->runtime_vaddr_disas_end = (xed_uint64_t)decode_info->addr_end;
          decode_info->symfn = get_symbol;
          decode_info->caller_symbol_data = symbol_table;
          decode_info->input_file_name   = decode_info->input_file_name;
          decode_info->line_number_info_fn = 0;
          xst_set_current_table(symbol_table,i + 1 + *sectoff);
          xed_disas_test(decode_info);

        }

    }
    *sectoff += sc->nsects;
    (void) bytes; (void) vmaddr;
}

////////////////////////////////////////////////////////////////////////////


void process_symbols32(xed_disas_info_t* decode_info,
		       xed_uint8_t* pos,
                       xed_uint8_t* current_position,
                       xed_symbol_table_t* symbol_table) {
    struct symtab_command* symtab  =
        XED_CAST(struct symtab_command*,current_position);
    /* symbols */
    xed_uint32_t nsyms = symtab->nsyms;
    xed_uint8_t* symoff = pos + symtab->symoff;
    /* strings table */
    xed_uint8_t* stroff = pos + symtab->stroff;
    /* xed_uint8_t* stroff_end = stroff + symtab->strsize; */
    xed_uint32_t i;
    struct nlist* p;
    p = XED_CAST(struct nlist*, symoff);
    for(i=0;i<nsyms;i++) {
        if ((p->n_type & N_STAB) == 0 &&
            (p->n_type & N_TYPE) == N_SECT)
        {
            char* str=0;
            str = XED_CAST(char*,stroff + p->n_un.n_strx);

            xst_add_local_symbol(
                symbol_table,
                XED_CAST(xed_uint64_t,p->n_value), 
                str,
                p->n_sect);
        }
        p++;
    }
    (void)decode_info;
}

void process_symbols64(xed_disas_info_t* decode_info,
		       xed_uint8_t* pos,
                       xed_uint8_t* current_position,
                       xed_symbol_table_t* symbol_table) {
    struct symtab_command* symtab  =
        XED_CAST(struct symtab_command*,current_position);
    /* symbols */
    xed_uint32_t nsyms = symtab->nsyms;
    xed_uint8_t* symoff = pos + symtab->symoff;
    /* strings table */
    xed_uint8_t* stroff = pos + symtab->stroff;
    xed_uint32_t i;
    struct nlist_64* p;
    
    p = XED_CAST(struct nlist_64*, symoff);
    for(i=0;i<nsyms;i++)
    {
        if ((p->n_type & N_STAB) == 0 &&
            (p->n_type & N_TYPE) == N_SECT)
        {
            char* str=0;
            str = XED_CAST(char*,stroff + p->n_un.n_strx);

            xst_add_local_symbol(
                symbol_table,
                XED_CAST(xed_uint64_t,p->n_value), 
                str,
                p->n_sect);
        }
        p++;
    }
    (void)decode_info;
}


void process32(xed_disas_info_t* decode_info,
               xed_uint8_t* current_position,
               struct mach_header* mh,
               xed_uint8_t* pos)
{
    xed_symbol_table_t symbol_table;
    xed_uint_t i, sectoff=0;
    if (CLIENT_VERBOSE2)
        printf("Number of load command sections = %d\n", mh->ncmds);
    // load commands point to segments which contain sections.
    decode_info->dstate.mmode = XED_MACHINE_MODE_LEGACY_32;
    xed_uint8_t* tmp_current_position = current_position;
    xed_symbol_table_init(&symbol_table);

    for( i=0;i< mh->ncmds; i++)    {
        struct load_command* lc = 
            XED_CAST(struct load_command*,tmp_current_position);
        // FIXME: not handling LD_DYSYMTAB
        if (lc->cmd == LC_SYMTAB) {
            process_symbols32(decode_info,
                              pos,
                              tmp_current_position,
                              &symbol_table);
        }
        tmp_current_position += lc->cmdsize;
    }

    for(i=0;i< mh->ncmds; i++)    {
        struct load_command* lc = 
            XED_CAST(struct load_command*,current_position);

        if (CLIENT_VERBOSE2)
            printf("load command %d\n", i);
        if (lc->cmd == LC_SEGMENT)    {
            if (CLIENT_VERBOSE2)
                printf("\tload command %d is a LC_SEGMENT\n", i);
            // we add the FAT offset to the start pointer to get to the
            // relative start point.
            struct segment_command* sc =
                XED_CAST(struct segment_command*,lc);
            process_segment32( &sectoff,
                               decode_info,
                               pos,
                               current_position,
                               lc->cmdsize ,
                               &symbol_table,
                               sc->vmaddr);
        }
        current_position += lc->cmdsize;
    }
}
void process64(xed_disas_info_t* decode_info,
               xed_uint8_t* current_position,
               struct mach_header_64* mh,
               xed_uint8_t* pos)
{

    xed_uint_t i, sectoff=0;
    xed_symbol_table_t symbol_table;
    if (CLIENT_VERBOSE2)
        printf("Number of load command sections = %d\n", mh->ncmds);
    // load commands point to segments which contain sections.
    xed_uint8_t* tmp_current_position = current_position;
    xed_symbol_table_init(&symbol_table);

    for( i=0;i< mh->ncmds; i++)    {
        struct load_command* lc = 
            XED_CAST(struct load_command*,tmp_current_position);
        // FIXME: not handling LD_DYSYMTAB
        if ( lc->cmd == LC_SYMTAB ) {
            process_symbols64(decode_info,
                              pos,
                              tmp_current_position,
                              &symbol_table);
        }
        tmp_current_position += lc->cmdsize;
    }

    for( i=0;i< mh->ncmds; i++)  {
        struct load_command* lc = 
            XED_CAST(struct load_command*,current_position);
        
        if (CLIENT_VERBOSE2)
            printf("load command %x\n", i);
        if (lc->cmd == LC_SEGMENT_64)    {
            if (CLIENT_VERBOSE2)
                printf("\tload command %d is a LC_SEGMENT\n", i);
            // we add the FAT offset to the start pointer to get to the
            // relative start point.
            struct segment_command_64* sc =
                XED_CAST(struct segment_command_64*,lc);
            process_segment64( &sectoff,
                               decode_info,
                               pos,
                               current_position,
                               lc->cmdsize,
                               &symbol_table,
                               sc->vmaddr );
        }
        current_position += lc->cmdsize;
    }
}


void
process_macho(xed_uint8_t* start,
              unsigned int length, // FIXME: Use this! Trusting internal consistency of headers
              xed_disas_info_t* decode_info)

{
    xed_uint8_t* base_pos  = start;
    xed_uint32_t narch = read_fat_header_narch(base_pos);
    xed_uint32_t fat_arch_slot=0;

    xed_uint32_t lim = 1;
    
    // we have one section if not a fat binary.
    if (narch > lim)
        lim = narch;

    for (fat_arch_slot = 0; fat_arch_slot < lim; fat_arch_slot++)
    {
        xed_uint32_t offset=0;
        xed_uint32_t size;
        xed_bool_t okay = 0;

        if (narch)  // for fat binaries
            okay = read_fat_header(base_pos, fat_arch_slot, &offset, &size);

        if (CLIENT_VERBOSE2 && !okay)
            if (decode_info->xml_format == 0)
                xedex_dwarn("Could not find x86 section of fat binary "
                            "-- checking for mach header");
        if (CLIENT_VERBOSE2)
            printf("Offset of load sections = %x\n", offset);

        xed_uint8_t* current_position = base_pos + offset;

        if (narch > 0) 
            printf("# FAT ARCH SECTION = %d\n", fat_arch_slot);
        struct mach_header* mh =
            XED_CAST(struct mach_header*,current_position);
        struct mach_header_64* mh64 =
            XED_CAST(struct mach_header_64*,current_position);
        if (mh->magic == MH_MAGIC) {
            current_position += sizeof(struct mach_header);
            process32(decode_info,
                      current_position,
                      mh,
                      start+offset);
        }
        else if (mh64->magic == MH_MAGIC_64) {
            current_position += sizeof(struct mach_header_64);
            process64(decode_info,
                      current_position,
                      mh64,
                      start+offset);
        }
        else   
            xedex_derror("Could not find mach header");
      } // for

    (void) length;
}

void xed_disas_macho_init(void) {
    xed_register_disassembly_callback(xed_disassembly_callback_function);
}


void
xed_disas_macho(xed_disas_info_t* fi)
{
    xed_uint8_t* region = 0;
    void* vregion = 0;
    unsigned int len = 0;

    xed_disas_macho_init();
    xed_map_region(fi->input_file_name, &vregion, &len);

    region = XED_CAST(xed_uint8_t*,vregion);
    process_macho(region, len, fi); 
    if (fi->xml_format == 0)
        xed_print_decode_stats(fi);
}
 


#endif
