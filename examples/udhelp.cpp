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
    return TRUE;
    (void)SymbolSize; //pacify compiler warning about unused param
}


dbg_help_client_t::dbg_help_client_t() {
    xed_symbol_table_init(&sym_tab);
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

static char* append3(const char* s1, const char* s2, const char* s3) {
    xed_uint_t  n = 1;
    char* p = 0;
    assert(s1 != 0);
    n += xed_strlen(s1);
    if (s2)    n += xed_strlen(s2);
    if (s3)    n += xed_strlen(s3);
    p = (char*) malloc(sizeof(char)*n);
    n=xed_strncpy(p,s1,n);
    if (s2) n=xed_strncat(p,s2,n);
    if (s3) n=xed_strncat(p,s3,n);
    return p;
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

 

int dbg_help_client_t::init(char const* const path,
                            char const* const search_path)
{
    DWORD64 dwBaseAddr=0;

    int chars;
    char exe_path[MAX_PATH];
    chars = GetModuleFileName(NULL, exe_path, MAX_PATH);
    if (chars == 0) { 
        fprintf(stderr,"Could not find base path for XED executable\n");
        fflush(stderr);
        exit(1);
    }

    char* dir = find_base_path(exe_path);

    char* dbghelp = append3(dir,"\\","dbghelp.dll");
#if defined(PIN_CRT)
    if (access(dbghelp,4) != 0)
#else
    if (_access_s(dbghelp,4) != 0)
#endif
    {
        return 0;
    }

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
        xed_strncpy(*filename, imgline.FileName, len+1);
        return 1; //success
    }
    return 0; //failed
}

#endif
