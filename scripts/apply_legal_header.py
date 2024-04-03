#!/usr/bin/env python 
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2024 Intel Corporation
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
from pathlib import Path
import sys
import os
import re
import datetime
from stat import *
import argparse
from collections import defaultdict, Counter
import subprocess

XED_ROOT = Path(__file__).parents[1]

TEMPLATE_PATH = Path(XED_ROOT, 'misc','legal-header.txt')
CURRENT_YEAR = datetime.date.today().strftime("%Y")
# ignore last modified year for files that only got their headers changed
HEADER_SKIP_COMMITS = ['5d594f8b09224e77524098bbac43e8f7f680d9f9']

def print_final_lines(output):
   print('[FINAL COMMAND OUTPUT]')
   for line in output:
      print("\t" + line)

def die(s):
    sys.stdout.write("ERROR: {0}\n".format(s))
    sys.exit(1)

def cond_die(v, cmd, msg, lines=[]):
   if v:
      if lines:
         print_final_lines(lines)
      s = msg + "\n  [CMD] " + cmd
      die(s)

def ensure_string(x):
    """handle non unicode output"""
    if isinstance(x, bytes):
        try:
            return x.decode('utf-8')
        except:
            return ''
    return x

def run_subprocess(cmd, **kwargs):
	"""front end to running subprocess"""
	sub = subprocess.Popen(cmd,
	                           shell=True,
	                           stdout=subprocess.PIPE,
	                           stderr=subprocess.STDOUT,
	                           **kwargs)
	lines = sub.stdout.readlines()
	lines = [ensure_string(x) for x in lines]
	sub.wait()
	return sub.returncode, lines

def run_shell_command(cmd, **kwargs):
   """INPUT: string with all args. OUTPUT: return the exit status, or die trying..."""
   try:
        (returncode, lines) = run_subprocess(cmd, **kwargs)
        cond_die(returncode, cmd,
               "Child was terminated by signal {0:d}".format(-returncode), lines)
        return (returncode, lines)
   except OSError as e:
     die("Execution failed: {0}".format(str(e)))

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
        retval.append( "#" + line )
    return retval

def replace_curr_year(file, year=''):
    """replaces the general year from the template with the given year.
    If not specified, it will be replaced with the current year."""
    if not year:
        year = CURRENT_YEAR
    updated_file = [sub.replace("<CURRENT_YEAR>", year) for sub in file]
    return updated_file

def apply_header_to_source_file(header, file, year=''):
    "apply header to file using C++ comment style"
    f = open(file,"r")
    mode = get_mode(file)
    contents = f.readlines()
    f.close()
    trimmed_contents = remove_existing_header(contents)
    newfile = file + ".new"
    curr_header = replace_curr_year(header, year)
    o = open(newfile,"w")
    o.write("/* BEGIN_LEGAL \n")
    o.writelines(curr_header)
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
    o.write("#BEGIN_LEGAL\n")
    o.writelines(lines)
    o.write("#END_LEGAL\n")
    
def apply_header_to_data_file(header, file, year=''):
    "apply header to file using script comment style"
    f = open(file,"r")
    mode = get_mode(file)
    #print "file: " + file + " mode: " + "%o"  % mode
    contents = f.readlines()
    f.close()
    trimmed_contents = remove_existing_header(contents)
    newfile = file + ".new"
    curr_header = replace_curr_year(header, year)
    o = open(newfile,"w")
    augmented_header = prepend_script_comment(curr_header)
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

def skip_file(file):
    """determines if we need to skip legal header change"""
    f = Path(file).resolve(strict=True)
    if f.is_dir():   # skip directories (e.g. submodule changes)
        return True

    skip_dirs = ['tests/resync']
    skip_dirs = [Path(XED_ROOT, d).resolve() for d in skip_dirs]  # convert to Path list
    dir = f.parent
    for skip_d in skip_dirs:
        if Path(os.path.commonpath([dir, skip_d])) == skip_d:
            return True

    skip_suffix = ['.pdf', '.msi', '.sln', '.vcproj', '.vcxproj', '.filters',
                   '.xsl', '.rtf', '.reference', '.rc', '.doc', '.html',
                   '.docx', '.msm', '.ico', '.bmp', '.exe', '.a', '.lib', '.csv', '.bz2',
                   '.zip', '.csproj', '.json', '.js', '.xz', '.TESTS', '.pyc', '.md', '.in']
    # Path().suffixes return a list of the final component's suffixes, if any.
    # check if the intersection with skip_suffix is empty or not
    if set(f.suffixes).intersection(skip_suffix):
        return True
    
    # skip specific files
    skip_list = ['misc/legal-header.txt', 'misc/API.NAMES.txt', 'misc/ci-branches.txt',
                 '.github/workflows/exclude_external.txt', 'LICENSE', 'scripts/run-pylint-scan',
                 'examples/xed-rc-template.txt', 'docsrc/xed-doxygen-header.txt']
    for se in skip_list:
        sf = Path(se).resolve()
        if sf.exists() and f.samefile(sf):
                return True
    
    #skip pattern
    skip_patterns = ['*.gitignore', '*README.*', 'tests/test*/*', 'tests/test*/**/*']
    for pattern in skip_patterns:
        if f.match(pattern):
            return True
        
    return False

def replace_headers(files, year=''):
    """Replaces legal headers for the given files with the specified legal header template"""
    source_files, data_files = [], []

    for file_name in  files:
        if skip_file(file_name):          # need to skip tests & legal header template for instance
            print(f"skipped file: {file_name}")
        elif re.search(r'[.][chp]$|(cpp)$',file_name, re.IGNORECASE):
            source_files.append(file_name)
        else:
            data_files.append(file_name)   # includes python scripts
    
    # opens legal header template
    with TEMPLATE_PATH.open('r') as header_template:
        legal_header = header_template.readlines()

    for f in source_files:
        apply_header_to_source_file(legal_header, f, year)
    
    for f in data_files:
        apply_header_to_data_file(legal_header, f, year)

def get_years_from_copyrights(copyrights):
    """Returns the year from a given copyright string. If not found, return None."""
    regx = '.*copyright.* (\d+\d+)[ ,].*'
    re_obj = re.compile(regx, re.IGNORECASE)
    match = re_obj.search(copyrights)

    if match:
        try:
            found_year = match.group(1)
            return found_year
        except: pass
    return None

def get_last_modified_data(file):
    """Retrieves the file's last modified year and commit hash."""
    cmd = f'git log -1 --format="%ad %H" {file}'
    _, out = run_shell_command(cmd)

    try:
        commit_info = out[0].split()     # out has format D M DATE H {YEAR} TZ {COMMIT_HASH}
        modified_year = commit_info[4]
        commit_hash = commit_info[6]
    except:
        modified_year = CURRENT_YEAR   # in case file was just added
        commit_hash = ''
    return modified_year, commit_hash

def check_years(curr_header, file, issues):
    """Checks if the current header's year matches the year it was last modified in."""

    found_year = get_years_from_copyrights(curr_header)
    if not found_year:
        issues[file] = f'Copyright year was not found.'
        return False
    
    excpected_year, file_cmt_hash = get_last_modified_data(file)
    if int(found_year) != int(excpected_year):
        if file_cmt_hash not in HEADER_SKIP_COMMITS:
            issues[file] = f'Bad copyright years - found "{found_year}", expected "{excpected_year}."'
        return False

    return True

def remove_year_from_header(copyright_lines):
    """Removes the line with the year from the legal header."""
    regx= '.*Copyright \(C\) .* intel corporation.*'
    re_obj = re.compile(regx, re.IGNORECASE)
    match = re_obj.search(copyright_lines)
    if match:
        years_start, years_end = match.span()
        copyright_lines = copyright_lines[:years_start] + copyright_lines[years_end:]
    return copyright_lines

def get_clean_lines(copyright_text):
    """Removes comments from copyright text."""
    copyright_lines = copyright_text.splitlines()
    copyright_lines = list(map(lambda x: x.strip('#*/'), copyright_lines))
    copyright_lines = list(map(lambda x: x.strip(), copyright_lines))
    return '\n'.join(copyright_lines)

def get_copyright_from_file(file_content):
    """Extracts the copyright text from the file content."""
    match_e = re.compile('.*END_LEGAL.*(\n)*', re.IGNORECASE).search(file_content)
    match_b = re.compile('.*BEGIN_LEGAL.*(\n)*', re.IGNORECASE).search(file_content)
    copyright_lines = file_content[match_b.start():match_e.end()]
    return copyright_lines

def check_copyright_text(file_content, file, issues):
    """Checks whether the legal header of the specified file matches the legal header template."""

    with open(TEMPLATE_PATH) as f:
        expected_header = f.read().strip()
    expected_header = remove_year_from_header(expected_header)

    copyright_lines = get_copyright_from_file(file_content) # current header
    copyright_lines = get_clean_lines(copyright_lines)      # remove comments
    copyright_lines = remove_year_from_header(copyright_lines)

    # truncate whitespaces and remove empty new lines and BEGIN_LEGAL/END_LEGAL
    copyright_lines = copyright_lines.strip().split()
    expected_header = expected_header.strip().split()
    del copyright_lines[0], copyright_lines[-1]

    if Counter(copyright_lines) != Counter(expected_header):
        issues[file] = 'Wrong copyright header found.'
        return False
    return True

def check_header_existence(file_content, file, issues):
    """Checks whether the legal header exists in the file."""
    start_hdr_pattern = ('.*BEGIN_LEGAL.*(\n)*'
                   '(:?.+\n)*'
                   '.*Copyright \(C\) (\d+) intel corporation.*\n')
    match = re.compile(start_hdr_pattern, re.IGNORECASE).search(file_content)
    if not match:
        issues[file] = 'Intel legal string not found.'
    return match

def print_copyright_errors(issues):
    """Prints scanned files' copyright errors."""
    if issues:
        print('======== Copyright Errors ========')
        for file, text in issues.items():
            print(f'{file} : {text}')

def check_copyrights(files, suppress_print=False):
    """Checks if the legal headers of the given files are appropriate; this includes year and text checks."""
    
    issues ={}

    for file in files:
        if skip_file(file):
            if not suppress_print:
                print(f'skipping {file}')
            continue

        try:
            with open(file) as file_obj:
                file_content = ''.join(file_obj.readlines()[:100])
        except Exception as e:
            issues[file] = f'Can not read from file: {e}'
            continue

        if not check_header_existence(file_content, file, issues):
            continue
        elif not check_years(file_content, file, issues):
            continue
        elif not check_copyright_text(file_content, file, issues):
            continue

    print_copyright_errors(issues)
    return issues

def validate_copyrights(files):
    """Returns the number of issues with the files to be scanned."""
    issues = check_copyrights(files, suppress_print=True)
    return len(issues)

def replace_copyrights(files2scan):
    """Replaces copyright headers for files2scan"""
    issues = check_copyrights(files2scan, suppress_print=True)
    
    # only replace files with invalid legal headers
    files2replace = list(issues.keys())

    files_by_year = defaultdict(list)   # partition the files into lists of files by last modification year

    for file in files2replace:
        last_mod_year, file_cmt_hash = get_last_modified_data(file)
        files_by_year[last_mod_year].append(file)

    for modified_year, files in files_by_year.items():
        replace_headers(files, modified_year)
    return 0

def retrieve_files(dir):
    """Returns a list of files in the given dir in the index and the working tree (excluding git-ignored files)"""
    cmd = f"git ls-files --directory {dir}"
    _, out = run_shell_command(cmd)
    files =[file.strip() for file in out]
    return files

def setup():
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='XED Copyrights Checker')
    parser.add_argument("--dir",
                      action="store",
                      dest="dir",
                      default=os.getcwd(),
                      help="directory to scan for copyrights")                      
    # defaultly changes legal header (don't use -validate-headers to change the headers)
    parser.add_argument("--validate-only",
                      action="store_true",
                      dest="validate_only",
                      default=False,
                      help="Only validate legal headers. Do not change the files' headers.")
    env = vars(parser.parse_args())
    return env

def main():
    env = setup()
    files_for_scan = []
    files = retrieve_files(env['dir'])
    for fname in files:
        fname = str(Path(fname).resolve(strict=True))
        files_for_scan.append(fname)
    if env['validate_only']:
        retval = validate_copyrights(files_for_scan)
    else: 
        retval = replace_copyrights(files_for_scan)
    sys.exit(retval)

if __name__ == '__main__':

    main()
