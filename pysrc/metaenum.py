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

# subprocess requires python 2.4 (replaces all os.popen() ) or later
import sys
import re
import enumer

###################################################################################


class metaenum_t(object):
    """This class is for reading in prefab enumeration files and
    generating the corresponding enumeration by calling the enumer.py
    module."""
    
    comment_pattern = re.compile(r'[#].*$')
    doxygen_comment_pattern = re.compile(r'//[/!]<.*')

    def __init__(self, enum_fn, gendir='.'):
        """The inputs are an enumeration specification file and an
        output directory."""
        self.cplusplus=False
        self.enum_fn = enum_fn # input file
        self.gendir = gendir
        self.tuples = None # list [enumer.enumer_value_t]
        self.cfn = None
        self.hfn = None
        self.density = ''
        self.namespace = None
        self.type_name = None
        self.prefix = None
        self.stream_ifdef = None
        self.proto_prefix=''
        self.extra_header=None # might be a list
        
        self.read_file()
        
    def read_file(self):
        """Read in an existing enumeration file name, and build our
        internal enumer structure. Return a tuple with the consumed data."""
        stream_ifdef = ''
        lines = open(self.enum_fn,'r').readlines()
        simple_tuples = []
        density = 'automatic'
        namespace = None
        proto_prefix = ''
        extra_header = []
        cplusplus = False
        for line in lines:
            nline = metaenum_t.comment_pattern.sub('',line).strip()
            if len(nline) == 0:
                continue
            wrds = nline.split()
            if wrds[0] == 'cplusplus':
                cplusplus = True
            elif wrds[0] == 'namespace':
                namespace = wrds[1]
            elif wrds[0] == 'hfn':
                hfn = wrds[1]
            elif wrds[0] == 'cfn':
                cfn = wrds[1]
            elif wrds[0] == 'density':
                density = wrds[1]
            elif wrds[0] == 'prefix':
                prefix = wrds[1]
            elif wrds[0] == 'typename':
                typename = wrds[1]
            elif wrds[0] == 'stream_ifdef':
                stream_ifdef = wrds[1]
            elif wrds[0] == 'proto_prefix':
                proto_prefix = wrds[1]
            elif wrds[0] == 'extra_header':
                extra_header.append(wrds[1])
            else:
                token = wrds[0]
                comment = None
                value = None
                if len(wrds) > 1:
                    if metaenum_t.doxygen_comment_pattern.match(wrds[1]):
                        comment = ' '.join(wrds[1:])
                    else:
                        value = wrds[1]
                        if len(wrds) > 2:
                            comment = ' '.join(wrds[2:])
                simple_tuples.append( (token, value, comment) )
              
        self.tuples = []
        for token,value,comment in simple_tuples:
            self.tuples.append(enumer.enumer_value_t(token,value,comment))
 
        self.cfn = cfn
        self.hfn = hfn
        self.density = density
        self.namespace = namespace
        self.type_name = typename
        self.prefix = prefix
        self.stream_ifdef = stream_ifdef
        self.proto_prefix= proto_prefix
        self.extra_header= extra_header
        self.cplusplus = cplusplus
        
    def run_enumer(self):
        e = enumer.enumer_t(self.type_name, self.prefix, self.tuples, 
                            self.cfn, self.hfn,
                            self.gendir,
                            self.namespace,
                            self.stream_ifdef,
                            cplusplus = self.cplusplus,
                            proto_prefix = self.proto_prefix,
                            extra_header=self.extra_header,
                            density=self.density)
        e.emit()
        self.src_full_file_name = e.cf.full_file_name
        self.hdr_full_file_name = e.hf.full_file_name


def _test_meta_enum():
    m = metaenum_t("datafiles/xed-machine-modes-enum.txt", "obj")
    m.run_enumer()
    
if __name__ == '__main__':
    args = len(sys.argv)
    if args == 1:
        sys.stderr.write("TESTING %s\n" % sys.argv[0])
        _test_meta_enum()
    elif args == 3:
        odir = sys.argv[1]
        enum_file = sys.argv[2]
        m = metaenum_t(enum_file, odir)
        m.run_enumer()
        sys.exit(0)
    else:
        sys.stderr.write("Usage: %s odir enumfile\n" % sys.argv[0])
        sys.exit(1)
    
