/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

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
/// @file xed-common-hdrs.h
/// 



#ifndef XED_COMMON_HDRS_H
# define XED_COMMON_HDRS_H



#if defined(__FreeBSD__) || defined(__NetBSD__)
# define XED_BSD
#endif
#if defined(__linux__)
# define XED_LINUX
#endif
#if defined(_MSC_VER)
# define XED_WINDOWS
#endif
#if defined(__APPLE__)
# define XED_MAC
#endif


#if defined(XED_DLL)
//  __declspec(dllexport) works with GNU GCC or MS compilers, but not ICC
//  on linux

#  if defined(XED_WINDOWS)
#     define XED_DLL_EXPORT __declspec(dllexport)
#     define XED_DLL_IMPORT __declspec(dllimport)
#  elif defined(XED_LINUX)  || defined(XED_BSD) || defined(XED_MAC)
#     define XED_DLL_EXPORT __attribute__((visibility("default")))
#     define XED_DLL_IMPORT
#  else
#     define XED_DLL_EXPORT
#     define XED_DLL_IMPORT
#  endif
    
#  if defined(XED_BUILD)
    /* when building XED, we export symbols */
#    define XED_DLL_GLOBAL XED_DLL_EXPORT
#  else
    /* when building XED clients, we import symbols */
#    define XED_DLL_GLOBAL XED_DLL_IMPORT
#  endif
#else
# define XED_DLL_EXPORT 
# define XED_DLL_IMPORT
# define XED_DLL_GLOBAL
#endif
    
#endif

