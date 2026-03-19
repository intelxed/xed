/* BEGIN_LEGAL 

Copyright (c) 2026 Intel Corporation

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
#include "udhelp.H"
#include <stdio.h>
extern "C" {
#include "xed/xed-interface.h"
#include "xed-examples-util.h" // xed_strdup
}
#include <process.h>
#include <windows.h>
#include <io.h>
#include <cstring>
#include <cstdio>
#include <cassert>

#if defined(XED_USING_DEBUG_HELP) && defined(XED_DECODER)
BOOL CALLBACK dbg_help_client_t::enum_modules(
    LPSTR   ModuleName, 
    DWORD64 BaseOfDll,  
    PVOID   UserContext )
{
    dbg_help_client_t* pthis = (dbg_help_client_t*)UserContext;
    pthis->gBaseOfDll = BaseOfDll;
    pthis->gModule=ModuleName;
    return TRUE;
}




BOOL CALLBACK dbg_help_client_t::enum_sym( 
    PSYMBOL_INFO pSymInfo,   
    ULONG SymbolSize,      
    PVOID UserContext)
{
    dbg_help_client_t* pthis = (dbg_help_client_t*)UserContext;
    xed_uint64_t addr = static_cast<xed_uint64_t>(pSymInfo->Address);
    
    xst_add_global_symbol(&pthis->sym_tab,
                          addr,
                          xed_strdup(pSymInfo->Name));
    (void)SymbolSize; //pacify compiler warning about unused param
    return TRUE;
}


dbg_help_client_t::dbg_help_client_t() {
    xed_symbol_table_init(&sym_tab);
    error=0;
    hProcess=INVALID_HANDLE_VALUE;
    processId=0;
    gBaseOfDll=0;
    actual_base=0;
    gModule=0;
    initialized=false;
}


char* find_base_path(char* driver_name) {
    char* x;
    char* path = xed_strdup(driver_name);
    x = strrchr(path,'\\');
    if (x) {
        *x = 0;
    }
    else {
        x = strrchr(path,'/');
        if (x) {
            *x = 0;
        }
        else { 
            /* FIXME */
        }
    }
    return path;
}






typedef union {
  short a[2];
  int   i;
} union16_t;

void get_dll_version(char* file_name, short u[4]) {
    VS_FIXEDFILEINFO* vsf;
    DWORD verlen, error, handle;
    UINT len;
    BOOL ret;
    char* ver;

    verlen = GetFileVersionInfoSize(file_name,&handle);
    if (verlen == 0)  {
        error = GetLastError();
        fprintf(stderr,"GetFileVersionInfoSize: error code was %u (0x%x)\n", 
               error, error);
        exit(1);
    }

    ver = new char[verlen];
    ret = GetFileVersionInfo(file_name,handle,verlen,ver);
    if (!ret)  {
        error = GetLastError();
        fprintf(stderr,
                "GetFileVersionInfo: error code was %u (0x%x)\n", error, error);
        exit(1);
    }
   
    // get a pointer to a location in ver stored in vsf
    ret = VerQueryValue(ver,"\\",(LPVOID*)&vsf,&len);
    if (!ret)  {
        error = GetLastError();
        fprintf(stderr,
                "VerQueryValue: error code was %u (0x%x)\n", error, error);
        exit(1);
    }
    assert(len == sizeof(VS_FIXEDFILEINFO));

    union16_t upper,lower;
    upper.i = vsf->dwFileVersionMS;
    lower.i = vsf->dwFileVersionLS;
    u[0] = upper.a[1];
    u[1] = upper.a[0];
    u[2] = lower.a[1];
    u[3] = lower.a[0];

    delete[] ver;
}

// Minimum required major version of dbghelp.dll.
// 6.0 is needed for SymLoadModuleEx / SymEnumSymbols.
#define DBGHELP_MIN_MAJOR_VERSION 6

// Verify that dbghelp.dll is loaded and meets the minimum required version
// Returns 1 on success, 0 on failure.
static xed_bool_t check_dbghelp_available(void) {
    HMODULE hDbgHelp = GetModuleHandle("dbghelp.dll");
    if (!hDbgHelp) {
        fprintf(stderr,
                "ERROR: dbghelp.dll is not loaded.\n"
                "  Use -no-dbghelp to disable symbol extraction.\n");
        return 0;
    }

    char dll_path[MAX_PATH];
    DWORD len = GetModuleFileName(hDbgHelp, dll_path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        if (CLIENT_VERBOSE)
            fprintf(stderr,
                    "NOTE: dbghelp.dll path could not be determined; "
                    "will attempt symbol extraction anyway.\n"
                    "  Use -no-dbghelp to disable symbol extraction.\n");
        return 1;
    }

    DWORD ver_handle;
    DWORD ver_size = GetFileVersionInfoSize(dll_path, &ver_handle);
    if (ver_size == 0) {
        if (CLIENT_VERBOSE)
            fprintf(stderr,
                    "NOTE: could not read version info for %s; "
                    "will attempt symbol extraction anyway.\n"
                    "  Use -no-dbghelp to disable symbol extraction.\n",
                    dll_path);
        return 1;
    }

    char* ver_data = new char[ver_size];
    if (!GetFileVersionInfo(dll_path, ver_handle, ver_size, ver_data)) {
        delete[] ver_data;
        if (CLIENT_VERBOSE)
            fprintf(stderr,
                    "NOTE: GetFileVersionInfo failed for %s; "
                    "will attempt symbol extraction anyway.\n"
                    "  Use -no-dbghelp to disable symbol extraction.\n",
                    dll_path);
        return 1;
    }

    VS_FIXEDFILEINFO* vsf = NULL;
    UINT vsf_len = 0;
    if (!VerQueryValue(ver_data, "\\", (LPVOID*)&vsf, &vsf_len) ||
        vsf_len < sizeof(VS_FIXEDFILEINFO))
    {
        delete[] ver_data;
        if (CLIENT_VERBOSE)
            fprintf(stderr,
                    "NOTE: version query failed for %s; "
                    "will attempt symbol extraction anyway.\n"
                    "  Use -no-dbghelp to disable symbol extraction.\n",
                    dll_path);
        return 1;
    }

    DWORD major = HIWORD(vsf->dwFileVersionMS);
    DWORD minor = LOWORD(vsf->dwFileVersionMS);
    delete[] ver_data;

    if (major < DBGHELP_MIN_MAJOR_VERSION) {
        fprintf(stderr,
                "ERROR: dbghelp.dll version %u.%u is too old "
                "(loaded from %s).\n"
                "  Minimum required major version is %u.\n"
                "  Use -no-dbghelp to disable symbol extraction.\n",
                (unsigned)major, (unsigned)minor, dll_path,
                (unsigned)DBGHELP_MIN_MAJOR_VERSION);
        return 0;
    }
    return 1;
}

int dbg_help_client_t::init(char const* const path,
                            char const* const search_path)
{
    DWORD64 dwBaseAddr=0;

    if (!check_dbghelp_available())
        return 0;

    SymSetOptions(SYMOPT_UNDNAME | SYMOPT_LOAD_LINES );
    hProcess = GetCurrentProcess();
    
    if (SymInitialize(hProcess, NULL, FALSE))     {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymInitialize returned error : %u 0x%x\n",
                error, error);
        fflush(stderr);
        return 0;
    }

    if (search_path)
    {
        if (SymSetSearchPath(hProcess, search_path))   {
            // nothing
        }
        else    {
            error = GetLastError();
            fprintf(stderr,"SymSetSearchPath returned error : %u 0x%x\n",
                    error, error);
            fflush(stderr);
            return 0;
        }
    }
    
    actual_base = SymLoadModuleEx(hProcess, NULL, path, NULL, 
                                  dwBaseAddr, 0, NULL, 0);
    if (actual_base) {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymLoadModuleEx returned error : %u 0x%x\n", 
                error, error);
        fflush(stderr);
        return 0;
    }


    if (SymEnumerateModules64(hProcess, 
                        (PSYM_ENUMMODULES_CALLBACK64)enum_modules, this)) {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymEnumerateModules64 returned error : %d 0x%x\n",
               error, error);
        fflush(stderr);
        return 0;
    }

    if (SymEnumSymbols(hProcess, actual_base, 0, enum_sym, this))    {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymEnumSymbols failed: %d 0x%x\n", error, error);
        fflush(stderr);
        return 0;
    }

    initialized = true;
    return 1;
}

bool dbg_help_client_t::get_symbol(DWORD64 address, char* symbol_name, 
                                   int sym_name_buflen, DWORD64* offset) 
{
    DWORD64  displacement;
    ULONG64 n = (sizeof(SYMBOL_INFO) +
                 sym_name_buflen*sizeof(TCHAR) +
                 sizeof(ULONG64) - 1) / sizeof(ULONG64);
    ULONG64* buffer = new ULONG64[n];
    PSYMBOL_INFO pSymbol = (PSYMBOL_INFO)buffer;
            
    pSymbol->SizeOfStruct = sizeof(SYMBOL_INFO);
    pSymbol->MaxNameLen = sym_name_buflen;
    
    if (SymFromAddr(hProcess, address, &displacement, pSymbol))    {
        if (offset)
            *offset = displacement;
        if (offset  || displacement == 0) {
            xed_strncpy(symbol_name, pSymbol->Name, sym_name_buflen);
            // force a null. WINDOWS doesn't have strlcpy()
            symbol_name[sym_name_buflen-1] = 0;
            delete [] buffer;
            return 0;
        }
        else {
            /* not at the beginning of a symbol and no offset was supplied */
            delete [] buffer;
            return 1;
        }
    }
    else    {
        error = GetLastError();
        fprintf(stderr,
                "SymFromAddr returned error : %d 0x%x for address %llx\n", 
                error, error, address);
        delete [] buffer;
        return 1;
    }


}

bool dbg_help_client_t::cleanup() {
    if (SymCleanup(hProcess))    {
        return 0;
    }
    else    {
        error = GetLastError();
        fprintf(stderr,
                "SymCleanup returned error : %d 0x%x\n", error,error);
        return 1;
    }
}

xed_bool_t dbg_help_client_t::get_file_and_line(xed_uint64_t address,
                                                char** filename,
                                                xed_uint32_t* line,
                                                xed_uint32_t* column)
{
    DWORD dw_column;
    IMAGEHLP_LINE64 imgline;
    imgline.SizeOfStruct = sizeof(IMAGEHLP_LINE64);
    if (SymGetLineFromAddr64(hProcess, address, &dw_column, &imgline))
    {
        xed_uint32_t len = xed_strlen(imgline.FileName);
        *column = dw_column;
        *line = imgline.LineNumber;
        *filename =(char*) malloc(len+1);
        if (*filename == 0)
            return 0; // failed, out of memory
        xed_strncpy(*filename, imgline.FileName, len+1);
        return 1; //success
    }
    return 0; //failed
}

#endif
