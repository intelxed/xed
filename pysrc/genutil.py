#-*- python -*-
# Mark Charney <mark.charney@intel.com>
# Generic utilities
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
import math
import traceback
#import types
import copy
import re
import stat
import platform

psystem = platform.system()
if (psystem == 'Microsoft' or
    psystem == 'Windows' or
    psystem.find('CYGWIN') != -1) :
    on_windows = True
else:
    on_windows = False

if not on_windows:
    import resource

def msgerr(s):
    "Write to stderr"
    sys.stderr.write("%s\n" % s)

msgout = sys.stdout
def set_msgs(fp):
    global msgout
    msgout = fp

def msge(s):
    "Write to msgout"
    msgout.write("%s\n" % s)
def msg(s):
    "Write to msgout"
    msgout.write("%s\n" % s)
def msgn(s):
    "Write to msgout"
    msgout.write(s)
def msgb(s,t=''):
    "Write to msgout"
    msgout.write('[%s] %s\n' % (s,t))

def cond_die(v, cmd, msg):
    if v != 0:
        s = msg + '\n  [CMD] ' + cmd
        die(s)

import pdb
_debugging = False

def activate_debugger():
    global _debugging
    _debugging = True
    pdb.set_trace()
    
def die(m):
    global _debugging
    msgerr('[ERROR] ' + m)
    if _debugging:
        pdb.set_trace()
    else:        
        traceback.print_stack()
    sys.exit(1)
def warn(m):
    msgerr('[WARNING] ' + m)


def check_python_version(argmaj, argmin):
    tup = sys.version_info
    major = tup[0]
    minor = tup[1]
    if ( (major > argmaj ) or 
         (major == argmaj and minor >= argmin) ):
        return 
    die('Need Python version %d.%d or later.' % (argmaj, argmin))
    
def make_readable_by_all_writeable_by_owner(fn, errorname=''):
    try:
        rwx = stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH
        os.chmod(fn, rwx)
    except IOError:
        die('Could not chmod: ' + errorname + ' file: [' + fn  + ']' )

def open_for_writing(mode):
  # The default mode is 'r'.
  mode = mode or 'r'
  for c in mode:
    if c in ['w', 'a', '+']:
      return True
  return False

def base_open_file(fn, rw, errorname=''):
    try:
        fp = open(fn,rw)
    except IOError:
        die('Could not open: ' + errorname + ' file: [' + fn  + ']' )
    if open_for_writing(rw):
      make_readable_by_all_writeable_by_owner(fn,errorname)
    return fp

def resource_usage():
    if on_windows:
        x  = (0,0,0,0,0,0)
    else:
        x = resource.getrusage(resource.RUSAGE_SELF)
    return x

def format_resource_usage(x):
    s = ''
    s += 'user: ' + str(x[0])
    s += ' sys: ' + str(x[1])
    # These don't work on linux
    #s += ' maxrss: ' + str(x[2])
    #s += ' maxshd: ' + str(x[3])
    #s += ' maxprv: ' + str(x[4])
    #s += ' maxstk: ' + str(x[5])
    return s

def get_memory_usage():
    """Return a tuple of (vmsize, vmrss, vmdata) on linux systems with
    /proc filesystems."""
    try:
        lines = open('/proc/%s/status' % os.getpid(),'r').readlines()
        pairs = [ x.split(':') for x in lines]
        dct = dict(pairs)
        return (dct['VmSize'].strip(), dct['VmRSS'].strip(),  dct['VmData'].strip())
    except:
        return (0,0,0)
   
def print_resource_usage(i=''):
    # 2014-05-19: disabled for now.
    return

    x = resource_usage()
    s = format_resource_usage(x)
    mem = get_memory_usage()
    msge('RUSAGE: %s %s vmsize: %s' % (str(i), str(s), str(mem[0])))
    


def flatten_sub(retlist,cur_list,rest):
    if len(rest)==0:
        retlist.append(cur_list)
        return
        
    r0 = rest[0]
    if type(r0) == list:
        for v in r0:
            tlist = copy.copy(cur_list)
            tlist.append(v)
            flatten_sub(retlist,tlist,rest[1:])
    else:
        cur_list.append(r0)
        flatten_sub(retlist,cur_list,rest[1:])
    

def flatten(list_with_sublists):
    """Take a list with some possible sublists, and return a list of
    lists of flat lists. All possible combinations."""
    retval = []
    flatten_sub(retval, [], list_with_sublists)
    return retval


def flatten_dict_sub(retlist,cur_dict,main_dict_with_lists,rest_keys):
    if len(rest_keys)==0:
        retlist.append(cur_dict)
        return

    # pick off the first key and see what it gives us from the dict
    r0 = rest_keys[0]
    rhs = main_dict_with_lists[r0]
    if type(rhs) == list:
        for v in rhs:
            tdict = copy.copy(cur_dict)
            # change the list-valued entry to a scalar-valued entry
            tdict[r0]=v 
            flatten_dict_sub(retlist,tdict,main_dict_with_lists,rest_keys[1:])
    else:
        cur_dict[r0] = rhs
        flatten_dict_sub(retlist,cur_dict,main_dict_with_lists,rest_keys[1:])
    

def flatten_dict(dict_with_lists):
    """Take a dict with some possible sublists, and return a list of
    dicts where no rhs is a list. All possible combinations"""
    retval = []
    kys = list(dict_with_lists.keys())
    flatten_dict_sub(retval, {}, dict_with_lists,kys)
    return retval

def cmkdir(path_to_dir):
    """Make a directory if it does not exist"""
    if not os.path.exists(path_to_dir):
        msgb("MKDIR", path_to_dir)
        os.makedirs(path_to_dir)



def convert_binary_to_hex(b):
   "convert a bit string to hex"
   decimal = 0
   radix = 1
   blist = list(b)
   blist.reverse()
   for bit in blist:
      if bit == '1':
         decimal = decimal + radix
      radix = radix + radix
   hexnum = hex(decimal)
   return  hexnum
   
def decimal_to_binary(i):
   "Take a decimal integer, and return a list of bits MSB to LSB"
   if i == 0:
      return [ '0' ]
   rev_out = []
   while i > 0:
      bit = i & 1
      #print hex(i),ig, bit
      rev_out.append(str(bit))
      i = i >> 1
   #print str(rev_out)
   rev_out.reverse()
   return rev_out

def hex_to_binary(x):
   "Take a hex number, no 0x prefix required, and return a list of bits MSB to LSB"
   i = int(x,16)
   return decimal_to_binary(i)

def stringify_list(lst):
    return ' '.join([ str(x) for x in lst])

def round_up_power_of_two(x):
   lg = math.ceil(math.log(x,2))
   return 1 << int(lg)



make_numeric_decimal_pattern = re.compile(r'^[-]?[0-9]+$')
make_numeric_hex_pattern = re.compile(r'^0[xX][0-9A-Fa-f]+$')
make_numeric_binary_pattern = re.compile(r'^0b[01_]+$') 

make_numeric_old_binary_pattern = re.compile(r"B['](?P<bits>[01_]+)") #   leading "B'"
make_numeric_old_decimal_pattern = re.compile(r'^0m[0-9]+$') # only base 10 numbers

def make_binary(bits):
    "return a string of 1s and 0s. Could return letter strings as well"
    # binary numbers must preserve the number of bits. If we are 
    # doing a conversion, then we just go with the number of bits we get.

    if make_numeric_binary_pattern.match(bits):
        # strip off the 0b prefix
        bits = re.sub('_','',bits)
        return bits[2:]
    # this might return fewer than the expected number of binary bits.
    # for example, if you are in a 4 bit field and use a 5, you will
    # only get 3 bits out. Because this routine is not cognizant of
    # the field width.

    if numeric(bits):
        v = make_numeric(bits)
        d = decimal_to_binary(v) # a list of bits
        return ''.join(d)
    bits = re.sub('_','',bits)
    return bits

def is_hex(s):
    if make_numeric_hex_pattern.match(s):
        return True
    return False

def numeric(s):
    if make_numeric_decimal_pattern.match(s):
        return True
    if make_numeric_hex_pattern.match(s):
        return True
    if make_numeric_binary_pattern.match(s):
        return True
    return False

def is_binary(s):
    if make_numeric_binary_pattern.match(s):
        return True
    return False

def make_numeric(s, restriction_pattern=None):
   global make_numeric_old_decimal_pattern
   global make_numeric_hex_pattern
   global make_numeric_binary_pattern
   global make_numeric_old_binary_pattern
   
   if type(s) == int:
       die("Converting integer to integer")
   elif make_numeric_hex_pattern.match(s):
       out = int(s,16)
   elif make_numeric_binary_pattern.match(s):  
       # I thought that I could leave the '0b' prefix. Python >= 2.6
       # handles '0b' just fine but Python 2.5 cannot.  As of
       # 2012-06-20 the pin team currently still relies upon python
       # 2.5.
       just_bits = s.replace('0b','')
       just_bits = just_bits.replace('_','')
       out = int(just_bits,2)
       #msgb("MAKE BINARY NUMERIC", "%s -> %d" % (s,out))
   elif make_numeric_old_decimal_pattern.match(s):
       sys.stderr.write("0m should not occur. Rewrite files!")
       sys.exit(1)
   elif make_numeric_old_binary_pattern.match(s): 
       sys.stderr.write("B' binary specifer should not occur. Rewrite files!")
       sys.exit(1)
   else:
       out = int(s)
   return out


#########################

def find_runs(blist):
   """Accept a bit list. Return a list tuples (letter,count)
   describing bit runs, the same bit repeated n times"""
   last = None
   run = 1
   output = []
   if blist == None:
      return output
   for b in blist:
      if last != None:
         if b == last:
            run = run + 1
         else:
            output.append( (last, run) )
            run = 1
      last = b
   if last != None:
      output.append( (last, run)  )
   return output

def print_runs(runs):
   s = []
   for (val, count)  in runs:
      s.append("(%s,%d)" % (val,count))
   msge("Runs: %s" % ' '.join(s) )

def no_underscores(s):
    v = s.replace('_','') # remove underscores
    return v

comment_pattern = re.compile(r'[#].*$')
def no_comments(line):
   global comment_pattern
   oline = comment_pattern.sub('',line)
   oline = oline.strip()
   return oline

def blank_line(line):
   if line == '':
      return False
   return True

continuation_pattern = re.compile(r'\\$')
def process_continuations(lines):
   global continuation_pattern
   olines=[]
   while len(lines) != 0:
      line = no_comments(lines[0])
      line = line.strip()
      lines.pop(0)
      if line == '':
          continue
      if continuation_pattern.search(line):
          # combine this line with the next line if the next line exists
          line = continuation_pattern.sub('',line)
          if len(lines) >= 1:
              combined_lines = [ line + lines[0] ]
              lines.pop(0)
              lines = combined_lines + lines
              continue
      olines.append(line)
   del lines
   return olines

def skip_junk(lines):
   while len(lines) != 0:
      line = no_comments(lines[0])
      line = line.strip()
      if line == '':
         lines.pop(0)
      else:
         break
   return lines
def field_check(obj,fld):
   "Return true if fld exists in obj"

   try:
      # ignore returned value
      s = getattr(obj,fld)
      return True
   except AttributeError:
      retval = False

   return retval
def generate_lookup_function_basis(gi,state_space):
   """Return a dictionary whose values are dictionaries of all the values
      that the operand decider might have"""
   argnames = {}  # tokens -> list of all values for that token 
   for ii in gi.parser_output.instructions:
      for bt in ii.ipattern.bits:
         if bt.is_operand_decider():
            if bt.token not in argnames:
               argnames[bt.token] = {}

            if bt.test == 'eq':
               argnames[bt.token][bt.requirement]=True
            elif bt.test == 'ne':
               all_values_for_this_od = state_space[bt.token]
               trimmed_vals = list(filter(lambda x: x != bt.requirement,
                                     all_values_for_this_od))
               for tv in trimmed_vals:
                  argnames[bt.token][tv]=True
            else:
               die("Bad bit test (not eq or ne) in " + ii.dump_str())
         elif bt.is_nonterminal():
            pass # FIXME make a better test
         else:
            die("Bad patten bit (not an operand decider) in " + ii.dump_str())
   return argnames

def uniqueify(values):
   s = {}
   for a in values:
      s[a] = True
   k = list(s.keys())
   k.sort()
   return k


def is_stringish(x):
   return isinstance(x,bytes) or isinstance(x,str) 
def make_list_of_str(lst):
   return [ str(x) for x in lst]
def open_readlines(fn):
   return open(fn,'r').readlines()
           
