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
#if !defined(_UDHELP_H_)
#define _UDHELP_H_

#if defined(_MSC_VER)  && defined(XED_DBGHELP)
// only try to use dbghelp on MSVS8 (2005) or later versions.
# if _MSC_VER >= 1400
#  define XED_USING_DEBUG_HELP
# endif
#endif

#if defined(XED_USING_DEBUG_HELP)
#include <windows.h>
#include <dbghelp.h>
extern "C" {
#include "xed-symbol-table.h"
}
class dbg_help_client_t {

    DWORD  error;
    HANDLE hProcess;
    DWORD  processId;

    DWORD64 gBaseOfDll;
    DWORD64 actual_base;
    char* gModule;

    bool initialized;

    static BOOL CALLBACK enum_modules(
        LPSTR   ModuleName, 
        DWORD64 BaseOfDll,  
        PVOID   UserContext );
    
    static BOOL CALLBACK dbg_help_client_t::enum_sym( 
        PSYMBOL_INFO pSymInfo,   
        ULONG SymbolSize,      
        PVOID UserContext);

    public:

    xed_symbol_table_t sym_tab; // EXPOSED

    dbg_help_client_t();

    // returns 1 on success and 0 on failure. sets "initialized" to true on
    // success
    int init(char const* const fpath,
             char const* const search_path);
    bool valid() const  { return initialized; }

    // if offset is nonzero, it will return best-fit symbols. If offset=0
    // then only exact symbols are returned.
    bool get_symbol(DWORD64 address, char* symbol_name, 
                    int sym_name_buflen, DWORD64* offset=0);
    
    xed_bool_t get_file_and_line(xed_uint64_t address,
                                 char** filename,
                                 xed_uint32_t* line,
                                 xed_uint32_t* column);
    bool cleanup();
};
#endif
#endif
