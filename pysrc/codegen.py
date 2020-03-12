#!/usr/bin/env python
# -*- python -*-
# Mark Charney <mark.charney@intel.com>
# Code generation support: emitting files, emitting functions, etc.
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
import glob

from genutil import *
def find_dir(d):
    directory = os.getcwd()
    last = ''
    while directory != last:
        target_directory = os.path.join(directory,d)
        if os.path.exists(target_directory):
            return target_directory
        last = directory
        directory = os.path.split(directory)[0]
    return None
sys.path.append(find_dir('mbuild'))
try:
   import mbuild
except:
   sys.stderr.write("\nERROR(file: codegen.py): Could not find mbuild. Might try setting PYTHONPATH env var.\n\n")
   sys.exit(1)

class ip_header_t(object):
   """Intellectual property headers"""
   def __init__(self):
      self.lines = None
   def read_header(self,fn):
      ##msge("Attempting to open: " + fn)
      fp = base_open_file(fn,"r")
      self.lines = fp.readlines()

   def emit_header(self, shell_type = False):
      eol = '\n'
      out = []
      if shell_type:
         out.append("#BEGIN_LEGAL" + eol)
         for line in self.lines:
            out.append("#" + line)
         out.append("#END_LEGAL" + eol)

      else:
         out.append("/*BEGIN_LEGAL" + eol)
         out.extend(self.lines)
         out.append("END_LEGAL */" + eol)
      return out


class file_emitter_t(object):
   """Attach IP headers, standard includes, and namespace decorations
   to generated files. This replaces the file objects I was using for
   emitting files."""
   header_file_name_pattern = re.compile(r'.[hH]$')


    # note: in the following the '-' must be last or it will (try to) act like a range!
   header_guard_pattern = re.compile(r'[./-]')

   def __init__(self,gendir, file_name, shell_file=False, namespace=None):
      """gendir is the output dir. If shell_file is True, we delimit
      the header differently."""
      self.file_name = file_name

      self.gendir = gendir
      self.namespace = namespace
      # True for shell-like files, False for C++ files. Determines the comment syntax
      self.shell_file = shell_file

      self.lines = []
      self.full_file_name = mbuild.join(self.gendir, self.file_name)
      self.eol = '\n'
      self.closed = False
      self.header = False
      if file_emitter_t.header_file_name_pattern.search(self.file_name):
         self.header = True
      self.headers = []
      self.system_headers = []
      self.misc_header = []


   def add_header(self,h):
      """Add h to the list of headers"""
      if type(h) == list:
         self.headers.extend(h)
      else:
         self.headers.append(h)

   def add_system_header(self,h):
      """Add h to the list of system headers"""
      if type(h) == list:
         self.system_headers.extend(h)
      else:
         self.system_headers.append(h)

   def add_misc_header(self,h):
      if type(h) == list:
         self.misc_header.extend(h)
      else:
         self.misc_header.append(h)

   def replace_headers(self,h):
      """Replace the existing headers with the header h"""
      if type(h) == list:
         self.headers = h
      else:
         self.headers = [h]

   def start(self, full_header=True):
      """Call this this after creating the objectd"""
      self.emit_header(full_header)
      if not self.shell_file:
         self.system_headers_emit()
         self.user_headers_emit()
         self.misc_headers_emit()
         self.namespace_start()

   def count_lines(self):
      return len(self.lines)

   def write(self,str):
      """Replaces the file pointer write() function call"""
      self.lines.append(str)
   def writelines(self,list_of_str):
      """Replaces the file pointer writelines() function call"""
      self.lines.extend(list_of_str)
   def add_code(self,str):
      """Add a line and newline"""
      self.write(str+'\n')
   def add_code_eol(self,str):
      """Add a line with semicolon, newline"""
      self.add_code(str+';')

   def close(self):
      if not self.closed:
         self.closed = True
         if not self.shell_file:
            self.namespace_end()
         if self.header:
            self.emit_header_guard_end()
         self.emit_file()
         del self.lines
      else:
         msge("FE: Closing an already-closed file: " + self.full_file_name)

   def emit_file(self):
      msge("FE:EMIT_FILE " + self.full_file_name)
      fp = self.open_file(self.full_file_name,"w")
      fp.writelines(self.lines)
      fp.close()

   # # # # # # # # # #   # # # # # # # # # #   # # # # # # # # # #

   def open_file(self,fn,rw):
      fp  = base_open_file(fn,rw)
      return fp

   def emit_ip_header(self, ip_header_file_name):
      iph = ip_header_t()
      iph.read_header(ip_header_file_name)
      s =  iph.emit_header(self.shell_file)
      return s

   def emit_header(self, full_header=True):
      if full_header:
          self.dox('@file ' + self.file_name)
          self.emit()
          self.cmt('This file was automatically generated.')
          self.cmt('Do not edit this file.')
          self.emit()
      if self.header:
         self.emit_header_guard_start()

   def emit_header_guard_start(self):
      s = file_emitter_t.header_guard_pattern.sub('_',self.file_name)
      defname = '%s' %  s.upper()
      self.emit_eol('#if !defined(' + defname + ')')
      self.emit_eol('# define ' + defname )
   def emit_header_guard_end(self):
      self.emit_eol("#endif")

   def dox(self,s):
      if self.shell_file:
         self.emit_eol('# '+ s)
      else:
         self.emit_eol('/// '+ s)
   def cmt(self,s):
      if self.shell_file:
         self.emit_eol('# '+ s)
      else:
         self.emit_eol('// '+ s)
   def emit(self,s='\n'):
      self.lines.append(s)
   def emit_eol(self,s=''):
      self.emit(s + '\n')

   def user_headers_emit(self):
      for h in self.headers:
         self.emit_eol('#include \"%s\"' % h  )

   def system_headers_emit(self):
      for h in self.system_headers:
         self.emit_eol('#include <%s>' % h  )

   def misc_headers_emit(self):
      for h in self.misc_header:
         self.emit_eol(h)


   def namespace_start(self):
      if self.namespace:
         self.emit_eol( ''.join(['namespace ' , self.namespace , ' {']))
   def namespace_end(self):
      if self.namespace:
         msge("FE:NAMESPACE " + self.full_file_name)
         self.emit_eol( '} // namespace')




class xed_file_emitter_t(file_emitter_t):
   """Attach IP headers, standard includes, and namespace decorations
   to generated files. This replaces the file objects I was using for
   emitting files."""

   def __init__(self, xeddir, gendir, file_name, shell_file=False,
                namespace=None, is_private=True):
      file_emitter_t.__init__( self,gendir, file_name, shell_file, namespace)
      self.xeddir = xeddir
      if is_private:
          self.headers.append('xed-internal-header.h')

   def start(self, full_header=True):
      """override the parent's start() function to apply the IP
      header."""
      self.emit_header(full_header)
      ip_header_file_name = mbuild.join(self.xeddir,
                                        'misc',
                                        'apache-header.txt')
      for line in self.emit_ip_header(ip_header_file_name):
         self.emit(line)
      if not self.shell_file:
         self.system_headers_emit()
         self.user_headers_emit()
         self.misc_headers_emit()
         self.namespace_start()

inline_sring = "XED_INLINE"

class function_object_t(object):
   inline_string = "XED_INLINE"

   def __init__(self,name, return_type='xed_bool_t', static=False, inline=False,
                doxgroup=None, force_no_inline=False, dll_export=False):
      self.function_name = name
      self.doxgroup=doxgroup
      self.return_type = return_type
      self.static=static
      self.inline=inline
      self.dll_export = dll_export
      self.body = []
      self.args = [] # list of pairs, (type+arg, meta type comment)
      self.const_member = False
      self.ref_return = False
      self.force_no_inline = force_no_inline

   def set_function_name(self,fname):
       self.function_name = fname
   def get_function_name(self):
       return self.function_name

   def lines(self):
      return len(self.body)

   def add_arg(self, arg, arg_type=None):
      self.args.append((arg,arg_type))
   def get_args(self):
       return self.args

   def get_arg_num(self):
       return len(self.args)

   def add_comment(self,s):
      self.body.append(''.join(['/* ' , s , ' */']))

   def set_const_member(self):
      self.const_member = True
   def set_ref_return(self):
      self.ref_return = True

   def add_code(self, line, comment=None):
      if comment:
          self.body.append(line + ' // {} '.format(comment) )
      else:
          self.body.append(line)
   def add_code_eol(self, line, comment=None):
      if comment:
          self.body.append(line + '; // {} '.format(comment) )
      else:
          self.body.append(line + ';')

   def add_lines(self, lines):
      self.body.extend(lines)

   def emit_header_internal(self, class_qualfier='', emit_group=False):
      """private function that emits the function name and args, but
      no newline or semicolon"""
      s = []
      if emit_group and self.doxgroup:
         s.append("/// @ingroup %s\n" % (self.doxgroup))
      if self.static:
         s.append("static ")
      if self.inline:
         s.append(   function_object_t.inline_string + " ")
      if self.force_no_inline:
          s.append('XED_NOINLINE ')
      if self.dll_export:
          s.append('XED_DLL_EXPORT ')
      s.append(self.return_type)
      if self.ref_return:
         s.append('&')
      s.append(' ')

      s.append(class_qualfier)

      s.append(self.function_name)
      s.append('(')
      first_arg = True
      for arg,arg_type in  self.args:
         if first_arg:
            first_arg = False
         else:
            s.append(', ')
         if arg_type:
             s.append("{} /*{}*/".format(arg,arg_type))
         else:
             s.append(arg)
      if first_arg: # no actual args so emit a "void"
         s.append('void')
      s.append(')')
      if self.const_member:
         s.append(' const')
      return ''.join(s)

   def emit_header(self):
      'emit the header with the semicolon and newline'
      s = [ self.emit_header_internal(emit_group=True), ";\n" ]
      return ''.join(s)

   def emit(self, class_qualfier=''):
      'emit the function body'
      eol = '\n'
      s = [ self.emit_header_internal(class_qualfier) ,  eol ]
      s.append('{')
      s.append(eol)
      for bline in self.body:
         s.extend([ '   ' , bline , eol])
      s.append('}')
      s.append(eol)
      return ''.join(s)

   def emit_file_emitter(self, fe, class_qualfier=''):
      'emit the function body'
      fe.add_code(self.emit_header_internal(class_qualfier))
      fe.add_code('{')
      for bline in self.body:
         fe.add_code(bline)
      fe.add_code('}')

   def emit_body(self):
       'emit function body as string'
       return '\n'.join([bline + ';' for bline in self.body])

############################################################

def dump_flist_2_header(h_file, functions, headers,
                        emit_headers=True,
                        emit_bodies=True):
    ''' emits the list of functions objects to a header file
        @type: functions: list of function_object_t
        @param functions: the function to emit
        @type: h_file: xed_file_emitter_t
        @param h_file: emmiting the function to this headr file
        @type: headers: list of strings
        @param headers: include headers to emit 
    '''
    for header in headers:
        h_file.add_header(header)
    h_file.start()

    if emit_headers:
        for fo in functions:
            decl = fo.emit_header()
            h_file.add_code(decl)

    if emit_bodies:
        for fo in functions:
            fo.emit_file_emitter(h_file)

    h_file.close()

def emit_function_list(func_list,
                       fn_prefix,
                       xeddir,
                       gendir,
                       hgendir,
                       namespace=None,
                       other_headers=None,
                       max_lines_per_file=3000,
                       is_private_header=True,
                       extra_public_headers=None): # list
   """Emit a list of functions to a numbered sequence of
   files. Breaking them up when the files get too big.

    @type func_list: list of function_object_t objects
    @param func_list: functions to emit
    @type fn_prefix: string
    @param fn_prefix: basis for the output file names.
    @type xeddir: string
    @param xeddir: location of the source directory so that we can find the legal header
    @type gendir: string
    @param gendir: directory where the output files go.
    @type hgendir: string
    @param hgendir: directory where the output hdr files go.
    @type namespace: string
    @param namespace: defaults to XED
    @type other_headers: list
    @param other_headers: extra headers to include
    @type max_lines_per_file: int
    @param max_lines_per_file: Approximate limit for file size, in lines. 
   """
   file_number = 0
   fe = None
   
   fn_header = "{}.h".format(fn_prefix)
   companion_header = fn_header
   if not is_private_header:
       companion_header = mbuild.join('xed',fn_header)
       
   fe_list = []
   fe_header = xed_file_emitter_t(xeddir,hgendir,fn_header,shell_file=False,namespace=namespace, is_private=is_private_header)
   if extra_public_headers:
       fe_header.add_header(extra_public_headers)
   fe_header.start()
   fe_list.append(fe_header)

   # remove any numbered files that we previously emitted. We won't
   # necessarily overwrite them all each build and do not want
   # stale files remaining from previous builds
   for fn in glob.glob(mbuild.join(gendir, fn_prefix + '-[0-9]*.c')):
       mbuild.remove_file(fn)

   for func in func_list:
      fe_header.write(func.emit_header())
      if not fe or fe.count_lines() + func.lines() >= max_lines_per_file:
         if fe:
            fe.close()
         fn = "%s-%d.c" % (fn_prefix, file_number)
         fe = xed_file_emitter_t(xeddir,gendir, fn, shell_file=False, namespace=namespace)
         fe.add_header(companion_header)
         if other_headers:
            for header in other_headers:
               fe.add_header(header)
         fe.start()
         fe_list.append(fe)
         file_number += 1

      func.emit_file_emitter(fe)


   fe.close()
   fe_header.close()
   return fe_list


############################################################


def function_call_sequence(fname, lst):
   """Return a function object (returning nothing) for a function
   named fname that calls all the functions in lst.

    @type fname: string
    @param fname:  function name
    @type lst: list
    @param lst: list  of function names without parens
    @rtype: function_object_t
    @return: function that calls each function in lst
   """
   fo = function_object_t(fname, "void")
   for fn in lst:
      fo.add_code_eol(fn + "()")
   return fo

def function_call_sequence_conditional(fname, lst, subroutine_arg=''):
   """Return a function object (that returns xed_bool_t) for a function named fname that calls
   all the functions in lst. Check each function call for an okay
   return value and have this function return false if any of the
   subroutines return false.

    @type fname: string
    @param fname:  function name
    @type lst: list
    @param lst: list  of function names without parens
    @type subroutine_arg: string
    @param subroutine_arg: optional parameter for the called functions

    @rtype: function_object_t
    @return: function that calls each function in lst
   """
   fo = function_object_t(fname, "xed_bool_t")
   fo.add_code_eol("xed_bool_t okay")
   args = "(%s)" % subroutine_arg
   for fn in lst:
      fo.add_code_eol("okay = " + fn + args)
      fo.add_code_eol("if (!okay) return 0")
   fo.add_code_eol("return 1")
   return fo

class class_generator_t(object):
   """Generate code for a c++ class (or union) declaration and
   implementation.

   If you want initialization or a printer, you can add your create
   your own functions and add them with add_function().
   """
   inline_string = "XED_INLINE"
   inline_pattern = re.compile(inline_string)

   def __init__(self,name, class_or_union='class', var_prefix = "_"):
      self.name = name
      self.var_type = [] # list of (variable,type,bit_width) tuples
      self.functions = [] # member functions
      self.class_or_union = class_or_union
      self.var_prefix = var_prefix

   def add_var(self, var, type, bit_width = None, accessors='set-get'):
      """Add a variable var of type. If accessors is set, generate
      set/get functions for it. The potential values are the following
      strings:

      set
      get
      set-get
      get-ref
      set-get-array
      none
      """
      pvar = self.var_prefix + var
      self.var_type.append((pvar,type,bit_width))
      if accessors == 'set-get-array':
         self.add_function(self.add_get_array_fn(var,pvar,type))
         self.add_function(self.add_set_array_fn(var,pvar,type))
      if accessors == 'set-get':
         self.add_function(self.add_get_fn(var,pvar,type))
         self.add_function(self.add_set_fn(var,pvar,type))
      elif accessors == 'set':
         self.add_function(self.add_set_fn(var,pvar,type))
      elif accessors == 'get':
         self.add_function(self.add_get_fn(var,pvar,type))
      elif accessors == 'get-ref':
         self.add_function(self.add_get_ref_fn(var,pvar,type))
      elif accessors == 'none':
         pass
      else:
         die("Unhandled accessor keyword: " +  accessors)

   def add_get_ref_fn(self,var,pvar,type):
      'A get-accessor function for class variable pvar, returns a reference'
      fname = 'get_' + var
      fo = function_object_t(fname, class_generator_t.inline_string + ' ' + type)
      fo.set_ref_return()
      fo.add_code_eol( 'return %s' %( pvar ))
      return fo

   def add_get_fn(self,var,pvar,type):
      'A get-accessor function for class variable pvar'
      fname = 'get_' + var
      fo = function_object_t(fname, class_generator_t.inline_string + ' ' + type)
      fo.set_const_member()
      fo.add_code_eol( 'return %s' % ( pvar ))
      return fo

   def add_set_fn(self, var,pvar,type):
      'A set-accessor function for class variable pvar'
      fname = 'set_' + var
      fo = function_object_t(fname, class_generator_t.inline_string + ' void')
      fo.add_arg(type + ' arg_' + var)
      fo.add_code_eol( '%s=arg_%s' % (pvar,var))
      return fo

   def add_get_array_fn(self,var,pvar,type):
      'A get-accessor function for class variable pvar'
      fname = 'get_' + var
      fo = function_object_t(fname, class_generator_t.inline_string + ' ' + type)
      fo.add_arg("unsigned int idx") #FIXME: parameterize unsigned int
      fo.set_const_member()
      # FIXME: add bound checking for array index
      fo.add_code_eol( 'return %s[idx]' % (pvar))
      return fo

   def add_set_array_fn(self, var,pvar,type):
      'A set-accessor function for class variable pvar'
      fname = 'set_' + var
      fo = function_object_t(fname, class_generator_t.inline_string +' void')
      fo.add_arg("unsigned int idx") #FIXME: parameterize unsigned int
      fo.add_arg(type + ' arg_' + var)
      # FIXME add bounds checking for array index
      fo.add_code_eol( '%s[idx]=arg_%s' % (pvar, var))
      return fo

   def add_function(self, function):
      self.functions.append(function)

   def emit_decl(self):
      'emit the class declaration'
      eol = '\n'
      pad = '   '

      s = []
      s.append(self.class_or_union +  ' ' + self.name + eol)
      s.append('{' + eol)
      s.append('  public:' + eol)
      for (var,type,bit_width)  in self.var_type:
         t = pad + type + ' ' + var
         if bit_width:
            t += ' : ' + str(bit_width)
         s.append(t+ ';' + eol)
      for fo in self.functions:
         s.append( pad + fo.emit_header())
      s.append('};' + eol)

      # emit the inline functions in the header
      for fo in self.functions:
         if class_generator_t.inline_pattern.search(fo.return_type):
            s.append(fo.emit(self.name + '::') )

      return ''.join(s)

   def emit_impl(self):
      'emit the class implementation'
      s = []
      # only emit the noninline functions
      for fo in self.functions:
         if not class_generator_t.inline_pattern.search(fo.return_type):
            s.append(fo.emit(self.name + '::') )
      return ''.join(s)

############################################################################
class c_switch_generator_t(object):
   def __init__(self, var_name, func_obj, pad='    '):
      self.func_obj = func_obj
      self.var_name = var_name
      self.pad = pad
      self._add('switch(%s) {' % (self.var_name))

   def _add(self,s):
      self.func_obj.add_code(self.pad + s)

   def add(self,s, pad='   '):
       self._add(pad + s)
       
   def add_case(self,case_name,clines, do_break=True):
      """Add a case with a bunch of lines of code -- no semicolons
      required"""
      self._add('case %s:' % (case_name))
      for line in clines:
         self.add(line)
      if do_break:
         self.add('break;')

   def add_default(self,clines, do_break=True):
      """Add a default case with a bunch of lines of code -- no
      semicolons required"""
      self._add('default:')
      for line in clines:
         self.add(line)
      if do_break:
         self.add('break;')

   def finish(self):
      self._add('}')


############################################################################

class c_class_generator_t(object):
   """Generate code for a C struct (or union) declaration and
   implementation.

   If you want initialization or a printer, you can add your create
   your own functions and add them with add_function().
   """

   type_ending_pattern = re.compile(r'_t$')
   def remove_suffix(self,x):
      return c_class_generator_t.type_ending_pattern.sub('',x)

   def __init__(self,name, class_or_union='struct', var_prefix = "_"):
      self.name = name
      self.var_type = [] # list of (variable,type,bit_width) tuples
      self.array_type = [] # list of (variable,type,limit) tuples
      self.functions = [] # member functions
      self.class_or_union = class_or_union
      self.var_prefix = var_prefix

   def add_array(self, var, type, limit):
      """Add an array variable var of type.
      """
      pvar = self.var_prefix + var
      self.array_type.append((pvar,type,limit))
      self.add_function(self.add_get_array_fn(var,pvar,type))
      self.add_function(self.add_set_array_fn(var,pvar,type))

   def add_var(self, var, type, bit_width = None, accessors='set-get'):
      """Add a variable var of type. If accessors is set, generate
      set/get functions for it. The potential values are the following
      strings:

      set
      get
      set-get
      get-ref
      set-get-array
      none
      """
      pvar = self.var_prefix + var
      self.var_type.append((pvar,type,bit_width))
      if accessors == 'set-get-array':
         self.add_function(self.add_get_array_fn(var,pvar,type))
         self.add_function(self.add_set_array_fn(var,pvar,type))
      if accessors == 'set-get':
         self.add_function(self.add_get_fn(var,pvar,type))
         self.add_function(self.add_set_fn(var,pvar,type))
      elif accessors == 'set':
         self.add_function(self.add_set_fn(var,pvar,type))
      elif accessors == 'get':
         self.add_function(self.add_get_fn(var,pvar,type))
      elif accessors == 'get-ref':
         self.add_function(self.add_get_ref_fn(var,pvar,type))
      elif accessors == 'none':
         pass
      else:
         die("Unhandled accessor keyword: " +  accessors)

   def add_get_ref_fn(self,var,pvar,type):
      """A get-accessor function for class variable pvar, returns a POINTER"""
      fname = self.remove_suffix(self.name) + '_get_' + var
      fo = function_object_t(fname, type + "*")
      fo.add_arg("%s* ppp" % self.name)
      fo.add_code_eol( 'return &(ppp->%s)' %( pvar ))
      return fo

   def add_get_fn(self,var,pvar,type):
      'A get-accessor function for class variable pvar'
      fname = self.remove_suffix(self.name) + '_get_' + var
      fo = function_object_t(fname,  type)
      fo.add_arg("%s* ppp" % self.name)
      fo.add_code_eol( 'return ppp->%s' % ( pvar ))
      return fo

   def add_set_fn(self, var,pvar,type):
      'A set-accessor function for class variable pvar'
      fname = self.remove_suffix(self.name) + '_set_' + var
      fo = function_object_t(fname, 'void')
      fo.add_arg("%s* ppp" % self.name)
      fo.add_arg(type + ' arg_' + var)
      fo.add_code_eol( 'ppp->%s=arg_%s' % (pvar,var))
      return fo

   def add_get_array_fn(self,var,pvar,type):
      'A get-accessor function for class variable pvar'
      fname = self.remove_suffix(self.name) + '_get_' + var
      fo = function_object_t(fname, type)
      fo.add_arg("%s* ppp" % self.name)
      fo.add_arg("unsigned int idx") #FIXME: parameterize unsigned int
      # FIXME: add bound checking for array index
      fo.add_code_eol( 'return ppp->%s[idx]' % (pvar))
      return fo

   def add_set_array_fn(self, var,pvar,type):
      'A set-accessor function for class variable pvar'
      fname = self.remove_suffix(self.name) + '_set_' + var
      fo = function_object_t(fname, 'void')
      fo.add_arg("%s* ppp" % self.name)
      fo.add_arg("unsigned int idx") #FIXME: parameterize unsigned int
      fo.add_arg(type + ' arg_' + var)
      # FIXME add bounds checking for array index
      fo.add_code_eol( 'ppp->%s[idx]=arg_%s' % (pvar, var))
      return fo

   def add_function(self, function):
      self.functions.append(function)

   def emit_decl(self):
      'emit the class declaration'
      eol = '\n'
      pad = '   '

      s = []
      # I replace the suffix _t$ first then append a _s or _u. This way it
      # adds a _s/_u even if no _t is present.

      struct_name = re.sub(r'_t$', '',self.name )
      if self.class_or_union == 'union':
         struct_name +=  '_u'
      else:
         struct_name +=  '_s'

      s.append('typedef %s %s {\n' % (self.class_or_union, struct_name))

      for (var,type,limit)  in self.array_type:
         t = "%s %s %s[%s];\n" % ( pad, type, var, str(limit))
         s.append(t)

      for (var,type,bit_width)  in self.var_type:
         t = '%s %s %s' % ( pad, type, var)
         if bit_width:
            t += ' : ' + str(bit_width)
         s.append(t+ ';' + eol)
      s.append('} %s;\n' % self.name )

      # accessor function prototypes
      for fo in self.functions:
         s.append( pad + fo.emit_header())
      return ''.join(s)

   def emit_impl(self):
      """emit the class implementation"""
      s = []
      # only emit the noninline functions
      for fo in self.functions:
            s.append(fo.emit() )
      return ''.join(s)


############################################################################

class array_gen_t(object):
    """A simple C++ multidimensional array generator. The ranges are
    typed. New values are added by specifying a list of indices, one
    per dimension and a value"""
    def __init__(self, name, type, target_op=None):
        """Set the name and storage type for the array"""
        self.name = name
        self.type = type
        self.target_op = target_op

        self.ranges = [] # list of tuples (range_type, minval, maxval+1, argname )
                         # including the  max
                         # value for dimensioning the array

        self.values = [] # list of tuples of tuples (dict(names->indices), value)

        self.lookup_fn = None
        self.init_fn = None

    def add_dimension(self, range_type, range_min, range_max, argname):
        """For one dimension, add the type of the range index and the
        min/max range values."""
        self.ranges.append((range_type,range_min, range_max, argname))

    def get_arg_names(self):
        return [range_tuple[3] for range_tuple in self.ranges]

    def get_target_opname(self):
        """Return the name of target operand of lookup function
        (if it was supplied)"""
        return self.target_op

    def get_dimension_num(self):
        """Return the number of array dimensions.
        In other words the number of the lookup function parameters."""
        return len(self.ranges)

    def get_values_space(self):
        """Return a list of all possible return values of a lookup function"""
        return [val for (_idx_dict, val) in self.values]

    def is_const_lookup_fun(self):
        """Return true if a lookup function always returns same value.
        Const lookup function and the array is just a variable."""
        return self.get_dimension_num() == 0

    def add_value(self, indx_dict, value):
        """set the scalar value  for the dictionary of indices"""
        self.values.append((indx_dict, value))

    def validate(self):
        """Make sure that all the index arrays have the expected
        number of elements."""
        expected_len = len(self.ranges)
        for idict,value in self.values:
            if len(list(idict.keys())) != expected_len:
                return False
        return True

    def gen_lookup_function(self, fn_name, check_bounds=True, static=False,
                            inline=False, check_const=False):
        """Create a lookup function that will look up the value and
        return the appropriate type. Typed args will be added for each
        dimension

        check_const argument is for checking if lookup function is of a form
        return var; - constant function. Then we can optimize it to a form
        return const; where const is a compile-time constant (a number).
        """

        fo = function_object_t(fn_name, self.type, static=static, inline=inline)

        #optimization for const functions
        if check_const:
            if self.is_const_lookup_fun() and len(self.values) == 1:
                fo.add_code('/*Constant function*/')
                value = self.values[0][1]
                fo.add_code_eol('return %s' % str(value))
                self.lookup_fn = fo
                return


        fo.add_code_eol(self.type + ' _v')

        index_expression = ''
        for i,range_tuple in enumerate(self.ranges):
            range_type, range_min, range_max, argname = range_tuple
            fo.add_arg(range_type + ' arg_' + argname)
            index_expression +=  '[arg_%s]' % (argname)
            lower_bound = str(range_min)
            upper_bound = str(range_max)
            if check_bounds:
                # FIXME: if the range type is unsigned, and the lower
                # bound is zero, then we need not check it. But it is
                # hard to tell from here with an arbitrary type. ICL
                # complains about this, warning/error #186.
                fo.add_code_eol('xed_assert(arg_'+ argname + '>=' + lower_bound +
                                ' && arg_' + argname + '<' + upper_bound + ')')

        fo.add_code_eol('_v='  + self.name + index_expression)

        fo.add_code_eol('return _v')
        self.lookup_fn = fo

    def emit_lookup_function(self):
        """Emit the lookup function as a string"""
        if self.lookup_fn == None:
            die("Need to generate the lookup function first for " + self.name)
        return self.lookup_fn.emit()

    def emit_lookup_function_header(self):
        """Emit the lookup function header as a string"""
        if self.lookup_fn == None:
            die("Need to generate the lookup function first for " + self.name)
        return self.lookup_fn.emit_header()

    def emit_initialization_function_header(self):
        if self.init_fn == None:
            die("Need to generate the init function first for " + self.name)
        return self.init_fn.emit_header()

    def emit_declaration(self, extern=False, static=False):
        """Emit the array declaration as a string."""
        s = []
        if static:
           s.append( 'static ')
        if extern:
           s.append( 'extern ')

        s.append( self.type + ' ' + self.name)
        for range_type, range_min, range_max, argname in self.ranges:
            s.append('[%s]' % (str(range_max)))
        s.append(';\n')
        return ''.join(s)

    def compute_missing_values(self,key):
        present_values = {}
        for indices_dict,value in self.values:
            if key in indices_dict:
                present_values[indices_dict[key]] = True
        return list(present_values.keys())


    def make_initialization_function(self, init_function_name,verbose=False):
       fo = function_object_t(init_function_name,'void')
       lines = self.emit_initialization(verbose=verbose)
       fo.add_lines(lines)
       self.init_fn = fo


    def emit_initialization(self,verbose=False): # private
        """Return a list of strings containing array initialization lines"""
        lines = []
        indices = [ x[3] for x in self.ranges] # get the argnames

        missing_key = None
        missed_one = True
        # if we missed one then we process everything all over again to make sure we
        # got everything. We only add one missing OD per pass
        while missed_one:
            missed_one = False

            new_values = []
            for indices_dict,value in self.values:
                missing_key = None # 2007-06-16 bug fix. This line was missing
                if verbose:
                   msge("AG: Processing value: %s  indices: %s" % ( value, str(indices_dict)))
                for key in indices:
                    if key not in indices_dict:
                        # we are missing values for this key.
                        if verbose:
                           msge("AG:  Missing key %s" % (key))
                        missing_key = key
                        missed_one = True
                if missing_key == None:
                    # We have this key, so add the dictionary
                    new_values.append((indices_dict,value))
                else:
                    # We must replicate this entry for all values of the
                    # *all* missing keys! We can do this one missing field
                    # at a time. Eventually, we'll get them all.
                    all_present_values = self.compute_missing_values(missing_key)
                    if verbose:
                       msge('AG:    Adding missing key %s to %s with values %s' % ( missing_key,
                                                                                   self.name,
                                                                                   str(all_present_values)))
                    for v in all_present_values:
                        new_dict = copy.copy(indices_dict)
                        new_dict[missing_key] = v
                        new_values.append((new_dict,value))
            del self.values
            self.values = new_values


        for indices_dict,value in self.values:
            s = [self.name]
            for key in indices:
                indx = indices_dict[key]
                if type(indx) == dict:
                   die("A dictionary escaped during array init building for " + self.name)
                s.append('[%s]' %(str(indx)))
            s.append( '=%s;' % str(value) )
            t = ''.join(s)
            if verbose:
               msge("AG:      %s" % t)
            lines.append(t)
        return lines

