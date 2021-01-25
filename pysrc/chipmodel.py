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



def expand_chip(chip, d):
    new_ext = []
    
    # ALL_OF(chip)
    for ext in d[chip]:
        all_of_match = all_of_pattern.match(ext)
        if all_of_match:
            sub_chip = all_of_match.group('chip')
            expand_chip(sub_chip, d)
            new_ext.extend(d[sub_chip])

    # COMMON_SUBSET(chip1,chip2)
    for ext in d[chip]:
        common_subset_match = common_subset_pattern.match(ext)
        if common_subset_match: 
            sub_chip1 = common_subset_match.group('chip1')
            sub_chip2 = common_subset_match.group('chip2')
            expand_chip(sub_chip1, d)
            expand_chip(sub_chip2, d)
            exts1 = set(d[sub_chip1])
            exts2 = set(d[sub_chip2])
            common = exts1.intersection(exts2)
            new_ext.extend(list(common))
            
    # NOT(ext)
    for ext in d[chip]:
        not_ext_match = not_pattern.match(ext)
        if not_ext_match: 
            ext = not_ext_match.group('ext')
            while ext in new_ext:
                new_ext.remove(ext)  # remove from the incoming stuff

    # add all the conventional extensions
    for ext in d[chip]:
        if (all_of_pattern.match(ext) or
            common_subset_pattern.match(ext) or
            not_pattern.match(ext) ):
            pass
        else:
            new_ext.append(ext)
            
    d[chip] = uniquify_list(new_ext)
        
        
def recursive_expand(d):
    '''d is a dict of lists.  The lists contain extension names, and 3
       operators: ALL_OF(chip), NOT(extension), and
       COMMON_SUBSET(chip1,chip2). Before inserting the extensions
       from an ALL_OF(x) reference we must remove the all of the
       NOT(y) in the extensions of x. This is because chip z might
       re-add y and we don't want the NOT(y) from x to mess that up.
    '''

    for chip in d.keys():
        expand_chip(chip,d)
            

def read_database(filename):
    lines = open(filename,'r').readlines()
    lines = filter_comments(lines)
    lines = genutil.process_continuations(lines)
    # returns a list and a dictionary
    (chips,chip_features_dict) = parse_lines(filename,lines) 

    recursive_expand(chip_features_dict)

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

def add_all_chip(d):
    # the XED_ISA_SET_ enum
    isa_set = set()
    for vl in list(d.values()):
        for v in vl:
            isa_set.add(v.upper())
    isa_set = list(isa_set)
    isa_set.sort()

    d['ALL'] = isa_set
    isa_set = ['INVALID'] + isa_set
    return isa_set



def _check_in_chip_hierarchy_not_instructions(isaset_ch, isaset_inst):
    genutil.msgb("FROM CHIP MODEL", isaset_ch)
    genutil.msgb("FROM INSTRUCTIONS ", isaset_inst)
    missing = []
    for v in isaset_ch: # stuff from the chip hierarchy model 
        if v in ['INVALID']:
            continue
        if v not in isaset_inst: # stuff from the instructions
            missing.append(v)
            genutil.warn("isa_set referenced by chip model hierarchy, " +
                         "but not used by any instructions: {}".format(v))
    return missing

def _check_in_instructions_not_chip_hierarchy(isaset_ch, isaset_inst):
    missing = []
    for v in isaset_inst: # stuff from the instructions
        if v in ['INVALID']:
            continue
        if v not in isaset_ch: # stuff from the chip hierarchy model
            missing.append(v)
            genutil.warn("isa_set referenced by instructions, " +
                         "but not part of any chip: {}".format(v))
    return missing

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
    isa_set = add_all_chip(chip_features_dict)

    #  missing1 is extra stuff in chip model hierarchy that usually
    #  needs to be deleted.
    missing1=_check_in_chip_hierarchy_not_instructions(isa_set, arg.isa_sets_from_instr)
    
    # missing2 is extra stuff in the instructions, not in chip
    # hierarchy that usually needs to be part of some chip.
    missing2=_check_in_instructions_not_chip_hierarchy(isa_set, arg.isa_sets_from_instr)
    if missing2:
        if arg.add_orphans_to_future:

            #  add missing2 to "FUTURE" and  "ALL" chips.
            chip_features_dict['ALL'].extend(missing2)
            if 'FUTURE' in chip_features_dict:
                genutil.warn("Adding {} to FUTURE chip".format(missing2))
                chip_features_dict['FUTURE'].extend(missing2)
            isa_set.extend(missing2)
        else:
            _die("These need to be part of some chip: {}".format(missing2))
            
    
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

    
    cfe.write("xed_uint64_t xed_chip_features[XED_CHIP_LAST][5];\n")
    hfe.write("extern xed_uint64_t xed_chip_features[XED_CHIP_LAST][5];\n")

    fo = codegen.function_object_t('xed_init_chip_model_info', 'void')    
    fo.add_code_eol("const xed_uint64_t one=1")
    # make a set for each machine name
    spacing = "\n      |"
    for c in chips:
        s0 = ['0']
        s1 = ['0']
        s2 = ['0']
        s3 = ['0']
        s4 = ['0']
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
            elif feature_index < 320:
                s4.append('(one<<(XED_ISA_SET_%s-256))' % (f))
            else:
                _die("Feature index > 320. Need another features array")

        s0s = spacing.join(s0)
        s1s = spacing.join(s1)
        s2s = spacing.join(s2)
        s3s = spacing.join(s3)
        s4s = spacing.join(s4)
        
        for i,x in enumerate([s0s, s1s, s2s,s3s, s4s]):
            fo.add_code_eol("xed_chip_features[XED_CHIP_{}][{}] = {}".format(c,i,x) )


    # figure out  which chips support  AVX512 for ILD evex processing
    cfe.write("xed_bool_t xed_chip_supports_avx512[XED_CHIP_LAST];\n")
    hfe.write("extern xed_bool_t xed_chip_supports_avx512[XED_CHIP_LAST];\n")
    for c in chips:
        supports_avx512=False
        for f in  chip_features_dict[c]:
            if 'AVX512' in f:
                supports_avx512=True
                break
        v = '1' if supports_avx512 else '0'
        fo.add_code_eol('xed_chip_supports_avx512[XED_CHIP_{}]={}'.
                        format(c, v))
                
    cfe.write(fo.emit())
    hfe.write(fo.emit_header())
    cfe.close()    
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
        self.add_orphans_to_future = False
        self.isa_sets_from_instr = None

if __name__ == '__main__':
    arg = args_t()
    arg.input_file_name = 'datafiles/xed-chips.txt'
    arg.xeddir = '.'
    arg.gendir = 'obj'
    files_created,chips,isa_set = work(arg)
    print("Created files: %s" % (" ".join(files_created)))
    sys.exit(0)
