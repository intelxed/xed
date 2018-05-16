#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2018 Intel Corporation
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

############################################################################
#See the execute() and work() functions down at the bottom of the file
#for the main routine.
############################################################################

## START OF IMPORTS SETUP
from __future__ import print_function
import sys
import os
import re
import shutil
import copy
import time
import glob
import types
import optparse
import collections
import stat

def _fatal(m):
    sys.stderr.write("\n\nXED ERROR: %s\n\n" % (m) )
    sys.exit(1)

try:
    import mbuild
except:
    _fatal("xed_mbuild.py could not find/import mbuild."  +
           " Should be a sibling of the xed directory.")
import xed_build_common as xbc
try:
   import xed_build_common as xbc
except:
   _fatal("xed_mbuild.py could not import xed_build_common.py")


## END OF IMPORTS SETUP
############################################################################

def aq(s):
    t = mbuild.cond_add_quotes(s)
    return t

def check_mbuild_file(mbuild_file, sig_file):
    if os.path.exists(sig_file):
        old_hash = open(sig_file,"r").readline().strip()
    else:
        old_hash = ''
    hash = mbuild.hash_list(open(sys.argv[0],'r').readlines())
    f = open(sig_file, 'w')
    f.write(hash)
    f.close()

    if hash == old_hash:
        retval = False
        mbuild.msgb("MBUILD INPUT FILE", "does not appear to have changes.")
    else:
        retval = True
        mbuild.msgb("MBUILD INPUT FILE", "appears to have changes.")
    return retval

def _write_file(fn, stream):
    """Write stream to fn"""
    mbuild.msgb("WRITING", fn)
    f = open(fn,'w')
    f.writelines(stream)
    f.close()

###########################################################################
# generators
    
class generator_inputs_t(object):
    def __init__(self, build_dir, 
                 amd_enabled=True,
                 limit_strings=False):
        self.fields = ['dec-spine',
                       'dec-instructions',
                       'enc-instructions',
                       'dec-patterns',
                       'enc-patterns',
                       'enc-dec-patterns', # decode patterns used for encode
                       'fields',
                       'state',
                       'registers',
                       'widths',
                       'extra-widths',
                       'pointer-names',
                       'element-types',
                       'element-type-base',
                       'chip-models',
                       'conversion-table',
                       'ild-scanners',
                       'ild-getters',
                       'cpuid'
                       ]
        self.files = {} # lists of input files per field type
        self.priority = {} # field type -> int

        # output file names. We concatenate all the input files of a
        # given type. These get used in the command are internal to the
        # execution of the generator.
        self.file_name = {}
        for fld in self.fields:
            self.files[fld] = [] # list of input files
            self.file_name[fld] = 'all-' + fld + '.txt'

        self.renamed = False
        self.intermediate_dir = None
        self.set_intermediate_dir(build_dir)
        self.use_intermediate_files()
        self.amd_enabled = amd_enabled
        self.limit_strings = limit_strings

    def add_file(self, file_type, file_name, priority=1):
        """Add a specific type of file to the right list"""

        curp = 1
        if file_type in self.priority:
           curp = self.priority[file_type]

        if curp > priority:
           mbuild.msgb("Skipping low priority file for type %s:  %s" % 
                       (file_type, file_name))
           return
        elif curp < priority:
           # new higher priority file blows away the list of files for
           # this file type.
           mbuild.msgb("Clearing file list for type %s: [ %s ]" % 
                       (file_type, 
                        ", ".join(self.files[file_type])))
           self.files[file_type] = []
           self.priority[file_type]=priority

        if file_name in self.files[file_type]:
            xbc.cdie('duplicate line: {}:{}'.format(file_type,file_name))
        self.files[file_type].append(file_name)

    def remove_file(self, file_type, file_name):
        """Remove a specific  file"""
        try:
            self.files[file_type].remove(file_name)
        except:
            xbc.cdie("Invalid type of file " +
                       "(%s) or file name (%s) not found: " % (file_type, 
                                                               file_name) )

    def clear_files(self,file_type):
        """Remove a specific type of file"""
        try:
            self.files[file_type]  = []
            mbuild.msgb("REMOVING FILE TYPE", file_type)
        except:
            xbc.cdie("Invalid type of file (%s) not found: " %
                 (file_type))
            
    def all_input_files(self):
        """Return a list of all the input file names so we can hook up
        the dependences"""
        fnames = []
        for flist in iter(self.files.values()):
            fnames.extend(flist)
        fnames.sort()
        return fnames
    
    def set_intermediate_dir(self, build_dir):
        self.intermediate_dir = mbuild.join(build_dir,'dgen')
        mbuild.cmkdir(self.intermediate_dir)

    def use_intermediate_files(self):
        """Prefix al the files by the intermediate directory name"""
        # just do this once
        if self.renamed:
            return
        self.renamed = True
        
        for f in self.fields:
            ofn = mbuild.join(self.intermediate_dir,self.file_name[f])
            self.file_name[f] = ofn # update file name-- only call once!
        
    def concatenate_input_files(self,env):
        """Concatenate all the files of each type"""
        for f in self.fields:
            self.concatenate_one_set_of_files(env,
                                              self.file_name[f],
                                              self.files[f])

    def decode_command(self, xedsrc, extra_args=None, on_windows=False):
        """Produce a decoder generator command"""
        s = []
        s.append( '%(pythonarg)s' )
        # s.append("-3") # python3.0 compliance checking using python2.6
        s.append(aq(mbuild.join(xedsrc,'pysrc','generator.py')))
        if self.limit_strings:
           s.append('--limit-enum-strings')
        s.append('--spine ' + aq(self.file_name['dec-spine']))
        s.append('--isa ' + aq(self.file_name['dec-instructions']))
        s.append('--patterns ' + aq(self.file_name['dec-patterns']))
        s.append('--input-fields ' + aq(self.file_name['fields']))
        s.append('--input-state ' + aq(self.file_name['state']))
        s.append('--chip-models ' + aq(self.file_name['chip-models']))
        s.append('--ctables ' + aq(self.file_name['conversion-table']))
        s.append('--input-regs ' +  aq(self.file_name['registers']))
        s.append('--input-widths ' + aq(self.file_name['widths']))
        s.append('--input-extra-widths ' +
                 aq(self.file_name['extra-widths']))
        s.append('--input-element-types ' +
                 aq(self.file_name['element-types']))
        s.append('--input-element-type-base ' +
                 aq(self.file_name['element-type-base']))
        s.append('--input-pointer-names ' +
                 aq(self.file_name['pointer-names']))
        s.append('--ild-scanners ' +
                 aq(self.file_name['ild-scanners']))
        s.append('--cpuid ' +
                 aq(self.file_name['cpuid']))
        if len(self.files['ild-getters']) > 0:
            s.append('--ild-getters ' +
                     aq(self.file_name['ild-getters']))
        if extra_args:
            s.append(extra_args)
        return ' '.join(s)

    def encode_command(self, xedsrc, extra_args=None, on_windows=False, amd_enabled=True):
        """Produce a decoder generator command"""
        s = []
        s.append( '%(pythonarg)s' )
        # s.append("-3") # python3.0 compliance checking using python2.6
        s.append( aq(mbuild.join(xedsrc,'pysrc', 'read-encfile.py')))
        s.append('--isa %s' % aq(self.file_name['enc-instructions']))
        s.append('--enc-patterns %s' % aq(self.file_name['enc-patterns']))
        s.append('--enc-dec-patterns %s' %
                 aq(self.file_name['enc-dec-patterns']))
        s.append('--input-fields %s' % aq(self.file_name['fields']))
        s.append('--input-state %s' % aq(self.file_name['state']))
        s.append('--input-regs %s' % aq(self.file_name['registers']))
        if not amd_enabled:
            s.append('--no-amd')
        if extra_args:
            s.append( extra_args)
        return ' '.join(s)

    def concatenate_one_set_of_files(self, env, target, inputs):
        """Concatenate input files creating the target file."""
        try:
            if mbuild.verbose(1):
                mbuild.msgb("CONCAT", "%s <-\n\t\t%s" % (target ,
                                                         '\n\t\t'.join(inputs)))
            output = open(target,"w")
            for f in inputs:
                if os.path.exists(f):
                    output.write("\n\n###FILE: %s\n\n" % (f))
                    for line in open(f,'r').readlines():
                        line = line.rstrip()
                        #replace the possible symbolic path %(cur_dir)s
                        #FIXME: could have used env's expand_string method,
                        #for src_dir and cur_dir.
                        file_dir = os.path.dirname(f)
                        line = line.replace('%(cur_dir)s', file_dir)
                        line = line.replace('%(xed_dir)s', env['src_dir'])
                        output.write(line + "\n")
                else:
                    xbc.cdie("Could not read input file: " + f)
            output.close()
        except xbc.xed_exception_t as e:
            raise  # re-raise exception
        except:
            xbc.cdie("Could not write file %s from inputs: %s" %
                       ( target, ', '.join(inputs)))

def run_generator_preparation(gc, env):
    """Prepare to run the encode and decode table generators"""
    if env == None:
        return (1, ['no env!'])
    
    xedsrc = env['src_dir']
    build_dir = env['build_dir']
    gc.concatenate_input_files(env)

    mbuild.touch(env.build_dir_join('dummy-prep'))
    return (0, [] )

def read_file_list(fn):
    a  = []
    for f in open(fn,'r').readlines():
        a.append(f.rstrip())
    return a

def run_decode_generator(gc, env):
    """Run the decode table generator"""
    if env == None:
        return (1, ['no env!'])
    
    xedsrc = env.escape_string(env['src_dir'])
    build_dir = env.escape_string(env['build_dir'])
    debug = ""
    other_args = " ".join(env['generator_options']) 
    gen_extra_args = "--gendir %s --xeddir %s %s %s" % (build_dir,
                                                        xedsrc, debug,
                                                        other_args)
    if env['gen_ild_storage']:
        gen_extra_args += ' --gen-ild-storage'
    
    if env['compress_operands']:
        gen_extra_args += " --compress-operands" 
        
    cmd = env.expand_string(gc.decode_command(xedsrc,
                                              gen_extra_args,
                                              env.on_windows()))

    if mbuild.verbose(2):
        mbuild.msgb("DEC-GEN", cmd)
    (retval, output, error_output) = mbuild.run_command(cmd,
                                                        separate_stderr=True)
    oo = env.build_dir_join('DEC-OUT.txt')
    oe = env.build_dir_join('DEC-ERR.txt')
    _write_file(oo, output)
    _write_file(oe, error_output)

    if retval == 0:
        list_of_files = read_file_list(gc.dec_output_file)
        mbuild.hash_files(list_of_files, 
                          env.build_dir_join(".mbuild.hash.xeddecgen"))

    mbuild.msgb("DEC-GEN", "Return code: " + str(retval))
    return (retval, error_output )

def run_encode_generator(gc, env):
    """Run the encoder table generator"""
    if env == None:
        return (1, ['no env!'])
    
    xedsrc = env.escape_string(env['src_dir'])
    build_dir = env.escape_string(env['build_dir'])
        
    gen_extra_args = "--gendir %s --xeddir %s" % (build_dir, xedsrc)
    cmd = env.expand_string(gc.encode_command(xedsrc,
                                              gen_extra_args,
                                              env.on_windows(),
                                              env['amd_enabled']))
    if mbuild.verbose(2):
        mbuild.msgb("ENC-GEN", cmd)
    (retval, output, error_output) = mbuild.run_command(cmd,
                                                        separate_stderr=True)
    oo = env.build_dir_join('ENC-OUT.txt')
    oe = env.build_dir_join('ENC-ERR.txt')
    _write_file(oo, output)
    _write_file(oe, error_output)

    if retval == 0:
        list_of_files = read_file_list(gc.enc_output_file)
        mbuild.hash_files(list_of_files, 
                          env.build_dir_join(".mbuild.hash.xedencgen"))

    mbuild.msgb("ENC-GEN", "Return code: " + str(retval))
    return (retval, [] )

def need_to_rebuild(fn,sigfile):
    rebuild = False
    if not os.path.exists(fn):
        return True
    
    list_of_files = read_file_list(fn)
    if mbuild.file_hashes_are_valid(list_of_files, sigfile):
        return False
    return True

###########################################################################
# legal header tagging

def legal_header_tagging(env):
    if 'apply-header' not in env['targets']:
        return
        
    source_files = [ 
        mbuild.join(env['src_dir'],'examples','*.cpp'),
        mbuild.join(env['src_dir'],'examples','*.c'),
        mbuild.join(env['src_dir'],'examples','*.[hH]'),
        mbuild.join(mbuild.join(env['build_dir'],'*.h')),
        mbuild.join(env['src_dir'],'src','*','*.c'),
        mbuild.join(env['src_dir'],'include', 'private','*.h'),
        mbuild.join(env['src_dir'],'include', 'public', 'xed', '*.h') ]
    
    data_files =   [
        mbuild.join(env['src_dir'],'examples','*.py'),
        mbuild.join(env['src_dir'],'scripts','*.py'),
        mbuild.join(env['src_dir'],'pysrc','*.py'),
        mbuild.join(env['src_dir'],'*.py')  ]

    # find and classify the files in datafiles directories
    for root,dirs,files in os.walk( mbuild.join(env['src_dir'],'datafiles') ):
        for f in files :
            fn = mbuild.join(root,f)
            if 'test' not in fn:
                if re.search(r'[~]$',fn):
                    # skip backup files
                    continue
                elif re.search(r'[.][ch]$',fn):
                    source_files.append(fn)
                else:
                    data_files.append(fn)

    if env.on_windows():
        xbc.cdie("ERROR","TAGGING THE IN-USE PYTHON FILES DOES " +
                   "NOT WORK ON WINDOWS.")

    legal_header = open(mbuild.join(env['src_dir'],'misc',
                                    'apache-header.txt'), 'r').readlines()
    header_tag_files(env, source_files, legal_header, script_files=False)
    header_tag_files(env, data_files,   legal_header, script_files=True)
    mbuild.msgb("STOPPING", "after %s" % 'header tagging')
    xbc.cexit(0)

def header_tag_files(env, files, legal_header, script_files=False):
    """Apply the legal_header to the list of files"""
    try: 
       import apply_legal_header
    except:
       xbc.cdie("XED ERROR: mfile.py could not find scripts directory")

    for g in files:
       print("G: ", g)
       for f in glob.glob(g):
          print("F: ", f)
          if script_files:
             apply_legal_header.apply_header_to_data_file(legal_header, f)
          else:
             apply_legal_header.apply_header_to_source_file(legal_header, f)
###########################################################################
# Doxygen build

def doxygen_subs(env,api_ref=True):
   subs = {}
   subs['XED_TOPSRCDIR']   = aq(env['src_dir'])
   subs['XED_KITDIR']      = aq(env['install_dir'])
   subs['XED_GENDOC']      = aq(env['doxygen_install'])
   if api_ref:
      subs['XED_INPUT_TOP'] = aq(env.src_dir_join(mbuild.join('docsrc',
                                                          'xed-doc-top.txt')))
   else:
      subs['XED_INPUT_TOP'] = aq(env.src_dir_join(mbuild.join('docsrc',
                                                            'xed-build.txt')))
   #subs['XED_HTML_HEADER'] = aq(env.src_dir_join(mbuild.join('docsrc',
   #                                                 'xed-doxygen-header.txt')))
   return subs

def make_doxygen_build(env, work_queue):
    """Make the doxygen how-to-build-xed manual"""
    if 'doc-build' not in env['targets']:
        return
    mbuild.msgb("XED BUILDING 'build' DOCUMENTATION")
    e2 = copy.deepcopy(env)
    e2['doxygen_cmd']= e2['doxygen']

    if e2['doxygen_install'] == '':
         d= mbuild.join(e2['build_dir'],'doc')
    else:
         d = env['doxygen_install']
    e2['doxygen_install'] = mbuild.join(d, 'build-manual') 

    mbuild.msgb("BUILDING BUILD MANUAL", e2['doxygen_install'])
    mbuild.cmkdir(e2['doxygen_install'])
    e2['doxygen_config'] = e2.src_dir_join(mbuild.join('docsrc', 
                                                       'Doxyfile.build'))

    subs = doxygen_subs(e2,api_ref=False)
    e2['doxygen_top_src'] = subs['XED_INPUT_TOP'] 
    inputs = [ subs['XED_INPUT_TOP'] ]
    inputs.append(  e2['mfile'] )
    mbuild.doxygen_run(e2, inputs, subs, work_queue, 'dox-build')

def make_doxygen_api(env, work_queue, install_dir):
    """We may install in the kit or elsewhere using files from the kit"""
    mbuild.msgb("XED BUILDING 'api' DOCUMENTATION")
    e2 = copy.deepcopy(env)
    e2['doxygen_cmd']= e2['doxygen']
    e2['doxygen_install'] = mbuild.join(install_dir,'ref-manual')
    mbuild.cmkdir(e2['doxygen_install'])
    e2['doxygen_config'] = e2.src_dir_join(mbuild.join('docsrc','Doxyfile'))
    subs = doxygen_subs(e2,api_ref=True)
    e2['doxygen_top_src'] = subs['XED_INPUT_TOP'] 
    inputs = []
    inputs.append(subs['XED_INPUT_TOP'])
    inputs.extend(  mbuild.glob(mbuild.join(e2['install_dir'],
                                            'include','*')))

    inputs.extend(  mbuild.glob(mbuild.join(e2['install_dir'],
                                            'examples','*.c')))
    inputs.extend(  mbuild.glob(mbuild.join(e2['install_dir'],
                                            'examples','*.cpp')))
    inputs.extend(  mbuild.glob(mbuild.join(e2['install_dir'],
                                            'examples','*.[Hh]')))
    inputs.append(  e2['mfile'] )
    mbuild.doxygen_run(e2, inputs, subs, work_queue, 'dox-ref')

    
def mkenv():
    """External entry point: create the environment"""
    if not mbuild.check_python_version(2,7):
        xbc.cdie("Need python 2.7.x...")

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
                                 gen_ild_storage=False,
                                 show_dag=False,
                                 ext=[],
                                 extf=[],
                                 xedext_dir='%(xed_dir)s/../xedext',
                                 default_isa='',
                                 avx=True,
                                 avx512=True,
                                 knc=False,
                                 ivb=True,
                                 hsw=True,
                                 mpx=True,
                                 cet=True,
                                 skl=True,
                                 skx=True,
                                 cnl=True,
                                 icl=True,
                                 future=True,
                                 knl=True,
                                 knm=True,
                                 bdw=True,
                                 dbghelp=False,
                                 install_dir=None,
                                 prefix_dir='',
                                 prefix_lib_dir='lib',
                                 kit_kind='base',
                                 win=False,
                                 amd_enabled=True,
                                 encoder=True,
                                 decoder=True,
                                 dev=False,
                                 generator_options=[],
                                 legal_header=None,
                                 pythonarg=None,
                                 ld_library_path=[],
                                 ld_library_path_for_tests=[],
                                 use_elf_dwarf=False,
                                 use_elf_dwarf_precompiled=False,
                                 limit_strings=False,
                                 strip='strip',
                                 pti_test=False,
                                 verbose = 0,
                                 compress_operands=False,
                                 test_perf=False,
                                 example_linkflags='',
                                 example_rpaths=[],
                                 android=False,
                                 copy_libc=False,
                                 pin_crt='',
                                 static_stripped=False,
                                 set_copyright=False,
                                 first_lib=None,
                                 last_lib=None)

    env['xed_defaults'] = standard_defaults
    env.set_defaults(env['xed_defaults'])
    return env

def xed_args(env):
    """For command line invocation: parse the arguments"""
    env.parser.add_option("--android", 
                          dest="android",
                          action="store_true",
                          help="Android build (avoid rpath for examples)")
    env.parser.add_option("--copy-runtime-libs", 
                          dest="copy_libc",
                          action="store_true",
                          help="Copy the libc to the kit." +
                          " Rarely necessary if building on old linux " +
                          "dev systems. Default: false")
    env.parser.add_option("--example-linkflags", 
                          dest="example_linkflags",
                          action="store",
                          help="Extra link flags for the examples")
    env.parser.add_option("--example-rpath", 
                          dest="example_rpaths",
                          action="append",
                          help="Extra rpath dirs for examples")
    env.parser.add_option("--doxygen-install", 
                          dest="doxygen_install",
                          action="store",
                          help="Doxygen installation directory")
    env.parser.add_option("--doxygen", 
                          dest="doxygen", 
                          action="store",
                          help="Doxygen command name")
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
    env.parser.add_option("--gen-ild-storage", 
                          action="store_true",
                          dest="gen_ild_storage",
                          help="Dump ILD storage data file.")
    env.parser.add_option("--show-dag",
                          action="store_true",
                          dest="show_dag",
                          help="Show the dependence DAG")

    env.parser.add_option("--ext", 
                          action="append",
                          dest="ext", 
                          help="Add extension files of the form " +
                                "pattern-name:file-name.txt")

    env.parser.add_option("--extf", 
                          action="append", 
                          dest="extf", 
                          help="Add extension configuration files " +
    "that contain lines of form pattern-name:file-name.txt. All files " +
    "references will be made relative to the directory in which the " +
    "config file is located.")

    env.parser.add_option("--xedext-dir", 
                          action="store", 
                          dest="xedext_dir", 
                          help="XED extension dir")

    env.parser.add_option("--default-isa-extf", 
                          action="store",
                          dest="default_isa",
                          help="Override the default ISA files.cfg file")

    env.parser.add_option("--knc",
                          action="store_true",
                          dest="knc", 
                          help="Include KNC support")
    env.parser.add_option("--no-avx",
                          action="store_false",
                          dest="avx", 
                          help="Do not include AVX (nor down-stream unrelated technologies).")
    env.parser.add_option("--no-avx512",
                          action="store_false",
                          dest="avx512", 
                          help="Do not include AVX512 (nor down-stream unrelated technologies).")
    env.parser.add_option("--no-ivb",
                          action="store_false", 
                          dest="ivb", 
                          help="Do not include IVB.")
    env.parser.add_option("--no-hsw",
                          action="store_false", 
                          dest="hsw", 
                          help="Do not include HSW.")
    env.parser.add_option("--no-mpx",
                          action="store_false", 
                          dest="mpx", 
                          help="Do not include MPX.")
    env.parser.add_option("--no-cet",
                          action="store_false", 
                          dest="cet", 
                          help="Do not include CET.")
    env.parser.add_option("--no-knl",
                          action="store_false", 
                          dest="knl", 
                          help="Do no include KNL AVX512{PF,ER}.")
    env.parser.add_option("--no-knm",
                          action="store_false", 
                          dest="knm", 
                          help="Do not include KNM.")
    env.parser.add_option("--no-skl",
                          action="store_false", 
                          dest="skl", 
                          help="Do not include SKL.")
    env.parser.add_option("--no-skx",
                          action="store_false", 
                          dest="skx", 
                          help="Do not include SKX.")
    env.parser.add_option("--no-cnl",
                          action="store_false", 
                          dest="cnl", 
                          help="Do not include CNL.")
    env.parser.add_option("--no-icl",
                          action="store_false", 
                          dest="icl", 
                          help="Do not include ICL.")
    env.parser.add_option("--no-future",
                          action="store_false", 
                          dest="future", 
                          help="Do not include future NI.")
    env.parser.add_option("--dbghelp", 
                          action="store_true", 
                          dest="dbghelp",
                          help="Use dbghelp.dll on windows.")
    env.parser.add_option("--prefix", 
                          dest="prefix_dir",
                          action="store",
                          help="XED System install directory.")
    env.parser.add_option("--prefix-lib-dir", 
                          dest="prefix_lib_dir",
                          action="store",
                          help="library subdirectory name. Default: lib")
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
    env.parser.add_option("--no-amd", 
                          action="store_false",
                          dest="amd_enabled",
                          help="Disable AMD public instructions")
    env.parser.add_option("--limit-strings", 
                          action="store_true",
                          dest="limit_strings",
                          help="Remove some strings to save space.")
    env.parser.add_option("--no-encoder", 
                          action="store_false",
                          dest="encoder",
                          help="Disable the encoder")
    env.parser.add_option("--no-decoder", 
                          action="store_false",
                          dest="decoder",
                          help="Disable the decoder")
    env.parser.add_option("--generator-options", 
                          action="append",
                          dest="generator_options",
                          help="Options to pass through for " + 
                                  "the decode generator")
    env.parser.add_option("--legal-header", 
                          action="store",
                          dest="legal_header",
                          help="Use this special legal header " +
                          "on public header files and examples.")
    env.parser.add_option("--python", 
                          action="store",
                          dest="pythonarg",
                          help="Use a specific version of python " +
                               "for subprocesses.")
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
    env.parser.add_option('--dev', 
                          action='store_true',
                          dest='dev',
                          help='Developer knob. Updates VERSION file')
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
    env.parser.add_option("--pti-test", 
                          action="store_true",
                          dest="pti_test",
                          help="INTERNAL TESTING OPTION.")
    env.parser.add_option("--compress-operands", 
                          action="store_true",
                          dest="compress_operands",
                          help="use bit-fields to compress the "+
                          "operand storage.")
    env.parser.add_option("--test-perf", 
                          action="store_true",
                          dest="test_perf",
                          help="Do performance test (on linux). Requires" + 
                          " specific external test binary.")
    env.parser.add_option("--pin-crt", 
                          action="store",
                          dest="pin_crt",
                          help="Compile for the Pin C-runtime. Specify" +
                          " path to pin kit")
    env.parser.add_option("--static-stripped", 
                          action="store_true",
                          dest="static_stripped",
                          help="Make a static libxed.a renaming internal symbols")
    env.parser.add_option("--set-copyright", 
                          action="store_true",
                          dest="set_copyright",
                          help="Set the Intel copyright on Windows XED executable")

    env.parse_args(env['xed_defaults'])
    
def init_once(env):
    xbc.init_once(env)
    if 'doc' in env['targets']:
        if 'install' not in env['targets']:
            xbc.cdie( "Doxygen API will not get built if not building a\n" +
                       """XED kit using the "install" command line target.""")
    
def init(env):
    if env['pythonarg']:
        python_command = env['pythonarg']
    else:
        python_command = sys.executable
        # Avoid using cygwin python which may be in the PATH of
        # noncygwin shells.
        if env.on_windows() and python_command in ['/bin/python',
                                                   '/usr/bin/python']:
            if env.on_cygwin() and env['compiler'] in ['ms','icl']:
                xbc.cdie("Cannot build with cygwin python. " +
                           "Please install win32 python")
            python_commands = [ 'c:/python27/python.exe',
                                'c:/python26/python.exe',
                                'c:/python25/python.exe' ]
            python_command = None
            for p in python_commands:
               if os.path.exists(p):
                  python_command = p
                  break
            if not python_command:
               xbc.cdie("Could not find win32 python at these locations: %s" %
                          "\n\t" + "\n\t".join(python_commands))
                
    env['pythonarg'] = env.escape_string(python_command)
    if mbuild.verbose(2):
        mbuild.msgb("PYTHON", env['pythonarg'])

    xbc.init(env)
    
    env.add_define('XED_GIT_VERSION="%(xed_git_version)s"')
    if env['shared']:
        env.add_define('XED_DLL')

    env.add_include_dir(mbuild.join(env['src_dir'],"include","private"))
    env.add_include_dir(mbuild.join(env['src_dir'],"include","public"))
    env.add_include_dir(mbuild.join(env['src_dir'],"include","public",'xed'))

    valid_targets = [ 'clean',       'just-prep',
                      'just-gen',    'skip-gen',
                      'install',
                      'apply-header',
                      'skip-lib',
                      'examples',    'cmdline',
                      'doc',         'doc-build',
                      'install',     'zip',
                      'test' ]
    for t in env['targets']:
        if t not in valid_targets:
            xbc.cdie("Invalid target supplied: " + t +
                       "\n  Valid targets:\n\t" +
                       "\n\t".join(valid_targets))
    if 'test' in env['targets']:
        if 'examples' not in env['targets']:
            mbuild.msgb("INFO",
                        "added examples to target list since running tests")
            env['targets'].append('examples')

def _wk_show_errors_only():
    #True means show errors only when building.
    if mbuild.verbose(1):
        return False # show output
    return True # show errors only.

def build_xed_ild_library(env, lib_env, lib_dag, sources_to_replace):
    # compile sources specific to ild
    xed_ild_sources = _get_src(env,'ild')
    ild_objs  = lib_env.compile( lib_dag, xed_ild_sources)
    
    # grab common sources compiled earlier
    common_sources = ['xed-ild.c',                 # dec
                      'xed-chip-features.c',       # dec
                      'xed-isa-set.c',             # common
                      'xed-chip-modes.c',          # common
                      'xed-chip-modes-override.c'] # common  (overrideable)
    common_sources = _replace_sources(common_sources, sources_to_replace)
    # strip paths coming from the replaced sources.
    common_sources = [ os.path.basename(x) for x in  common_sources]
    common_sources += ['xed-chip-features-table.c', # generated
                       'xed-ild-disp-l3.c',         # generated
                       'xed-ild-eosz.c',            # generated
                       'xed-ild-easz.c',            # generated
                       'xed-ild-imm-l3.c']          # generated
    common_objs = lib_env.make_obj(common_sources)
    
    ild_objs += xbc.build_dir_join(lib_env, common_objs)

    lib,dll = xbc.make_lib_dll(env,'xed-ild')

    if lib_env['shared']:
        u = lib_env.dynamic_lib(ild_objs, dll, relocate=True)
    else:
        u = lib_env.static_lib(ild_objs,  lib, relocate=True)
    env['link_libild'] = lib_env.build_dir_join(lib)
    env['shd_libild']  = lib_env.build_dir_join(dll)
    lib_dag.add(lib_env,u)


def make_static_stripped_library(env, objs, obj_clean):
    c = mbuild.plan_t(name='repack-and-clean',
                       command=repack_and_clean,
                       args=[obj_clean, objs],
                       env=env,
                       input=objs,
                       output=obj_clean)
    return c

    
def repack_and_clean(args, env):
    """Run ld -r foo.o objs... and then use objcopy --redefine-syms=file
    to redefine the internal symbols. The renamed obj file is packed
    in to a static library. The "file" is a list of old new pairs, one
    per line.  The public symbols come from the file
    misc/API.NAMES.txt every other non-external label is considered
    internal and gets renamed."""

    tobj_clean = args[0]
    objs = args[1]


    # step 1: ld -r
    ldcmd = env['toolchain'] + 'ld'
    tobj_dirty = env.expand(env.build_dir_join('xed-tobj-dirty%(OBJEXT)s'))

    repack_cmd = "{} -r -o {} {}".format(ldcmd, tobj_dirty, " ".join(objs))
    mbuild.run_command(repack_cmd)

    # step 2: extract a list of all symbols
    nmcmd = env['toolchain'] + 'nm'
    nm = "{} --defined-only {}".format(nmcmd, tobj_dirty)
    all_syms_fn = env.build_dir_join('all-syms.txt')
    mbuild.run_command_output_file(nm, output_file_name=all_syms_fn)

    # step 3: parse the all_syms_fn.
    all_syms = open(all_syms_fn, 'r').readlines()
    all_syms = [x.strip() for x in  all_syms]
    all_syms = set([x.split(' ',2)[2] for x in all_syms])

    # step 4: subtract the public symbols
    api_names_fn = env.src_dir_join(mbuild.join('misc','API.NAMES.txt'))
    api_names = open(api_names_fn,'r').readlines()
    api_names = set([x.strip() for x in  api_names])

    private_syms = all_syms - api_names

    # step 5: make rename file for the private symbols
    redef_fn = env.build_dir_join('symbol-redef.txt')
    f = open(redef_fn,"w")
    for i,x in enumerate(private_syms):
        f.write("{} xedint{}\n".format(x, i))
    f.close()

    # step 6: run objcopy, renaming the symbols
    objcopy_cmd = env['toolchain'] + 'objcopy'
    ocargs = "--redefine-syms={}".format(redef_fn) 
    ocmd = "{} {} {} {}".format(objcopy_cmd, ocargs, tobj_dirty, tobj_clean)
    mbuild.run_command(ocmd)
    return (0, ["success"])

def _get_check(wrds,n,default=None):
    if n < len(wrds):
        return wrds[n].strip()
    if default:
        return default
    xbc.cdie("Looking for token {} in input line [{}]".format(
        n, wrds))

def _fn_expand(env, edir, fname):
    if  re.search('%[(].*[)]',fname):
        fname = env.expand(fname)
        full_name = os.path.abspath(fname)
    else:
        full_name = mbuild.join(edir,fname)
    if not os.path.exists(full_name):
        xbc.cdie("Cannot open extension file: %s"  % full_name)
    return full_name

def _parse_extf_files_new(env, gc):
    """READ EACH EXTENSION FILE-of-FILES. gc is the generator_inputs_t object"""
    # local
    comment_pattern = re.compile(r'[#].*$')
    source_prio = collections.defaultdict(int)
    sources_dict = {}
    
    # returned
    sources_to_remove = []
    sources_to_add = []
    sources_to_replace = []

    dup_check = {}
    for ext_file in env['extf']:
        mbuild.msgb("EXTF PROCESSING", ext_file)
        if not os.path.exists(ext_file):
            xbc.cdie("Cannot open extension configuration file: %s" % 
                       ext_file)
        if os.path.isdir(ext_file):
            xbc.cdie("Please specify a file, not a directory " + 
                       "for --extf option: %s" % ext_file)
        if ext_file in dup_check:
            mbuild.warn("Ignoring duplicate extf file in list %s" % ext_file)
            continue
        dup_check[ext_file]=True
        edir = os.path.dirname(ext_file)
        for line in  open(ext_file,'r').readlines():
            line = line.strip()
            line = comment_pattern.sub('',line)
            if len(line) > 0:
                wrds = line.split(':')
                cmd = wrds[0]
                if cmd == 'clear':
                    ptype = _get_check(wrds,1)
                    gc.clear_files(ptype)
                elif cmd == 'define':
                    definition = _get_check(wrds,1)
                    env.add_define(definition)
                elif cmd == 'remove-source':
                    ptype = _get_check(wrds,1) # unused
                    fname = _get_check( wrds,2)
                    sources_to_remove.append(fname)
                #elif cmd == 'remove':
                #    ptype = _get_check(wrds,1)
                #    fname = _fn_expand(env, edir, _get_check(wrds,2))
                #    gc.remove_file(ptype,full_name)
                elif cmd == 'add-source':
                    ptype = _get_check(wrds,1)
                    fname = _fn_expand(env, edir, _get_check(wrds,2))
                    priority =  int(_get_check(wrds,3, default=1))
                    print("CONSIDERING SOURCE", fname, ptype, priority)
                    if source_prio[ptype] < priority:
                        print("ADDING SOURCE", fname, ptype, priority)
                        source_prio[ptype] = priority
                        sources_dict[ptype] = fname
                elif cmd == 'replace-source':
                    ptype = _get_check(wrds,1)
                    oldfn = _get_check(wrds,2)
                    newfn = _fn_expand(env, edir, _get_check(wrds,3))
                    priority =  int(_get_check(wrds,4, default=1))
                    sources_to_replace.append((oldfn, newfn, ptype, priority))
                elif cmd == 'add':
                    ptype = _get_check(wrds,1)
                    fname = _fn_expand(env, edir, _get_check(wrds,2))
                    priority =  int(_get_check(wrds,3, default=1))
                    gc.add_file(ptype, fname, priority)
                else: # default is to add "keytype: file" (optional priority)
                    if len(wrds) not in [2,3]:
                        xbc.die('badly formatted extension line. expected 2 or 3 arguments: {}'.format(line))
                    ptype = _get_check(wrds,0)
                    fname = _fn_expand(env, edir, _get_check(wrds,1))
                    priority =  int(_get_check(wrds,2, default=1))
                    gc.add_file(ptype, fname, priority)

    for v in iter(sources_dict.values()):
        sources_to_add.append(v)

    return (sources_to_remove, sources_to_add, sources_to_replace )

def _replace_sources(srclist, sources_to_replace):
    prio_d = {}
    newfn_d = {}
    for s in srclist:
        prio_d[s] = 1
        newfn_d[s] = s
        for (oldfn,newfn,ptype,prio) in sources_to_replace:
            # substring search to avoid absolute vs relative path issues
            if oldfn in s: 
                if prio > prio_d[s]:
                    mbuild.msgb("REPLACING {} with {}".format(s, newfn))
                    prio_d[s] = prio
                    newfn_d[s] = newfn
    return newfn_d.values()

def _test_chip(env, names_list):
    for nm in names_list:
        if env[nm]:
            return True
    return False
        
def _configure_libxed_extensions(env):
    if env['amd_enabled']:
        env.add_define('XED_AMD_ENABLED')

    if env['avx']:
        env.add_define('XED_AVX')

    if _test_chip(env, ['knl','knm', 'skx', 'cnl', 'icl']):
        env.add_define('XED_SUPPORTS_AVX512')
    if env['knc']:
        env.add_define('XED_SUPPORTS_KNC')
    if env['mpx']:
        env.add_define('XED_MPX')
    if env['cet']:
        env.add_define('XED_CET')
    #SHA on GLM & CNL, support by default
    env.add_define('XED_SUPPORTS_SHA')
    if env['icl']:
        env.add_define('XED_SUPPORTS_WBNOINVD')

    if env['decoder']:
        env.add_define('XED_DECODER')
    if env['encoder']:
        env.add_define('XED_ENCODER')

    #insert default isa files at the front of the extension list
    newstuff = []
    if env['default_isa'] == '':
        newstuff.append( env.src_dir_join(mbuild.join('datafiles',
                                                      'files.cfg')))

        # This has the NT definitions for things like XMM_B() which
        # are needed for >= SSE-class machines.
        newstuff.append( env.src_dir_join(mbuild.join('datafiles',
                                                      'files-xregs.cfg')))
        if not env['avx']:
           # this has the xmm reg and nesting for sse-class machines.
           # not useful/appropriate for AVX1/2 or AVX512-class machines.
           newstuff.append( env.src_dir_join(mbuild.join('datafiles',
                                                         'files-xmm.cfg')))
    else:
        newstuff.append( env['default_isa'] )

    # add AMD stuff under knob control
    if env['amd_enabled']:
        newstuff.append( env.src_dir_join(mbuild.join('datafiles',
                                                      'files-amd.cfg')))
        if env['avx']:
            newstuff.append( env.src_dir_join(mbuild.join('datafiles',
                                                         'amdxop',
                                                         'files.cfg')))

    def _add_normal_ext(tenv,x , y='files.cfg'):
        e =  tenv.src_dir_join(mbuild.join('datafiles', x, y))
        if e not in tenv['extf']:
            tenv['extf'].append( e )

    if env['knc']:
        if env['knm'] or env['knl'] or env['skx']:
            _add_normal_ext(env,'knc', 'files-with-avx512f.cfg')
        else:
            _add_normal_ext(env,'knc', 'files-no-avx512f.cfg')
            
    if env['mpx']: # MPX first on GLM or SKL
        _add_normal_ext(env,'mpx')
    if env['cet']:
        _add_normal_ext(env,'cet')

    # Silvermont & Ivybridge
    _add_normal_ext(env,'rdrand') 
    # Goldmont
    _add_normal_ext(env,'glm')
    _add_normal_ext(env,'sha')
    _add_normal_ext(env,'xsaveopt')
    _add_normal_ext(env,'xsaves')
    _add_normal_ext(env,'xsavec')
    _add_normal_ext(env,'clflushopt')
    _add_normal_ext(env,'rdrand')
    _add_normal_ext(env,'rdseed')
    _add_normal_ext(env,'fsgsbase')
    _add_normal_ext(env,'smap')
    _add_normal_ext(env,'xsaveopt')
    # Goldmont plus
    _add_normal_ext(env,'sgx')
    _add_normal_ext(env,'rdpid')
    _add_normal_ext(env,'pt')
    # Tremont
    _add_normal_ext(env,'tremont')
    _add_normal_ext(env,'movdir')
    _add_normal_ext(env,'waitpkg')
    _add_normal_ext(env,'cldemote')
    _add_normal_ext(env,'sgx-enclv') 

    if env['avx']:
        _add_normal_ext(env,'avx')
        _add_normal_ext(env,'xsaveopt')
        if env['ivb']:
            _add_normal_ext(env,'fsgsbase')
            _add_normal_ext(env,'rdrand')
            _add_normal_ext(env,'ivbavx')
        if env['hsw']:
            env.add_define('XED_SUPPORTS_LZCNT_TZCNT')
            _add_normal_ext(env,'hswavx')
            _add_normal_ext(env,'hswbmi') # AMD XOP requires the reg NT defns
            _add_normal_ext(env,'hsw')
        if env['bdw']:
            _add_normal_ext(env,'bdw')
            _add_normal_ext(env,'smap')
            _add_normal_ext(env,'rdseed')
        if env['skl'] or env['skx']: # FIXME: requires MPX and BDW
            _add_normal_ext(env,'skl')
            _add_normal_ext(env,'sgx')
            _add_normal_ext(env,'xsaves')
            _add_normal_ext(env,'xsavec')
            _add_normal_ext(env,'clflushopt')
        if env['skx']:
            _add_normal_ext(env,'skx')
            _add_normal_ext(env,'pku')
            _add_normal_ext(env,'clwb')
        if env['knl']:
            _add_normal_ext(env,'knl')
        if env['knm']:
            _add_normal_ext(env,'knm')
            _add_normal_ext(env,'4fmaps-512')
            _add_normal_ext(env,'4vnniw-512')
            _add_normal_ext(env,'vpopcntdq-512')
            
        if env['skx'] or env['knl'] or env['knm']:
            _add_normal_ext(env,'avx512f','shared-files.cfg')
            _add_normal_ext(env,'avx512f')
            _add_normal_ext(env,'avx512cd')
        if env['skx']:
            _add_normal_ext(env,'avx512-skx')
        if env['cnl']:
            _add_normal_ext(env,'cnl')
            _add_normal_ext(env,'sha')
            _add_normal_ext(env,'avx512ifma')
            _add_normal_ext(env,'avx512vbmi')
        if env['icl']:
            _add_normal_ext(env,'icl')
            _add_normal_ext(env,'wbnoinvd') # icl server
            _add_normal_ext(env,'sgx-enclv') # icl server           
            _add_normal_ext(env,'pconfig') # icl server 
            _add_normal_ext(env,'rdpid')   
            _add_normal_ext(env,'bitalg')            
            _add_normal_ext(env,'vbmi2')
            _add_normal_ext(env,'vnni')
            _add_normal_ext(env,'gfni-vaes-vpcl', 'files-sse.cfg')
            _add_normal_ext(env,'gfni-vaes-vpcl', 'files-avx-avx512.cfg')
            _add_normal_ext(env,'vpopcntdq-512')
            _add_normal_ext(env,'vpopcntdq-vl')
            
        if env['future']: # now based on ICL
            _add_normal_ext(env,'future')
            _add_normal_ext(env,'pt')


        
    env['extf'] = newstuff + env['extf']

def _get_src(env,subdir):
    return mbuild.glob(mbuild.join(env['src_dir'],'src',subdir,'*.c'))

def _abspath(lst):
  return [ os.path.abspath(x) for x in  lst]

def _remove_src(lst, fn_to_remove):
    """Remove based on substring to avoid relative vs absolute path issues"""
    nlist = []
    for lfn in lst:
        if fn_to_remove not in lfn: # substring search
            nlist.append(lfn)
    return nlist
def _remove_src_list(lst, list_to_remove):
    nlist = []
    for lfn in lst:
        keep = True
        for rfn in list_to_remove:
            if rfn in lfn:
                keep = False
                break
        if keep:
            nlist.append(lfn)
    return nlist

def build_libxed(env,work_queue):
    "Run the generator and build libxed"
    
    # create object that will assemble our command line.
    gc = generator_inputs_t(env['build_dir'], 
                            env['amd_enabled'],
                            env['limit_strings'])

    # add individual extension files
    for ext_files in env['ext']:
        (ptype, fname) = ext_files.split(':')
        gc.add_file(ptype,fname)

    _configure_libxed_extensions(env)     
    (sources_to_remove,
     sources_to_add,
     sources_to_replace ) = _parse_extf_files_new(env,gc)

    emit_defines_header(env)

    # Basic idea: First, concatenate the input files, then run the
    # encoder and decoder generators. Then build the libraries (xed
    # and ild).
    
    prep_files = env.build_dir_join('prep-inputs') 
    f = open(prep_files,"w")
    f.write( "\n".join(gc.all_input_files()) + "\n")
    f.close()
    
    #mbuild.msgb("PREP INPUTS", ", ".join(gc.all_input_files()))
    c0 = mbuild.plan_t(name='decprep',
                       command=run_generator_preparation,
                       args=gc,
                       env=env,
                       input=gc.all_input_files() + [env['mfile'], prep_files],
                       output= env.build_dir_join('dummy-prep') )
    gen_dag = mbuild.dag_t('xedgen', env=env)
    prep = gen_dag.add(env,c0)

    if 'just-prep' in env['targets']:
        okay = work_queue.build(dag=gen_dag,
                                show_progress=True,
                                show_output=True,
                                show_errors_only=_wk_show_errors_only())

        if not okay:
            xbc.cdie("[PREP] failed. dying...")
        mbuild.msgb("STOPPING", "after prep")
        xbc.cexit()

    # Python imports used by the 2 generators.
    # generated 2016-04-15 by importfinder.py:
    #   pysrc/importfinder.py generator pysrc
    #   pysrc/importfinder.py read-encfile pysrc
    #  importfinder.py is too slow to use on every build, over 20seconds/run.

    dec_py =['pysrc/actions.py', 'pysrc/genutil.py',
             'pysrc/ild_easz.py', 'pysrc/ild_codegen.py', 'pysrc/tup2int.py',
             'pysrc/encutil.py', 'pysrc/verbosity.py', 'pysrc/ild_eosz.py',
             'pysrc/xedhash.py', 'pysrc/ild_phash.py',
             'pysrc/actions_codegen.py', 'pysrc/patterns.py',
             'pysrc/operand_storage.py', 'pysrc/opnds.py', 'pysrc/hashlin.py',
             'pysrc/hashfks.py', 'pysrc/ild_info.py', 'pysrc/ild_cdict.py',
             'pysrc/xed3_nt.py', 'pysrc/codegen.py', 'pysrc/ild_nt.py',
             'pysrc/hashmul.py', 'pysrc/enumer.py', 'pysrc/enum_txt_writer.py',
             'pysrc/xed3_nt.py', 'pysrc/ild_disp.py', 'pysrc/ild_imm.py',
             'pysrc/ild_modrm.py', 'pysrc/ild_storage.py',
             'pysrc/ild_storage_data.py', 'pysrc/slash_expand.py',
             'pysrc/chipmodel.py', 'pysrc/flag_gen.py', 'pysrc/opnd_types.py',
             'pysrc/hlist.py', 'pysrc/ctables.py', 'pysrc/ild.py',
             'pysrc/refine_regs.py', 'pysrc/metaenum.py', 'pysrc/classifier.py']
          
    enc_py = ['pysrc/genutil.py', 'pysrc/encutil.py',
              'pysrc/verbosity.py', 'pysrc/patterns.py', 'pysrc/actions.py',
              'pysrc/operand_storage.py', 'pysrc/opnds.py', 'pysrc/ild_info.py',
              'pysrc/codegen.py', 'pysrc/ild_nt.py', 'pysrc/actions.py',
              'pysrc/ild_codegen.py', 'pysrc/tup2int.py',
              'pysrc/constraint_vec_gen.py', 'pysrc/xedhash.py',
              'pysrc/ild_phash.py', 'pysrc/actions_codegen.py',
              'pysrc/hashlin.py', 'pysrc/hashfks.py', 'pysrc/hashmul.py',
              'pysrc/func_gen.py', 'pysrc/refine_regs.py',
              'pysrc/slash_expand.py', 'pysrc/nt_func_gen.py',
              'pysrc/scatter.py', 'pysrc/ins_emit.py']

    dec_py = env.src_dir_join(dec_py)
    enc_py = env.src_dir_join(enc_py)
    dec_py += mbuild.glob(env.src_dir_join('datafiles/*enum.txt'))

    dd = env.build_dir_join('DECGEN-OUTPUT-FILES.txt')
    if os.path.exists(dd):
        need_to_rebuild_dec = need_to_rebuild(dd, 
                                  env.build_dir_join(".mbuild.hash.xeddecgen"))
        if need_to_rebuild_dec:
            mbuild.remove_file(dd)

    gc.dec_output_file = dd

    dec_input_files = (gc.all_input_files() + prep.targets +
                       dec_py + [env['mfile']])
    c1 = mbuild.plan_t(name='decgen',
                       command=run_decode_generator,
                       args=gc,
                       env=env,
                       input=dec_input_files,
                       output= dd)
    dec_cmd = gen_dag.add(env,c1)
       
    if env['encoder']:
        ed = previous_output_fn = env.build_dir_join('ENCGEN-OUTPUT-FILES.txt')
        if os.path.exists(ed):
            need_to_rebuild_enc = need_to_rebuild(ed,
                                   env.build_dir_join('.mbuild.hash.xedencgen'))
            if need_to_rebuild_enc:
                mbuild.remove_file(ed)

        gc.enc_output_file = ed
        enc_input_files = (gc.all_input_files() + prep.targets +
                           enc_py + [env['mfile']])
        c2 = mbuild.plan_t(name='encgen',
                           command=run_encode_generator,
                           args=gc,
                           env=env,
                           input=enc_input_files,
                           output= ed)
        enc_cmd = gen_dag.add(env,c2)

    phase = "DECODE/ENCODE GENERATORS"
    if 'skip-gen' in env['targets']:
        mbuild.msgb(phase, "SKIPPING!")
    else:
        okay = work_queue.build(dag=gen_dag,
                                show_progress=True, 
                                show_output=True,
                                show_errors_only=_wk_show_errors_only())

        if not okay:
            xbc.cdie("[%s] failed. dying..." % phase)
        if mbuild.verbose(2):
            mbuild.msgb(phase, "succeeded")

    if 'just-gen' in env['targets']:
        mbuild.msgb("STOPPING", "after %s" % phase)
        xbc.cexit(1)

    #########################################################################
    # everything is generated, so now build libxed

    libxed_lib, libxed_dll = xbc.make_lib_dll(env,'xed')
    if  env['shared']:
        env['shd_libxed']  = env.build_dir_join(libxed_dll)
        env['link_libxed'] = env.build_dir_join(libxed_lib)
    else:
        env['shd_libxed']  = env.build_dir_join(libxed_lib)
        env['link_libxed'] = env['shd_libxed'] # same

    # pick up the generated header files in the header scans
    env.add_include_dir(env['build_dir'])
    env['private_generated_header_dir'] = mbuild.join(env['build_dir'],
                                                      'include-private')
    env.add_include_dir(env['private_generated_header_dir'])

    generated_library_sources = mbuild.glob(mbuild.join(env['build_dir'],'*.c'))
    
    nongen_lib_sources = _get_src(env,'common') 
    if env['decoder']:
        nongen_lib_sources.extend(_get_src(env,'dec'))
    else:
        generated_library_sources = _remove_src(generated_library_sources,
                                                'xed-iform-map-init.c')
    if env['encoder']:
         nongen_lib_sources.extend(_get_src(env,'enc'))
    if env['encoder'] and env['decoder']:
         nongen_lib_sources.extend(_get_src(env,'encdec'))

    nongen_lib_sources = _remove_src_list(nongen_lib_sources, sources_to_remove)
    nongen_lib_sources.extend(sources_to_add)
    nongen_lib_sources = _replace_sources(nongen_lib_sources, sources_to_replace)

    lib_dag = mbuild.dag_t('xedlib', env=env)
    lib_env = copy.deepcopy(env)
    lib_env.add_cc_define("XED_BUILD")

    lib_objs = []
    # first_lib and last_lib are for supporting compilations using
    # custom C runtimes.
    if env['first_lib']:
        lib_objs.append(env['first_lib'])
    lib_objs += lib_env.compile( lib_dag, generated_library_sources)
    lib_objs += lib_env.compile( lib_dag, nongen_lib_sources)
    if env['last_lib']:
        lib_objs.append(env['last_lib'])

    if lib_env['shared']:
        # use gcc for making the shared object
        lib_env['CXX_COMPILER']= lib_env['CC_COMPILER']

    # libxed
    if lib_env['shared']:
        u = lib_env.dynamic_lib(lib_objs, env['shd_libxed'])
    elif env.on_linux() and lib_env['static_stripped']:
        tobj_clean = env.expand(env.build_dir_join('xed-tobj-clean%(OBJEXT)s'))
        u = make_static_stripped_library(lib_env, lib_objs, tobj_clean)
        lib_dag.add(lib_env,u)
        u = lib_env.static_lib([tobj_clean], env['link_libxed'])
    else:
        u = lib_env.static_lib(lib_objs, env['link_libxed'])
    lib_dag.add(lib_env,u)

    # libxed-ild
    if env['decoder'] and not lib_env['static_stripped']:
        build_xed_ild_library(env, lib_env, lib_dag, sources_to_replace)

    if lib_dag.cycle_check():
        xbc.cdie("Circularities in dag...")
    if 'skip-lib' in env['targets']:
        mbuild.msgb("SKIPPING LIBRARY BUILD")
    else:
        okay = work_queue.build(lib_dag,
                                die_on_errors=lib_env['die_on_errors'],
                                show_progress=True, 
                                show_output=True,
                                show_errors_only=_wk_show_errors_only())

        if okay and env['shared'] and not env['debug']:
            xbc.strip_file(env,     env['shd_libxed'], '-x')
            if os.path.exists(env['shd_libild']):
                xbc.strip_file(lib_env, env['shd_libild'], '-x')
        if not okay:
            xbc.cdie("Library build failed")
        if mbuild.verbose(2):
            mbuild.msgb("LIBRARY", "build succeeded")

    del lib_env
    
def _modify_search_path_mac(env, fn):
   """Make example tools refer to the libxed.so from the lib directory
   if doing and install. Mac only."""
   if not env['shared']:
      return
   if not env.on_mac():
      return 
   if not xbc.installing(env):
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
      xbc.dump_lines("install_name_tool stdout", stdout)
      xbc.dump_lines("install_name_tool stderr", stderr)
      xbc.cdie("Could not modify dll path: " + cmd)

def _test_perf(env):
    """Performance test. Should compile with -O3 or higher. Linux
    only. Requires a specific test binary."""
    if not env.on_linux():
        return
    if not env['test_perf']:
        return

    # find the XED command line tool binary
    xed = None    
    for exe in env['example_exes']:
        if 'xed' == os.path.basename(exe):
            xed = exe
    if not xed:
        xbc.cdie("Could not find the xed command line tool for perf test")

    import perftest
    args = perftest.mkargs()
    args.xed = xed
    r = perftest.work(args) # 2016-04-22 FIXME: need to update interface
    if r != 0:
        # perf test failed. Although calling xbc.cexit() avoids saving
        # mbuild hash state and causes rebuilds.
        xbc.cdie( "perf test failed") 

def _get_xed_min_size(env):
    if not env.on_linux():
        return
    
    xed_min = None    
    #check if we have xed-min test
    for exe in env['example_exes']:
        if 'xed-min' in exe:
            xed_min = exe

    if not xed_min:
        return 
    
    xbc.strip_file(env,xed_min)
    
    #get the size in MB
    size_bytes = os.path.getsize(xed_min)
    size_meg = size_bytes / (1024*1024.0) 
    mbuild.msgb("XED-MIN SIZE", "%d = %.2fMB" % (size_bytes,size_meg))

    import elf_sizes
    d = elf_sizes.work(xed_min,die_on_errors=False)
    if d:
        elf_sizes.print_table(d)

def build_examples(env):
    env['example_exes'] = []
    if not set(['examples','cmdline']).intersection(env['targets']):
        return

    sys.path.insert(0, mbuild.join(env['src_dir'],'examples'))
    import xed_examples_mbuild
    env_ex = copy.deepcopy(env)
    env_ex['CPPPATH'] = [] # clear out libxed-build headers.
    env_ex['src_dir'] = mbuild.join(env['src_dir'], 'examples')
    env_ex['xed_lib_dir'] = env['build_dir']
    env_ex['xed_inc_dir'] = env['build_dir']

    env_ex['set_copyright'] = False    
    if env.on_windows():
        env_ex['set_copyright'] = env['set_copyright']
        
    try:
        retval = xed_examples_mbuild.examples_work(env_ex)
    except Exception as e:
        xbc.handle_exception_and_die(e)
    if 'example_exes' in env_ex:
        env['example_exes'] = env_ex['example_exes']
    _get_xed_min_size(env_ex)
    _test_perf(env_ex)

def copy_dynamic_libs_to_kit(env, kitdir):
    """Copy *all* the dynamic libs that ldd finds to the extlib dir in the
       kit"""
    import external_libs
    
    if not env.on_linux() and not env.on_freebsd() and not env.on_netbsd():
        return

    kit_ext_lib_dir = mbuild.join(kitdir,'extlib')
    bindir = mbuild.join(kitdir,'bin')
    executables = glob.glob(mbuild.join(bindir,'*'))
    mbuild.cmkdir(kit_ext_lib_dir)
    if 'extern_lib_dir' not in env:
        env['extern_lib_dir']  = '%(xed_dir)s/external/lin/lib%(arch)s'
        
    extra_ld_library_paths = (env['ld_library_path'] +
                              [ env.expand('%(extern_lib_dir)s')])

    # run LDD to find the shared libs and do the copies
    okay = external_libs.copy_system_libraries(env,
                                               kit_ext_lib_dir,
                                               executables,
                                               extra_ld_library_paths)
    if not okay:
        mbuild.warn("There was a problem running LDD when making the kit")

    # copy the libelf/dwarf license
    if env['use_elf_dwarf_precompiled']:
        env2 = copy.deepcopy(env)
        xbc.cond_add_elf_dwarf(env2)
        mbuild.copy_file(env2['libelf_license'], kit_ext_lib_dir)
        

def copy_ext_libs_to_kit(env,dest): # 2014-12-02: currently unused
    if not env['use_elf_dwarf_precompiled']:
       return

    extlib = mbuild.join(dest,"extlib")
    mbuild.cmkdir(extlib)

    env2 = copy.deepcopy(env)
    xbc.cond_add_elf_dwarf(env2)
 
    for f in env2['ext_libs']:
        mbuild.copy_file(env2.expand(f),extlib)
    existing_file_name = os.path.basename(env2['libelf'])
    dest_path_and_link = mbuild.join(extlib,env2['libelf_symlink'])
    if os.path.exists(dest_path_and_link):
        mbuild.remove_file(dest_path_and_link)
    mbuild.symlink(env, existing_file_name, dest_path_and_link)
    mbuild.copy_file(env2['libelf_license'], extlib)

def apply_legal_header2(fn, legal_header):

    def _c_source(x):
        t = x.lower()
        for y in ['.c', '.h', '.cpp']:
            if t.endswith(y):
                return True
        return False
    
    try: 
       import apply_legal_header
    except:
       xbc.cdie("XED ERROR: mfile.py could not find scripts directory")
       
    if mbuild.verbose(2):
        mbuild.msgb("HEADER TAG", fn)

    if _c_source(fn):
        apply_legal_header.apply_header_to_source_file(legal_header,fn)
    else:
        apply_legal_header.apply_header_to_data_file(legal_header,fn)

def _gen_lib_names(env):
    libnames_template = [ 'lib%(base_lib)s.a',
                          'lib%(base_lib)s.so',
                          '%(base_lib)s.lib',
                          '%(base_lib)s.dll',
                          'lib%(base_lib)s.dylib' ] 
    libnames = []
    for base_lib in ['xed', 'xed-ild']:
        # use base_lib to trigger mbuild expansion
        env['base_lib']=base_lib  
        libnames.extend(env.expand(libnames_template))

    libs = [ mbuild.join(env['build_dir'], x) for x in libnames]
    libs = list(filter(lambda x: os.path.exists(x), libs))
    return libs

do_system_copy = True

def _copy_generated_headers(env, dest):
    global do_system_copy
    gen_inc = mbuild.join(mbuild.join(env['build_dir'],'*.h'))
    gincs= mbuild.glob(gen_inc)
    if len(gincs) == 0:
        xbc.cdie("No generated include headers found for install")
    for  h in gincs:
        if do_system_copy:
            mbuild.copy_file(h,dest)

def _copy_nongenerated_headers(env, dest):
    global do_system_copy
    src_inc = mbuild.join(env['src_dir'],'include',"public",'xed','*.h')
    incs= mbuild.glob(src_inc)
    if len(incs) == 0:
        xbc.cdie("No standard include headers found for install")
    for  h in incs:
        if do_system_copy:
            mbuild.copy_file(h,dest)

def _get_legal_header(env):
    if env['legal_header'] == 'default' or env['legal_header'] == None:
        env['legal_header'] = mbuild.join(env['src_dir'],
                                          'misc',
                                          'apache-header.txt')
    legal_header = open(env['legal_header'],'r').readlines()
    return legal_header

def _apply_legal_header_to_headers(env,dest):
    """apply legal header to all installed headers 
       in the include directory."""

    legal_header = _get_legal_header(env)

    for h in  mbuild.glob(mbuild.join(dest,'*.[Hh]')):
        if mbuild.verbose(2):
            mbuild.msgb("HEADER TAG", h)
        apply_legal_header2(h, legal_header)

                                                 
def system_install(env, work_queue):
    """Build install in the prefix_dir. Use prefix_lib_dir as library name
       since some systems use lib, lib32 or lib64. non-windows only.
    """
    global do_system_copy
    if env.on_windows():
        return

    if not env['prefix_dir']:
        return

    include = mbuild.join(env['prefix_dir'], 'include', 'xed')
    lib     = mbuild.join(env['prefix_dir'], env['prefix_lib_dir'])

    mbuild.msgb("Making install dirs (if they do not exist)")

    def _set_perm(fn):
        "-rwx-r-xr-x"
        os.chmod(fn, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|
                     stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH|
                     stat.S_IWUSR)


    if not os.path.exists(include):
        mbuild.cmkdir(include)
        _set_perm(include)
    if not os.path.exists(lib):
        mbuild.cmkdir(lib)
        _set_perm(include)


    # copy the libraries
    libs = _gen_lib_names(env)
    if len(libs) == 0:
        xbc.cdie("No libraries found for install")
    for f in libs:
        if do_system_copy:
            mbuild.copy_file(f, lib)
            fn = mbuild.join(lib,os.path.basename(f))
            if env['shared']:
                _set_perm(fn)
            else:
                mbuild.make_read_only(fn)



    _copy_generated_headers(env, include)
    _copy_nongenerated_headers(env, include)
    _apply_legal_header_to_headers(env, include)

    for fn in glob.glob(mbuild.join(include,'*.h')):
        mbuild.make_read_only(fn)

def build_kit(env, work_queue):
    "Build the XED kit"
    if not xbc.installing(env):
        return
    # add a default legal header if we are building a kit and none is
    # specified.
    legal_header = _get_legal_header(env)
    if not env['install_dir']:
        date = time.strftime("%Y-%m-%d")
        sd = 'xed-install-%s-%s-%s-%s' % ( env['kit_kind'], 
                                           date, 
                                           env['build_os'], 
                                           env['host_cpu'] )
        mbuild.cmkdir('kits')
        env['install_dir'] = os.path.join('kits', sd)
    dest = env['install_dir']
    if os.path.exists(dest): # start clean
        mbuild.remove_tree(dest)
    if mbuild.verbose(2):
        mbuild.msgb("INSTALL DIR", dest)
    include = mbuild.join(dest,"include",'xed')
    lib = mbuild.join(dest,"lib")
    examples = mbuild.join(dest,"examples")
    bin_dir = mbuild.join(dest,"bin")
    doc = mbuild.join(dest,"doc")
    misc = mbuild.join(dest,"misc")
    mbld = mbuild.join(dest,"mbuild")
    mbld2 = mbuild.join(mbld,'mbuild')
    
    for d in [dest,lib,include,examples,bin_dir,misc,mbld, mbld2]:
        mbuild.cmkdir(d)

    boilerplate = env.src_dir_join([ 'README.md' ])
    boilerplate.append(mbuild.join(env['src_dir'],'LICENSE'))
    for f in boilerplate:
        if os.path.exists(f):
            mbuild.copy_file(f,dest)
        else:
            mbuild.warn("Could not find %s" % (f))

    # copy the miscellaneous files to the misc directory
    for gfn in ['idata.txt', 'cdata.txt']:
        full_gfn =mbuild.join(env['build_dir'], gfn)
        mbuild.copy_file(full_gfn, misc)
        apply_legal_header2(mbuild.join(misc,gfn), legal_header)

    # copy mbuild to kit
    msrc = mbuild.join(env['src_dir'], '..', 'mbuild')
    for fn in glob.glob(mbuild.join(msrc,'mbuild','*.py')):
        mbuild.copy_file(fn, mbld2)
        dfn = mbuild.join(mbld2,os.path.basename(fn))
        apply_legal_header2(dfn, legal_header)

    # copy the common build file to the examples dir of the kits
    common =mbuild.join(env['src_dir'],'xed_build_common.py')
    mbuild.copy_file(common, examples)
    apply_legal_header2(mbuild.join(examples,'xed_build_common.py'),
                        legal_header)
    
    # copy the examples that we just built
    example_exes = env['example_exes']
    copied = False
    if len(example_exes) > 0:
        for f in example_exes:
            if os.path.exists(f):
                if not env['debug']:
                    xbc.strip_file(env,f)
                mbuild.copy_file(f,bin_dir)
                copied=True
                _modify_search_path_mac(env, 
                                        mbuild.join( bin_dir, 
                                                    os.path.basename(f)))
    if copied:
        copy_dynamic_libs_to_kit(env, dest)

    # copy dbghelp.dll to the bin on windows
    if env['dbghelp'] and env.on_windows():
        # locate src sibling directory dbghelp
        dbghelp = mbuild.join(mbuild.posix_slashes(os.path.dirname(
	                          os.path.abspath(env['src_dir']))),'dbghelp')
        mbuild.msgb("Trying dbghelp", dbghelp)
        if os.path.exists(dbghelp):
            dll = mbuild.join(dbghelp,env['arch'],'dbghelp.dll')
            mbuild.msgb("trying to find dll", dll)
            if os.path.exists(dll):
                mbuild.copy_file(dll,bin_dir)
            

    # copy the libraries. (DLL goes in bin)
    libs = _gen_lib_names(env)
    if len(libs) == 0:
        xbc.cdie("No libraries found for install")

    for f in libs:
        print(f)
        if f.find('.dll') != -1:
            mbuild.copy_file(f, bin_dir)
        else:
            mbuild.copy_file(f, lib)
            
    # copy any *.pdb files if one exists
    copy_pdb_files = False
    if copy_pdb_files:
        pdb_files = mbuild.glob(mbuild.join(env['build_dir'],'*.pdb'))
        for pdb in pdb_files:
            if os.path.exists(pdb):
                mbuild.copy_file(pdb,lib)


    # copy examples source
    for ext in ['*.[Hh]', '*.c', '*.cpp', '*.py', 'README.txt']:
        esrc = mbuild.glob(mbuild.join(env['src_dir'],'examples',ext))
        if len(esrc) == 0:
            xbc.cdie( "No standard examples to install")
        for  s in esrc:
            mbuild.copy_file(s,examples)

            # legal header stuff
            base = os.path.basename(s)
            tgt = mbuild.join(examples,base)
            if 'LICENSE' not in tgt:
                apply_legal_header2(tgt, legal_header)
                
    _copy_nongenerated_headers(env,include)
    _copy_generated_headers(env, include)
    _apply_legal_header_to_headers(env, include)

    # After applying the legal header, create the doxygen from the kit
    # files, and place the output right in the kit.
    if 'doc' in env['targets']:
        mbuild.cmkdir(doc)
        make_doxygen_api(env, work_queue, doc)
        # for the web...
        if env['doxygen_install']:        
            make_doxygen_api(env, work_queue, env['doxygen_install'])

    # build a zip file
    if 'zip' in env['targets']:
        wfiles = os.walk( env['install_dir'])
        zip_files = []
        for (path,dirs,files) in wfiles:
            zip_files.extend( [ mbuild.join(path,x) for x in  files] )
        import zipfile
        archive = env['install_dir'] + '.zip'
        z = zipfile.ZipFile(archive,'w')
        for f in zip_files:
            z.write(f)
        z.close()
        mbuild.msgb("ZIPFILE", archive)
        env['kit_zip_file']=archive
    mbuild.msgb("XED KIT BUILD COMPLETE")

def get_git_cmd(env):
   git = 'git'
   if 'GITCMD' in os.environ:
      gite = os.environ['GITCMD']
      if os.path.exists(gite):
         git = gite
   return git

def autodev(env):
   if env['dev']:
      return True
   if os.path.exists(mbuild.join(env['src_dir'],".developer")):
      return True
   return False

def get_git_version(env):
   fn = mbuild.join(env['src_dir'],'VERSION')
   # are we in a GIT repo?
   if os.path.exists(mbuild.join(env['src_dir'],'.git')):
      cmd = get_git_cmd(env) + ' describe --tags'
      (retcode, stdout, stderr) = mbuild.run_command(cmd,
                                                     directory=env['src_dir'])
      if retcode == 0:
         # git worked, update VERSION file
         line = stdout[0].strip()
         # update the VERSION file conditionally. It will mess up nightly
         # machines to modify a tracked file on every build.
         if autodev(env):
            f = open(fn,'w')
            f.write(line + "\n")
            f.close()
            
         return line
      else:
         xbc.dump_lines("git description stdout", stdout)
         xbc.dump_lines("git description stderr", stderr)

   # not a git repo or git failed or was not found.
   try:
      lines = open(fn,'r').readlines()
      line = lines[0].strip()
      return line
   except:
      xbc.cdie("Could not find VERSION file, git or git repo")

def emit_defines_header(env):
    """Grab all the XED_* defines and the model name and emit a header file"""

    def _emit_define(s):
        short = s
        short = re.sub(r'[=].*','',s)

        # grab right hand side of equals sign, if any
        rhs = None
        if '=' in s:
            rhs = re.sub(r'.*[=]','',s)

        klist = []
        klist.append( "#  if !defined(%s)" % (short))
        if rhs:
            klist.append( "#    define %s %s" % (short,rhs))
        else:
            klist.append( "#    define %s" % (short))
        klist.append( "#  endif")
        return klist
    output_file_name = "xed-build-defines.h"

    klist = []
    klist.append("#if !defined(XED_BUILD_DEFINES_H)")
    klist.append("#  define XED_BUILD_DEFINES_H\n")

    kys = list(env['DEFINES'].keys())
    kys.sort()
    for d in kys:
        if re.match(r'^XED_',d):
            define = env.expand(d)
            klist.extend(_emit_define(define))
    klist.append("#endif")
    
    klist = [ x+'\n' for x in klist ]
    
    fn = env.build_dir_join(output_file_name)
    if mbuild.hash_list(klist) != mbuild.hash_file(fn):
        mbuild.msgb("EMIT BUILD DEFINES HEADER FILE")
        f = open(fn,"w")
        for line in klist:
            f.write(line)
        f.close()
    else:
        mbuild.msgb("REUSING BUILD DEFINES HEADER FILE")

def update_version(env):
   new_rev = get_git_version(env)
   date = time.strftime("%Y-%m-%d")
   if new_rev:
      mbuild.msgb("GIT VERSION", new_rev)
   else:
      new_rev = "000"
      mbuild.warn("Could not find GIT revision number")

   # For developer builds, include the date in the git version.  For
   # non developer builds, do not include the date. The git version
   # gets put in the xed-build-defines.h file.  If the git version
   # includes the date, it would trigger rebuilds on a daily basis.
   
   if autodev(env):
       env['xed_git_version'] =  new_rev + " " + date
   else:
       env['xed_git_version'] =  new_rev
       
def _test_setup(env):
    osenv = None
    if 'ld_library_path_for_tests' in env and env['ld_library_path_for_tests']:
        osenv = copy.deepcopy(os.environ)
        s = None
        if 'LD_LIBRARY_PATH' in osenv:
            s = osenv['LD_LIBRARY_PATH']
        osenv['LD_LIBRARY_PATH'] = ":".join(env['ld_library_path_for_tests'])
        if s:
            osenv['LD_LIBRARY_PATH'] += ":" + s

    if env.on_windows() and env['shared']:
        # copy the xed.dll to the env['build_dir']/examples dir so
        # that it is found by the executable tests.
        mbuild.copy_file( env.expand( env.build_dir_join( env.shared_lib_name('xed'))),
                          env.build_dir_join('examples'))
    return osenv

def _test_cmdline_decoder(env,osenv):
    """Disassemble something with the command line decoder to make sure it
       works. Returns 0 on success, and nonzero on failure."""

    output_file = env.build_dir_join('CMDLINE.OUT.txt')
    cmd = "%(build_dir)s/examples/xed -n 1000 -i %(build_dir)s/examples/xed%(OBJEXT)s"
    cmd  = env.expand_string(cmd)
    (retval, output, oerror) = mbuild.run_command_output_file(cmd,
                                                              output_file,
                                                              osenv=osenv)
    if retval:
        mbuild.msgb("XED CMDLINE TEST", "failed. retval={}".format(retval))
        if output:
            xbc.dump_lines("[STDOUT]", output)
        if oerror:
            xbc.dump_lines("[STDERR]", oerror)
    else:
        mbuild.msgb("XED CMDLINE TEST", "passed")

    return retval

def _run_canned_tests(env,osenv):
    """Run the tests from the tests subdirectory"""
    retval = 0 # success
    env['test_dir'] = env.escape_string(mbuild.join(env['src_dir'],'tests'))        
    cmd = "%(python)s %(test_dir)s/run-cmd.py --build-dir %(build_dir)s/examples " 

    dirs = ['tests-base', 'tests-knc', 'tests-avx512', 'tests-xop']
    if env['cet']:
        dirs.append('tests-cet')
    for d in dirs:
        x  = env.escape_string(mbuild.join(env['test_dir'],d))
        cmd += " --tests %s " % (x)

    # add test restriction/subetting codes
    codes = []
    if env['encoder']:
        codes.append('ENC')
    if env['decoder']:
        codes.append('DEC')
    if env['avx']:
        codes.append('AVX')
    if env['knc']:
        codes.append('KNC')
    if env['skx']:
        codes.append('AVX512X')
    if env['knm'] or env['knl']:
        codes.append('AVX512PF')
    if env['hsw']: 
        codes.append('HSW')
    if env['amd_enabled'] and env['avx']:
        codes.append('XOP')
    for c in codes:
        cmd += ' -c ' + c

    output_file = env.build_dir_join('TEST.OUT.txt')
    cmd  = env.expand_string(cmd)
    if mbuild.verbose(1):
        mbuild.msgb("TEST COMMAND", "%s > %s" %(cmd,str(output_file)))
    (retcode, stdout, stderr) = mbuild.run_command_output_file(cmd,
                                                               output_file,
                                                               osenv=osenv)
    if retcode == 1:
       for l in stdout:
          print(l.rstrip())

    for l in stdout:
        l = l.rstrip()
        if re.search(r'^[[](TESTS|ERRORS|SKIPPED|PASS_PCT|FAIL)[]]',l):
           mbuild.msgb("TESTSUMMARY", l)
    if retcode == 0:
        mbuild.msgb("CANNED TESTS", "PASSED")
    else:
        mbuild.msgb("CANNED TESTS", "FAILED")
        retval = 1  # failure
        
    return retval

def run_tests(env):
    """Run the tests"""

    if 'test' not in env['targets']:
        return 0 # success
    mbuild.msgb("RUNNING TESTS")
    osenv = _test_setup(env)
    
    retval_cmdline = 0    
    if env['decoder']:
        retval_cmdline = _test_cmdline_decoder(env,osenv)
    retval_canned = _run_canned_tests(env,osenv)
    if retval_canned or retval_cmdline:
        mbuild.msgb("OVERALL TESTING", "failed")
        return 1 # failure
    return 0 # success

def verify_args(env):
    if not env['avx']:
        mbuild.warn("No AVX -> Disabling SNB, IVB, HSW, BDW, SKL, SKX, CNL, ICL, KNL, KNM Future\n\n\n")
        env['ivb'] = False
        env['hsw'] = False
        env['bdw'] = False
        env['skl'] = False
        env['skx'] = False
        env['cnl'] = False
        env['icl'] = False
        env['knl'] = False
        env['knm'] = False
        env['future'] = False

    # default is enabled. oldest disable disables upstream (younger, newer) stuff.
    if not env['knl']:
        env['knm'] = False
        
    if not env['avx']:
        env['avx512'] = False
        
    if not env['avx512']:
        env['skx'] = False
        env['cnl'] = False
        env['icl'] = False
        env['knl'] = False
        env['knm'] = False
        env['future'] = False

    if not env['ivb']:
        env['hsw'] = False
    if not env['hsw']:
        env['bdw'] = False
    if not env['bdw']:
        env['skl'] = False
    if not env['skl']:
        env['skx'] = False
    if not env['skx']:
        env['cnl'] = False
    if not env['cnl']:
        env['icl'] = False
    if not env['icl']:
        env['future'] = False

    if env['knc']: 
        mbuild.warn("Disabling AVX512, FUTURE, for KNC build\n\n\n")
        env['knl'] = False
        env['knm'] = False
        env['skx'] = False
        env['cnl'] = False
        env['icl'] = False
        env['future'] = False
        
    if not env['future']:
        env['cet'] = False

    if env['use_elf_dwarf_precompiled']:
       env['use_elf_dwarf'] = True
       

def work(env):
    """External entry point for non-command line invocations.
    Initialize the environment, build libxed, the examples, the kit
    and run the tests"""

    xbc.prep(env)
    env['xed_dir'] = env['src_dir']
    verify_args(env)
    start_time=mbuild.get_time()
    update_version(env)
    init_once(env)
    init(env)
    if 'clean' in env['targets'] or env['clean']:
        xbc.xed_remove_files_glob(env)
        if len(env['targets'])<=1:
            xbc.cexit(0)

    mbuild.cmkdir(env['build_dir'])
    mbuild.cmkdir(mbuild.join(env['build_dir'], 'include-private'))
    work_queue = mbuild.work_queue_t(env['jobs']) 

    build_libxed(env, work_queue)
    legal_header_tagging(env)
    build_examples(env)
    build_kit(env,work_queue)
    system_install(env,work_queue) # like in /usr/local/{lib,include/xed}
    make_doxygen_build(env,work_queue)
    retval = run_tests(env)

    end_time=mbuild.get_time()
    mbuild.msgb("ELAPSED TIME", mbuild.get_elapsed_time(start_time,
                                                        end_time))
    mbuild.msgb("RETVAL={}".format(retval))
    return retval

# for compatibility with older user script conventions
def set_xed_defaults(env):
    xbc.set_xed_defaults(env)

def execute():
    """Main external entry point for command line invocations"""
    env = mkenv()
    # xed_args() is skip-able for remote (import) invocation. The env
    # from mkenv can be updated programmatically. One must call
    # xbc.set_xed_defaults(env) if not calling xed_args(env)
    xed_args(env)  # parse command line knobs
    retval = work(env)
    return retval

