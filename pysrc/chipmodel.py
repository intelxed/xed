#!/usr/bin/env  python
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
import enum_txt_writer
import codegen
import genutil

def _die(s):
    genutil.die(s)

def filter_comments(lines):
    n = []
    for line in lines:
        t = re.sub('#.*','',line)
        t = t.strip()
        if t:
            n.append(t)
    return n

all_of_pattern  = re.compile(r'ALL_OF[(](?P<chip>[A-Z0-9a-z_]+)[)]')
not_pattern  = re.compile(r'NOT[(](?P<ext>[A-Z0-9a-z_]+)[)]')
common_subset_pattern  = re.compile(r'COMMON_SUBSET[(](?P<chip1>[A-Z0-9a-z_]+),(?P<chip2>[A-Z0-9a-z_]+)[)]')

def uniquify_list(l):
    d = {}
    for a in l:
        d[a]=True
    return list(d.keys())

def expand_common_subset(d):
    """return true to keep going, false otherwise"""
    found = False
    for chip,ext_list in d.items():
        newexts = []
        for ext in ext_list:
            m = common_subset_pattern.match(ext)
            if m:
                found = True
                chip1 = m.group('chip1')
                chip2 = m.group('chip2')
                exts1 = set(d[chip1])
                exts2 = set(d[chip2])
                common = exts1.intersection(exts2)
                newexts.extend(list(common))
            else:
                newexts.append(ext)
        d[chip]  = uniquify_list(newexts)
                
    return found


def expand_all_of_once(d):
    """return true to keep going, false otherwise"""
    found = False
    for chip,ext_list in d.items():
        newexts = []
        for ext in ext_list:
            m = all_of_pattern.match(ext)
            if m:
                found = True
                other_chip = m.group('chip')
                newexts.extend(d[other_chip])

            else:
                newexts.append(ext)
        d[chip]  = uniquify_list(newexts)
    return found

def expand_macro(d,expander):
    found = True
    while found:
        found = expander(d)

def expand_macro_not(d):
    for chip,ext_list in d.items():
        to_remove = []
        positive_exts = []
        for ext in ext_list:
            m = not_pattern.match(ext)
            if m:
                to_remove.append( m.group('ext'))
            else:
                positive_exts.append(ext)
        
        for r in to_remove:
            try:
                positive_exts.remove(r)
            except:
                _die("Could not remove %s from %s for chip %s" % 
                                     ( r, " ".join(positive_exts), chip))
                                 
        d[chip]  = uniquify_list(positive_exts)

def  parse_lines(input_file_name, lines): # returns a dictionary
    """Return a list of chips and a dictionary indexed by chip containing
    lists of isa-sets    """
    d = {}
    chips = []
    for line in lines:
        if line.find(':') == -1:
            _die("reading file {}: missing colon in line: {}".format(
                 input_file_name, line))
        try:
            (chip, extensions) = line.split(':')
        except:
            _die("Bad line: {}".format(line))
            
        chip = chip.strip()
        chips.append(chip)
        extensions = extensions.split()
        if chip in d:
            _die("Duplicate definition of %s in %s" % 
                (chip, input_file_name))
        if chip == 'ALL':
            _die("Cannot define a chip named 'ALL'." +
                 " That name is reserved.")
        d[chip] = extensions
    return (chips,d)
        

def _feature_index(all_features, f):
    try:
        return all_features.index(f)
    except:
        _die("Did not find isa set %s in list\n" % (f))



def read_database(filename):
    lines = open(filename,'r').readlines()
    lines = filter_comments(lines)
    lines = genutil.process_continuations(lines)
    # returns a list and a dictionary
    (chips,chip_features_dict) = parse_lines(filename,lines) 

    expand_macro(chip_features_dict,expand_all_of_once)
    expand_macro(chip_features_dict,expand_common_subset)
    expand_macro_not(chip_features_dict)

    return (chips,chip_features_dict)


def _format_names(lst):
    cols = 4
    lines = ('\t'.join(lst[i:i+cols]) for i in range(0,len(lst),cols))
    return '\n\t'.join(lines)
            
def dump_chip_hierarchy(arg, chips, chip_features_dict):
    fe = codegen.xed_file_emitter_t(arg.xeddir, 
                                     arg.gendir, 
                                     'cdata.txt', 
                                     shell_file=True)
    fe.start(full_header=False)
    for c in chips:
        fl = chip_features_dict[c]
        fl.sort()
        s = "{} :\n".format(c)
        s = s + '\t' + _format_names(fl)  + '\n'
        fe.write(s)
    fe.close()
    return fe.full_file_name
    
def work(arg):
    (chips,chip_features_dict) = read_database(arg.input_file_name) 

    isa_set_per_chip_fn = dump_chip_hierarchy(arg, chips, chip_features_dict)
    # the XED_CHIP_ enum
    chips.append("ALL")
    chip_enum =  enum_txt_writer.enum_info_t(['INVALID'] + chips,
                                             arg.xeddir,
                                             arg.gendir,
                                             'xed-chip',
                                             'xed_chip_enum_t',
                                             'XED_CHIP_',
                                             cplusplus=False)
    chip_enum.print_enum()
    chip_enum.run_enumer()

    # Add the "ALL" chip
    
    # the XED_ISA_SET_ enum
    isa_set = set()
    for vl in list(chip_features_dict.values()):
        for v in vl:
            isa_set.add(v.upper())
    isa_set = list(isa_set)
    isa_set.sort()

    chip_features_dict['ALL'] = isa_set

    isa_set = ['INVALID'] + isa_set
    isa_set_enum =  enum_txt_writer.enum_info_t(isa_set, 
                                                arg.xeddir, 
                                                arg.gendir,
                                                'xed-isa-set',
                                                'xed_isa_set_enum_t',
                                                'XED_ISA_SET_',
                                                cplusplus=False)
    isa_set_enum.print_enum()
    isa_set_enum.run_enumer()

    # the initialization file and header 
    chip_features_cfn = 'xed-chip-features-table.c'
    chip_features_hfn = 'xed-chip-features-table.h'
    cfe = codegen.xed_file_emitter_t(arg.xeddir, 
                                     arg.gendir, 
                                     chip_features_cfn, 
                                     shell_file=False)
    private_gendir = os.path.join(arg.gendir,'include-private')
    hfe = codegen.xed_file_emitter_t(arg.xeddir, 
                                     private_gendir,
                                     chip_features_hfn, 
                                     shell_file=False)
    for header in [ 'xed-isa-set-enum.h', 'xed-chip-enum.h' ]:
        cfe.add_header(header)
        hfe.add_header(header)
    cfe.start()
    hfe.start()

    
    cfe.write("xed_uint64_t xed_chip_features[XED_CHIP_LAST][4];\n")
    hfe.write("extern xed_uint64_t xed_chip_features[XED_CHIP_LAST][4];\n")

    fo = codegen.function_object_t('xed_init_chip_model_info', 'void')    
    fo.add_code_eol("const xed_uint64_t one=1")
    # make a set for each machine name
    spacing = "\n      |"
    for c in chips:
        s0 = ['0']
        s1 = ['0']
        s2 = ['0']
        s3 = ['0']
        # loop over the features
        for f in  chip_features_dict[c]:
            feature_index = _feature_index(isa_set,f)

            if feature_index < 64:
                s0.append('(one<<XED_ISA_SET_%s)' % (f))
            elif feature_index < 128:
                s1.append('(one<<(XED_ISA_SET_%s-64))' % (f))
            elif feature_index < 192:
                s2.append('(one<<(XED_ISA_SET_%s-128))' % (f))
            elif feature_index < 256:
                s3.append('(one<<(XED_ISA_SET_%s-192))' % (f))
            else:
                _die("Feature index > 256. Need anotehr features array")

        s0s = spacing.join(s0)
        s1s = spacing.join(s1)
        s2s = spacing.join(s2)
        s3s = spacing.join(s3)
        
        for i,x in enumerate([s0s, s1s, s2s,s3s]):
            fo.add_code_eol("xed_chip_features[XED_CHIP_{}][{}] = {}".format(c,i,x) )

    cfe.write(fo.emit())
    cfe.close()
    hfe.write(fo.emit_header())
    hfe.close()

    return ( [ isa_set_per_chip_fn,
               chip_enum.hdr_full_file_name,
               chip_enum.src_full_file_name,
               isa_set_enum.hdr_full_file_name,
               isa_set_enum.src_full_file_name,
               hfe.full_file_name, 
               cfe.full_file_name],
             chips, isa_set)
    

class args_t(object):
    def __init__(self):
        self.input_file_name = None
        self.xeddir = None
        self.gendir = None

if __name__ == '__main__':
    arg = args_t()
    arg.input_file_name = 'datafiles/xed-chips.txt'
    arg.xeddir = '.'
    arg.gendir = 'obj'
    files_created,chips,isa_set = work(arg)
    print("Created files: %s" % (" ".join(files_created)))
    sys.exit(0)

