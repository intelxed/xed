#!/usr/bin/env python
# -*- python -*-
# Mark Charney <mark.charney@intel.com>
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
import os
import sys
import re
import codegen

def find_dir(d):
    directory = os.getcwd()
    last = ''
    while directory != last:
        target_dir = os.path.join(directory,d)
        if os.path.exists(target_dir):
            return target_dir
        last = directory
        directory = os.path.split(directory)[0]
    return None
sys.path.append(find_dir('mbuild'))
try:
   import mbuild
except:
   sys.stderr.write("\nERROR(enumer.py): Could not find mbuild. Might try setting PYTHONPATH env var.\n\n")
   sys.exit(1)
   
class enumer_value_t(object):
    def __init__(self, name, value=None, doxygen=None, duplicate=False, display_str=None):
        self.name = name
        # display_str is a string to use for the parser. may contain
        # values that are not valid enumeration characters (like
        # parenthesis, etc.). display_str was added later and defaults
        # to the value supplied for name.
        if display_str:
            self.display_str = display_str
        else:
            self.display_str = self.name
        self.value=value
        self.doxygen=doxygen
        self.duplicate=duplicate
        
    def in_comment(self,s):
        """is s substring in comment?"""
        if self.doxygen:
            if s in self.doxygen:
                return True
        return False
        


def  _make_str2foo():
    l  = [
        "/// This converts strings to #%(type)s types.",
        "/// @param s A C-string.",
        "/// @return #%(type)s",
        "/// @ingroup ENUM",
        "%(prefix)s %(type)s str2%(type)s(const char* s)",
        ]
    s = "\n".join(l)
    return s
def _make_foo2str():
    l  = [
        "/// This converts strings to #%(type)s types.",
        "/// @param p An enumeration element of type %(type)s.",
        "/// @return string",
        "/// @ingroup ENUM",
        "%(prefix)s const char* %(type)s2str(const %(type)s p)" 
        ]
    s = "\n".join(l)
    return s

        
class enumer_t(object):
    def __init__(self, type_name, prefix, values, cfn, hfn,  gendir,
                 namespace=None, stream_guard=None, 
                 add_last_element=True, cplusplus=False,
                 proto_prefix='', extra_header=None, density='automatic',
                 string_convert=1 ):
        """
        @type  type_name: string
        @param type_name: the name of the generated type

        @type  prefix: string
        @param prefix: prepended to all enumeration names

        @type  values: list
        @param values: list of L{enumer_value_t} objects

        @type  cfn: string
        @param cfn: output source file name
        @type  hfn: string
        @param hfn: output header file name


        @type  gendir: string
        @param gendir: output directory

        @type  namespace: string
        @param namespace: namespace wrapper

        @type  stream_guard: string

        @param stream_guard: #ifdef test for ostream/istream functionality

        @type  add_last_element: xed_bool_t
        @param add_last_element: If  True (default), add a _LAST element.

        @type  cplusplus: xed_bool_t
        @param cplusplus:  True=>C++ or False=>C

        @type  proto_prefix: string
        @param proto_prefix:  default is empty string. useful for DLL export decorations

        @type  extra_header: string or list
        @param extra_header: another header to include in the .H file. 

        @type  density: string
        @param density: density of enumerated values. Can be sparse (default) or dense. Default is automatic which use the presence or absence of preset values to determine density

        @type  string_convert: integer
        @param string_convert: 1=default, generate convert routines, 0=empty stubs, -1=no-stubs or prototypes
        """
        self.debug = False
        self.proto_prefix = proto_prefix

        self.cplusplus = cplusplus
        self.type_name = type_name
        self.prefix = prefix
        self.cfn = cfn
        self.hfn = hfn
        self.density = density
        self.string_convert = string_convert
        self.extra_header = extra_header
        self.values= self._unique(values) # list of enumer_value_t's

        self.can_be_dense = True
        self.preset_values = self._scan_for_preset_values(self.values)
        if self.preset_values:
           self.can_be_dense = \
               self._scan_for_dense_zero_based_preset_values(self.values)

        #sys.stderr.write("Can be dense %s\n" % (str(self.can_be_dense)))
        #sys.stderr.write("Preset values %s\n" % (str(self.preset_values)))
        
        if self.density == 'automatic':
           if self.can_be_dense:
              self.density = 'dense'
           else:
              self.density = 'sparse'

        if self.preset_values and \
               self.can_be_dense == False and \
               self.density == 'dense':
           sys.stderr.write("\nERROR(enumer.py): dense enum had some values specified preventing dense-enum generation\n\n")
           sys.exit(1)

        self.add_last_element = add_last_element
        if add_last_element:
            self.values.append(enumer_value_t('LAST'))

        (unique, duplicates) = self._partition_duplicates(self.values)
        # clobber the values with just the unique values
        self.values = unique
        self.duplicates = duplicates

        self.namespace=namespace
        self.stream_guard=stream_guard
        self.system_headers = [ "string.h" ]
        if self.cplusplus:
            self.system_headers.append("cassert")
            self.system_headers.append("string")
        else:
            self.system_headers.append('assert.h')


        self.convert_function_headers = [ _make_str2foo(), _make_foo2str() ]

        if self.cplusplus:
            self.ostream_function_headers = ['std::ostream& operator<<(std::ostream& o, const %s& v)',
                                             'std::istream& operator>>(std::istream& o,  %s& v)' ]
            self.operator_function_headers = ['%s& operator++(%s& x, int)',
                                              '%s& operator--(%s& x, int)' ]
        else:
            self.ostream_function_headers = []
            self.operator_function_headers = []


        if self.cplusplus:
            namespace = self.namespace
        else:
            namespace = None
            
        full_header_file_name = mbuild.join(gendir,self.hfn)
        self.hf = codegen.file_emitter_t(gendir, self.hfn,
                                         namespace=namespace)
        if type(self.extra_header) == list:
            for hdr in self.extra_header:
                self.hf.add_header(hdr)
        elif self.extra_header:
            self.hf.add_header(self.extra_header)
        
        full_source_file_name = mbuild.join(gendir,self.cfn)
        self.cf = codegen.file_emitter_t(gendir, self.cfn,
                                         namespace=namespace)
        self.cf.add_header(self.hfn)
        
        for sh in self.system_headers:
            self.cf.add_system_header(sh)

        if self.cplusplus:
            if self.stream_guard and self.stream_guard != '':
                self.hf.add_misc_header("#if %s==1" % self.stream_guard)
                self.hf.add_misc_header("# include <iostream>")
                self.hf.add_misc_header("#endif")
            else:
                self.hf.add_misc_header("#include <iostream>")
        self.hf.start()
        self.cf.start()

    def emit(self):
        self._emit_header_file()
        self._emit_source_file()
        self._close()
    #######################################################
    def _scan_for_preset_values(self, vals):
       for v in vals:
          if v.value != None:
             return True
       return False
    def _make_number(self, s):
       if re.match(r'^0x',s):
          return (True,int(s,16))
       if re.match(r'^[0-9]*$',s):
          return (True,int(s,10))
       return (False,s)

    def _partition_duplicates(self, vals):
       duplicates = []
       unique = []
       for v in vals:
          if v.duplicate:
             duplicates.append(v)
          else:
             unique.append(v)
       return (unique,duplicates)
    def _scan_for_dense_zero_based_preset_values(self, vals):
       """Scan the list of values, and check that each one has the
       expected zero-based value, or no specified value (as often
       happens with the LAST element). Return True if it dense and
       zero based. """
       if self.debug:
          print("SCAN FOR DENSE")
       b = 0
       n = 0
       for v in vals:
          if self.debug:
             print("\tTESTING [%s]->[%s]" % (v.name, str(v.value)))
          if v.value == None:
             b = b + 1
             n = n + 1
             continue
          (is_number,ov) = self._make_number(v.value)
          if self.debug:
             print("\t\t isnum=%s %s" % ( str(is_number), str(ov)))
          if is_number and ov == b:
             b = b + 1
             n = n + 1
             continue
          # if it matches a previous value then it can still be dense,
          # but we must not put this value in the value-2-string
          # table. It must be in a separate string2value table.
          #print "\t\t [%s]" % ( str(vals[0:n]))
          previous_values = [ x.name for x in  vals[0:n] ] 
          if self.debug:
             print("\t\t [%s]" % ( str(previous_values)))
          if v.value in previous_values:
             v.duplicate = True
             n = n + 1
             continue
          if self.debug:
             print("\t\t Not in previous values")
          return False
       return True
    def _unique(self, vals):
        """Return a list of unique values, given a list of
        enumer_value_t objects"""
        uvals = {}
        for v in vals:
            if v.name in uvals:
                if uvals[v.name].value != v.value:
                    sys.stderr.write("ENUMER ERROR: duplicate key name in enumeration with different values: %s\n" % v.name)
                    sys.exit(1)
            uvals[ v.name ] = v

        # attempt to preserve the order of the values in the returned sequence.
        # make sure INVALID is first though!
        ovals = []
        if 'INVALID' in uvals:
            ovals.append(uvals['INVALID'])
            del uvals['INVALID']
        for v in vals:
            if v.name in uvals:
                ovals.append(uvals[v.name])
                del uvals[v.name]
        return ovals
    def _close(self):
        self.cf.close()
        self.hf.close()

    def _emit_header_file(self):
        self._emit_defines()
        self._emit_typedef()
        if self.string_convert >= 0:
            self._emit_convert_protos()
        if self.add_last_element:
           self._emit_last_fn_proto()
        if self.cplusplus:
            self._emit_ostream_protos()
            self._emit_operators_protos()
        
    def _emit_source_file(self):
        if self.string_convert == 1:
            self._emit_name_table_type()
            self._emit_name_table()
            self._emit_duplicate_name_table()
            self._emit_converts()
        elif self.string_convert == 0:
            self._emit_convert_stubs()
        if self.add_last_element:
           self._emit_last_fn()
        if self.cplusplus:
            self._emit_ostream()
            self._emit_operators()
        self._emit_comment()

    def _emit_defines(self):
        for v in self.values + self.duplicates:
            self.hf.emit_eol('#define {}{}_DEFINED 1'.format(self.prefix, v.name))
            
    def _emit_typedef(self):
        xmax = len(self.values) + len(self.duplicates)
        self.hf.emit_eol("typedef enum {")
        for i,v in enumerate(self.values):
            self.hf.emit("  %s%s" % (self.prefix,v.name))
            if v.value != None:
                self.hf.emit("=%s" % v.value)
            if i < xmax-1:
                self.hf.emit(',')
            if v.doxygen != None:
                self.hf.emit(" %s" % v.doxygen)
            self.hf.emit_eol()

        if len(self.duplicates) == 0:
           self.hf.emit_eol("} %s;" % self.type_name)
           self.hf.emit_eol()
           return

        bias = len(self.values)
        for i,v in enumerate(self.duplicates):
            self.hf.emit("  %s%s" % (self.prefix,v.name))
            if v.value != None:
                if v.duplicate:
                   self.hf.emit("=%s%s" % (self.prefix,v.value))
                else:
                   self.hf.emit("=%s" % v.value)
            if i+bias < xmax-1:
                self.hf.emit(',')
            if v.doxygen != None:
                self.hf.emit(" %s" % v.doxygen)
            self.hf.emit_eol()
           
        self.hf.emit_eol("} %s;" % self.type_name)
        self.hf.emit_eol()
        
    def _emit_convert_protos(self):
        for x in self.convert_function_headers:
            d = { 'type' : self.type_name,
                  'prefix' : self.proto_prefix }
            self.hf.add_code_eol(x % (d))
        self.hf.emit_eol()
        
    def _emit_ostream_protos(self):
        if self.stream_guard and self.stream_guard != '':
            self.hf.emit_eol("#if %s==1" % self.stream_guard)
        for x in self.ostream_function_headers:
            t = "%s " + x
            self.hf.add_code_eol(t  % (self.proto_prefix,self.type_name))
        if self.stream_guard and self.stream_guard != '':
            self.hf.emit_eol("#endif")
        self.hf.emit_eol()
    def _emit_operators_protos(self):
        for x in self.operator_function_headers:
            t = "%s " + x
            self.hf.add_code_eol(t % \
                      (self.proto_prefix, self.type_name, self.type_name))
        self.hf.emit_eol()
        
    def _emit_name_table_type(self):
        nt_string = """
typedef struct {
    const char* name;
    %(type)s value;
} name_table_%(type)s;"""
        self.cf.emit_eol(nt_string % {'type':self.type_name})

    def _emit_name_table(self):
        s = "static const name_table_%(type)s name_array_%(type)s[] = {"
        self.cf.emit_eol(s % {'type':self.type_name})
        for v in self.values:
            s = """{"%s", %s%s},""" % (v.display_str,self.prefix,v.name)
            self.cf.emit_eol(s)
        s = "{%s, %s%s}," % ('0',self.prefix,self.values[-1].name)
        self.cf.emit_eol(s)
        self.cf.emit_eol('};')

    def _emit_duplicate_name_table(self):
        if len(self.duplicates) == 0:
           return

        s = "static const name_table_%(type)s dup_name_array_%(type)s[] = {"
        self.cf.emit_eol(s % {'type':self.type_name})
        for v in self.duplicates:
            s = """{"%s", %s%s},""" % (v.display_str,self.prefix,v.name)
            self.cf.emit_eol(s)
        s = "{%s, %s%s}," % ('0',self.prefix,self.values[-1].name)
        self.cf.emit_eol(s)
        self.cf.emit_eol('};')

    def _invalid_or_last(self):
        for v in self.values:
            if v.name == 'INVALID':
                return 'INVALID'
        return self.values[-1].name

    def _emit_last_fn_proto(self):
       """Emit a function that returns the LAST element"""
       l = [
        "/// Returns the last element of the enumeration",
        "/// @return %(type)s The last element of the enumeration.",
        "/// @ingroup ENUM",
        "%(proto_prefix)s %(type)s %(type)s_last(void);"
        ]
       s = "\n".join(l)
       self.hf.emit_eol(s % {'type':self.type_name,
                             'proto_prefix':self.proto_prefix} )
       
    def _emit_last_fn(self):
       """Emit a function that returns the LAST element"""
       s = """
%(type)s %(type)s_last(void) {
    return %(prefix)sLAST;
}
       """
       self.cf.emit_eol(s % {'type':self.type_name, 'prefix':self.prefix} )
    
    def _emit_convert_stubs(self):
       self._emit_str2enum_convert_stub()
       self._emit_enum2str_convert_stub()
    def _emit_str2enum_convert_stub(self):
        """Emit a fake from-string converter that always returns invalid"""
        top = """
%(type)s str2%(type)s(const char* s)
{
   return %(prefix)s%(invalid)s;
   (void)s;
}"""
        invalid = self._invalid_or_last()
        d =  {'type':self.type_name,
              'prefix':self.prefix,
              'invalid':invalid}
        self.cf.emit_eol(top % (d))

    def _emit_enum2str_convert_stub(self):
        """Emit a fake to-string converter that always returns invalid"""
        s = """
const char* %(type)s2str(const %(type)s p)
{
   return "INVALID";
   (void)p;
}"""
        invalid = self._invalid_or_last()
        self.cf.emit_eol(s % {'type':self.type_name,
                              'prefix':self.prefix,
                              'invalid':invalid})

    def _emit_converts(self):
       self._emit_str2enum_convert()
       self._emit_enum2str_convert()

    def _emit_str2enum_convert(self):
       top = """
        
%(type)s str2%(type)s(const char* s)
{
   const name_table_%(type)s* p = name_array_%(type)s;
   while( p->name ) {
     if (strcmp(p->name,s) == 0) {
      return p->value;
     }
     p++;
   }
        """
       dups = """
   {
     const name_table_%(type)s* q = dup_name_array_%(type)s;
     while( q->name ) {
       if (strcmp(q->name,s) == 0) {
        return q->value;
       }
       q++;
     }
   } 
        """
       end = """
   return %(prefix)s%(invalid)s;
}"""
       
       invalid = self._invalid_or_last()
       d =  {'type':self.type_name,
             'prefix':self.prefix,
             'invalid':invalid}
       self.cf.emit_eol(top % (d))
       if self.duplicates:
          self.cf.emit_eol(dups % (d))
       self.cf.emit_eol(end % (d))

    def _emit_enum2str_convert(self):
       if self.density == 'sparse':
          self._emit_sparse_enum2str_convert()
       else:
          self._emit_dense_enum2str_convert()

    def _emit_sparse_enum2str_convert(self):
       s = """

const char* %(type)s2str(const %(type)s p)
{
   const name_table_%(type)s* q = name_array_%(type)s;
   while( q->name ) {
      if (q->value == p) {
         return q->name;
      }
      q++;
   }
   return "???";
}"""
       
       invalid = self._invalid_or_last()
       self.cf.emit_eol(s % {'type':self.type_name,
                             'prefix':self.prefix,
                             'invalid':invalid})

    def _emit_dense_enum2str_convert(self):

       s = """

const char* %(type)s2str(const %(type)s p)
{
   %(type)s type_idx = p;
   if ( p > %(prefix)sLAST) type_idx = %(prefix)sLAST;
   return name_array_%(type)s[type_idx].name;
}"""
       
       invalid = self._invalid_or_last()
       self.cf.emit_eol(s % {'type':self.type_name,
                             'prefix':self.prefix,
                             'invalid':invalid})
        
    def _emit_ostream(self):
        s = """

std::ostream& operator<<(std::ostream& o, const %(type)s& v) {
   o << %(type)s2str(v);
   return o;
}

std::istream& operator>>(std::istream& i, %(type)s& v) {
   std::string s; 
   i >> s; 
   v = str2%(type)s( s.c_str() );
   return i;
}"""
        if self.stream_guard and self.stream_guard != '':
            self.cf.emit_eol("#if %s==1" % self.stream_guard)
        self.cf.emit_eol(s % {'type':self.type_name})
        if self.stream_guard and self.stream_guard != '':
            self.cf.emit_eol("#endif")
            

    def _emit_operators(self):
        s = """
%(type)s& operator++(%(type)s& x, int)
{
   return x = %(type)s(x+1);
}
%(type)s& operator--(%(type)s& x, int)
{
   return x = %(type)s(x-1);
}"""
        self.cf.emit_eol(s % {'type':self.type_name})

    def _emit_comment(self):
        self.cf.emit_eol("/*")
        self.cf.emit_eol()
        self.cf.emit_eol("Here is a skeleton switch statement embedded in a comment")
        self.cf.emit_eol()
        self.cf.emit_eol()
        self.cf.emit_eol("  switch(p) {")
        for v in self.values:
            self.cf.emit_eol("  case %s%s:" % (self.prefix, v.name))
        self.cf.emit_eol("  default:")
        self.cf.emit_eol("     xed_assert(0);")
        self.cf.emit_eol("  }")
        self.cf.emit_eol("*/")
    

def _test_enumer():
    values = map(enumer_value_t, ['aaa','bbb','ccc'])
    e = enumer_t("test_type_t", "TEST_TYPE_", values,
                 "enumer-test.cpp", "enumer-test.H", ".",
                 namespace = "XED",
                 stream_guard ="XEDPRINT")
    e.emit()
    
if __name__ == '__main__':
    _test_enumer()
