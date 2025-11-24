#-*- python -*-
# Generic utilities
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
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
"""
Generic utilities for XED generators.

This module provides common utility functions used throughout the XED build
system including file operations, string manipulation, error handling, list
operations, bit manipulation, and platform-specific helpers.
"""
import sys
import os
import math
import traceback
import copy
import re
import stat
import platform
from typing import Any, Optional

psystem = platform.system()
if (psystem == 'Microsoft' or
    psystem == 'Windows' or
    psystem.find('CYGWIN') != -1) :
    on_windows = True
else:
    on_windows = False

if not on_windows:
    import resource

def msgerr(msg: str):
    """Write to stderr"""
    sys.stderr.write("%s\n" % msg)

msgout = sys.stdout
def set_msgs(fp):
    global msgout
    msgout = fp

def msge(msg: str):
    """Write to msgout"""
    msgout.write("%s\n" % msg)
def msg(msg: str):
    """Write to msgout"""
    msgout.write("%s\n" % msg)
def msgn(msg: str):
    """Write to msgout"""
    msgout.write(msg)
def msgb(title: str, msg: str = ''):
    """Write to msgout"""
    msgout.write('[%s] %s\n' % (title, msg))

def cond_die(v, cmd, msg):
    if v != 0:
        s = msg 
        if cmd: s += '\n  [CMD] ' + cmd
        die(s)

import pdb
_debugging = False

def activate_debugger():
    global _debugging
    _debugging = True
    pdb.set_trace()
def die(msg: str):
    msgerr('[ERROR] ' + msg)
    if _debugging:
        pdb.set_trace()
    else:
        traceback.print_stack()
    sys.exit(1)
def warn(msg: str):
    msgerr('[WARNING] ' + msg)


def find_dir(d: str) -> Optional[str]:
    """Attempts to find directory `d` in the current directory or any parent directory."""

    directory = os.getcwd()
    last = ''
    while directory != last:
        target_directory = os.path.join(directory, d)
        if os.path.exists(target_directory):
            return target_directory
        last = directory
        directory = os.path.split(directory)[0]
    return None


def add_mbuild_to_path():
    """
    Add the mbuild directory to the python path.

    This will do nothing if `mbuild` already exists in the python path.
    """
    try:
        if any('mbuild' in x for x in sys.path):
            return
    except:
        pass
    mbuild_dir = find_dir('mbuild')
    if not mbuild_dir:
        die('Could not find mbuild directory.')
    sys.path = [mbuild_dir] + sys.path

def check_python_version(argmaj: int, argmin: int):
    tup = sys.version_info
    major: int = tup[0]
    minor: int = tup[1]
    if ((major > argmaj) or
            (major == argmaj and minor >= argmin)):
        return
    die(f'Need Python version {argmaj}.{argmin} or later (current version: {major}.{minor}).')

def make_readable_by_all_writeable_by_owner(file_name: str, errorname: str = ''):
    try:
        rwx = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        os.chmod(file_name, rwx)
    except IOError:
        die('Could not chmod: ' + errorname + ' file: [' + file_name + ']')

def open_for_writing(mode: str) -> bool:
    # The default mode is 'r'.
    mode = mode or 'r'
    for c in mode:
        if c in ['w', 'a', '+']:
            return True
    return False


def base_open_file(file_name: str, rw: str, errorname: str = ''):
    try:
        fp = open(file_name, rw)
    except IOError:
        die('Could not open: ' + errorname + ' file: [' + file_name + ']')
    if open_for_writing(rw):
        make_readable_by_all_writeable_by_owner(file_name, errorname)
    return fp

def resource_usage():
    if on_windows:
        x = (0, 0, 0, 0, 0, 0)
    else:
        x = resource.getrusage(resource.RUSAGE_SELF)
    return x

def format_resource_usage(x) -> str:
    s = ''
    s += 'user: ' + str(x[0])
    s += ' sys: ' + str(x[1])
    # These don't work on linux
    #s += ' maxrss: ' + str(x[2])
    #s += ' maxshd: ' + str(x[3])
    #s += ' maxprv: ' + str(x[4])
    #s += ' maxstk: ' + str(x[5])
    return s

def get_memory_usage() -> tuple[int, int, int]:
    """Return a tuple of (vmsize, vmrss, vmdata) on linux systems with
    /proc filesystems."""
    try:
        lines = open('/proc/%s/status' % os.getpid(), 'r').readlines()
        pairs = [x.split(':') for x in lines]
        dct = dict(pairs)
        return (dct['VmSize'].strip(), dct['VmRSS'].strip(), dct['VmData'].strip())
    except:
        return (0, 0, 0)

def print_resource_usage(i: str = ''):
    # 2014-05-19: disabled for now.
    return

    x = resource_usage()
    s = format_resource_usage(x)
    mem = get_memory_usage()
    msge('RUSAGE: %s %s vmsize: %s' % (str(i), str(s), str(mem[0])))

def flatten_sub(retlist, cur_list, rest):
    if len(rest) == 0:
        retlist.append(cur_list)
        return

    r0 = rest[0]
    if type(r0) == list:
        for v in r0:
            tlist = copy.copy(cur_list)
            tlist.append(v)
            flatten_sub(retlist, tlist, rest[1:])
    else:
        cur_list.append(r0)
        flatten_sub(retlist, cur_list, rest[1:])


def flatten(list_with_sublists: list[list[Any]]) -> list[Any]:
    """
    Take a list with some possible sublists, and return a list of
    lists of flat lists. All possible combinations.

    Example:
        >>> l = [ [1, 2], [3, 4] ]
        >>> flatten(l)
        [ [1, 3], [1, 4], [2, 3], [2, 4] ]
    """
    retval = []
    flatten_sub(retval, [], list_with_sublists)
    return retval


def flatten_dict_sub(retlist: list[Any], cur_dict: dict[Any, Any], main_dict_with_lists: dict[Any, Any], rest_keys: list[Any]):
    if len(rest_keys) == 0:
        retlist.append(cur_dict)
        return

    # pick off the first key and see what it gives us from the dict
    r0 = rest_keys[0]
    rhs = main_dict_with_lists[r0]
    if type(rhs) == list:
        for v in rhs:
            tdict = copy.copy(cur_dict)
            # change the list-valued entry to a scalar-valued entry
            tdict[r0] = v
            flatten_dict_sub(retlist, tdict, main_dict_with_lists, rest_keys[1:])
    else:
        cur_dict[r0] = rhs
        flatten_dict_sub(retlist, cur_dict, main_dict_with_lists, rest_keys[1:])


def flatten_dict(dict_with_lists: dict[Any, Any]) -> list[dict[Any, Any]]:
    """
    Take a dict with some possible sublists, and return a list of
    dicts where no rhs is a list. All possible combinations.

    Example:
        >>> d = { 'a': 1, 'b': [1, 2] }
        >>> flatten_dict(d)
        [{ 'a': 1, 'b': 1 }, { 'a': 1, 'b': 2 }]
    """
    retval = []
    kys = list(dict_with_lists.keys())
    flatten_dict_sub(retval, {}, dict_with_lists, kys)
    return retval

def cmkdir(path_to_dir):
    """Make a directory if it does not exist"""
    if not os.path.exists(path_to_dir):
        msgb("MKDIR", path_to_dir)
        os.makedirs(path_to_dir)


def convert_binary_to_hex(bit_string: str) -> str:
    """convert a bit string to hex string"""
    decimal = 0
    radix = 1
    blist = list(bit_string)
    blist.reverse()
    for bit in blist:
        if bit == '1':
            decimal = decimal + radix
        radix = radix + radix
    hexnum = hex(decimal)
    return hexnum


def decimal_to_binary(i: int) -> list[str]:
    """Take a decimal integer, and return a list of bits MSB to LSB"""
    if i == 0:
        return ['0']
    rev_out = []
    while i > 0:
        bit = i & 1
        # print hex(i),ig, bit
        rev_out.append(str(bit))
        i = i >> 1
    # print str(rev_out)
    rev_out.reverse()
    return rev_out


def hex_to_binary(x: str) -> list[str]:
    """Take a hex number, no 0x prefix required, and return a list of bits MSB to LSB"""
    i = int(x, 16)
    return decimal_to_binary(i)


def stringify_list(lst: list[Any]) -> str:
    return ' '.join([str(x) for x in lst])


def round_up_power_of_two(x: int) -> int:
    lg = math.ceil(math.log(x, 2))
    return 1 << int(lg)


make_numeric_decimal_pattern = re.compile(r'^[-]?[0-9]+$')
make_numeric_hex_pattern = re.compile(r'^0[xX][0-9A-Fa-f]+$')
make_numeric_binary_pattern = re.compile(r'^0b[01_]+$')

make_numeric_old_binary_pattern = re.compile(r"B['](?P<bits>[01_]+)")  # leading "B'"
make_numeric_old_decimal_pattern = re.compile(r'^0m[0-9]+$')  # only base 10 numbers


def make_binary(bits: str) -> str:
    """return a string of 1s and 0s. Could return letter strings as well"""
    # binary numbers must preserve the number of bits. If we are 
    # doing a conversion, then we just go with the number of bits we get.

    if make_numeric_binary_pattern.match(bits):
        # strip off the 0b prefix
        bits = re.sub('_', '', bits)
        return bits[2:]
    # this might return fewer than the expected number of binary bits.
    # for example, if you are in a 4 bit field and use a 5, you will
    # only get 3 bits out. Because this routine is not cognizant of
    # the field width.

    if is_numeric(bits):
        v = make_numeric(bits)
        d = decimal_to_binary(v)  # a list of bits
        return ''.join(d)
    bits = re.sub('_', '', bits)
    return bits


def is_hex(s: str) -> bool:
    if make_numeric_hex_pattern.match(s):
        return True
    return False


def is_numeric(s: str) -> bool:
    if make_numeric_decimal_pattern.match(s):
        return True
    if make_numeric_hex_pattern.match(s):
        return True
    if make_numeric_binary_pattern.match(s):
        return True
    return False


def is_binary(s: str) -> bool:
    if make_numeric_binary_pattern.match(s):
        return True
    return False


def make_numeric(s: str, restriction_pattern=None) -> int:
    if type(s) == int:
        die("Converting integer to integer")
    elif make_numeric_hex_pattern.match(s):
        out = int(s, 16)
    elif make_numeric_binary_pattern.match(s):
        out = int(s, 2)
    elif make_numeric_old_decimal_pattern.match(s):
        die("0m should not occur. Rewrite files!")
    elif make_numeric_old_binary_pattern.match(s):
        die("B' binary specifer should not occur. Rewrite files!")
    else:
        out = int(s)
    return out


#########################

def find_runs(blist: list[str]) -> list[tuple[str, int]]:
    """Accept a bit list. Return a list tuples (letter,count)
   describing bit runs, the same bit repeated n times"""
    last = None
    run = 1
    output: list[tuple[str, int]] = []
    if blist == None:
        return output
    for b in blist:
        if last != None:
            if b == last:
                run = run + 1
            else:
                output.append((last, run))
                run = 1
        last = b
    if last != None:
        output.append((last, run))
    return output


def no_underscores(s: str) -> str:
    v = s.replace('_', '')  # remove underscores
    return v


comment_pattern = re.compile(r'[#].*$')


def no_comments(line: str) -> str:
    global comment_pattern
    oline = comment_pattern.sub('', line)
    oline = oline.strip()
    return oline


def blank_line(line: str) -> bool:
    if line == '':
        return False
    return True


continuation_pattern = re.compile(r'\\$')
def process_continuations(lines: list[str]) -> list[str]:
    global continuation_pattern
    olines: list[str] = []
    while len(lines) != 0:
        line = no_comments(lines[0])
        line = line.strip()
        lines.pop(0)
        if line == '':
            continue
        if continuation_pattern.search(line):
            # combine this line with the next line if the next line exists
            line = continuation_pattern.sub('', line)
            if len(lines) >= 1:
                combined_lines = [line + lines[0]]
                lines.pop(0)
                lines = combined_lines + lines
                continue
        olines.append(line)
    del lines
    return olines


def field_check(obj: Any, field: str) -> bool:
    "Return true if fld exists in obj"

    try:
        # ignore returned value
        s = getattr(obj, field)
        return True
    except AttributeError:
        retval = False

    return retval


def generate_lookup_function_basis(gi, state_space):
    """Return a dictionary whose values are dictionaries of all the values
      that the operand decider might have"""
    argnames = {}  # tokens -> list of all values for that token
    for ii in gi.parser_output.instructions:
        for bt in ii.ipattern.bits:
            if bt.is_operand_decider():
                if bt.token not in argnames:
                    argnames[bt.token] = {}

                if bt.test == 'eq':
                    argnames[bt.token][bt.requirement] = True
                elif bt.test == 'ne':
                    all_values_for_this_od = state_space[bt.token]
                    trimmed_vals = list(filter(lambda x: x != bt.requirement,
                                               all_values_for_this_od))
                    for tv in trimmed_vals:
                        argnames[bt.token][tv] = True
                else:
                    die("Bad bit test (not eq or ne) in " + ii.dump_str())
            elif bt.is_nonterminal():
                pass  # FIXME make a better test
            else:
                die("Bad patten bit (not an operand decider) in " + ii.dump_str())
    return argnames


def uniqueify(values: list) -> list:
    return sorted(list(set(values)))


def is_stringish(x: Any) -> bool:
    return isinstance(x, bytes) or isinstance(x, str)


def make_list_of_str(lst: list[Any]) -> list[str]:
    return [str(x) for x in lst]


def open_readlines(file_name: str) -> list[str]:
    return open(file_name, 'r').readlines()
