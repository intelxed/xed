#!/usr/bin/env python 
# -*- python -*-
# BEGIN_LEGAL
# 
# Copyright (c) 2021 Intel Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#   
# END_LEGAL
from __future__ import print_function
import sys
import os
import re
from stat import *

def get_mode(fn):
    "get the mode of the file named fn, suitable for os.chmod() or open() calls"
    mode = os.stat(fn)[ST_MODE]
    cmode = S_IMODE(mode)
    return cmode

def replace_original_with_new_file(file,newfile):
    "Replace file with newfile"
    # os.system(" mv -f %s %s" % ( newfile, file))
    os.unlink(file)
    os.rename(newfile,file)

def remove_existing_header(contents):
    "remove existing legal header, if any"
    retval = []
    skipping = False
    start_pattern = re.compile(r"^(/[*][ ]*BEGIN_LEGAL)|(#[ ]*BEGIN_LEGAL)")
    stop_pattern = re.compile(r"^[ ]*(END_LEGAL[ ]?[*]/)|(#[ ]*END_LEGAL)")
    for line in contents:
        if start_pattern.match(line):
            skipping = True
        if skipping == False:
            retval.append(line)
        if stop_pattern.match(line):
            skipping = False
    return retval

def prepend_script_comment(header):
    "Apply script comment marker to each line"
    retval = []
    for line in header:
        retval.append( "# " + line )
    return retval

def apply_header_to_source_file(header, file):
    "apply header to file using C++ comment style"
    f = open(file,"r")
    mode = get_mode(file)
    contents = f.readlines()
    f.close()
    trimmed_contents = remove_existing_header(contents)
    newfile = file + ".new"
    o = open(newfile,"w")
    o.write("/* BEGIN_LEGAL \n")
    o.writelines(header)
    o.write("END_LEGAL */\n")
    o.writelines(trimmed_contents)
    o.close()
    os.chmod(newfile,mode)
    replace_original_with_new_file(file,newfile)

# FIXME: this will flag files that have multiline C-style comments
# with -*- in them even though the splitter will not look for the
# comment properly

def shell_script(lines):
    """return true if the lines are the start of shell script or
    something that needs a mode comment at the top"""
    
    first = ""
    second = ""
    if len(lines) > 0:
        first = lines[0];
    if len(lines) > 1:
        second = lines[1];
        
    if re.match("#!",first):
        #print "\t\t First script test true"
        return True
    if re.search("-\*-",first) or re.search("-\*-",second):
        #print "\t\t Second script test true"
        return True
    return False

def split_script(lines):
    "Return a tuple of (header, body) for shell scripts, based on an input line list"
    header = []
    body  = []

    f = lines.pop(0)
    while re.match("#",f) or re.search("-\*-",f):
        header.append(f)
        f = lines.pop(0)

    # tack on the first non matching line from the above loop
    body.append(f);
    body.extend(lines);
    return (header,body)

def write_script_header(o,lines):
    "Write the file header for a script"
    o.write("# BEGIN_LEGAL\n")
    o.writelines(lines)
    o.write("# END_LEGAL\n")
    
def apply_header_to_data_file(header, file):
    "apply header to file using script comment style"
    f = open(file,"r")
    mode = get_mode(file)
    #print "file: " + file + " mode: " + "%o"  % mode
    contents = f.readlines()
    f.close()
    trimmed_contents = remove_existing_header(contents)
    newfile = file + ".new"
    o = open(newfile,"w")
    augmented_header = prepend_script_comment(header)
    if shell_script(trimmed_contents):
        (script_header, script_body) = split_script(trimmed_contents)
        o.writelines(script_header)
        write_script_header(o, augmented_header)
        o.writelines(script_body)
    else:
        write_script_header(o,augmented_header)
        o.writelines(trimmed_contents)
    o.close()
    os.chmod(newfile,mode)
    replace_original_with_new_file(file,newfile)

####################################################################
### MAIN
####################################################################
if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage " + sys.argv[0] + " [-s|-t] legal-header file-name [file-name...]\n")
        sys.exit(1)

    type = sys.argv[1]
    header_file = sys.argv[2]
    if not os.path.exists(header_file):
        print("Could not find header file: [%s]\n" % (header_file))
        sys.exit(1)

    files_to_tag = sys.argv[3:]
    f = open(header_file,"r")
    header = f.readlines()
    f.close()

    sources  = files_to_tag

    if type in [ '-c', "-s"]:
        for file in sources:
            if re.search(".svn",file) == None and re.search(".new$",file) == None:
                apply_header_to_source_file(header, file.strip())
    elif type in ['-d', "-t"]:
        for file in sources:
            if  re.search(".svn",file) == None and re.search(".new$",file) == None:
                apply_header_to_data_file(header, file.strip())
    else:
        print("2nd argument must be -s or -t\n")
        sys.exit(1)
