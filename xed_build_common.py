#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL
from __future__ import print_function
import sys
import os
import re
import shutil
import copy
import time
import types
import optparse
import mbuild 
    
############################################################################
class xed_exception_t(Exception):
    def __init__(self,kind,value,msg=""):
        self.kind = kind
        self.value = value
        self.msg = msg
    def __str__(self):
        return "KIND: %s VALUE: %d MSG: %s" % (self.kind, self.value, self.msg)

def handle_exception_and_die(e):
    if hasattr(e,'kind'):
        if e.kind == 'die':
            sys.stderr.write('ABORT: ' + e.msg + '\n')
            sys.exit(e.value)
        elif e.kind == 'exit':
            sys.stderr.write('EXITING\n')
            sys.exit(e.value)
    else:
        print(str(e))
        sys.exit(1)

def cdie(s):
    raise xed_exception_t("die", 1, s)
def cexit(r=0):
    raise xed_exception_t("exit", r)

def write_file(fn, stream):
    """Write stream to fn"""
    mbuild.vmsgb(1, "WRITING", fn)
    f = open(fn,'w')
    f.writelines(stream)
    f.close()

def add_to_flags(env,s):
    env.add_to_var('CCFLAGS',s)
    env.add_to_var('CXXFLAGS',s)

def security_level_match(env: dict, level: int) -> bool:
    ''' Return True if the "level" argument matches the build's security level '''
    return env['security_level'] >= level

def  _gcc_version_string(env):
    gcc = env.expand('%(CC)s')
    vstr = mbuild.get_gcc_version(gcc)
    return vstr

def  _clang_version_string(env):
    gcc = env.expand('%(CC)s')
    vstr = mbuild.get_clang_version(gcc)
    return vstr

def  _greater_than_gcc(env:dict, amaj:int, amin:int, aver:int) -> bool:
    vstr = _gcc_version_string(env)
    try:
        vstr = re.sub(r"[^\d\.]", "", vstr)
        (vmaj, vmin, vver) = vstr.split('.')
    except:
        return False
    
    vmaj = int(vmaj)
    if vmaj > amaj:
        return True
    
    vmin = int(vmin)
    if vmaj == amaj and vmin > amin:
        return True
    
    vver = int(vver)
    if vmaj == amaj and vmin == amin and vver >= aver:
        return True
    
    return False


def gnu_secured_build(env: dict) -> str:
    """ Example of extending the GNU environment for compilation """
    flags = ''
    if security_level_match(env, 2):
        ### Compiler Warnings and Error Detection ###
        flags += ' -Wextra'
        # codegen.py puts assert to check bounded value. if the range type is unsigned,
        # and the lower bound is zero, then we need not to check it because sometimes it
        # is hard to tell the operand type.
        flags += ' -Wno-error=type-limits'

        ### Format String Defense ###
        # Treats format string security warnings as errors
        if not env['debug']:
            flags += ' -Werror=format-security'

        ### Pre-processor Macros ###
        # enables the fortified source code features provided by the compiler, triggering
        # additional security checks and modifications in the generated code
        if env['opt'] in ['2', '3']:  # requires compiling with optimization
            flags += ' -D_FORTIFY_SOURCE=2'

        ### Stack Protection ###
        if env['debug']:
            # Enables stack protection by adding a stack canary to detect buffer overflows
            flags += ' -fstack-protector'
        else:
            # Enables stronger stack protection with a stronger stack canary
            flags += ' -fstack-protector-strong'

        if not env.on_windows():
            ### Position Independent Code ###
            # Generates position-independent code during the compilation phase
            flags += ' -fPIC'
            if not env['debug']:
                ### Stack and Heap Overlap Protection ###
                # Enables Read-Only Relocation (RELRO) and Immediate Binding protections
                env.add_to_var('LINKFLAGS','-Wl,-z,relro,-z,now')
                ### Inexecutable Stack ###
                # Specifies that the stack memory should be marked as non-executable
                env.add_to_var('LINKFLAGS','-z noexecstack')
        else:  # Windows
            # Enables Data Execution Prevention (DEP) for executables.
            env.add_to_var('LINKFLAGS','-Wl,-nxcompat')
            # Enables address space layout randomization (ASLR) for executables.
            env.add_to_var('LINKFLAGS','-Wl,--dynamicbase')
            # Warnings as errors (Linker specific)
            env.add_to_var('LINKFLAGS','-Werror')
            # Enables Link-Time Code Generation
            env.add_to_var('LINKFLAGS', '-flto')

    return flags


def set_env_gnu(env):
    """Example of setting up the GNU GCC environment for compilation"""
    env['LINK'] = env['CC']

    flags = ''
        
    #coverage testing  using the local compiler
    #flags += ' -fprofile-arcs -ftest-coverage'
    #env['LIBS'] += ' -lgcov'
    
    flags += ' -Wall'
    # the windows compiler finds this stuff so flag it on other platforms
    flags += ' -Wunused' 
    
    # 2018-11-28: I am working on hammering out all the issues found by these knobs:
    #flags += ' -Wconversion'
    #flags += ' -Wsign-conversion'

    if env['use_werror']:
        flags += ' -Werror'

    flags += ' -Wno-long-long'
    flags += ' -Wno-unknown-pragmas'
    flags += ' -fmessage-length=0'
    flags += ' -pipe'
    flags += ' -fno-exceptions'
    flags += ' -Wformat-security'
    flags += ' -Wformat'

    # -pg is incompatible with -fomit-frame-pointer
    if (re.search(r' -pg', env['CXXFLAGS']) == None and 
        re.search(r' -pg', env['CCFLAGS']) == None):
        flags += ' -fomit-frame-pointer'

    # c99 is required for c++ style comments.
    env['CSTD'] = 'c99'
    env['CCFLAGS'] += ' -std=%(CSTD)s '
    if env['pedantic']:
        env['CCFLAGS'] += ' -pedantic '

    if env['shared']:
        hidden = ' -fvisibility=hidden' 
        env['LINKFLAGS'] += hidden
        flags += hidden

    if env['compiler'] in ['gnu', 'clang']:
        flags += gnu_secured_build(env)

    env['CCFLAGS'] += flags
    env['CCFLAGS'] += ' -Wstrict-prototypes'
    env['CCFLAGS'] += ' -Wwrite-strings'
    env['CCFLAGS'] += ' -Wredundant-decls'

    # Disabled the following. Generates too many silly errors/warnings
    #env['CCFLAGS'] += ' -Wmissing-prototypes'

    env['CXXFLAGS'] += flags


def set_env_clang(env):
    set_env_gnu(env)
    env['CXXFLAGS'] += ' -Wno-unused-function'
        
def set_env_ms(env):
    """Set up the MSVS environment for compilation"""
    flags = ''
    cxxflags = ''
    if env['clr']:
        flags += ' /TP /clr '
        # linker fail suggested libcmt was a problem for CLR. 2007-07-17
        env['LINKFLAGS'] += ' /NODEFAULTLIB:libcmt' 

    # remove dead code from executable
    env['LINKFLAGS'] += ' /OPT:REF /OPT:ICF=3'

    # enable security features
    if env['msvs_version'] and int(env['msvs_version']) >=  8: # MSVS2005
        env.add_to_var('LINKFLAGS','/NXCOMPAT')
        env.add_to_var('LINKFLAGS','/DYNAMICBASE')


    if env['msvs_version'] == '6':
        flags  += ' /w'    # disable warnings
    else:
        #cxxflags  += ' /wd4530'# disable warning on unhandled exceptions
        #flags  += ' /wd4214'   # disable /W4 warning on nonstd typed-bitfields
        if not env['clr']:
            cxxflags += ' /EHsc'   # use windows exceptions
    if not env['clr']:
        cxxflags += ' /GR-'        # do not use RTTI
    if env['msvs_version'] != '6':
        flags += ' /W4'         # Maximum warning level.
        flags += ' /WX'         # Warnings as errors.
        flags += ' /wd4091'     # disable dbghelp.h warning in msvs2015
        # Disable warnings about conditional expression is constant
        #      used by xed_assert()'s "while(0)" and
        #      a few other "if (1)..." things.
        flags += ' /wd4127'  
        flags += ' /wd4505'     # Disable warnings about unused functions.
        flags += ' /wd4702'     # Disable warnings about unreachable code
                                #       (shows up in generated code). FIXME
        flags += ' /wd4244'     # Disable warnings about changing widths.
        # Disable warnings about compiler limit in MSVC7(.NET / 2003)
        flags += ' /wd4292'

        if security_level_match(env, 2):
            env.add_to_var('LINKFLAGS','/WX')  # Warnings as errors (Linker specific)

            ## Position Independent Code ##
            # Enables function-level linking, which can improve code sharing and optimization
            flags += ' /Gy'

            ## Control Flow Integrity ##
            env.add_to_var('LINKFLAGS', '/LTCG')  # Enables Link-Time Code Generation
            flags += ' /sdl'   # Enables the "Additional Security Check" feature

            ## Stack Protection ##
            flags += ' /GS' # Enables buffer security checks with a stack canary
        if security_level_match(env, 3):
            ############## NOTE: Major performance impact ##############
            ## Spectre Protection ##
            # Enables Spectre variant 1 and variant 2 mitigations
            flags += ' /Qspectre'

    # /Zm200 is required on VC98 for xed-decode.cpp to avoid
    # internal compiler error
    #flags += ' /Zm200'
    env['CCFLAGS'] += flags
    env['CXXFLAGS'] += cxxflags + " " + flags


def intel_compiler_disables(env):
    """Return a comma separated string of compile warning number disables
       for ICC/ICL."""
    disables = []
    disables.append( 810 ) # loss of precision
    # value copied to temporary, reference to temporary used.
    disables.append( 383 ) 
    disables.append( 108 ) # signed bit fields of 1 bit length
    disables.append( 111 ) # statement is unreachable
    disables.append( 1419 ) # external declaration in primary source file
    disables.append( 981 ) #  operands are evaluated in unspecified order
    if env['icc_version'] !=  '7':
        # function "strncat" or "strcpy" (etc.)  was declared
        # "deprecated" # NOT ON ECL7
        disables.append( 1478 ) 
    disables.append( 188 ) # enumerated type mixed with another type
    disables.append( 310 ) # old-style parameter list (anachronism)
    disables.append( 592 ) # variable "c" is used before its value is set
    disables.append( 1418 ) # external definition with no prior declaration 
    disables.append( 186 ) # pointless comparison of unsigned integer with zero
    disables.append( 279 ) # controlling expression is constant
    disables.append( 128 ) # loop is not reachable from preceding code
    disables.append( 177 ) # function  was declared but never referenced
    
    # Explicit conversion of a 64-bit integral type to a smaller integral type.
    #disables.append( 1683 ) 
                             
    if env['icc_version'] not in ['7','8','9']:
        # non-pointer conversion/lose significant bits, ICL11
        disables.append( 2259 ) 
    return ",".join(map(str,disables))

def set_env_icc(env):
    set_env_gnu(env)
    env['CCFLAGS'] += ' -wd' + intel_compiler_disables(env)
    env['CXXFLAGS'] += ' -wd' + intel_compiler_disables(env)
    
def set_env_icl(env):
    set_env_ms(env)
    env['CCFLAGS'] += ' /Qwd' + intel_compiler_disables(env)
    env['CXXFLAGS'] += ' /Qwd' + intel_compiler_disables(env)

###########################################################################

def xed_remove_files_glob(env):
    """Clean up"""
    mbuild.msgb("CLEANING")
    try:
        if 'build_dir' in env:
            path = env['build_dir']
            if path != '.' and path != '..':
                mbuild.remove_tree(path)
                return
    except:
        cdie("clean failed")

###########################################################################


def set_xed_defaults(env):
    """External entry point: Users must call set_xed_defaults() or
    xed_args().  This post-processes the environment"""
    env.process_user_settings()
    
def init_once(env):
    p = os.path.join(env['src_dir'], 'scripts')
    if os.path.exists(p):
        sys.path.insert(0, p)
    
def init(env):
    # we make the python command contingent upon the mfile itself to catch
    # build changes.
    
    if 'init' in env and env['init']:
        return
    env['init']=True
    
    env['mfile'] = env.src_dir_join('mfile.py')
    env['arch'] = get_arch(env)

    mbuild.msgb("SECURITY BUILD LEVEL", env['security_level'])

    if env['compiler'] == 'gnu':
        set_env_gnu(env)
        mbuild.msgb("GNU/GCC VERSION", _gcc_version_string(env))
    elif env['compiler'] == 'clang':
        set_env_clang(env)
        mbuild.msgb("CLANG VERSION", _clang_version_string(env))
    elif env['compiler'] == 'ms':
        set_env_ms(env)
        mbuild.msgb("MS VERSION", env['msvs_version'])
    elif env['compiler'] in ['icc', 'icl']:
        cdie(f'"{env["compiler"]}" is no longer supported')
    else:
        cdie("Unknown compiler: " + env['compiler'])
    
    if env['xed_messages']:
        env.add_define('XED_MESSAGES')
    if env['xed_asserts']:
        env.add_define("XED_ASSERTS")

def strip_file(env,fn,options=''):
    if env.on_windows():
        return
    fne = env.expand(fn)
    mbuild.msgb("STRIPPING", fne)
    strip_cmd = " ".join([env['strip'], options, fne])
    #mbuild.msgb("STRIP CMD", strip_cmd)
    (retcode,stdout,stderr) = mbuild.run_command(strip_cmd)
    if retcode != 0:
       dump_lines("strip stdout", stdout)
       dump_lines("strip stderr", stderr)
       cdie("Could not strip " + fne)

def src_dir_join(env, lst):
    return [ mbuild.join(env['src_dir'],'src',x) for x in lst ]

def build_dir_join(env, lst):
    return [ mbuild.join(env['build_dir'],x)for x in  lst]

def make_lib_dll(env,base):
    """Return the static or link lib and shared-lib name.  For a given
       base we return base.lib and base.dll on windows.  base.so and
       base.so on non-windows.  Users link against the link lib."""
    
    dll = env.shared_lib_name(base)
    static_lib = env.static_lib_name(base)
    
    if env['shared']:
        if env.on_windows():
            link_lib = static_lib
        else:
            link_lib = dll
    else:
        link_lib = static_lib

    return link_lib, dll

def _xed_lib_dir_join(env, s):
    return mbuild.join(env['xed_lib_dir'],s)

def get_libxed_names(env):
    libxed_lib, libxed_dll = make_lib_dll(env,'xed')
    env['link_libxed'] = _xed_lib_dir_join(env,libxed_lib)
    env['shd_libxed']  = _xed_lib_dir_join(env,libxed_dll)
        
    lib,dll = make_lib_dll(env,'xed-ild')
    env['link_libild'] = _xed_lib_dir_join(env,lib)
    env['shd_libild']  = _xed_lib_dir_join(env,dll)
    
def installing(env):
    if 'install' in env['targets'] or 'zip' in env['targets']:
       return True
    return False
    
def _modify_search_path_mac(env, fn):
   """Make example tools refer to the libxed.so from the lib directory
   if doing and install. Mac only."""
   if not env['shared']:
      return
   if not env.on_mac():
      return 
   if not installing(env):
      return
   env['odll'] = '%(build_dir)s/libxed.dylib'
   env['ndll'] = '"@loader_path/../lib/libxed.dylib"'
   cmd = 'install_name_tool -change %(odll)s %(ndll)s ' + fn
   cmd = env.expand(cmd)
   env['odll'] = None
   env['ndll'] = None

   mbuild.msgb("SHDOBJ SEARCH PATH", cmd)
   (retcode,stdout,stderr) = mbuild.run_command(cmd)
   if retcode != 0:
      dump_lines("install_name_tool stdout", stdout)
      dump_lines("install_name_tool stderr", stderr)
      cdie("Could not modify dll path: " + cmd)


def get_arch(env):
    if env['host_cpu'] == 'ia32':
       arch = '32'
    else:
       arch = '64'
    return arch


def dump_lines(s,lines):
   if lines:
      print("========")
      print(s + ":")
      for line in lines:
         print(line.strip())
      print("========")


def prep(env):
    mbuild.vmsgb(1, "PYTHON VERSION", "%d.%d.%d" %
                 (mbuild.get_python_version_tuple()))


###########################################################################
# ELF/DWARF (linux only)

def _use_elf_dwarf(env):
   """Do not call this directly. See cond_add_elf_dwarf.  Tell the
   build we want to use libelf and libdwarf. Some systems have these
   libraries installed and this is sufficient for those systems."""

   env['LIBS'] += ' -lelf'
   env.add_define('XED_DWARF')
   env['LIBS'] += ' -ldwarf'


def _add_elf_dwarf_precompiled(env):
   """Do not call this directly. See cond_add_elf_dwarf.  Set up to
   use our precompiled libelf/libdwarf. """
   
   env.add_include_dir('%(xedext_dir)s/external/include')
   env.add_include_dir('%(xedext_dir)s/external/include/libelf')

   env.add_define('XED_PRECOMPILED_ELF_DWARF')
   
   env['extern_lib_dir']  = '%(xedext_dir)s/external/lin/lib%(arch)s'

   env['libdwarf'] = '%(extern_lib_dir)s/libdwarf.so'
   env['libelf']   = env.expand('%(extern_lib_dir)s/libelf.so.0.8.13')
   env['libelf_symlink'] = 'libelf.so.0'
   env['libelf_license'] = env.expand('%(xedext_dir)s/external/EXTLICENSE.txt')
   if env.on_freebsd():
      env['LINKFLAGS'] += " -Wl,-z,origin"

   env['LINKFLAGS'] += " -L%(extern_lib_dir)s"
   if installing(env):
      env['LINKFLAGS'] += " -Wl,-rpath,'$ORIGIN/../extlib'"
   else:
      # this case is a little ambiguous. If not making a kit we
      # just use a full path to the source tree.
      p = os.path.abspath(env.expand("%(extern_lib_dir)s"))
      env['LINKFLAGS'] += " -Wl,-rpath," + p

   env['ext_libs' ].append(env['libelf'])
   env['ext_libs' ].append(env['libdwarf'])
   
def cond_add_elf_dwarf(env):
   "Set up for using libelf/libdwarf on linux."
   
   if 'ext_libs' not in env:
      env['ext_libs'] = []

   if env['use_elf_dwarf']:
      if not env.on_linux():
         die("No libelf/dwarf for this platform")
   else:
      return

   mbuild.msgb("ADDING ELF/DWARF")
   # set up the preprocessor define and linker requirements.
   _use_elf_dwarf(env)

   if env['use_elf_dwarf_precompiled']:
      mbuild.msgb("ADDING ELF/DWARF PRECOMPILED")
      _add_elf_dwarf_precompiled(env)
   else:
      env.add_include_dir('/usr/include/libdwarf')

#    
###########################################################################
