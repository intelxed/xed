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
/// @file xed-disas-pecoff.cpp

//// ONLY COMPILES IF -mno-cygwin is thrown on to GCC compilations
extern "C" {
#include "xed/xed-interface.h"  // for XED_DECODER
}
#if defined(XED_DECODER)
#include <cassert>
#include <cstdio>

#if defined(XED_MSVC8_OR_LATER) && !defined(XED_64B)
    // to enable the wow64 redirection function on MSVC8
#   define  _WIN32_WINNT 0x0501
#endif
#include <windows.h>
#include <winnt.h>

// xed headers -- THESE MUST BE AFTER THE WINDOWS HEADERS

extern "C" {
#include "xed-disas-pecoff.h" 

// This really must be after the windows.h include
#include "xed-symbol-table.h"
}

#if defined(XED_DBGHELP)
# include "udhelp.H" // dbghelp interface
#endif
using namespace std;

static void
windows_error(const char* syscall, 
              const char* filename)
{
  printf("Mapped file:: %s",syscall);
  printf(" for file %s failed: ", filename);
  switch (GetLastError())
    {
    case 2:
      printf("File not found");
      break;
    case 3:
      printf("Path not found");
      break;
    case 5:
      printf("Access denied");
      break;
    case 15:
      printf("Invalid drive");
      break;
    default:
      printf("error code %u",
             XED_STATIC_CAST(xed_uint32_t,GetLastError()));
      break;
    }
  xedex_derror("Exiting.");
}

typedef int (WINAPI *fptr_t)(void*);

static fptr_t find_fn_ptr(const char* function_name)  {
   fptr_t p;

   p = (fptr_t) GetProcAddress(
                   GetModuleHandle(TEXT("kernel32.dll")), 
                   function_name);
   return p;
}

static int find_wow64_redir(fptr_t* disable, fptr_t* revert) {
   *disable = find_fn_ptr("Wow64DisableWow64FsRedirection");
   *revert  = find_fn_ptr("Wow64RevertWow64FsRedirection");
   if (*disable && *revert)
       return 1; // success
   return 0;
}

class pecoff_reader_t
{
  /// NT handle for the open file.
  void* file_handle_;

  /// NT handle for the memory mapping.
  void* map_handle_;

  void* base_;
  xed_bool_t okay_;
  xed_bool_t sixty_four_bit_;

  const IMAGE_FILE_HEADER* ifh;
  const IMAGE_SECTION_HEADER* hdr;
  const IMAGE_SECTION_HEADER* orig_hdr;
  unsigned int nsections;
  xed_uint64_t image_base;
  xed_bool_t verbose;


public:
  xed_uint32_t section_index;

  pecoff_reader_t(int arg_verbose=1)
  {
    verbose = arg_verbose;
    init();
  }
  ~pecoff_reader_t()
  {
    close();
  }

  void* base() const { return base_; }
  xed_bool_t okay() const { return okay_; }
  xed_bool_t sixty_four_bit() const { return sixty_four_bit_; }

  void
  init()
  {
    file_handle_ = INVALID_HANDLE_VALUE;
    map_handle_ = INVALID_HANDLE_VALUE;
    okay_ = false;
    sixty_four_bit_ = false;
    
    hdr=0;
    orig_hdr=0;
    nsections=0;
    image_base=0;
    section_index=0;
  }

  void
  close()
  {
    if (base_)
      {
        UnmapViewOfFile(base_);
      }
    if (map_handle_ != INVALID_HANDLE_VALUE)
      {
        CloseHandle(map_handle_);
      }
    if (file_handle_ != INVALID_HANDLE_VALUE)
      {
        CloseHandle(file_handle_);
      }
        
    init();
  }


  xed_bool_t
  map_region(const char* input_file_name, 
             void*& vregion,
             xed_uint32_t& len)
  {
    okay_ = false;

#if defined(XED_MSVC8_OR_LATER) && !defined(XED_64B)
    bool disabled_redirection = false;
    void* old=0;
    fptr_t disable, revert;
    if (find_wow64_redir(&disable, &revert))
        if ( (*disable)(&old) ) 
            disabled_redirection = true;
#endif

    file_handle_ = CreateFileA(input_file_name,
                              GENERIC_READ,
                              FILE_SHARE_READ,
                              NULL,
                              OPEN_EXISTING,
                              FILE_FLAG_NO_BUFFERING + FILE_ATTRIBUTE_READONLY,
                              NULL);

#if defined(XED_MSVC8_OR_LATER) && !defined(XED_64B)
    if (disabled_redirection) {
      if (! (*revert)(old)) {
          fprintf(stderr,"Could not re-enable wow64 redirection. Dying...\n");
          exit(1);
      }
    }
#endif
    if (file_handle_ == INVALID_HANDLE_VALUE)  {
      windows_error("CreateFile", input_file_name);
    }

    map_handle_ = CreateFileMapping(file_handle_,
                                    NULL,
                                    PAGE_READONLY,
                                    0,
                                    0,
                                    NULL);

    if (map_handle_ == INVALID_HANDLE_VALUE)   {
      windows_error("CreateFileMapping", input_file_name);
    }

    base_ = MapViewOfFile(map_handle_,
                          FILE_MAP_READ, 0, 0, 0);
    if (base_ != NULL)   {
      okay_ = true;
      vregion = base_;
      len = 0; //FIXME
      return true;
    }
    CloseHandle(map_handle_);
    map_handle_ = INVALID_HANDLE_VALUE;
        
    CloseHandle(file_handle_);
    file_handle_ = INVALID_HANDLE_VALUE;
    return false;

  }


  xed_bool_t read_header() {
    if (! parse_nt_file_header(&nsections, &image_base, &hdr)) {
      xedex_derror("Could not read nt file header");
      return false;
    }

    orig_hdr=hdr;
    return true;
  }


  void read_coff_symbols() {
      xed_uint32_t i;
      xed_uint32_t sym_offset = ifh->PointerToSymbolTable;
      xed_uint32_t nsym = ifh->NumberOfSymbols;
      PIMAGE_SYMBOL p = (PIMAGE_SYMBOL)((char*)base() + sym_offset);
      char* string_table_base = (char*)(p+nsym);
      for(i=0;i<nsym;i++) {
          printf("%5d: ", (int)i);
          printf(" Value: %08x", (int) p[i].Value);
          printf(" Section: %4d", p[i].SectionNumber);
          printf(" Type: %04x", p[i].Type);
          printf(" StgCls: %02x ", p[i].StorageClass);
          if (p[i].N.Name.Short == 0) {
              int k=0;
              char* str = string_table_base + p[i].N.LongName[1];

              //FIXME: not handling BIG string tables
              if (sizeof(void*) == 4)
                  assert( p[i].N.LongName[0] == 0);

              printf("[");
              while(*str && k < 100) {
                  printf("%c",*str);
                  str++;
                  k++;
              }
              printf("]");
          }
          else {
              int j;
              printf("[");
              for(j=0;j<8;j++) {
                  char c = p[i].N.ShortName[j];
                  if (c)
                      printf("%c", c);
                  else 
                      break;
              }
              printf("]");
          }

          printf("\n");
          i += p[i].NumberOfAuxSymbols;
      }
  }


  void print_section_headers() { 
    const IMAGE_SECTION_HEADER* jhdr = orig_hdr;
    for (unsigned int j = 0; j < nsections; j++, jhdr++)   {
        printf("# SECNAME  %u",j);
        printf(XED_FMT_X, (unsigned int) jhdr->Characteristics);
        if ((jhdr->Characteristics & IMAGE_SCN_CNT_CODE) == IMAGE_SCN_CNT_CODE)
        {
            printf(" CODE");
            xed_uint8_t* section_start;
            xed_uint32_t section_size;
            xed_uint64_t virtual_addr;
            
            virtual_addr  = jhdr->VirtualAddress  + image_base;
            section_size = (jhdr->Misc.VirtualSize > 0 ? 
                            jhdr->Misc.VirtualSize
                            : jhdr->SizeOfRawData);
            section_start = (xed_uint8_t*)ptr_add(base_,
                                                  jhdr->PointerToRawData);
            
            printf(" VAddr    " XED_FMT_LX16, virtual_addr);
            printf(" SecStart %p" , section_start);
            printf(" %016I64x" , (xed_uint64_t)jhdr->PointerToRawData);
            printf(" SecSize  " XED_FMT_08X,section_size);
        }
        printf("\n");
    }
  }

  xed_bool_t
  module_section_info(
                      const char* secname,
                      xed_uint8_t*& section_start,
                      xed_uint32_t& section_size,
                      xed_uint64_t& virtual_addr)
  {
    unsigned int i,ii;
    char my_name[IMAGE_SIZEOF_SHORT_NAME];
    unsigned int match_len = 0;
        
    // Extract the name into a 0-padded 8 byte string.
    if (secname) {
      memset(my_name,0,IMAGE_SIZEOF_SHORT_NAME);
      for( i=0;i<IMAGE_SIZEOF_SHORT_NAME;i++)   {
        my_name[i] = secname[i];
        if (secname[i] == 0)
          break;
      }
      // match the substring that starts with the given target_section_name
      match_len = static_cast<unsigned int>(strlen(secname));
      if (match_len > IMAGE_SIZEOF_SHORT_NAME)
        match_len = IMAGE_SIZEOF_SHORT_NAME;
    }

    // There are section names that LOOK like .text$x but they really have
    // a null string embedded in them. So when you strcmp, you hit the
    // null.
    

    for ( ii = section_index; ii < nsections; ii++, hdr++)   
    {
      int found = 0;
      if (hdr->SizeOfRawData == 0)
        continue;
      /* If no section name, match codde sections.  If we have a
         section name that matches , just disasssemble whatever they
         want. */
      if (secname==0) {
          if ((hdr->Characteristics & IMAGE_SCN_CNT_CODE) == 
              IMAGE_SCN_CNT_CODE)  
              found = 1;
      }
      else if (strncmp(reinterpret_cast<const char*>(hdr->Name), 
                       my_name, match_len) == 0) 
      {
          found = 1;
      }
      if (found) {
            // Found it.  Extract the info and return.
            virtual_addr  = hdr->VirtualAddress  + image_base;
            section_size = (hdr->Misc.VirtualSize > 0 ? 
                            hdr->Misc.VirtualSize
                            : hdr->SizeOfRawData);
            section_start = (xed_uint8_t*)ptr_add(base_, 
                                                  hdr->PointerToRawData);
            section_index = ii+1;
            hdr++;
            return true;
      }
    }
    section_index = ii;
    return false;
  }

private:
  static inline const void*
  ptr_add(const void* ptr, unsigned int n)  {
    return static_cast<const char*>(ptr)+n;
  }

  xed_bool_t
  is_valid_module()  {
    // Point to the DOS header and check it.
    const IMAGE_DOS_HEADER* dh = static_cast<const IMAGE_DOS_HEADER*>(base_);
    if (dh->e_magic != IMAGE_DOS_SIGNATURE)
        return false;
        
    // Point to the PE signature word and check it.
    const DWORD* sig = static_cast<const DWORD*>(ptr_add(base_, dh->e_lfanew));
        
    // This must be a valid PE file with a valid DOS header.
    if (*sig != IMAGE_NT_SIGNATURE)
        return false;

    return true;
  }
  xed_bool_t
  parse_nt_file_header(unsigned int* pnsections,
                       xed_uint64_t* pimage_base,
                       const IMAGE_SECTION_HEADER** phdr)
  {
    // Oh joy - the format of a .obj file on Windows is *different*
    // from the format of a .exe file.  Deal with that.
        
    // Check the header to see if this is a valid .exe file
    if (is_valid_module())
      {
        // Point to the DOS header.
        const IMAGE_DOS_HEADER* dh = 
            static_cast<const IMAGE_DOS_HEADER*>(base_);
            
        // Point to the COFF File Header (just after the signature)
        ifh = static_cast<const IMAGE_FILE_HEADER*>(ptr_add(base_, 
                                                            dh->e_lfanew + 4));
      }
    else
      {
        // Maybe this is a .obj file, which starts with the image file header
        ifh = static_cast<const IMAGE_FILE_HEADER*>(base_);
      }
        

    
#if !defined(IMAGE_FILE_MACHINE_AMD64)
# define IMAGE_FILE_MACHINE_AMD64 0x8664
#endif

    if (ifh->Machine == IMAGE_FILE_MACHINE_I386) {
        if (verbose)
            printf("# IA32 format\n");
        sixty_four_bit_ = false;
    }
    else if (ifh->Machine == IMAGE_FILE_MACHINE_AMD64) {
        if (verbose)
            printf("# Intel64 format\n");
        sixty_four_bit_ = true;
    }
    else  {
        // We only support Windows formats on IA32 and Intel64
        return false;
    }
        
    *pimage_base = 0;
        
    // Very important to use the 32b header here because the
    // unqualified IMAGE_OPTIONAL_HEADER gets the wrong version on
    // win64!
    const IMAGE_OPTIONAL_HEADER32* opthdr32
      = static_cast<const IMAGE_OPTIONAL_HEADER32*>(ptr_add(ifh, sizeof(*ifh)));

    // Cygwin's w32api winnt.h header doesn't distinguish 32 and 64b.
#if !defined(IMAGE_NT_OPTIONAL_HDR32_MAGIC)
# define IMAGE_NT_OPTIONAL_HDR32_MAGIC IMAGE_NT_OPTIONAL_HDR_MAGIC
#endif
    // And it lacks the definition for 64b headers
#if !defined(IMAGE_NT_OPTIONAL_HDR64_MAGIC)
# define IMAGE_NT_OPTIONAL_HDR64_MAGIC 0x20b
#endif

    if (ifh->SizeOfOptionalHeader > 0)
      {
        if (opthdr32->Magic == IMAGE_NT_OPTIONAL_HDR32_MAGIC)
          {
            *pimage_base = opthdr32->ImageBase;
          }
        else if (opthdr32->Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC)
          {
#if defined(_MSC_VER)
# if _MSC_VER >= 1400
            const IMAGE_OPTIONAL_HEADER64* opthdr64 =
                     static_cast<const IMAGE_OPTIONAL_HEADER64*>(
                                            ptr_add(ifh, sizeof(*ifh)));
            *pimage_base = opthdr64->ImageBase;
# else
            xedex_derror("No support for 64b optional headers because "
                         "older MS compilers do not have the type yet");
# endif
#else
            xedex_derror("No support for 64b optional headers because "
                         "cygwin does nt have the type yet");
            return false;
#endif
          }
        else 
          {
            // Optional header is not a form we recognize, so punt.
            return false;
          }
      }
        
    // Point to the first of the Section Headers
    *phdr = static_cast<const IMAGE_SECTION_HEADER*>(ptr_add(opthdr32,
                                                  ifh->SizeOfOptionalHeader));
    *pnsections = ifh->NumberOfSections;
    return true;
  }



};

////////////////////////////////////////////////////////////////////////////
#if defined(XED_USING_DEBUG_HELP)
static dbg_help_client_t dbg_help;

extern "C" void
print_file_and_line(xed_uint64_t addr)
{
    char* filename;
    xed_uint32_t line, column;

    if (dbg_help.get_file_and_line(addr, &filename, &line, &column))
    {
        if (column)
            printf( " # %s:%d.%d", filename, line, column);
        else
            printf( " # %s:%d", filename, line);
        free(filename);
    }
}

char* windows_symbols_callback(xed_uint64_t addr, void* closure) {
    dbg_help_client_t* p = (dbg_help_client_t*)closure;
    char buffer[2000];
    int r = p->get_symbol(addr, buffer, sizeof(char)*2000);
    if (r == 0) {
        int n = (int)strlen(buffer)+1;
        char* symbol = new char[n]; 
        symbol[0]=0;
        xed_strncat(symbol, buffer, n);
        return symbol;
    }
    else {
        return 0;
    }
}

int xed_pecoff_callback_function(
    xed_uint64_t address,
    char* symbol_buffer,
    xed_uint32_t buffer_length,
    xed_uint64_t* offset,
    void* caller_data) 
{
    dbg_help_client_t* p = (dbg_help_client_t*)caller_data;
    int r = p->get_symbol(address, symbol_buffer, buffer_length, offset);
    if (r == 0)
        return 1;
    return 0;
}
#endif

void xed_disas_pecoff_init() {
#if defined(XED_USING_DEBUG_HELP)
    if (dbg_help.valid()) {
        //xed_register_disassembly_callback(xed_pecoff_callback_function);
        xed_register_disassembly_callback(xed_disassembly_callback_function);
    }
#endif
}

bool dot_obj(const char* s) {
    int len = (int)strlen(s);
    const char* p = s + len - 4;
    if (strcmp(p,".obj") == 0 ||
        strcmp(p,".OBJ") == 0)
        return true;
    return false;
}

void
process_pecoff(xed_uint8_t* start,
               unsigned int length,
               xed_disas_info_t& decode_info,
               pecoff_reader_t& reader)
{
  xed_uint8_t* section_start = 0;
  xed_uint32_t section_size = 0;
  xed_uint64_t runtime_vaddr  = 0;
    
  xed_bool_t okay = true;
  xed_bool_t found = false;
#if defined(XED_USING_DEBUG_HELP)
  int init_ok = dbg_help.init( decode_info.input_file_name,
                               decode_info.symbol_search_path);
  if (init_ok == 0) {
     if (CLIENT_VERBOSE0)   {
         if (dot_obj(decode_info.input_file_name)) 
             fprintf(stderr,
                     "WARNING: No COFF symbol support yet for OBJ files.\n");
         else
             fprintf(stderr,
                     "WARNING: DBGHELP initialization failed. "
                     "Please copy the appropriate\n" 
                     "  (ia32,intel64) dbghelp.dll to the directory "
                     "where your xed.exe exists.\n"
                     "   Version 6.9.3.113 or later is required.\n");
         fflush(stderr);
     }
  }
#endif
  xed_disas_pecoff_init();

  while(okay) {
      okay = reader.module_section_info(decode_info.target_section,
                                        section_start,
                                        section_size,
                                        runtime_vaddr);
      if (okay) { 
          if (decode_info.xml_format == 0) 
              printf ("# SECTION %u\n", reader.section_index-1);
          found = true;

          decode_info.s = XED_REINTERPRET_CAST(unsigned char*,start);
          decode_info.a =
              XED_REINTERPRET_CAST(unsigned char*,section_start); 
          decode_info.q = XED_REINTERPRET_CAST(unsigned char*,
                                      section_start + section_size);

          decode_info.runtime_vaddr = runtime_vaddr + decode_info.fake_base;
          decode_info.runtime_vaddr_disas_start = decode_info.addr_start;
          decode_info.runtime_vaddr_disas_end = decode_info.addr_end;

#if defined(XED_USING_DEBUG_HELP)
          if (dbg_help.valid()) {
              decode_info.line_number_info_fn = print_file_and_line;
                            
              // This version is slow
              //decode_info.symfn = windows_symbols_callback;
              //decode_info.caller_symbol_data = &dbg_help;
              
              // This version is faster
              decode_info.symfn = get_symbol;
              decode_info.caller_symbol_data = &(dbg_help.sym_tab);
          }
#endif

          xed_disas_test(&decode_info);
      }
  }
  if (!found)
      xedex_derror("text section not found");
#if defined(XED_USING_DEBUG_HELP)
  if (dbg_help.valid())
      dbg_help.cleanup();
#endif
  (void) length;
}




extern "C" void
xed_disas_pecoff(xed_disas_info_t* fi)
{
  xed_uint8_t* region = 0;
  void* vregion = 0;
  xed_uint32_t len = 0;
  pecoff_reader_t image_reader(fi->xml_format==0);
  xed_bool_t okay = image_reader.map_region(fi->input_file_name, 
                                            vregion, 
                                            len);
  if (!okay)
    xedex_derror("image read failed");
  if (CLIENT_VERBOSE1)
    printf("Mapped image\n");
  image_reader.read_header();
  //image_reader.print_section_headers();

  //image_reader.read_coff_symbols();
  region = XED_REINTERPRET_CAST(xed_uint8_t*,vregion);

  if (image_reader.sixty_four_bit() &&
      fi->sixty_four_bit == 0 &&
      fi->use_binary_mode)
  {
      /* modify the default dstate values because we were not expecting a
       * 64b binary */
      fi->dstate.mmode = XED_MACHINE_MODE_LONG_64;
  }
  
  process_pecoff(region, len,  *fi, image_reader);
  if (fi->xml_format == 0)
      xed_print_decode_stats(fi);
}
 


#endif
