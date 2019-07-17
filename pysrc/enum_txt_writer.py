#!/usr/bin/env python
# -*- python -*-
# Mark Charney <mark.charney@intel.com>
# Enumeration support
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

import codegen
import enumer
import genutil

###################################################################################

class enum_info_t(object):
    """This class can build enumeration txt files for offline
    generation and it can also emit the enumeration by calling in to
    the enumer.py module"""
    
    def __init__(self,
                 lines,
                 xeddir,
                 gendir,
                 base_name,
                 type_name,
                 prefix,
                 namespace='XED',
                 stream_ifdef='XED_PRINT',
                 cplusplus=True,
                 proto_prefix='XED_DLL_EXPORT',
                 extra_header="xed-common-hdrs.h",
                 upper_case=True,
                 density='automatic',
                 string_convert=True):
        self.cplusplus = cplusplus
        self.lines = lines
        self.tuples = None # list  [enumer.enumer_value_t] objects
        self.gendir = gendir
        self.xeddir = xeddir
        self.base_name = base_name
        self.type_name = type_name
        self.prefix = prefix
        self.proto_prefix = proto_prefix
        self.extra_header = extra_header # could be a list
        self.upper_case= upper_case
        self.density = density
        self.string_convert = string_convert
        self.file_emitter = \
            codegen.xed_file_emitter_t(xeddir,
                                       gendir,
                                       self.base_name +'-enum.txt',
                                       shell_file=True)
        self.base_fn = self.base_name + '-enum'
        if self.cplusplus:
            self.cfn = self.base_fn + '.cpp'
            self.hfn = self.base_fn + '.H'
        else:
            self.cfn = self.base_fn + '.c'
            self.hfn = self.base_fn + '.h'
        self.namespace = namespace
        self.stream_ifdef = stream_ifdef
        
    def set_namespace(self,namespace):
        self.namespace = namespace
      
    def print_enum_header(self,fp): # private
        fp.write('namespace %s\n' % self.namespace)
        fp.write('cfn %s\n' % self.cfn)
        fp.write('hfn %s\n' % self.hfn)
        fp.write('typename %s\n' % self.type_name)
        fp.write('prefix %s\n' % self.prefix)
        if self.stream_ifdef and self.stream_ifdef != '':
            fp.write('stream_ifdef %s\n' % self.stream_ifdef)
        if self.cplusplus:
            fp.write("cplusplus\n")
        if self.proto_prefix:
            fp.write("proto_prefix %s\n" % self.proto_prefix)
        if self.extra_header:
            if isinstance(self.extra_header,list):
                for f in self.extra_header:
                    fp.write("extra_header %s\n" % f)
            else:
                fp.write("extra_header %s\n" % self.extra_header)

    def prep_name(self,s):
        if self.upper_case:
            return s.upper()
        return s

    def _print_lines(self, fp): # private
        """print the lines"""
        eol = '\n'
        for line in self.lines:
            if isinstance(line, enumer.enumer_value_t):
                fp.write(self.prep_name(line.name) + eol)                            
            elif type(line) == tuple:
                (token, val, comment) = line
                fp.write(' '.join((self.prep_name(token), val, comment)) + eol)
            else:
                 fp.write(self.prep_name(line) + eol)
    def print_enum(self): # public
        """emit the enumeration description file"""
        self.file_emitter.start()
        self.print_enum_header(self.file_emitter)
        self._print_lines(self.file_emitter)
        self.file_emitter.close()
        

    def prepare_lines(self):
        """Convert the lines to the appropriate type for emitting the
        enumeration"""
        self.tuples = []
        for line in self.lines:
            if isinstance(line, enumer.enumer_value_t):
                self.tuples.append(line)
            elif type(line) == tuple:
                if len(line) == 3:
                    (token, value, comment) = line
                else:
                    genutil.die("Cannot handle line: %s" % (str(line)))
                token = self.prep_name(token)
                self.tuples.append(enumer.enumer_value_t(token, value, comment))
            else:
                token = self.prep_name(line)
                self.tuples.append(enumer.enumer_value_t(token))

    def run_enumer(self): # public
        """Emit the enumeration"""
        if self.tuples == None:
            self.prepare_lines()
        e = enumer.enumer_t(self.type_name,
                            self.prefix,
                            self.tuples,
                            self.cfn,
                            self.hfn,
                            self.gendir,
                            self.namespace,
                            self.stream_ifdef,
                            cplusplus = self.cplusplus,
                            proto_prefix=self.proto_prefix,
                            extra_header=self.extra_header,
                            density=self.density,
                            string_convert=self.string_convert)
        e.emit()
        self.hdr_full_file_name = e.hf.full_file_name
        self.src_full_file_name = e.cf.full_file_name


       

