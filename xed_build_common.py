#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2019 Intel Corporation
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
        return "KIND: %s VALUE: %d MSG: %s" % (kind, value, msg)

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

def compile_with_pin_crt_lin_mac_common_cplusplus(env):
    env.add_to_var('LINKFLAGS','-lstlport-dynamic')
    env.add_to_var('CXXFLAGS','-fno-exceptions')
    env.add_to_var('CXXFLAGS', '-fno-rtti')
    
def _compile_with_pin_crt_lin_mac_common(env):    
    env.add_system_include_dir('%(pin_root)s/extras/stlport/include')
    env.add_system_include_dir('%(pin_root)s/extras/libstdc++/include')
    env.add_system_include_dir('%(pin_root)s/extras/crt/include')
    env.add_system_include_dir(
        '%(pin_root)s/extras/crt/include/arch-%(bionic_arch)s')
    env.add_system_include_dir(
        '%(pin_root)s/extras/crt/include/kernel/uapi')
    env.add_system_include_dir(
        '%(pin_root)s/extras/crt/include/kernel/uapi/asm-x86')

    env.add_to_var('LINKFLAGS','-nostdlib')
    env.add_to_var('LINKFLAGS','-lc-dynamic')
    env.add_to_var('LINKFLAGS','-lm-dynamic')
    env.add_to_var('LINKFLAGS','-L%(pin_crt_dir)s')

    # FIXME: if we ever support kits with Pin CRT, we'll need to copy
    # the PINCRT to the XED kit and use a different rpath.
    env.add_to_var('example_linkflags','-Wl,-rpath,%(pin_crt_dir)s')

    # -lpin3dwarf FIXME

    if env['shared']:
        # when building dynamic library
        env['first_lib'] = '%(pin_crt_dir)s/crtbeginS%(OBJEXT)s'
    env['first_example_lib'] = '%(pin_crt_dir)s/crtbegin%(OBJEXT)s'

    _add_to_flags(env,'-funwind-tables')
    
def _compile_with_pin_crt_lin(env):
    _compile_with_pin_crt_lin_mac_common(env)
    env.add_define('TARGET_LINUX')
    if env['shared']:
        env['last_lib'] = '%(pin_crt_dir)s/crtendS%(OBJEXT)s' 
    env['last_example_lib'] = '%(pin_crt_dir)s/crtend%(OBJEXT)s'    
    
def _compile_with_pin_crt_mac(env):
    _compile_with_pin_crt_lin_mac_common(env)
    env.add_define('TARGET_MAC')
    env.add_to_var('LINKFLAGS','-Wl,-no_new_main')
    
def _compile_with_pin_crt_win(env):
    env.add_include_dir('%(pin_root)s/extras/stlport/include')
    env.add_include_dir('%(pin_root)s/extras')
    env.add_include_dir('%(pin_root)s/extras/libstdc++/include')
    env.add_include_dir('%(pin_root)s/extras/crt/include')
    env.add_include_dir('%(pin_root)s/extras/crt')
    env.add_include_dir('%(pin_root)s/extras/crt/include/arch-%(bionic_arch)s')
    env.add_include_dir('%(pin_root)s/extras/crt/include/kernel/uapi')
    env.add_include_dir('%(pin_root)s/extras/crt/include/kernel/uapi/asm-x86')

    env.add_to_var('LINKFLAGS','/NODEFAULTLIB')
    env.add_to_var('LINKFLAGS','stlport-static.lib')
    env.add_to_var('LINKFLAGS','m-static.lib')
    env.add_to_var('LINKFLAGS','c-static.lib')
    env.add_to_var('LINKFLAGS','os-apis.lib')
    env.add_to_var('LINKFLAGS','ntdll-%(arch)s.lib')
    env.add_to_var('LINKFLAGS','/IGNORE:4210')
    env.add_to_var('LINKFLAGS','/IGNORE:4049')
    env.add_to_var('LINKFLAGS','/LIBPATH:%(pin_crt_dir)s')
    env.add_to_var('LINKFLAGS','/LIBPATH:%(pin_root)s/%(pin_arch)s/lib-ext')

    # for DLLs
    if env['shared']:
        env['first_lib'] = '%(pin_crt_dir)s/crtbeginS%(OBJEXT)s'

    # for EXEs
    env['first_example_lib'] = '%(pin_crt_dir)s/crtbegin%(OBJEXT)s'

    _add_to_flags(env,'/GR-')
    _add_to_flags(env,'/GS-')

    env['original_windows_h_path'] = mbuild.join(
                                   os.environ['WindowsSdkDir'], 'Include','um')
    env.add_define('_WINDOWS_H_PATH_="%(original_windows_h_path)s"')
    _add_to_flags(env,'/FIinclude/msvc_compat.h')
    env.add_define('TARGET_WINDOWS')
       
def _compile_with_pin_crt(env):
   if env['arch'] == '32':
       env['pin_arch'] = 'ia32'
       env['bionic_arch'] = 'x86'       
       env.add_define('TARGET_IA32')
   else:
       env['pin_arch'] = 'intel64'
       env['bionic_arch'] = 'x86_64'
       env.add_define('TARGET_IA32E')

   env['pin_root'] = env['pin_crt']
   env['pin_crt_dir'] = '%(pin_root)s/%(pin_arch)s/runtime/pincrt'
   env.add_define('__PIN__=1')
   env.add_define('PIN_CRT=1')

   env.add_include_dir('%(pin_root)s/extras/stlport/include')
   env.add_include_dir('%(pin_root)s/extras')
   env.add_include_dir('%(pin_root)s/extras/libstdc++/include')
   env.add_include_dir('%(pin_root)s/extras/crt/include')
   env.add_include_dir('%(pin_root)s/extras/crt')
   env.add_include_dir('%(pin_root)s/extras/crt/include/arch-%(bionic_arch)s')
   env.add_include_dir('%(pin_root)s/extras/crt/include/kernel/uapi')
   env.add_include_dir('%(pin_root)s/extras/crt/include/kernel/uapi/asm-x86')

   if get_arch(env) == '32':
       env.add_define('__i386__')
   else:
       env.add_define('__LP64__')   
    
   if env.on_linux():
       _compile_with_pin_crt_lin(env)
   elif env.on_mac():
       _compile_with_pin_crt_mac(env)
   elif env.on_windows():
       _compile_with_pin_crt_win(env)
       
def  _gcc_version_string(env):
    gcc = env.expand('%(CC)s')
    vstr = mbuild.get_gcc_version(gcc)
    return vstr

def  _greater_than_gcc(env,amaj,amin,aver):
    vstr = _gcc_version_string(env)
    try:
        (vmaj, vmin, vver) = vstr.split('.')
    except:
        return False
    vmaj = int(vmaj)
    vmin = int(vmin)
    vver = int(vver)
    if vmaj > amaj:
        return True
    if vmaj == amaj and vmin > amin:
        return True
    if vmaj == amaj and vmin == amin and vver >= aver:
        return True
    return False

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
    if env['compiler'] != 'icc':
        flags += ' -Wno-long-long'
        flags += ' -Wno-unknown-pragmas'
        flags += ' -fmessage-length=0'
        flags += ' -pipe'

    # -pg is incompatible with -fomit-frame-pointer
    if (re.search(r' -pg', env['CXXFLAGS']) == None and 
        re.search(r' -pg', env['CCFLAGS']) == None  and 
        (env['compiler'] != 'icc' or env['icc_version'] not in ['7','8'])):
        flags += ' -fomit-frame-pointer'

    if env['compiler'] != 'icc' or (env['compiler'] == 'icc' and 
                                    env['icc_version'] != '7'):
        flags += ' -fno-exceptions'

    # 2019-06-05: disabled - no longer needed
    # required for gcc421 xcode to avoidundefined symbols when linking tools.
    #if env.on_mac():
    #    flags += ' -fno-common'

    if env['build_os'] == 'win' or _greater_than_gcc(env,4,9,0):
        flags += ' -Wformat-security'
        flags += ' -Wformat'
    else:
        # gcc3.4.4 on windows has problems with %x for xed_int32_t.
        # gcc4.9.2 works well.
        flags += ' -Wno-format'
        flags += ' -Wno-format-security'

    if env['compiler'] != 'icc':
        # c99 is required for c++ style comments.
        env['CSTD'] = 'c99'
        env['CCFLAGS'] += ' -std=%(CSTD)s '
        if env['pedantic']:
            env['CCFLAGS'] += ' -pedantic '

    if env['shared']:
        if not env.on_windows():
            # -fvisibility=hidden only works on gcc>4. If not gcc,
            # assume it works. Really only a problem for older icc
            # compilers.
            if env['compiler'] == 'gcc':
                vstr = _gcc_version_string(env)
                mbuild.msgb("GCC VERSION", vstr)
            if env['compiler'] != 'gcc' or _greater_than_gcc(env,4,0,0):
                hidden = ' -fvisibility=hidden' 
                env['LINKFLAGS'] += hidden
                flags += hidden
        
    env['CCFLAGS'] += flags
    env['CCFLAGS'] += ' -Wstrict-prototypes'
    env['CCFLAGS'] += ' -Wwrite-strings'
    if env['compiler'] != 'icc':
        env['CCFLAGS'] += ' -Wredundant-decls'

    # Disabled the following. Generates too many silly errors/warnings
    #env['CCFLAGS'] += ' -Wmissing-prototypes'

    env['CXXFLAGS'] += flags

def set_env_clang(env):
   set_env_gnu(env)
   env['CCFLAGS'] += ' -Wno-language-extension-token'
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
    
    if env['compiler'] == 'gnu':
        set_env_gnu(env)
    elif env['compiler'] == 'clang':
        set_env_clang(env)
    elif env['compiler'] == 'ms':
        set_env_ms(env)
    elif env['compiler'] == 'icc':
        set_env_icc(env)
    elif env['compiler'] == 'icl':
        set_env_icl(env)
    else:
        cdie("Unknown compiler: " + env['compiler'])
        
    if env['pin_crt']:
        _compile_with_pin_crt(env)
    
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
