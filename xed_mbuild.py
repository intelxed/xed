#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2021 Intel Corporation
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
    return mbuild.escape_string(s)

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

###########################################################################
# generators
    
class generator_inputs_t(object):
    def __init__(self, build_dir, 
                 amd_enabled=True,
                 limit_strings=False,
                 encoder_chip='ALL'):
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
                       'cpuid',
                       'map-descriptions',
                       ]
        self.encoder_chip = encoder_chip
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
           mbuild.vmsgb(1, "Clearing file list for type %s: [ %s ]" %
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

    def decode_command(self, xedsrc, extra_args=None):
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
        s.append('--cpuid ' +
                 aq(self.file_name['cpuid']))
        s.append('--map-descriptions ' +
                 aq(self.file_name['map-descriptions']))
        if extra_args:
            s.append(extra_args)
        return ' '.join(s)

    def encode_command(self, xedsrc, extra_args=None, amd_enabled=True, chip='ALL'):
        """Produce an encoder generator command"""
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
        s.append('--map-descriptions ' + aq(self.file_name['map-descriptions']))
        s.append('--chip-models ' + aq(self.file_name['chip-models']))
        s.append('--chip ' + aq(self.encoder_chip))

        if not amd_enabled:
            s.append('--no-amd')
        if extra_args:
            s.append( extra_args)
        return ' '.join(s)
    

    def concatenate_one_set_of_files(self, env, target, inputs):
        """Concatenate input files creating the target file."""
        try:
            mbuild.vmsgb(2, "CONCAT", "%s <-\n\t\t%s" % (target ,
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
    """Run the decode table generator. This function is executed as
     required by the work_queue."""
    if env == None:
        return (1, ['no env!'])
    
    xedsrc    = aq(env['src_dir'])
    build_dir = aq(env['build_dir'])
    debug = ""
    other_args = " ".join(env['generator_options']) 
    gen_extra_args = "--gendir %s --xeddir %s %s %s" % (build_dir,
                                                        xedsrc, debug,
                                                        other_args)
    
    if env['compress_operands']:
        gen_extra_args += " --compress-operands" 
    if env['add_orphan_inst_to_future_chip']:
        gen_extra_args += " --add-orphan-inst-to-future-chip"
        
    cmd = env.expand(gc.decode_command(xedsrc, gen_extra_args))


    mbuild.vmsgb(3, "DEC-GEN", cmd)
    (retval, output, error_output) = mbuild.run_command(cmd,
                                                        separate_stderr=True)
    oo = env.build_dir_join('DEC-OUT.txt')
    oe = env.build_dir_join('DEC-ERR.txt')
    xbc.write_file(oo, output)
    xbc.write_file(oe, error_output)

    if retval == 0:
        list_of_files = read_file_list(gc.dec_output_file)
        mbuild.hash_files(list_of_files, gc.dec_hash_file)

    mbuild.vmsgb(1, "DEC-GEN", "Return code: " + str(retval))
    return (retval, error_output )

def run_encode_generator(gc, env):
    """Run the encoder table generator. This function is executed as
     required by the work_queue."""
    if env == None:
        return (1, ['no env!'])
    
    xedsrc    = aq(env['src_dir'])
    build_dir = aq(env['build_dir'])
        
    gen_extra_args = "--gendir %s --xeddir %s" % (build_dir, xedsrc)
    cmd = env.expand(gc.encode_command(xedsrc,
                                       gen_extra_args,
                                       env['amd_enabled'],
                                       env['encoder_chip']))
    mbuild.vmsgb(3, "ENC-GEN", cmd)
    (retval, output, error_output) = mbuild.run_command(cmd,
                                                        separate_stderr=True)
    oo = env.build_dir_join('ENC-OUT.txt')
    oe = env.build_dir_join('ENC-ERR.txt')
    xbc.write_file(oo, output)
    xbc.write_file(oe, error_output)

    if retval == 0:
        list_of_files = read_file_list(gc.enc_output_file)
        mbuild.hash_files(list_of_files, gc.enc_hash_file)

    mbuild.vmsgb(1, "ENC-GEN", "Return code: " + str(retval))
    return (retval, [] )

def _encode_command2(args):
    """Produce an encoder2 generator command."""
    s = []
    s.append( '%(pythonarg)s' )
    s.append( aq(mbuild.join(args.xeddir, 'pysrc', 'enc2gen.py')))
    s.append('--xeddir %s' % aq(args.xeddir))
    s.append('--gendir %s' % aq(args.gendir))
    s.extend( args.config.as_args() )
    if args.test_checked_interface:
        s.append('-chk' )  
    s.append('--output-file-list %s' % aq(args.enc2_output_file))
    return ' '.join(s)

def run_encode_generator2(args, env):
    """Run the encoder2 table generator. This function is executed as
     required by the work_queue."""
    if env == None:
        return (1, ['no env!'])
    
    args.xeddir = aq(env['src_dir'])
    # we append our own paths in the generator
    args.gendir = aq(env['libxed_build_dir']) 
        
    cmd = env.expand( _encode_command2(args) )

    mbuild.vmsgb(3, "ENC2-GEN", cmd)
    (retval, output, error_output) = mbuild.run_command(cmd,
                                                        separate_stderr=True)
    oo = env.build_dir_join('ENC2-OUT.txt')
    oe = env.build_dir_join('ENC2-ERR.txt')
    xbc.write_file(oo, output)
    xbc.write_file(oe, error_output)

    if retval == 0:
        list_of_files = read_file_list(args.enc2_output_file)
        mbuild.hash_files(list_of_files, args.enc2_hash_file)

    mbuild.vmsgb(1, "ENC2-GEN", "Return code: " + str(retval))
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
       for f in mbuild.glob(g):
          print("F: ", f)
          if script_files:
             apply_legal_header.apply_header_to_data_file(legal_header, f)
          else:
             apply_legal_header.apply_header_to_source_file(legal_header, f)
###########################################################################
# Doxygen build
def get_kit(env):
    if xbc.installing(env):
        return env['ikit'].kit
    return env['wkit'].kit
    
def doxygen_subs(env,api_ref=True):
   '''Create substitutions dictionary for customizing doxygen run'''
   subs = {}
   subs['XED_TOPSRCDIR']   = aq(env['src_dir'])
   dir = get_kit(env)
   if not os.path.exists(dir):
       xbc.cdie("Cannot find kit directory ({}) when building docs.".format(dir))
   subs['XED_KITDIR']      = aq(dir)
   subs['XED_GENDOC']      = aq(env['doxygen_install'])
   if api_ref:
      subs['XED_INPUT_TOP'] = aq(env.src_dir_join(mbuild.join('docsrc',
                                                          'xed-doc-top.txt')))
   else:
      subs['XED_INPUT_TOP'] = aq(env.src_dir_join(mbuild.join('docsrc',
                                                            'xed-build.txt')))
   #subs['XED_HTML_HEADER'] = aq(env.src_dir_join(mbuild.join('docsrc',
   #                                                 'xed-doxygen-header.txt')))
   if env['doxygen_internal']:
       subs['XED_EXTERNAL'] = ''
   else:
       subs['XED_EXTERNAL'] = 'EXTERNAL'

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

def create_doxygen_api_documentation(env, work_queue):
    # After applying the legal header, create the doxygen from the kit
    # files, and place the output right in the kit.
    if 'doc' in env['targets']:
        if xbc.installing(env):
            kitdoc = env['ikit'].doc
        else:
            kitdoc = env['wkit'].doc
        make_doxygen_api(env, work_queue, kitdoc)
        if env['doxygen_install']:        
            make_doxygen_api(env, work_queue, env['doxygen_install'])
    
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

    kitdir = get_kit(e2)
    inputs.extend(  mbuild.glob(kitdir,'include', 'xed', '*'))
    inputs.extend(  mbuild.glob(kitdir,'examples','*.c'))
    inputs.extend(  mbuild.glob(kitdir,'examples','*.cpp'))
    inputs.extend(  mbuild.glob(kitdir,'examples','*.[Hh]'))
    inputs.append(  e2['mfile'] )
    mbuild.doxygen_run(e2, inputs, subs, work_queue, 'dox-ref')

    
def mkenv():
    """External entry point: create the environment"""
    if not mbuild.check_python_version(2,7):
        xbc.cdie("Need python 2.7 or later.  Suggested >= 3.7")
    if sys.version_info.major >= 3:
        if not mbuild.check_python_version(3,4):
            xbc.cdie("Need python 3.4 or later.  Suggested >= 3.7")

    # create an environment, parse args
    env = mbuild.env_t()
    standard_defaults = dict(    doxygen_install='',
                                 doxygen='',
                                 doxygen_internal=False,
                                 clean=False,
                                 die_on_errors=True,
                                 xed_messages=False,
                                 xed_asserts=False,
                                 pedantic=True,
                                 clr=False,
                                 use_werror=True,
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
                                 clx=True,
                                 cpx=True,
                                 cnl=True,
                                 icl=True,
                                 tgl=True,
                                 adl=True,
                                 spr=True,
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
                                 encoder_chip='ALL',
                                 via_enabled=True,
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
                                 verbose = 1,
                                 compress_operands=False,
                                 add_orphan_inst_to_future_chip=False,
                                 test_perf=False,
                                 example_linkflags='',
                                 example_flags='',
                                 example_rpaths=[],
                                 android=False,
                                 copy_libc=False,
                                 pin_crt='',
                                 static_stripped=False,
                                 set_copyright=False,
                                 asan=False,
                                 enc2=False,
                                 enc2_test=False,
                                 enc2_test_checked=False,
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
    env.parser.add_option("--example-flags", 
                          dest="example_flags",
                          action="store",
                          help="Extra compilation flags for the examples")
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
    env.parser.add_option("--doxygen-internal", 
                          dest="doxygen_internal", 
                          action="store_true",
                          help="Create internal version of build documentation (just changes paths for git repos)")
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
                          help="Do not include SKL (Skylake Client).")
    env.parser.add_option("--no-skx",
                          action="store_false", 
                          dest="skx", 
                          help="Do not include SKX (Skylake Server).")
    env.parser.add_option("--no-clx",
                          action="store_false", 
                          dest="clx", 
                          help="Do not include CLX (Cascade Lake Server).")
    env.parser.add_option("--no-cpx",
                          action="store_false", 
                          dest="cpx", 
                          help="Do not include CPX (Cooper Lake Server).")
    env.parser.add_option("--no-cnl",
                          action="store_false", 
                          dest="cnl", 
                          help="Do not include CNL.")
    env.parser.add_option("--no-icl",
                          action="store_false", 
                          dest="icl", 
                          help="Do not include ICL.")
    env.parser.add_option("--no-tgl",
                          action="store_false", 
                          dest="tgl", 
                          help="Do not include TGL.")
    env.parser.add_option("--no-adl",
                          action="store_false", 
                          dest="adl", 
                          help="Do not include ADL.")
    env.parser.add_option("--no-spr",
                          action="store_false", 
                          dest="spr", 
                          help="Do not include SPR.")
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
    env.parser.add_option("--no-via", 
                          action="store_false",
                          dest="via_enabled",
                          help="Disable VIA public instructions")
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
    env.parser.add_option("--add-orphan-inst-to-future-chip", 
                          action="store_true",
                          dest="add_orphan_inst_to_future_chip",
                          help="Add orphan isa-sets to future chip definition.")
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
    env.parser.add_option("--asan", 
                          action="store_true",
                          dest="asan",
                          help="Use Address Sanitizer (on linux)")
    env.parser.add_option("--enc2", 
                          action="store_true",
                          dest="enc2",
                          help="Build the enc2 fast encoder. Longer build.")
    env.parser.add_option("--enc2-test", 
                          action="store_true",
                          dest="enc2_test",
                          help="Build the enc2 fast encoder *tests*. Longer build.")
    env.parser.add_option("--enc2-test-checked", 
                          action="store_true",
                          dest="enc2_test_checked",
                          help="Build the enc2 fast encoder *tests*. Test the checked interface. Longer build.")
    env.parser.add_option("--encoder-chip", 
                          action="store",
                          dest="encoder_chip",
                          help="Specific encoder chip. Default is ALL")
    env.parse_args(env['xed_defaults'])

def init_once(env):
    xbc.init_once(env)
    
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
            if mbuild.is_python3():
                vers = ['39', '38', '37', '36', '35']
                python_commands = [ 'c:/python{}/python.exe'.format(x) for x in vers ]
            else:
                vers = ['27','26','25']
                python_commands = [ 'c:/python{}/python.exe'.format(x) for x in vers ]
            python_command = None
            for p in python_commands:
               if os.path.exists(p):
                  python_command = p
                  break
            if not python_command:
               xbc.cdie("Could not find win32 python at these locations: %s" %
                          "\n\t" + "\n\t".join(python_commands))
                
    env['pythonarg'] = aq(python_command)
    mbuild.vmsgb(3, "PYTHON", env['pythonarg'])

    xbc.init(env)
    
    env.add_define('XED_GIT_VERSION="%(xed_git_version)s"')
    if env['shared']:
        env.add_define('XED_DLL')

    # includes
    env.add_include_dir(mbuild.join(env['src_dir'],"include","private"))
    # this is required for older code that has not been updated to use xed/ on includes
    env.add_include_dir(mbuild.join(env['src_dir'],"include","public",'xed'))
    env.add_include_dir(mbuild.join(env['src_dir'],"include","public"))
    
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
    if mbuild.verbose(2):
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
        mbuild.vmsgb(1, "EXTF PROCESSING", ext_file)
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
                    mbuild.vmsgb(1, "CONSIDERING SOURCE",
                                 '{} {} {}'.format(fname, ptype, priority))
                    if source_prio[ptype] < priority:
                        mbuild.vmsgb(1, "ADDING SOURCE",
                                     '{} {} {}'.format(fname, ptype, priority))
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
                        xbc.cdie('badly formatted extension line. expected 2 or 3 arguments: {}'.format(line))
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
    if env['via_enabled']:
        env.add_define('XED_VIA_ENABLED')

    if env['avx']:
        env.add_define('XED_AVX')

    if _test_chip(env, ['knl','knm', 'skx', 'clx', 'cpx', 'cnl', 'icl', 'tgl', 'spr']):
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
    if env['enc2']:
        env.add_define('XED_ENC2_ENCODER')

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
        
    if env['via_enabled']:
        newstuff.append( env.src_dir_join(mbuild.join('datafiles', 'via',
                                                      'files-via-padlock.cfg')))

    # add AMD stuff under knob control
    if env['amd_enabled']:
        newstuff.append( env.src_dir_join(mbuild.join('datafiles','amd',
                                                      'files-amd.cfg')))
        if env['avx']:
            newstuff.append( env.src_dir_join(mbuild.join('datafiles','amd',
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
    if not env['knc']:
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
        if env['clx']:
            _add_normal_ext(env,'clx')
            _add_normal_ext(env,'vnni')
        if env['cpx']:
            _add_normal_ext(env,'cpx')
            _add_normal_ext(env,'avx512-bf16')
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
        if env['tgl']:
            _add_normal_ext(env,'tgl')
            _add_normal_ext(env,'cet')
            _add_normal_ext(env,'movdir')
            _add_normal_ext(env,'vp2intersect')
            _add_normal_ext(env,'keylocker')
        if env['adl']:
            _add_normal_ext(env,'adl')
            _add_normal_ext(env,'hreset')
            _add_normal_ext(env,'avx-vnni')
            _add_normal_ext(env,'keylocker')
        if env['spr']:
            _add_normal_ext(env,'spr')
            _add_normal_ext(env,'hreset')
            _add_normal_ext(env,'uintr')
            _add_normal_ext(env,'cldemote')
            _add_normal_ext(env,'avx-vnni')
            _add_normal_ext(env,'amx-spr')
            _add_normal_ext(env,'waitpkg')
            _add_normal_ext(env,'avx512-bf16')
            _add_normal_ext(env,'enqcmd')
            _add_normal_ext(env,'tsx-ldtrk')
            _add_normal_ext(env,'serialize')
            _add_normal_ext(env,'tdx')
            _add_normal_ext(env,'avx512-fp16')
            _add_normal_ext(env,'evex-map5-6')
            
        if env['future']: 
            _add_normal_ext(env,'future')
            _add_normal_ext(env,'tdx')



        
    env['extf'] = newstuff + env['extf']

def _get_src(env,subdir):
    return mbuild.glob(env['src_dir'],'src',subdir,'*.c')

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

def add_encoder_command(env, gc, gen_dag, prep):
    enc_py = [ 'pysrc/read-encfile.py',
               'pysrc/map_info_rdr.py',
               'pysrc/genutil.py', 'pysrc/encutil.py',
               'pysrc/verbosity.py', 'pysrc/patterns.py', 'pysrc/actions.py',
               'pysrc/operand_storage.py', 'pysrc/opnds.py', 'pysrc/ild_info.py',
               'pysrc/codegen.py', 'pysrc/ild_nt.py', 'pysrc/actions.py',
               'pysrc/ild_codegen.py', 'pysrc/tup2int.py',
               'pysrc/constraint_vec_gen.py', 'pysrc/xedhash.py',
               'pysrc/ild_phash.py', 'pysrc/actions_codegen.py',
               'pysrc/hashlin.py', 'pysrc/hashfks.py', 'pysrc/hashmul.py',
               'pysrc/func_gen.py', 'pysrc/refine_regs.py',
               'pysrc/slash_expand.py', 'pysrc/nt_func_gen.py',
               'pysrc/scatter.py', 'pysrc/ins_emit.py',
               'pysrc/chipmodel.py' ]

    enc_py = env.src_dir_join(enc_py)
    gc.enc_hash_file = env.build_dir_join('.mbuild.hash.xedencgen')
    
    ed = env.build_dir_join('ENCGEN-OUTPUT-FILES.txt')
    if os.path.exists(ed):
        need_to_rebuild_enc = need_to_rebuild(ed, gc.enc_hash_file)
        if need_to_rebuild_enc:
            mbuild.remove_file(ed)

    gc.enc_output_file = ed
    enc_input_files = gc.all_input_files() + prep.targets + enc_py + [env['mfile']]
    c2 = mbuild.plan_t(name='encgen',
                       command=run_encode_generator,
                       args=gc,
                       env=env,
                       input=enc_input_files,
                       output= ed)
    enc_cmd = gen_dag.add(env,c2)

class dummy_obj_t(object):
    def __init__(self):
        pass
    
class enc2_config_t(object):
    def __init__(self, mode, asz):
        self.mode=mode
        self.asz=asz
        
    def as_args(self):
        return ['-m{}'.format(self.mode),
                '-a{}'.format(self.asz) ]
    
    def __str__(self):
        return 'enc2-m{}-a{}'.format(self.mode,self.asz)
    def cpp_define(self):
        return 'XED_ENC2_CONFIG_M{}_A{}'.format(self.mode, self.asz)
    
def add_encoder2_command(env, dag, input_files, config):
    enc_py = ['pysrc/genutil.py',
              'pysrc/codegen.py',
              'pysrc/read_xed_db.py',
              'pysrc/opnds.py',
              'pysrc/opnd_types.py',
              'pysrc/cpuid_rdr.py',
              'pysrc/slash_expand.py',
              'pysrc/patterns.py',
              'pysrc/gen_setup.py',              
              'pysrc/enc2gen.py',
              'pysrc/enc2test.py',
              'pysrc/enc2argcheck.py' ]

    enc2args = dummy_obj_t()
    enc_py = env.src_dir_join(enc_py)
    enc2args.enc2_hash_file   = env.build_dir_join('.mbuild.hash.xedencgen2-{}'.format(config))
    enc2args.enc2_output_file = env.build_dir_join('ENCGEN2-OUTPUT-FILES-{}.txt'.format(config))
    enc2args.config = config
    enc2args.test_checked_interface = env['enc2_test_checked']
    if os.path.exists(enc2args.enc2_output_file):
        need_to_rebuild_enc = need_to_rebuild(enc2args.enc2_output_file,
                                              enc2args.enc2_hash_file)
        if need_to_rebuild_enc:
            mbuild.remove_file(enc2args.enc2_output_file)

    enc_input_files = input_files +  enc_py + [env['mfile']]
    c = mbuild.plan_t(name='encgen2-{}'.format(config),
                      command=run_encode_generator2,
                      args=enc2args,
                      env=env,
                      input=enc_input_files,
                      output=enc2args.enc2_output_file)
    enc_cmd = dag.add(env,c)

# Python imports used by the 2 generators.
# generated 2016-04-15 by importfinder.py:
#   pysrc/importfinder.py generator pysrc
#   pysrc/importfinder.py read-encfile pysrc
#  importfinder.py is too slow to use on every build, over 20seconds/run.

def add_decoder_command(env, gc, gen_dag, prep):
    dec_py =['pysrc/generator.py',
             'pysrc/map_info_rdr.py',
             'pysrc/actions.py', 'pysrc/genutil.py',
             'pysrc/ild_easz.py', 'pysrc/ild_codegen.py', 'pysrc/tup2int.py',
             'pysrc/encutil.py', 'pysrc/verbosity.py', 'pysrc/ild_eosz.py',
             'pysrc/xedhash.py', 'pysrc/ild_phash.py',
             'pysrc/actions_codegen.py', 'pysrc/patterns.py',
             'pysrc/operand_storage.py', 'pysrc/opnds.py', 'pysrc/hashlin.py',
             'pysrc/hashfks.py', 'pysrc/ild_info.py', 'pysrc/ild_cdict.py',
             'pysrc/codegen.py', 'pysrc/ild_nt.py',
             'pysrc/hashmul.py', 'pysrc/enumer.py', 'pysrc/enum_txt_writer.py',
             'pysrc/dec_dyn.py', 'pysrc/ild_disp.py', 'pysrc/ild_imm.py',
             'pysrc/ild_modrm.py', 'pysrc/ild_storage.py',
             'pysrc/slash_expand.py',
             'pysrc/chipmodel.py', 'pysrc/flag_gen.py', 'pysrc/opnd_types.py',
             'pysrc/hlist.py', 'pysrc/ctables.py', 'pysrc/ild.py',
             'pysrc/refine_regs.py', 'pysrc/metaenum.py', 'pysrc/classifier.py']
          
    dec_py = env.src_dir_join(dec_py)
    dec_py += mbuild.glob(env['src_dir'], 'datafiles/*enum.txt')

    gc.dec_hash_file = env.build_dir_join('.mbuild.hash.xeddecgen')

    dd = env.build_dir_join('DECGEN-OUTPUT-FILES.txt')
    if os.path.exists(dd):
        need_to_rebuild_dec = need_to_rebuild(dd, gc.dec_hash_file)
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
                       output=dd)
    dec_cmd = gen_dag.add(env,c1)

def wq_build(env,work_queue, dag):
    okay = work_queue.build(dag,
                            die_on_errors=env['die_on_errors'],
                            show_progress=True, 
                            show_output=True,
                            show_errors_only=_wk_show_errors_only())
    return okay
    
    
def build_libxed(env,work_queue):
    "Run the generator and build libxed"
    
    # create object that will assemble our command line.
    gc = generator_inputs_t(env['build_dir'], 
                            env['amd_enabled'],
                            env['limit_strings'],
                            env['encoder_chip'])

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

    # Add commands for building decoder and encoder(s)
    add_decoder_command(env, gc, gen_dag, prep)
    if env['encoder']:
        add_encoder_command(env, gc, gen_dag, prep)

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
        mbuild.vmsgb(3, phase, "succeeded")

    if 'just-gen' in env['targets']:
        mbuild.vmsgb(1, "STOPPING", "after %s" % phase)
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

    generated_library_sources = mbuild.glob(env['build_dir'],'*.c')
    
    nongen_lib_sources = _get_src(env,'common') 
    if env['decoder']:
        nongen_lib_sources.extend(_get_src(env,'dec'))
    else:
        generated_library_sources = _remove_src(generated_library_sources,
                                                'xed-iform-map-init.c')
    if env['encoder']:
         for d in ['enc']:
             nongen_lib_sources.extend(_get_src(env,d))
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
        mbuild.vmsgb(1, "SKIPPING LIBRARY BUILD")
    else:
        okay = wq_build(env, work_queue, lib_dag)
        if okay and env['shared'] and not env['debug']:
            xbc.strip_file(env,     env['shd_libxed'], '-x')
            if os.path.exists(env['shd_libild']):
                xbc.strip_file(lib_env, env['shd_libild'], '-x')
        if not okay:
            xbc.cdie("Library build failed")
        mbuild.vmsgb(3, "LIBRARY", "build succeeded")

    del lib_env
    input_files = gc.all_input_files() + prep.targets
    return input_files

def build_libxedenc2(arg_env, work_queue, input_files, config):
    '''Create and run the builder that creates the xed enc2 encoder source
       files, header files and associated tests. Then compile the
       generated files.    '''

    env = copy.deepcopy(arg_env)

    # *** REDEFINE THE BUILD DIRECTORY ***
    # keep the libxed build dir around in case we need it
    env['libxed_build_dir'] = env['build_dir']
    env['build_dir'] = mbuild.join(env['libxed_build_dir'], str(config))
    mbuild.cmkdir(env['build_dir'])
    
    dag = mbuild.dag_t('xedenc2gen-{}'.format(config), env=env)
    add_encoder2_command(env, dag, input_files, config)

    phase = "ENCODE2 GENERATOR FOR CONFIGURATION {}".format(config)
    mbuild.vmsgb(3, phase, "building...")
    okay = wq_build(env, work_queue, dag)
    if not okay:
        xbc.cdie("[%s] failed. dying..." % phase)

    # The unchecked enc2 library
    lib, dll = xbc.make_lib_dll(env,'xed-{}'.format(config))
    x = mbuild.join(env['build_dir'], lib)
    env['shd_enc2_lib']  = x
    env['link_enc2_lib'] = x
    if  env['shared']:
        env['shd_enc2_lib']  = mbuild.join(env['build_dir'], dll)
        # use gcc for making the shared object
        env['CXX_COMPILER']= env['CC_COMPILER']

    gen_src    = mbuild.glob(env['build_dir'],'src','*.c')
    hdr_dir    = mbuild.join(env['build_dir'],'hdr')
    nongen_src = _get_src(env,'enc2')
    
    dag = mbuild.dag_t('xedenc2lib-{}'.format(config), env=env)
    env.add_include_dir(hdr_dir)
    objs = env.compile( dag, gen_src + nongen_src)
    if env['shared']:
        u = env.dynamic_lib(objs, env['shd_enc2_lib'])
    else:
        u = env.static_lib(objs, env['link_enc2_lib'])
    dag.add(env,u)


    # The *checked* enc2 library
    lib_chk, dll_chk = xbc.make_lib_dll(env,'xed-chk-{}'.format(config))
    x = mbuild.join(env['build_dir'], lib_chk)
    env['shd_chk_lib']  = x
    env['link_chk_lib'] = x
    if  env['shared']:
        env['shd_chk_lib']  = mbuild.join(env['build_dir'], dll_chk)

    gen_src    = mbuild.glob(env['build_dir'],'src-chk','*.c')
    nongen_src = _get_src(env,'enc2chk')

    objs = env.compile( dag, gen_src + nongen_src)
    if env['shared']:
        u = env.dynamic_lib(objs, env['shd_chk_lib'])
    else:
        u = env.static_lib(objs, env['link_chk_lib'])
    dag.add(env,u)

    
    okay = wq_build(env, work_queue, dag)
    if not okay:
        xbc.cdie("XED ENC2Library build failed")
    mbuild.vmsgb(3, "LIBRARY", "XED ENC2 build succeeded")

    if env['enc2_test']:
        build_enc2_test(env, work_queue, config)
        
    return (env['shd_enc2_lib'], env['link_enc2_lib'],
            env['shd_chk_lib'],  env['link_chk_lib']    )

def build_enc2_test(arg_env, work_queue, config):
    '''Build the enc2 tester program for the specified config '''
    # this env has build_dir set to the current mode/asz config
    env = copy.deepcopy(arg_env)
    env['shared']=False 
    
    env['config'] = str(config)
    exe         = mbuild.join(env['build_dir'],'enc2tester-%(config)s%(EXEEXT)s')
    gen_src     = mbuild.glob(env['build_dir'],'test','src','*.c')
    gen_hdr_dir = mbuild.join(env['build_dir'],'test','hdr')
    static_src  = mbuild.glob(env['src_dir'],'src','enc2test','*.c')

    env.add_define(config.cpp_define())
    
    dag = mbuild.dag_t('xedenc2test-{}'.format(config), env=env)
    env.add_include_dir(gen_hdr_dir)
    objs = env.compile( dag, gen_src + static_src )

    if env.on_linux() and env['shared']:
        env['LINKFLAGS'] += " -Wl,-rpath,'$ORIGIN/../wkit/lib'"
    
    lc = env.link(objs + [ env['link_chk_lib'], env['link_enc2_lib'], env['link_libxed']], exe)
    cmd = dag.add(env,lc)
    mbuild.vmsgb(3, 'BUILDING', "ENC2 config {} test program".format(config))
    okay = wq_build(env, work_queue, dag)
    if not okay:
        xbc.cdie("XED ENC2 config {} test program build failed".format(config))
    if env.on_mac() and env['shared']:
        _modify_search_path_mac(env, exe, '@loader_path/../wkit/lib')
    mbuild.vmsgb(3, "TESTPROG", "XED ENC2 config {} test program build succeeded".format(config))

def _modify_search_path_mac(env, fn, tgt=None):
   """Make example tools refer to the libxed.so from the lib directory
   if doing and install. Mac only."""
   if not env['shared']:
      return
   if not env.on_mac():
      return 
   if not xbc.installing(env):
      return
   env['odll'] = '%(build_dir)s/libxed.dylib'
   
   if tgt:
       env['ndll'] = tgt
   else:
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
    wkit = env['wkit']
    for exe in mbuild.glob(wkit.bin, '*'):
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
    wkit = env['wkit']
    xed_min = None    
    #check if we have xed-min test
    for exe in mbuild.glob(wkit.bin, '*'):
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

def _clean_out_wkit_bin(env):        
    wkit = env['wkit']
    for f in mbuild.glob(wkit.bin,'*'):
        mbuild.remove_file(f)

def _copy_examples_to_bin(env,xkit):
    for f in env['example_exes']:
        if os.path.exists(f):
            mbuild.copy_file(f,xkit.bin)
            _modify_search_path_mac(env,
                                    mbuild.join( xkit.bin, os.path.basename(f)))
    
def _test_examples(env):
    _get_xed_min_size(env)
    _test_perf(env)


def build_examples(env):
    '''Build examples in the kit. Copy executables to wkit.bin'''

    env['example_exes'] = []
    if not set(['examples','cmdline']).intersection(env['targets']):
        return
    
    wkit = env['wkit']
    sys.path.insert(0, wkit.examples )
    import xed_examples_mbuild
    env_ex = copy.deepcopy(env)
    env_ex['CPPPATH']   = [] # clear out libxed-build headers.
    env_ex['src_dir']   = wkit.examples 
    env_ex['build_dir'] = mbuild.join(wkit.examples, 'obj')
    mbuild.cmkdir( env_ex['build_dir'] )
    
    env_ex['xed_lib_dir'] =   wkit.lib 
    env_ex['xed_inc_dir'] =  [ wkit.include_top ] 

    env_ex['set_copyright'] = False
    if env.on_windows():
        env_ex['set_copyright'] = env['set_copyright']

    if env['enc2']:
        env_ex['xed_enc2_libs'] = ( mbuild.glob(wkit.lib, '*xed-chk-enc2-*') + 
                                    mbuild.glob(wkit.lib, '*xed-enc2-*')      )

    try:
        retval = xed_examples_mbuild.examples_work(env_ex)
    except Exception as e:
        xbc.handle_exception_and_die(e)
        
    if 'example_exes' in env_ex:
        env['example_exes'] = env_ex['example_exes']


def _copy_dynamic_libs_to_kit(env,xkit):
    """Copy *all* the dynamic libs that ldd finds to the extlib dir in the
       (wkit or ikit) kit"""
    import external_libs

    if not env.on_linux() and not env.on_freebsd() and not env.on_netbsd():
        return
    
    xkit.extlib = mbuild.join(xkit.kit,'extlib')
    if os.path.exists(xkit.extlib):
        mbuild.remove_tree(xkit.extlib)
    mbuild.cmkdir(xkit.extlib)
    executables = mbuild.glob(xkit.bin,'*')

    extra_ld_library_paths = env['ld_library_path']    
    if env['use_elf_dwarf_precompiled']:
        if 'extern_lib_dir' not in env:
            env['extern_lib_dir']  = '%(xedext_dir)s/external/lin/lib%(arch)s'

        extra_ld_library_paths.append( env.expand('%(extern_lib_dir)s') )

    # run LDD to find the shared libs and do the copies
    okay = external_libs.copy_system_libraries(env,
                                               xkit.extlib,
                                               executables,
                                               extra_ld_library_paths)
    if not okay:
        mbuild.warn("There was a problem running LDD when making the kit")

    # copy the libelf/dwarf license
    if env['use_elf_dwarf_precompiled']:
        env2 = copy.deepcopy(env)
        xbc.cond_add_elf_dwarf(env2)
        mbuild.copy_file(env2['libelf_license'], xkit.extlib)


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
       
    mbuild.vmsgb(3, "HEADER TAG", fn)

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
        lib1 = [ env.expand(x) for x in libnames_template ]
        lib2 = [ mbuild.join(env['build_dir'], x) for x in lib1 ]
        libnames.extend(lib2)

    if env['enc2']:
        for config in env['enc2_configs']:
            c = str(config) # used in template expansion
            env['base_lib'] = 'xed-{}'.format(c)
            lib1 = [ env.expand(x) for x in libnames_template ]
            lib2 = [ mbuild.join(env['build_dir'], c, x ) for x in lib1 ]
            libnames.extend(lib2)
            
            env['base_lib'] = 'xed-chk-{}'.format(c)
            lib1 = [ env.expand(x) for x in libnames_template ]
            lib2 = [ mbuild.join(env['build_dir'], c, x ) for x in lib1 ]
            libnames.extend(lib2)
    
    libs = list(filter(lambda x: os.path.exists(x), libnames))
    return libs

def _copy_generated_headers(env, dest):
    gincs = mbuild.glob(env['build_dir'],'*.h')

    if env['enc2']:
        for config in env['enc2_configs']:
            gincs += mbuild.glob(env['build_dir'], str(config), 'hdr', 'xed', '*.h')
    
    if len(gincs) == 0:
        xbc.cdie("No generated include headers found for install")
    for  h in gincs:
        mbuild.copy_file(h,dest)

def _copy_nongenerated_headers(env, dest):
    src_inc = mbuild.join(env['src_dir'],'include',"public",'xed','*.h')
    incs= mbuild.glob(src_inc)
    if len(incs) == 0:
        xbc.cdie("No standard include headers found for install")
    for  h in incs:
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

    for h in  mbuild.glob(dest,'*.[Hh]'):
        mbuild.vmsgb(3, "HEADER TAG", h)
        apply_legal_header2(h, legal_header)

                                                 
def system_install(env, work_queue):
    """Build install in the prefix_dir. Use prefix_lib_dir as library name
       since some systems use lib, lib32 or lib64. non-windows only.
    """
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
        mbuild.copy_file(f, lib)
        fn = mbuild.join(lib,os.path.basename(f))
        if env['shared']:
            _set_perm(fn)
        else:
            mbuild.make_read_only(fn)

    _copy_generated_headers(env, include)
    _copy_nongenerated_headers(env, include)
    _apply_legal_header_to_headers(env, include)

    for fn in mbuild.glob(include,'*.h'):
        mbuild.make_read_only(fn)

def create_install_kit_structure(env, work_queue):
    if xbc.installing(env):
        ikit = dummy_obj_t()
        env['ikit'] = ikit
        
        if env['install_dir']:
            if env['install_dir'] == env['build_dir']:
                xbc.die("install_dir cannot have same value as build_dir")
            if env['install_dir'] == env['wkit'].kit:
                xbc.die("install_dir cannot have same value as build_dir working kit")
            ikit.kit = env['install_dir']
        else:
            date = time.strftime("%Y-%m-%d")
            sd = 'xed-install-%s-%s-%s-%s' % ( env['kit_kind'], 
                                               date, 
                                               env['build_os'], 
                                               env['host_cpu'] )
            ikit.kit = os.path.join('kits', sd)

        if os.path.exists(ikit.kit): # start clean
            mbuild.remove_tree(ikit.kit)
        mbuild.cmkdir(ikit.kit)
        _make_kit_dirs(env, ikit)

def _prep_kit_dirs(env):
    def pr(x):
        return (x,x)
    env['kit_dirs'] = [ ('include_top',mbuild.join('include')),
                        ('include_xed',mbuild.join('include','xed')),
                        ('mbuild', mbuild.join('mbuild','mbuild')),
                        pr('lib'),
                        pr('extlib'),
                        pr('examples'),
                        pr('bin'),
                        pr('doc'),
                        pr('misc') ]
    
def _make_kit_dirs(env,some_kit):
    for key,pth in env['kit_dirs']:
        d = mbuild.join(some_kit.kit,pth)
        setattr(some_kit, key, d)
        mbuild.cmkdir(d)
    
def create_working_kit_structure(env, work_queue):
    '''Create directories and copy files in to the XED "working" kit.'''

    wkit = dummy_obj_t()

    # add a default legal header if we are building a kit and none is
    # specified.
    legal_header = _get_legal_header(env)
    
    wkit.kit = mbuild.join(env['build_dir'], 'wkit')
    
    # We are not going to start clean because otherwise
    # examples rebuild on each rebuild.
    
    mbuild.cmkdir(wkit.kit)
    env['wkit'] = wkit
    _make_kit_dirs(env, wkit)
    _clean_out_wkit_bin(env)
    
    boilerplate = env.src_dir_join([ 'LICENSE', 'README.md' ])
    for f in boilerplate:
        if os.path.exists(f):
            mbuild.copy_file(f,wkit.kit)
        else:
            mbuild.die("Could not find {}".format(f))

    # copy the miscellaneous files to the misc directory
    for gfn in ['idata.txt', 'cdata.txt']:
        full_gfn = mbuild.join(env['build_dir'], gfn)
        mbuild.copy_file(full_gfn, wkit.misc)
        apply_legal_header2(mbuild.join(wkit.misc,gfn), legal_header)

    # copy mbuild to kit
    for fn in mbuild.glob(env['src_dir'], '..', 'mbuild', 'mbuild','*.py'):
        mbuild.copy_file(fn, wkit.mbuild)
        dfn = mbuild.join(wkit.mbuild, os.path.basename(fn))
        apply_legal_header2(dfn, legal_header)

    # copy the common build file to the examples dir of the kits
    common =mbuild.join(env['src_dir'],'xed_build_common.py')
    mbuild.copy_file(common, wkit.examples)
    apply_legal_header2(mbuild.join(wkit.examples, 'xed_build_common.py'),
                        legal_header)

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
                mbuild.copy_file(dll,wkit.bin)

    # copy the libraries. (DLL goes in bin)
    libs = _gen_lib_names(env)
    if len(libs) == 0:
        xbc.cdie("No libraries found for install")

    for f in libs:
        if f.find('.dll') != -1:
            mbuild.copy_file(f, wkit.bin)
        else:
            mbuild.copy_file(f, wkit.lib)
            
    # copy any *.pdb files if one exists
    copy_pdb_files = False
    if copy_pdb_files:
        pdb_files = mbuild.glob(env['build_dir'],'*.pdb')
        for pdb in pdb_files:
            if os.path.exists(pdb):
                mbuild.copy_file(pdb,wkit.lib)

    # copy examples source
    for ext in ['*.[Hh]', '*.c', '*.cpp', '*.py', '*.txt']:
        esrc = mbuild.glob(env['src_dir'],'examples',ext)
        if len(esrc) == 0:
            xbc.cdie( "No examples files to install with extension {}".format(ext))
        for  s in esrc:
            mbuild.copy_file(s,wkit.examples)

            # legal header stuff
            base = os.path.basename(s)
            tgt = mbuild.join(wkit.examples,base)
            if 'LICENSE' not in tgt and not 'rc-template' in tgt:
                apply_legal_header2(tgt, legal_header)
                
    _copy_nongenerated_headers(env,wkit.include_xed)
    _copy_generated_headers(env, wkit.include_xed)
    _apply_legal_header_to_headers(env, wkit.include_xed)


def copy_working_kit_to_install_dir(env):
    def keeper(fn):
        if fn in ['obj','__pycache__']:
            return False
        if fn.endswith('.pyc'):
            return False
        if os.path.isdir(fn):
            return False
        return True

    
    if xbc.installing(env):
        ikit = env['ikit']
        wkit = env['wkit']
        mbuild.msgb("INSTALL DIR", ikit.kit)

        for key, kd in env['kit_dirs']:
            src = getattr(wkit,key)
            dst = getattr(ikit,key)
            for f in mbuild.glob(src,'*'):
                if keeper(f):
                    mbuild.copy_file(f,dst)
        
        # copy the examples that we just built
        for f in env['example_exes']:
            if os.path.exists(f):
                if not env['debug']:
                    xbc.strip_file(env,f)
                mbuild.copy_file(f,ikit.bin)
                _modify_search_path_mac(env, 
                                        mbuild.join( ikit.bin, 
                                                     os.path.basename(f)))
        # we get the extlib files from the wkit
            
def compress_kit(env):
    '''build a zip file'''
    if 'zip' in env['targets']:
        ikit = env['ikit']
        wfiles = os.walk( ikit.kit )
        zip_files = []
        for (path,dirs,files) in wfiles:
            zip_files.extend( [ mbuild.join(path,x) for x in  files] )
        import zipfile
        archive = ikit.kit + '.zip'
        z = zipfile.ZipFile(archive,'w')
        for f in zip_files:
            z.write(f)
        z.close()
        mbuild.msgb("ZIPFILE", archive)
        env['kit_zip_file']=archive


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
        mbuild.vmsgb(1, "EMIT BUILD DEFINES HEADER FILE")
        f = open(fn,"w")
        for line in klist:
            f.write(line)
        f.close()
    else:
        mbuild.vmsgb(1, "REUSING BUILD DEFINES HEADER FILE")

def update_version(env):
   new_rev = get_git_version(env)
   date = time.strftime("%Y-%m-%d")
   if new_rev:
      mbuild.vmsgb(1, "GIT VERSION", new_rev)
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
    wkit = env['wkit']
    cmd = "{}/xed -n 1000 -i {}/obj/xed%(OBJEXT)s".format(wkit.bin, wkit.examples)
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
    env['test_dir'] = aq(mbuild.join(env['src_dir'],'tests'))
    wkit = env['wkit']
    cmd = "%(python)s %(test_dir)s/run-cmd.py --build-dir {} ".format(wkit.bin)

    dirs = ['tests-base', 'tests-knc', 'tests-avx512', 'tests-xop', 'tests-syntax']
    if env['cet']:
        dirs.append('tests-cet')
    for d in dirs:
        x  = aq(mbuild.join(env['test_dir'],d))
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
    if env['via_enabled']:
        codes.append('VIA')
    if env['amd_enabled']:
        codes.append('AMD')
    for c in codes:
        cmd += ' -c ' + c

    output_file = env.build_dir_join('TEST.OUT.txt')
    cmd  = env.expand_string(cmd)
    mbuild.vmsgb(2, "TEST COMMAND", "%s > %s" %(cmd,str(output_file)))
    (retcode, stdout, stderr) = mbuild.run_command_output_file(cmd,
                                                               output_file,
                                                               osenv=osenv)
    #if retcode == 1:
    #   for l in stdout:
    #      print(l.rstrip())

    for l in stdout:
        l = l.rstrip()
        if re.search(r'^\[(TESTS|ERRORS|SKIPPED|PASS_PCT|FAIL)\]',l):
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
        mbuild.warn("No AVX -> Disabling SNB, IVB, HSW, BDW, SKL, SKX, CLX, CPX, CNL, ICL, TGL, ADL, SPR, KNL, KNM Future\n\n\n")
        env['ivb'] = False
        env['hsw'] = False
        env['bdw'] = False
        env['skl'] = False
        env['skx'] = False
        env['clx'] = False
        env['cpx'] = False
        env['tgl'] = False
        env['adl'] = False
        env['spr'] = False
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
        env['clx'] = False
        env['cpx'] = False
        env['cnl'] = False
        env['icl'] = False
        env['tgl'] = False
        env['spr'] = False
        env['knl'] = False
        env['knm'] = False
        env['future'] = False

    # turn off downstream (later) stuff logically
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
        env['clx'] = False
        env['cpx'] = False        
    if not env['cnl']:
        env['icl'] = False
    if not env['icl']:
        env['tgl'] = False
    if not env['tgl']:
        env['cet'] = False
        env['spr'] = False
    if not env['spr']:
        env['future'] = False
        
    if env['knc']: 
        mbuild.warn("Disabling AMD, AVX512, FUTURE, for KNC build\n\n\n")
        env['amd_enabled']=False
        env['knl'] = False
        env['knm'] = False
        env['skx'] = False
        env['clx'] = False
        env['cpx'] = False
        env['cnl'] = False
        env['icl'] = False
        env['tgl'] = False
        env['spr'] = False
        env['adl'] = False
        env['cet'] = False
        env['future'] = False
        
    if env['use_elf_dwarf_precompiled']:
       env['use_elf_dwarf'] = True
       

def macro_args(env):

    # undefined behavior sanitizer
    #
    # 2021-05-13: xed has several locations where it dereferences
    #  unaligned pointers for 16/32/64 displacements & immediates. The
    #  code generated by clang -O3 is worse for these cases when using
    #  legal C. Thinking about how to handle that.
    
    
    if  (env.on_linux()  or env.on_mac()) and 0:
        fcmd = '-fsanitize=undefined  -fstrict-aliasing'
        env.add_to_var('CXXFLAGS', fcmd)
        env.add_to_var('CCFLAGS', fcmd)
        env.add_to_var('LINKFLAGS', fcmd)

    if env.on_linux() and env['asan']:
        fcmd = '-fsanitize=address'
        env.add_to_var('CXXFLAGS', fcmd)
        env.add_to_var('CCFLAGS', fcmd)
        env.add_to_var('LINKFLAGS', fcmd)
        
    if env['enc2_test_checked']:
        env['enc2_test']=True
    if env['enc2_test']:
        env['enc2']=True
        env['enc']=True

def work(env):
    """External entry point for non-command line invocations.
    Initialize the environment, build libxed, the examples, the kit
    and run the tests"""

    macro_args(env)
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

    input_files = build_libxed(env, work_queue)

    env['enc2_configs'] = [] # used for installing kits
    if env['enc2']:
        configs = [ enc2_config_t(64,64),   # popular
                    enc2_config_t(32,32),   
                    #enc2_config_t(16,16),   # infrequent
                    #enc2_config_t(64,32),   # obscure 
                    #enc2_config_t(32,16),   # more obscure
                    #enc2_config_t(16,32)   # more obscure
                   ]

        test_libs = []
        for config in configs: 
            (shd_enc2,lnk_enc2, shd_chk, lnk_chk) = build_libxedenc2(env, work_queue, input_files, config)
            test_libs.append((shd_enc2, lnk_enc2, shd_chk, lnk_chk))
            env['enc2_configs'].append(config)
    legal_header_tagging(env)
    _prep_kit_dirs(env)
    create_working_kit_structure(env,work_queue) # wkit
    create_install_kit_structure(env,work_queue) # ikit

    build_examples(env) # in the working kit now
    _copy_examples_to_bin(env,env['wkit'])
    _copy_dynamic_libs_to_kit(env,env['wkit'])
    _test_examples(env)

    copy_working_kit_to_install_dir(env)
    # put the doxygen in working kit, if not installing, and the final
    # kit if installing.
    create_doxygen_api_documentation(env, work_queue)
    compress_kit(env)
    mbuild.vmsgb(1, "XED KIT BUILD COMPLETE")
    
    system_install(env,work_queue) # like in /usr/local/{lib,include/xed}
    make_doxygen_build(env,work_queue)
    retval = run_tests(env)

    end_time=mbuild.get_time()
    mbuild.vmsgb(1, "ELAPSED TIME", mbuild.get_elapsed_time(start_time,
                                                        end_time))
    mbuild.vmsgb(1, "RETVAL={}".format(retval))
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

