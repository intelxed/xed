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


// Function pointer types for dbghelp.dll APIs resolved at runtime.
typedef DWORD   (WINAPI *pfn_SymSetOptions)(DWORD);
typedef BOOL    (WINAPI *pfn_SymInitialize)(HANDLE, PCSTR, BOOL);
typedef BOOL    (WINAPI *pfn_SymSetSearchPath)(HANDLE, PCSTR);
typedef DWORD64 (WINAPI *pfn_SymLoadModuleEx)(HANDLE, HANDLE, PCSTR, PCSTR,
                                              DWORD64, DWORD, PMODLOAD_DATA,
                                              DWORD);
typedef BOOL    (WINAPI *pfn_SymEnumerateModules64)(HANDLE,
                                                    PSYM_ENUMMODULES_CALLBACK64,
                                                    PVOID);
typedef BOOL    (WINAPI *pfn_SymEnumSymbols)(HANDLE, ULONG64, PCSTR,
                                            PSYM_ENUMERATESYMBOLS_CALLBACK,
                                            PVOID);
typedef BOOL    (WINAPI *pfn_SymFromAddr)(HANDLE, DWORD64, PDWORD64,
                                         PSYMBOL_INFO);
typedef BOOL    (WINAPI *pfn_SymGetLineFromAddr64)(HANDLE, DWORD64, PDWORD,
                                                   PIMAGEHLP_LINE64);
typedef BOOL    (WINAPI *pfn_SymCleanup)(HANDLE);

static pfn_SymSetOptions          pSymSetOptions;
static pfn_SymInitialize          pSymInitialize;
static pfn_SymSetSearchPath       pSymSetSearchPath;
static pfn_SymLoadModuleEx        pSymLoadModuleEx;
static pfn_SymEnumerateModules64  pSymEnumerateModules64;
static pfn_SymEnumSymbols         pSymEnumSymbols;
static pfn_SymFromAddr            pSymFromAddr;
static pfn_SymGetLineFromAddr64   pSymGetLineFromAddr64;
static pfn_SymCleanup             pSymCleanup;

static HMODULE hDbgHelp;  // loaded module handle

// Attempt to load dbghelp.dll from a trusted location only:
//   1. The executable's own directory (supports newer bundled versions), or
//   2. The Windows system directory (e.g. C:\Windows\System32).
// Returns the HMODULE on success, NULL on failure.
static HMODULE load_trusted_dbghelp(void) {
    char path[MAX_PATH];
    UINT slen;

    // Search for dbghelp.dll where the application is.
    HMODULE h = LoadLibraryEx("dbghelp.dll", NULL,
                              LOAD_LIBRARY_SEARCH_APPLICATION_DIR);
    if (!h) {
        // Fall back to the Windows system directory.
        slen = GetSystemDirectory(path, MAX_PATH);
        if (slen != 0 && slen < MAX_PATH &&
            (slen + sizeof("\\dbghelp.dll")) < MAX_PATH)
        {
            strcat_s(path, MAX_PATH, "\\dbghelp.dll");
            h = LoadLibrary(path);
        }
    }

    return h;
}

// Resolve all required dbghelp function pointers from the given module.
// Returns 1 if all functions were resolved, 0 otherwise.
static xed_bool_t resolve_dbghelp_functions(HMODULE h) {
    pSymSetOptions = (pfn_SymSetOptions)
        GetProcAddress(h, "SymSetOptions");
    pSymInitialize = (pfn_SymInitialize)
        GetProcAddress(h, "SymInitialize");
    pSymSetSearchPath = (pfn_SymSetSearchPath)
        GetProcAddress(h, "SymSetSearchPath");
    pSymLoadModuleEx = (pfn_SymLoadModuleEx)
        GetProcAddress(h, "SymLoadModuleEx");
    pSymEnumerateModules64 = (pfn_SymEnumerateModules64)
        GetProcAddress(h, "SymEnumerateModules64");
    pSymEnumSymbols = (pfn_SymEnumSymbols)
        GetProcAddress(h, "SymEnumSymbols");
    pSymFromAddr = (pfn_SymFromAddr)
        GetProcAddress(h, "SymFromAddr");
    pSymGetLineFromAddr64 = (pfn_SymGetLineFromAddr64)
        GetProcAddress(h, "SymGetLineFromAddr64");
    pSymCleanup = (pfn_SymCleanup)
        GetProcAddress(h, "SymCleanup");

    if (!pSymSetOptions || !pSymInitialize || !pSymSetSearchPath ||
        !pSymLoadModuleEx || !pSymEnumerateModules64 || !pSymEnumSymbols ||
        !pSymFromAddr || !pSymGetLineFromAddr64 || !pSymCleanup)
        return 0;
    return 1;
}

// Minimum required major version of dbghelp.dll.
// 6.0 is needed for SymLoadModuleEx / SymEnumSymbols.
#define DBGHELP_MIN_MAJOR_VERSION 6

// Check that the loaded dbghelp.dll meets the minimum version requirement.
// Returns 1 if the version is acceptable (or cannot be determined), 0 if
// the DLL is definitely too old.
static xed_bool_t check_dbghelp_version(HMODULE h) {
    char dll_path[MAX_PATH];
    DWORD len = GetModuleFileName(h, dll_path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        if (CLIENT_VERBOSE)
            fprintf(stderr,
                    "NOTE: dbghelp.dll path could not be determined; "
                    "will attempt symbol extraction anyway.\n"
                    "  Use -no-dbghelp to disable symbol extraction.\n");
        return 1;  // continue gracefully
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
        return 1;  // continue gracefully
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
        return 1;  // continue gracefully
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
        return 1;  // continue gracefully
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

// Load dbghelp.dll from a trusted location, verify the minimum required
// version, and resolve all function pointers.
// Returns 1 on success, 0 on failure.
static xed_bool_t init_dbghelp(void) {
    hDbgHelp = load_trusted_dbghelp();
    if (!hDbgHelp) {
        fprintf(stderr,
                "NOTE: dbghelp.dll could not be loaded from a trusted"
                " location.\n"
                "  Looked in the executable directory and the Windows"
                " system directory.\n"
                "  Use -no-dbghelp to disable symbol extraction.\n");
        return 0;
    }

    if (!check_dbghelp_version(hDbgHelp)) {
        FreeLibrary(hDbgHelp);
        hDbgHelp = NULL;
        return 0;
    }

    if (!resolve_dbghelp_functions(hDbgHelp)) {
        fprintf(stderr,
                "NOTE: failed to resolve required dbghelp.dll functions.\n"
                "  Use -no-dbghelp to disable symbol extraction.\n");
        FreeLibrary(hDbgHelp);
        hDbgHelp = NULL;
        return 0;
    }

    return 1;
}

int dbg_help_client_t::init(char const* const path,
                            char const* const search_path)
{
    DWORD64 dwBaseAddr=0;
    xed_bool_t sym_initialized = 0;

    if (!init_dbghelp())
        return 0;

    pSymSetOptions(SYMOPT_UNDNAME | SYMOPT_LOAD_LINES );
    hProcess = GetCurrentProcess();
    
    if (pSymInitialize(hProcess, NULL, FALSE))     {
        sym_initialized = 1;
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymInitialize returned error : %u 0x%x\n",
                error, error);
        fflush(stderr);
        goto fail;
    }

    if (search_path)
    {
        if (pSymSetSearchPath(hProcess, search_path))   {
            // nothing
        }
        else    {
            error = GetLastError();
            fprintf(stderr,"SymSetSearchPath returned error : %u 0x%x\n",
                    error, error);
            fflush(stderr);
            goto fail;
        }
    }
    
    actual_base = pSymLoadModuleEx(hProcess, NULL, path, NULL, 
                                   dwBaseAddr, 0, NULL, 0);
    if (actual_base) {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymLoadModuleEx returned error : %u 0x%x\n", 
                error, error);
        fflush(stderr);
        goto fail;
    }


    if (pSymEnumerateModules64(hProcess, 
                         (PSYM_ENUMMODULES_CALLBACK64)enum_modules, this)) {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymEnumerateModules64 returned error : %d 0x%x\n",
               error, error);
        fflush(stderr);
        goto fail;
    }

    if (pSymEnumSymbols(hProcess, actual_base, 0, enum_sym, this))    {
        // nothing
    }
    else    {
        error = GetLastError();
        fprintf(stderr,"SymEnumSymbols failed: %d 0x%x\n", error, error);
        fflush(stderr);
        goto fail;
    }

    initialized = true;
    return 1;

fail:
    if (sym_initialized)
        pSymCleanup(hProcess);
    FreeLibrary(hDbgHelp);
    hDbgHelp = NULL;
    return 0;
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
    
    if (pSymFromAddr(hProcess, address, &displacement, pSymbol))    {
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
    if (pSymCleanup(hProcess))    {
        FreeLibrary(hDbgHelp);
        hDbgHelp = NULL;
        return 0;
    }
    else    {
        error = GetLastError();
        fprintf(stderr,
                "SymCleanup returned error : %d 0x%x\n", error,error);
        FreeLibrary(hDbgHelp);
        hDbgHelp = NULL;
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
    if (pSymGetLineFromAddr64(hProcess, address, &dw_column, &imgline))
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
