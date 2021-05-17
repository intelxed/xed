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

import sys
import os
import re
import shutil
import copy
import time
import types
import optparse
# sys.path is set up by calling script (mfile.py ususally)
import mbuild 
import xed_build_common as xbc    

def ex_compile_and_link(env, dag, src, objs):
   """Return the  exe name - used for the examples"""
   basename = os.path.basename(src)
   exe = env.build_dir_join(env.resuffix(basename, env['EXEEXT']))
   all_obj = []
   
   # first_example_lib and last_example_lib are for supporting
   # compilations using custom C runtimes.
   if 'first_example_lib' in env:
        all_obj.append(env['first_example_lib'])
   all_obj.extend(env.compile(dag, [src]))
   all_obj.extend(objs)
   if 'last_example_lib' in env:
        all_obj.append(env['last_example_lib'])
        
   lc = env.link(all_obj, exe)
   cmd = dag.add(env,lc)
   return cmd.targets[0]

###########################################################################

def mkenv():
    """External entry point: create the environment"""
    if sys.version_info[0] == 3 and sys.version_info[1] < 4:        
        _fatal("Need python version 3.4 or later.")
    elif sys.version_info[0] == 2 and sys.version_info[1] < 7:        
        _fatal("Need python version 2.7 or later.")
    # create an environment, parse args
    env = mbuild.env_t()
    standard_defaults = dict(    doxygen_install='',
                                 doxygen='',
                                 clean=False,
                                 die_on_errors=True,
                                 xed_messages=False,
                                 xed_asserts=False,
                                 pedantic=True,
                                 clr=False,
                                 use_werror=True,
                                 dbghelp=False,
                                 install_dir='',
                                 kit_kind='base',
                                 win=False,
                                 dev=False,
                                 legal_header=None,
                                 encoder=True,
                                 enc2=True,
                                 decoder=True,
                                 ld_library_path=[],
                                 ld_library_path_for_tests=[],
                                 use_elf_dwarf=False,
                                 use_elf_dwarf_precompiled=False,
                                 strip='strip',
                                 verbose = 1,
                                 example_linkflags='',
                                 example_flags='',
                                 example_rpaths=[],
                                 android=False,
                                 xed_inc_dir=[],
                                 xed_lib_dir='',
                                 xed_enc2_libs=[],
                                 xed_dir='',
                                 build_cpp_examples=False,
                                 set_copyright=False,
                                 pin_crt='')

    env['xed_defaults'] = standard_defaults
    env.set_defaults(env['xed_defaults'])
    return env

def xed_args(env):
    """For command line invocation: parse the arguments"""
    env.parser.add_option("--no-encoder", 
                          dest="encoder",
                          action="store_false",
                          help="No encoder")
    env.parser.add_option("--no-enc2", 
                          dest="enc2",
                          action="store_false",
                          help="No enc2 encoder")
    env.parser.add_option("--no-decoder", 
                          dest="decoder",
                          action="store_false",
                          help="No decoder")
    env.parser.add_option("--android", 
                          dest="android",
                          action="store_true",
                          help="Android build (avoid rpath for examples)")
    env.parser.add_option("--example-linkflags", 
                          dest="example_linkflags",
                          action="store",
                          help="Extra link flags for the examples")
    env.parser.add_option("--example-flags", 
                          dest="example_flags",
                          action="store",
                          help="Extra compilation flags for the examples")
    env.parser.add_option("--example-rpath", 
                          dest="example_rpaths",
                          action="append",
                          help="Extra rpath dirs for examples")
    env.parser.add_option("-c","--clean", 
                          dest="clean", 
                          action="store_true",
                          help="Clean targets")
    env.parser.add_option("--keep-going", '-k', 
                          action="store_false",
                          dest="die_on_errors",
                          help="Keep going after errors occur when building")
    env.parser.add_option("--messages", 
                          action="store_true",
                          dest="xed_messages",
                          help="Enable use xed's debug messages")
    env.parser.add_option("--no-pedantic", 
                          action="store_false",
                          dest="pedantic",
                          help="Disable -pedantic (gnu/clang compilers).")
    env.parser.add_option("--asserts", 
                          action="store_true",
                          dest="xed_asserts",
                          help="Enable use xed's asserts")
    env.parser.add_option("--clr", 
                          action="store_true", 
                          dest="clr",
                          help="Compile for Microsoft CLR")
    env.parser.add_option("--no-werror", 
                          action="store_false",
                          dest="use_werror",
                          help="Disable use of -Werror on GNU compiles")
    env.parser.add_option("--dbghelp", 
                          action="store_true", 
                          dest="dbghelp",
                          help="Use dbghelp.dll on windows.")
    env.parser.add_option("--install-dir", 
                          dest="install_dir",
                          action="store",
                          help="XED Install directory. " +
                          "Default: kits/xed-install-date-os-cpu")
    env.parser.add_option("--kit-kind", 
                          dest="kit_kind", 
                          action="store",
                          help="Kit version string.  " +
                          "The default is 'base'")
    env.parser.add_option("--win", 
                          action="store_true", 
                          dest="win",
                          help="Add -mno-cygwin to GCC-on-windows compilation")
    env.parser.add_option("--ld-library-path", 
                          action="append",
                          dest="ld_library_path",
                          help="Specify additions to LD_LIBRARY_PATH " +
                          "for use when running ldd and making kits")
    env.parser.add_option("--ld-library-path-for-tests", 
                          action="append",
                          dest="ld_library_path_for_tests",
                          help="Specify additions to LD_LIBRARY_PATH " +
                          "for use when running the tests")

    # elf.h is different than libelf.h.
    env.parser.add_option("--elf-dwarf", "--dwarf",
                          action="store_true",
                          dest="use_elf_dwarf",
                          help="Use libelf/libdwarf. (Linux only)")
    env.parser.add_option("--elf-dwarf-precompiled", 
                          action="store_true",
                          dest="use_elf_dwarf_precompiled",
                          help="Use precompiled libelf/libdwarf from " +
                          " the XED source distribution." + 
                          " This is the currently required" +
                          " if you are installing a kit." +
                          " Implies the --elf-dwarf knob."
                          " (Linux only)")
    env.parser.add_option("--strip", 
                          action="store",
                          dest="strip",
                          help="Path to strip binary. (Linux only)")
    env.parser.add_option("--pin-crt", 
                          action="store",
                          dest="pin_crt",
                          help="Compile for the Pin C-runtime. Specify" +
                          " path to pin kit")
    env.parser.add_option("--lib-dir", 
                          action='store',
                          dest="xed_lib_dir",
                          help="directory where libxed* is located.")
    env.parser.add_option("--enc2-lib", 
                          action='append',
                          dest="xed_enc2_libs",
                          help="Filenames (with paths) of the XED enc2 libraries.")
    env.parser.add_option("--inc-dir", 
                          action="append",
                          dest="xed_inc_dir",
                          help="directory where xed generated headers are located.")
    env.parser.add_option("--xed-dir", 
                          action="store",
                          dest="xed_dir",
                          help="directory where xed sources are located.")
    env.parser.add_option("--build-cpp-examples", 
                          action="store_true",
                          dest="build_cpp_examples",
                          help="Build the C++ examples default: False.")
    env.parser.add_option("--set-copyright", 
                          action="store_true",
                          dest="set_copyright",
                          help="Set the Intel copyright on Windows XED executable")

    env.parse_args(env['xed_defaults'])
    
def nchk(env,s):
    #null string check or not set check
    if s not in env or len(env[s]) == 0:
       return True
    return False
 
def init(env):
    xbc.init(env)
    if nchk(env,'xed_lib_dir'):
        env['xed_lib_dir'] = '../lib'


    if nchk(env,'xed_enc2_libs'):
        env['xed_enc2_libs'] = ( mbuild.glob(env['xed_lib_dir'],'*xed-chk-enc2-*') + 
                                 mbuild.glob(env['xed_lib_dir'],'*xed-enc2-*')      )
    if nchk(env,'xed_enc2_libs'):
        # do not build enc2 examples if libraries are missing
        env['enc2'] = False
        
    if nchk(env,'xed_inc_dir'):
        env['xed_inc_dir'] = ['../include']
    if nchk(env,'xed_dir'):
        env['xed_dir'] = '..'
    env.add_include_dir( env['src_dir'] )  # examples dir
    for inc in  env['xed_inc_dir']: 
        env.add_include_dir( inc )

def _wk_show_errors_only():
    #True means show errors only when building.
    if mbuild.verbose(2):
        return False # show output
    return True # show errors only.


def _add_libxed_rpath(env):
   """Make example tools refer to the libxed.so from the lib directory"""
   if env['shared'] and env.on_linux() and not env['android']:
       env['LINKFLAGS'] += " -Wl,-rpath,'$ORIGIN/../lib'"


def build_asmparse(env, dag, otherobj):
    srcs = env.src_dir_join(['xed-asmparse.c'])
    objs = env.compile(dag, srcs)

    exe = ex_compile_and_link(env,
                              dag,
                              env.src_dir_join('xed-asmparse-main.c'),
                              objs + otherobj + [env['link_libxed']])
    return exe

      

def build_examples(env, work_queue):
    """Build the examples"""
    example_exes = [] 
    env['example_exes'] = []  # used by install
    examples_dag = mbuild.dag_t('xedexamples', env=env)
    
    if not env.on_windows():
        for d in env['example_rpaths']:
            env.add_to_var('example_linkflags',
                                   '-Wl,-rpath,{}'.format(d))
    env.add_to_var('LINKFLAGS', env['example_linkflags'])
    env.add_to_var('CCFLAGS', env['example_flags'])
    env.add_to_var('CXXFLAGS', env['example_flags'])
    mbuild.cmkdir(env['build_dir'])

    link_libxed = env['link_libxed']
    
    if env['shared']:
       _add_libxed_rpath(env)

    # C vs C++: env is for C++ and env_c is for C programs.
    if env['compiler'] in  ['gnu','clang', 'icc']:
        env['LINK'] = env['CXX']
    env_c = copy.deepcopy(env)
    if env_c['compiler'] in ['gnu','clang']:
        env_c['LINK'] = '%(CC)s'
        
    if env['pin_crt']:
        xbc.compile_with_pin_crt_lin_mac_common_cplusplus(env)
    
    # shared files
    cc_shared_files = env.src_dir_join([ 
          'xed-examples-util.c'])
    if env['decoder']:
        cc_shared_files.extend(env.src_dir_join([ 
          'xed-dot.c',
          'xed-dot-prep.c']))
        
    if env['encoder']:
       cc_shared_files += env.src_dir_join([ 'xed-enc-lang.c'])
    cc_shared_objs  = env.compile( examples_dag, cc_shared_files)
    # the XED command line tool
    xed_cmdline_files = [ 'xed-disas-raw.c',
                          'avltree.c',
                          'xed-disas-hex.c',
                          'xed-symbol-table.c']
    if env.on_windows() and env['set_copyright']:
        # AUTOMATICALLY UPDATE YEAR IN THE RC FILE
        year = time.strftime("%Y")
        lines = open(env.src_dir_join('xed-rc-template.txt')).readlines()
        lines = [ re.sub('%%YEAR%%',year,x) for x in lines ]
        xbc.write_file(env.src_dir_join('xed.rc'), lines)
        xed_cmdline_files.append("xed.rc")
        
    extra_libs = []    
    if env['decoder']:

        if env.on_linux() or env.on_freebsd() or env.on_netbsd():
            xed_cmdline_files.append('xed-disas-filter.c')
            xed_cmdline_files.append('xed-nm-symtab.c')
            
        elif env.on_mac():
            xed_cmdline_files.append('xed-disas-macho.c')

        elif env.on_windows():
            xed_cmdline_files.append('xed-disas-pecoff.cpp')
            if ( env['dbghelp'] and 
                 env['msvs_version'] not in ['6','7'] ):
                env.add_define("XED_DBGHELP")
                xed_cmdline_files.append('udhelp.cpp')
                extra_libs = ['dbghelp.lib', 'version.lib' ]

    xed_cmdline_files = env.src_dir_join(xed_cmdline_files)
    xed_cmdline_obj = copy.deepcopy(cc_shared_objs)

    # Env for cmdline tool (with libelf/dwarf on linux.)
    if env.on_windows():  # still C++
        cenv = copy.deepcopy(env)
    else: # lin/mac are C code only.
        cenv = copy.deepcopy(env_c)
        
    if env.on_linux():
        xbc.cond_add_elf_dwarf(cenv)
        
    if env.on_linux() or env.on_freebsd() or env.on_netbsd():
        src_elf = env.src_dir_join('xed-disas-elf.c')
        if env['use_elf_dwarf_precompiled']:
            cenv2 = copy.deepcopy(cenv)
            # need to remove -pedantic because of redundant typedef Elf in dwarf header file
            cenv2.remove_from_var('CCFLAGS','-pedantic')
            xed_cmdline_obj += cenv2.compile(examples_dag, [src_elf])
        else:
            xed_cmdline_files.append(src_elf)
            
    xed_cmdline_obj += cenv.compile(examples_dag, xed_cmdline_files)
    xed_cmdline = ex_compile_and_link(cenv, examples_dag,
                                      env.src_dir_join('xed.c'),
                                      xed_cmdline_obj + [link_libxed] +
                                      extra_libs)

    mbuild.msgb("CMDLINE", xed_cmdline)
    example_exes.append(xed_cmdline)

    if env['encoder']:
        exe = build_asmparse(cenv, examples_dag, cc_shared_objs)
        example_exes.append(exe)
        

    ild_examples = []
    other_c_examples = []
    enc2_examples = []
    small_examples = ['xed-size.c']
    if env['enc2']:
        enc2_examples += [ 'xed-enc2-1.c',
                           'xed-enc2-2.c',
                           'xed-enc2-3.c' ]
    if env['encoder']:
       small_examples += ['xed-ex5-enc.c']
       other_c_examples += ['xed-ex3.c']
    if env['decoder'] and env['encoder']:
       other_c_examples += ['xed-ex6.c',
                            'xed-ex9-patch.c' ]
    if env['decoder']:
       ild_examples += [ 'xed-ex-ild.c' ]
       other_c_examples += ['xed-ex1.c',
                            'xed-ex-ild2.c',
                            'xed-min.c',
                            'xed-reps.c',
                            'xed-ex4.c',
                            'xed-tester.c',
                            'xed-dec-print.c',           
                            'xed-ex-agen.c',
                            'xed-ex7.c',
                            'xed-ex8.c',
                            'xed-ex-cpuid.c',
                            'xed-tables.c',
                            'xed-find-special.c',                            
                            'xed-dll-discovery.c']

    # compile & link other_c_examples
    for example in env.src_dir_join(other_c_examples):
        example_exes.append(ex_compile_and_link(env_c,
                                                examples_dag,
                                                example,
                                                cc_shared_objs + [ link_libxed ]))
    # compile & link ild_examples
    if os.path.exists(env['link_libild']):
        for example in env.src_dir_join(ild_examples):
            example_exes.append(ex_compile_and_link(env_c,
                                                    examples_dag,
                                                    example,
                                                    [ env['link_libild'] ]))
            
    # compile & link small_examples
    for example in env.src_dir_join(small_examples):
        example_exes.append(ex_compile_and_link(env_c,
                                                examples_dag,
                                                example,
                                                [ link_libxed ]))
    
    for example in env.src_dir_join(enc2_examples):
        example_exes.append(ex_compile_and_link(  env_c,
                                                  examples_dag,
                                                  example,
                                                  env['xed_enc2_libs'] + [link_libxed]  ))

    mbuild.vmsgb(4, "ALL EXAMPLES", "\n\t".join(example_exes))

    examples_to_build   = example_exes
    env['example_exes'] = example_exes
    
    mbuild.msgb("BUILDING EXAMPLES")
    okay = work_queue.build(examples_dag,
                            targets=examples_to_build,
                            die_on_errors=env['die_on_errors'],
                            show_progress=True, 
                            show_output=True,
                            show_errors_only=_wk_show_errors_only())
    if not okay:
        xbc.cdie( "XED EXAMPLES build failed")
    mbuild.vmsgb(3, "XED EXAMPLES", "build succeeded")
    return 0

def verify_args(env):
    if env['use_elf_dwarf_precompiled']:
       env['use_elf_dwarf'] = True

def examples_work(env):
    """External entry point for non-command line invocations.
    Initialize the environment, build libxed, the examples, the kit
    and run the tests"""
    xbc.prep(env)
    verify_args(env)
    start_time=mbuild.get_time()
    xbc.init_once(env)
    
    init(env)
    
    if 'clean' in env['targets'] or env['clean']:
        xbc.xed_remove_files_glob(env)
        if len(env['targets'])<=1:
            xbc.cexit(0)

    mbuild.cmkdir(env['build_dir'])
    
    work_queue = mbuild.work_queue_t(env['jobs']) 

    xbc.get_libxed_names(env)
    retval = build_examples(env, work_queue)
    end_time=mbuild.get_time()
    mbuild.msgb("EXAMPLES BUILD ELAPSED TIME",
                mbuild.get_elapsed_time(start_time, end_time))
    return retval

def execute():
    """Main external entry point for command line invocations"""
    
    import mbuild
    env = mkenv()
    # xed_args() is skip-able for remote (import) invocation. The env
    # from mkenv can be updated programmatically. One must call
    # xbc.set_xed_defaults(env) if not calling xed_args(env)
    xed_args(env)  # parse command line knobs
    retval = examples_work(env)
    return retval
