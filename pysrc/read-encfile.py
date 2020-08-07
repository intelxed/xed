#!/usr/bin/env python
#  Read the encode format files
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2020 Intel Corporation
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

# There are dictionaries of nonterminals and sequencers. The
# sequencers are ordered lists of nonterminals. The nonterminals
# consist of rule_t's. Each rule has conditions and actions.  An
# action can be a simple bit encoding or it can be a binding of a
# value to a field. A condition contains a list of or'ed condtion_t's
# and a list of and'ed condition_t's. When all the and'ed conditions
# are satisfied and one of the or'ed conditions (if any) are
# satisfied, then the action should occur. The conditions are field
# values that are = or != to a right hand side. The right hand side
# could be a value or a nonterminal (NTLUF really). Also the field
# name could be bound to some bits that are used in the action, using
# square brackets after the name.



import re
import sys
import os
import optparse
import stat
import copy

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

mbuild_install_path = os.path.join(os.path.dirname(sys.argv[0]), 
                                   '..', '..', 'mbuild')

if not os.path.exists(mbuild_install_path):
    mbuild_install_path =  find_dir('mbuild')
sys.path=  [mbuild_install_path]  + sys.path
try:
   import mbuild
except:

   sys.stderr.write("\nERROR(read-encfile.py): Could not find mbuild." + 
                    " Should be a sibling of the xed2 directory.\n\n")
   sys.exit(1)

xed2_src_path = os.path.join(os.path.dirname(sys.argv[0]))
if not os.path.exists(xed2_src_path):
    xed2_src_path =  find_dir('xed2')
sys.path=  [xed2_src_path]  + sys.path
sys.path=  [ os.path.join(xed2_src_path,'pysrc') ]  + sys.path

try:
    from codegen import *
    from genutil import *
    from scatter import *
    from verbosity import *
    import slash_expand
    import operand_storage
    import nt_func_gen
    import map_info_rdr
    import chipmodel
except:
   sys.stderr.write("\nERROR(read-encfile.py): Could not find " + 
                    "the xed directory for python imports.\n\n")
   sys.exit(1)
   
import actions
import ins_emit
import encutil
from patterns import *

storage_fields = {}
def outreg():
    return operand_storage.get_op_getter_full_func('outreg',
                                                   encutil.enc_strings)
def error_operand():
    return operand_storage.get_op_getter_full_func('error',encutil.enc_strings)

xed_encoder_request = "xed_encoder_request_t"

output_file_emitters = []

def _vmsgb(s,b=''):
    if vencode():
        mbuild.msgb(s,b)

def make_writable(fn):
    """Make the file or directory readable/writable/executable by me"""
    _rwx_by_me         =  stat.S_IWUSR| stat.S_IRUSR|stat.S_IXUSR
    os.chmod(fn, _rwx_by_me)

def remove_file(fn):
    """Remove a file if it exists."""
    if os.path.exists(fn):
       _vmsgb("Removing ", fn)
       make_writable(fn)
       os.unlink(fn)

    
    

       
class blot_t(object):
    """A blot_t is  make a fragment of a decoder pattern"""
    def __init__(self,type=None):
        self.type = type  # 'bits', 'letters', 'nt', "od" (operand decider)
        self.nt = None    # name of a nonterminal
        self.value = None # integer representing this blot_t's value
        self.length = 0   # number of bits for this blot_t
        self.letters = None # sequence of substitution letters for this blot. All must be the same letter
        self.field_name = None # name of the operand storage field that has the values for this blot-t
        self.field_offset = 0 # offset within the field
        self.od_equals = None

    def make_action_string(self):
        """
        @rtype: string or None
        @returns: string if the blot is something we want to make in to an action
        """
        if vblot():
            msgb("Making action for blot", str(self) )
        if self.type == 'bits':
            binary = ''.join(decimal_to_binary(self.value))
            if vblot():
                msgb("CONVERT", "%s <-- %s" % ( binary, str(self)))
            blen = len(binary)
            if blen < self.length:
                # pad binary on the left with 0's until it is self.length bits long
                need_zeros = self.length - blen
                #msgerr("Padding with %d zeros" % need_zeros)
                binary = "%s%s" % ('0'*need_zeros , binary)
                blen = len(binary)
            if blen > self.length:
                die("bit length problem in %s --- %s" % (str(self), binary))
            if self.field_name:
                return "%s[0b%s]" % (self.field_name,binary)
            return "0b%s" % binary
        
        elif self.type == 'letters':
            return "%s[%s]" % (self.field_name,self.letters)
        elif self.type == 'od':
            if self.od_equals == False:
                #return "%s!=0x%x" % (self.field_name, self.value) #EXPERIMENT 2007-08-07
                if vignoreod():
                    msgerr("Ignoring OD != relationships in actions: %s" % str(self))
                return None
            return "%s=0x%x" % (self.field_name, self.value)
        elif self.type == 'nt':
            return "%s()" % self.nt
        else:
            die("Unhandled type: %s" % self.type)

    def __str__(self):
        s = []
        if self.type:
            s.append("%8s" % self.type)
        else:
            s.append("%8s" % "no-type")
        if self.nt:
            s.append("nt: %s" % self.nt)
        if self.field_name:
            s.append("field_name: %s" % self.field_name)

        if self.od_equals != None:
            if self.od_equals:
                v = '='
            else:
                v = '!='
            s.append(v)
        if self.type == 'letters':
            s.append( "".join(self.letters) )
        if self.value != None:
            s.append("0x%x" % self.value) # print as HEX
            s.append("(raw %s)" % self.value)
        if self.nt == None and self.od_equals == None:
            s.append("length: %d" % self.length)
            s.append("field_offset: %d" % self.field_offset)
        return ' '.join(s)
    
class operand_t(object):
    """These are main ISA (decode) operands being used for encode
    conditions. They are either individual tokens or X=y bindings. The
    tokens or RHS of bindings can have qualifiers separated by colons:
    (1) r/w/rw/cr/crcw/rcw/cw, (2) EXPL, IMPL, SUPP or ECOND, (3)
    length-code. The EXPL/IMPL/SUPP/ECOND is optional as is the length
    code. Memops must have the length code."""

    convert_pattern = re.compile(r'TXT=(?P<rhs>[0-9A-Za-z_]+)')
    
    def __init__(self,s):
        pieces=s.split(':')
        op_or_binding = pieces[0]
        self.lencode = '?'
        self.vis = None
        explicit_vis = None
        self.rw = '?'
        self.type = None # 'token', 'binding', 'ntluf'
        if len(pieces) >= 2:
            nxt= pieces[1]
            if nxt in [ 'IMPL', 'SUPP','EXPL', 'ECOND']:
                explicit_vis = nxt
            else:
                self.rw = pieces[1]
            if len(pieces) >= 3:
                for p in pieces[2:]:
                    cp=operand_t.convert_pattern.match(p)
                    if cp:
                        cvt = cp.group('rhs') # ignored
                    elif p in [ 'IMPL', 'SUPP', 'EXPL', 'ECOND']:
                        explicit_vis = p
                    elif self.lencode == '?':
                        self.lencode = p
                    else:
                        _vmsgb("Ignoring [%s] from %s" % (p,s))
                        #die("Unhandled operand: %s" % s)

        self.value = None
        self.ntluf = False
        ap = equals_pattern.match(op_or_binding)
        if ap:       # binding
            (self.var,self.value) = ap.group('lhs','rhs')
            ntluf_match = nt_name_pattern.match(self.value)
            if ntluf_match:
                self.value = ntluf_match.group('ntname')
                self.ntluf = True
                self.type = 'ntluf'
            else:
                self.type = 'binding'
        else:        # operand (MEM/IMM/DISP/etc.)
            self.var = op_or_binding
            self.type = 'token'

        if explicit_vis:
            self.vis = explicit_vis
        else:
            default_vis = storage_fields[self.var].default_visibility
            if default_vis == 'SUPPRESSED':
                self.vis = 'SUPP'
            elif default_vis == 'EXPLICIT':
                self.vis = 'EXPL'
            elif default_vis == 'ECOND':
                self.vis = 'ECOND'
            else:
                die("unhandled default visibility: %s for %s" % (default_vis, self.var))
            
    def make_condition(self):
        """
        @rtype: condition_t or None
        @return: list of conditions based on this operand """
        # ignore suppressed operands in encode conditions
        if self.vis == 'SUPP':
            return None

        # make s, a string from which we manufacture a condition_t
        if self.type == 'binding':
            if letter_pattern.match(self.value):
                # associate the field with some letters
                s = "%s[%s]=*" % (self.var, self.value)
            else:
                s = "%s=%s" % (self.var, self.value)
        elif self.type  == 'token':
            s = "%s=1" % (self.var) # FIXME need to specify memop widths
        elif self.type == 'ntluf':
            s = "%s=%s()" % (self.var,self.value)
        else:
            die("Unhandled condition: %s" % str(self))
        #msgerr("MAKE COND %s" % s)
        c = condition_t(s)

        #msgerr("XCOND type: %s var: %s lencode: %s" % (self.type, self.var, str(self.lencode)))
        # FIXME: THIS IS A DISGUSTING HACK
        if self.type == 'token' and self.var == 'MEM0':
            # add a secondary condition for checking the width of the memop.
            #
            #  NOTE: this MEM_WIDTH is not emitted! It is used in
            #  xed_encoder_request_t::memop_compatible()
            c2 = condition_t('MEM_WIDTH',self.lencode) # MEM_WIDTH
            #msgerr("\tRETURNING LIST WITH MEM_WIDTH")
            return [c, c2]
        return [c]
    
    def __str__(self):
        if self.vis == 'EXPL':
            pvis = ''
        else:
            pvis = ":%s" % self.vis

        if self.lencode == '?':
            plen = ''
        else:
            plen = ":%s" % self.lencode

        if self.rw == '?':
            prw = ''
        else:
            prw = ":%s" % self.rw
        
        if self.value:
            if self.ntluf:
                parens = '()'
            else:
                parens = ''
            return  "%s=%s%s%s%s%s" % ( self.var, self.value, parens, prw, plen, pvis)
        return  "%s%s%s%s" % ( self.var, prw, plen, pvis)
        

class rvalue_t(object):
    """The right hand side of an operand decider equation. It could be
    a value, a NTLUF, a * or an @. 
    For thing that are bits * means any value.  
    A @ is shorthand for ==XED_REG_INVALID"""
    def __init__(self, s):
        self.string = s
        m = nt_name_pattern.search(s)
        if m:
            self.nt = True
            self.value = m.group('ntname')
        else:
            self.nt = False
            if decimal_pattern.match(s) or binary_pattern.match(s):
                #_vmsgb("MAKING NUMERIC FOR %s" %(s))
                self.value = str(make_numeric(s))
            else:
                #_vmsgb("AVOIDING NUMERIC FOR %s" %(s))
                self.value = s
            
    def nonterminal(self):
        """Returns True if this rvalue is a nonterminal name"""
        return self.nt
    
    def null(self):
        if self.value == '@':
            return True
        return False
    def any_valid(self):
        if self.value == '*':
            return True
        return False
    def __str__(self):
        s =  self.value
        if self.nt:
            s += '()'
        return s
    
        
class condition_t(object):
    """ xxx[bits]=yyyy or xxx=yyy or xxx!=yyyy. bits can be x/n where
    n is a repeat count.  Can also be an 'otherwise' clause that is
    the final action for a nonterminal if no other rule applies.
    """
    def __init__(self, s, lencode=None, chip_check=None):
        #_vmsgb("examining %s" % s)
        self.string = s
        self.bits = None # bound bits
        self.rvalue = None
        self.equals = None
        self.lencode = lencode # for memory operands
        self.chip_check = chip_check
        
        b = bit_expand_pattern.search(s)
        if b:
            expanded = b.group('bitname') * int(b.group('count'))
            ss = bit_expand_pattern.sub(expanded,s)
        else:
            ss = s
        rhs = None
        e= equals_pattern.search(ss)
        if e:
            #_vmsgb("examining %s --- EQUALS" % s)
            raw_left_side = e.group('lhs')
            lhs = lhs_capture_pattern.search(raw_left_side)
            self.equals = True
            rhs = e.group('rhs')
            self.rvalue = rvalue_t(rhs)
            #_vmsgb("examining %s --- EQUALS rhs = %s" % (s,str(self.rvalue)))
  
        else:
            ne = not_equals_pattern.search(ss)
            if ne:
                raw_left_side = ne.group('lhs')
                lhs = lhs_capture_pattern.search(raw_left_side)
                self.equals = False
                self.rvalue = rvalue_t(ne.group('rhs'))
            else:
                # no equals or not-equals... just a binding. assume "=*"
                raw_left_side = ss
                #msgerr("TOKEN OR  BINDING %s" % (raw_left_side))
                            
                lhs = lhs_capture_pattern.search(raw_left_side)
                self.equals = True
                self.rvalue = rvalue_t('*')

        # the lhs is set if we capture bits for an encode action
        
        if lhs:
            self.field_name = lhs.group('name')
            self.bits = lhs.group('bits')
        else:
            #_vmsgb("examining %s --- NO LHS" % (s))
            self.field_name = raw_left_side
            if self.is_reg_type() and self.rvalue.any_valid():
                die("Not supporting 'any value' (*) for reg type in: %s" % s)
            if self.is_reg_type() and self.equals == False:
                die("Not supporting non-equal sign for reg type in: %s" % s)
            
            # Some bit bindings are done like "SIMM=iiiiiiii" instead
            # of "MOD[mm]=*". We must handle them as well. Modify the captured rvalue
            if rhs and self.equals:
                rhs_short = no_underscores(rhs)
                if letter_pattern.match(rhs_short):
                    #msgerr("LATE LETTER BINDING %s %s" % (raw_left_side, str(self.rvalue)))
                    self.bits = rhs_short
                    del self.rvalue
                    self.rvalue = rvalue_t('*')
                    return
                    
            #msgerr("NON BINDING  %s" % (s)) # FIXME: what reaches here?

    def contains(self, s):
        if self.field_name == s:
            return True
        return False
    
    def capture_info(self):
        # FIXME: could locally bind bit fields in capture region to
        # avoid redundant calls to xes.operands().
        return ( operand_storage.get_op_getter_full_func(self.field_name,
                                                         encutil.enc_strings),
                                                         self.bits )

    def is_bit_capture(self):
        """Binding an OD to some bits"""
        if self.bits != None:
            return True
        return False

    def is_otherwise(self):
        """Return True if this condition is an 'otherwise' final
        condition."""
        if self.field_name == 'otherwise':
            return True
        return False
    
    def is_reg_type(self):
        if self.field_name not in storage_fields:
            return False 
        ctype = storage_fields[self.field_name].ctype
        return ctype == 'xed_reg_enum_t'
        
    def __str__(self):
        s = [ self.field_name ]
        if self.chip_check:
            s.append(" (CHIPCHECK {})".format(self.chip_check))
        elif self.memory_condition(): # MEM_WIDTH
            s.append(" (MEMOP %s)" % self.lencode)
        if self.bits:
            s.append( '[%s]' % (self.bits))
        if self.equals:
            s.append( '=' )
        else:
            s.append('!=')
        s.append(str(self.rvalue))
        return ''.join(s)
    
    def is_chip_check(self): 
        return self.chip_check != None
    
    def memory_condition(self): # MEM_WIDTH
        if self.lencode != None:
            return True
        return False

    def emit_code(self):
        #msgerr("CONDEMIT " + str(self))
        if self.is_otherwise():
            return "1"
        
        if self.equals:
            equals_string = '=='
        else:
            equals_string = '!='

        #FIXME: get read off this old accessor
        op_accessor = operand_storage.get_op_getter_full_func(self.field_name,
                                                        encutil.enc_strings)
        
        if self.is_chip_check(): 
            s = 'xed_encoder_request_chip_check(xes,{})'.format(self.chip_check)
        elif self.memory_condition(): # MEM_WIDTH
            s = 'xed_encoder_request__memop_compatible(xes,XED_OPERAND_WIDTH_%s)' % (self.lencode.upper())
        elif self.rvalue.nonterminal():
            s = 'xed_encode_ntluf_%s(xes,%s)' % (self.rvalue.value,op_accessor)
        elif self.rvalue.any_valid():
            if storage_fields[self.field_name].ctype == 'xed_reg_enum_t':
                # FOO=* is the same as FOO!=XED_REG_INVALID. So we
                # invert the equals sign here.
                if self.equals:
                    any_equals = "!="
                else:
                    any_equals = "=="
                s = "(%s %s XED_REG_INVALID)" % (op_accessor,any_equals)
            else:
                s = '1'
                
        elif self.rvalue.null():
            s = "(%s %s XED_REG_INVALID)" % (op_accessor,equals_string)
        else: # normal bound value test
            if self.rvalue.value == 'XED_REG_ERROR':
                s = '0'
            else:
                #msgerr("CONDEMIT2 " + str(self) + " -> " + self.rvalue.value)
                s = "(%s %s %s)" % (op_accessor,equals_string,
                                    self.rvalue.value)
        return s
        
        
class conditions_t(object):
    """list of condition_t objects that get ANDed together""" 
    def __init__(self):
        self.and_conditions = []
    def contains(self,s):
        for c in self.and_conditions:
            if c.contains(s):
                return True
        return False
            
    def and_cond(self, c):
        if is_stringish(c):
            nc = condition_t(c)
        else:
            nc = c
        self.and_conditions.append(nc)

    def has_otherwise(self):
        for a in self.and_conditions:
            if a.is_otherwise():
                return True
        return False
    
    def __str__(self):
        s = []
        for a in self.and_conditions:
            s.append(str(a))
            s.append(' ')
        return ''.join(s)

    def _captures_from_list(self, clist):
        """
        @type clist: list of condition_t
        @param clist: list of condition_t
        
        Return a list of tuples (fieldname, bits) for use by code
        generation (emit actions), by searching the conditions to see
        which ones are captures"""
        if vcapture():
            msgb("CAPTURE COLLECTION USING:\n\t%s\n" % "\n\t".join( [ str(x) for x in clist] ))
        full_captures = list(filter(lambda x: x.is_bit_capture(), clist))
        captures = [  x.capture_info() for x in full_captures]
        return captures
    
    def compute_field_capture_list(self):
        """Study the conditions and return a list of tuples
        (fieldname, bits) for use by code-emit actions, by searching
        the conditions to see which ones are captures"""

        captures = self._captures_from_list(self.and_conditions) 
        return captures

    def emit_code(self):
        if len(self.and_conditions) == 1:
            if self.and_conditions[0].is_otherwise():
                return [ 'conditions_satisfied = 1;' ]
            
        # conditions_satisfied = f1 && f2 && f3
        #
        # if conditions are operand deciders we just do the test.
        # if conditions are NTLUFs then we must see if the name is in
        # the set defined by the NTLUF.  For example, BASE0=ArAX(). If
        # BASE0 is rAX then we are and the corresponding subexpression
        # should be True.

        s = ['conditions_satisfied = ' ]
        emitted = False
        if len(self.and_conditions) == 0:
            # no conditions. that's okay. encoder's job is simple in this case...
            s.append('1')
            emitted = True
        elif (len(self.and_conditions) == 1 and
              self.and_conditions[0].field_name == 'ENCODER_PREFERRED'):
            s.append('1')
            emitted = True
        else:
            first_and = True
            for and_cond in self.and_conditions:
                if and_cond.field_name == 'ENCODER_PREFERRED':
                    continue
                try:
                    t = and_cond.emit_code()
                    if t != '1':
                        if first_and:
                            first_and = False
                        else:
                            s.append( ' &&\n\t\t ')
                        emitted = True
                        s.append( t )
                except:
                    die("Could not emit code for condition %s of %s" % 
                        (str(and_cond), str(self))  )
        if not emitted:
            s.append('1')
            
        s.append(';')
        return [ ''.join(s) ]
    

class iform_builder_t(object):
    '''Remember nonterminal names. Emit a structure/type with a u32 for
       each NT.  These x_WHATEVER fields are filled in during the
       value-binding phase of encoding. They hold the result of
       NT-table evaluation. For instructions, those become the encoder
       iform numbers. But for everything else it is a misnomer.'''
    def __init__(self):
        self.iforms = {}         
    def remember_iforms(self,ntname):
        if ntname not in self.iforms:
            self.iforms[ntname] = True
    def _build(self):
        self.cgen = c_class_generator_t("xed_encoder_iforms_t", var_prefix="x_")
        for v in self.iforms.keys():
                self.cgen.add_var(v, 'xed_uint32_t', accessors='none')
    def emit_header(self):
        self._build()
        return self.cgen.emit_decl()


iform_builder = iform_builder_t() # FIXME GLOBAL

class rule_t(object):
    """The encoder conditions -> actions. These are stored in nonterminals."""
    def __init__(self, conditions, action_list, nt):
        """
        @type conditions: conditions_t
        @param conditions: a conditions_t object specifying the encode conditions
        
        @type action_list: list of strings/action_t
        @param action_list: list of actions can string or action_t obj.
        
        @type nt: string
        @param nt: the nt which this rule is belong to 
        """
        _vmsgb("MAKING RULE", "%s - > %s" % (str(conditions), str(action_list)))
        self.default = False    #indicates whether this rule is a default rule
        self.nt = nt
        self.index = 0  #index is used to identify the correct emit order 
        self.conditions = self.handle_enc_preferred(conditions)
        self.actions = [] 
        
        for action in action_list:
            if is_stringish(action):
                self.actions.append(actions.action_t(action))
            else:
                self.actions.append(action)
    
    def __str__(self):
        s = [ str(self.conditions) , " ->\t" ]
        first = True
        for a in self.actions:
            if first:
                first=False
            else:
                s.append(" \t")
            s.append(str(a))
        return ''.join(s)
    
    def handle_enc_preferred(self,conditions):
        ''' remove the ENCODER_PREFERRED constraint and replace it with 
        an attribute  '''
        for cond in conditions.and_conditions:
            if cond.field_name == "ENCODER_PREFERRED":
                self.enc_preferred = True
                conditions.and_conditions.remove(cond)
            
            else:
                self.enc_preferred = False
        return conditions    
            
    def compute_field_capture_list(self):
        """Look at the conditions and return a list of tuples
        (fieldname, bits) for use by code generation, by searching the
        conditions to see which one s are captures"""
        
        # 2009-02-08: using the bind-phase test conditions is wrong,
        # as we do not need to test all the bindings.

        return self.conditions.compute_field_capture_list()

    def prepare_value_for_emit(self, a):
        """@return: (length-in-bits, value-as-hex)"""
        if a.emit_type == 'numeric':
            v = hex(a.int_value)
            return (a.nbits, v) # return v with the leading 0x
        s = a.value
        if hex_pattern.match(s):
            return ((len(s)-2)*4, s) #hex nibbles - 0x -> bytes
        s_short = no_underscores(s)
        if bits_pattern.match(s_short): # ones and zeros
            return (len(s_short), hex(int(s_short,2)))
        die("prepare_value_for_emit: Unhandled value [%s] for rule: [%s]" %(s,str(self)))

    def uses_bit_vector(self):
        """For encoding multiple prefixes, we need to stash multiple values in the IFORM. This is the key."""
        for a in self.actions:
            if a.is_field_binding():
                if a.field_name == 'NO_RETURN': # FIXME: check value ==1?
                    return True
        return False
    
    def has_nothing_action(self):
        for a in self.actions:
            if a.is_nothing():
                return True
        return False

    def has_error_action(self):
        for a in self.actions:
            if a.is_error():
                return True
            elif a.is_field_binding() and a.field_name == 'ERROR':
                return True
        return False
    
    def has_emit_action(self):
        for a in self.actions:
            if a.is_emit_action():
                return True
        return False
    def has_nonterminal_action(self):
        for a in self.actions:
            if a.is_nonterminal():
                return True
        return False

    def has_naked_bit_action(self):
        for a in self.actions:
            if a.naked_bits():
                return True
        return False
   

    def has_no_return_action(self):
        for a in self.actions:
            if a.is_field_binding():
                # for repeating prefixes, we have the NO_RETURN field.
                if a.field_name == 'NO_RETURN': # FIXME: check value ==1?
                    return True
        return False

    def has_otherwise_rule(self):
        if self.conditions.has_otherwise():
            return True
        return False
    
    def get_nt_in_cond_list(self):
        #returns the condition with nt, if exists
        nts = []
        for cond in self.conditions.and_conditions:
            rvalue = cond.rvalue
            if rvalue.nonterminal():
                nts.append(cond)
        
        if len(nts) == 0:
            return None
        if len(nts) == 1:
            return nts[0]
        error = ("the rule %s has more than one nt in the" +
             "condition list, we do not support it currently") % str(self)
        die(error)

    def emit_isa_rule(self, ith_rule, group):
        ''' emit code for INSTRUCTION's rule:
            1. conditions.
            2. set of the encoders iform index.
            3. call the field binding pattern function to set values to fields. 
            4. nonterminal action type.
        '''
        lines = []
        # 1.
        lines.extend( self.conditions.emit_code() )
        lines.append( "if (conditions_satisfied) {")
        real_opcodes = group.get_ith_field(ith_rule, 'real_opcode')
        isa_sets     = group.get_ith_field(ith_rule, 'isa_set')
        lines.append( " // real_opcode {} isa_set {}".format(real_opcodes, isa_sets))
        lines.append( "    okay=1;")
        
        # 2.
        obj_name = encutil.enc_strings['obj_str'] 
        set_iform = 'xed_encoder_request_set_iform_index'
        code = '%s(%s,iform_ids[iclass_index][%d])'
        code = code % (set_iform,obj_name,ith_rule)
        lines.append('    %s;' % code)
        
        # 3.
        get_fb_ptrn = ('    fb_ptrn_function = '+
                       'xed_encoder_get_fb_ptrn(%s);' % obj_name )
        lines.append(get_fb_ptrn)
        #call function that sets the values to the fileid
        lines.append('    (*fb_ptrn_function)(%s);' % obj_name)
        
        # 4.    
        for a in self.actions:
            if a.is_nonterminal():
                lines += a.emit_code('BIND')
        
        lines.append( "    if (okay) return 1;")
        lines.append( "}")
        return lines
        
    def emit_rule_bind(self, ith_rule, nt_name, ntluf):
        lines = []
        #
        # emit code for the conditions and if the conditions are true, do the action
        #
        lines.extend( self.conditions.emit_code() )
        lines.append( "if (conditions_satisfied) {")
        lines.append( "    okay=1;") # 2007-07-03 start okay over again...
        obj_name = encutil.enc_strings['obj_str']
        
        do_return = True
        use_bit_vector = self.uses_bit_vector()
        has_nothing_action = self.has_nothing_action()
        has_error_action = self.has_error_action()
        has_nonterminal_action = self.has_nonterminal_action()        
        has_emit_action = self.has_emit_action()

        # NESTED FUNCTION!
        def emit_code_bind_sub(a,lines, do_return):
            #msgerr("Codegen for action %s" % str(a))
            if a.is_field_binding():
                # for repeating prefixes, we have the NO_RETURN field.
                if a.field_name == 'NO_RETURN': # FIXME: could check bound value == 1.
                    do_return = False
            lines.extend( a.emit_code('BIND') )
            return do_return

        
        # first do the non nonterminals    
        for a in self.actions:
            if not a.is_nonterminal():
                do_return = emit_code_bind_sub(a, lines, do_return)

        # do the nonterminals after everything else
        for a in self.actions:
            if a.is_nonterminal():
                do_return = emit_code_bind_sub(a, lines, do_return)
            
        #here we are setting the enc iform ordinal 
        if (has_emit_action or has_nonterminal_action) and \
          not has_error_action:
            # We do not set the iform for the "nothing" actions.
            if not has_nothing_action:
                if use_bit_vector:
                    code = 'xed_encoder_request_iforms(%s)->x_%s |=(1<<%d)'
                    code = code % (obj_name,nt_name,ith_rule)
                    lines.append( '    %s;' % code)
                else:
                    code = 'xed_encoder_request_iforms(%s)->x_%s=%d'
                    code = code % (obj_name,nt_name,ith_rule)
                    lines.append( '    %s;' % code)
                    iform_builder.remember_iforms(nt_name)
        
        if do_return:
            # 2007-07-03 I added the condtional return to allow
            # checking other encode options in the event that a
            # sub-nonterminal (in this case SIMMz) tanks a partially made "BIND" decision.
            lines.append( "    if (okay) return 1;")

        lines.append( "}")
        return lines

    def emit_rule_emit(self, ith_rule_arg, nt_name, captures):
        """Return a list of lines of code for the nonterminal function.

        @type  ith_rule_arg: integer
        @param ith_rule_arg: number of the iform for which  we are emitting code.
        
        @type  ntname: string
        @param ntname: name of the nonterm
        
        @type  captures: list 
        @param captures: list of tuples (c-string,bits) (optional)
        """
        lines = []
        # emit code for the conditions and if the conditions are true, do the action

        use_bit_vector = self.uses_bit_vector()
        has_error_action = self.has_error_action()
        has_nothing_action = self.has_nothing_action()
        has_no_return_action = self.has_no_return_action()
        has_otherwise_rule = self.has_otherwise_rule()
        
        #complicated_nt are nonterminals that can not be auto generated using 
        #hash function and lookup tables due to their complexity
        #so we generete them in the old if statement structure 
        complicated_nt = nt_func_gen.get_complicated_nt()        
        
        # the 'INSTRUCTIONS' and the complicated nts emit iform are 
        # using the old ordering mechnism
        # all other nts are using the new attribute index to set the order
        ith_rule = ith_rule_arg
        if nt_name != 'INSTRUCTIONS' and nt_name not in complicated_nt:
            ith_rule = self.index
            has_otherwise_rule = self.default

        if veemit():
            msgb("EEMIT", "%d %s %s" % (ith_rule, nt_name, self.__str__()))

        if has_no_return_action:
            cond_else = '/* no return */ '
        else:
            cond_else = '/* %d */ ' % (ith_rule)


        if has_otherwise_rule:
            # 2007-07-23: otherwise rules always fire in emit. There
            # is no "else" for the otherwise rule. It is a catch-all.
            lines.append( "if (1) { /*otherwise*/")
        elif has_nothing_action:
            # Some rules have 'nothing' actions that serve as epsilon accepts.
            lines.append( "%sif (1) { /* nothing */" % (cond_else))
            for a in self.actions:
                if not a.is_nothing():
                    die("Nothing action mixed with other actions")
        elif has_error_action:
            #
            # do not check the iform on error actions -- just ignore
            # them. They are caught in the "BIND" step.
            return []
        
        elif use_bit_vector:
            lines.append( "%sif (iform&(1<<%d)) {" % (cond_else,ith_rule))
        else:
            lines.append( "%sif (iform==%d) {" % (cond_else,ith_rule))
        do_return = True
        
        for a in self.actions:
            if veemit():
                msgb("Codegen for action",  str(a))

            if a.is_field_binding():
                # for repeating prefixes, we have the NO_RETURN field.
                if a.field_name == 'NO_RETURN': # FIXME: check value ==1?
                    do_return = False
                    continue

            if a.is_nonterminal():
                if veemit():
                    msgb("EEMIT NT ACTION", str(a))
                t =  a.emit_code('EMIT') # EMIT for NTs
                if veemit():
                    for x in t:
                        msgb("NT EMIT", x)
                lines.extend( t )

            elif a.is_emit_action():
                # emit actions require knowledge of all the conditions
                # which have the field bindings so we emit them here.
                if captures:
                    list_of_tuples = captures
                else:
                    list_of_tuples = self.compute_field_capture_list()

                if vtuples():
                    msgb("TUPLES", (" ,".join( [str(x) for x in list_of_tuples] )))
                if len(list_of_tuples) == 0 or a.emit_type == 'numeric':
                    # no substitutions required
                    (length, s) = self.prepare_value_for_emit(a)
                    if veemit():
                        msgb("SIMPLE EMIT", "bits=%d  value=%s" % (length, s))
                else:
                    (length,s) = scatter_gen( a.value, list_of_tuples)
                    #msgerr("SCATTERGEN %s %s -> %s %s" % (str(a.value), str(list_of_tuples), length, s))
                t =  "    xed_encoder_request_encode_emit(xes,%s,%s);" % (length,s)
                if veemit():
                    msgb("EMITTING" , t)
                lines.append(t)
                
        if do_return:
            #lines.append( "    if (okay && %s != XED_ERROR_NONE) okay=0;" % (error_operand()))
            lines.append( "    if (%s != XED_ERROR_NONE) okay=0;" % (error_operand()))
            #lines.append( "    if (okay) return 1;")
            lines.append( "    return okay;")
        lines.append( "}") # close iform
        return lines
        
    def emit_rule(self, bind_or_emit, ith_rule, nt_name, captures=None):
        """Return a list of lines of code for the nonterminal
        function.

        @type  bind_or_emit: string
        @param bind_or_emit: 'BIND', 'EMIT' or 'NTLUF'
        """
        if bind_or_emit == 'NTLUF':
            ntluf = True
        else:
            ntluf = False
            
        if bind_or_emit == 'BIND' or bind_or_emit == 'NTLUF':
            return self.emit_rule_bind(ith_rule, nt_name, ntluf)
        elif bind_or_emit == 'EMIT':
            return self.emit_rule_emit(ith_rule, nt_name,captures)
        else:
            die("Need BIND or EMIT")
    
    def get_all_fbs(self):
        ''' collect all the actions that sets fields '''
        fbs = []
        for action in self.actions:
            if action.is_field_binding():
                    fbs.append(action)
            if action.is_emit_action() and action.emit_type == 'numeric':
                if action.field_name:
                    fbs.append(action)
        return fbs
    
    def get_all_emits(self):
        ''' return a list of all emit type actions '''
        emits = []
        for action in self.actions:
            if action.is_emit_action():
                emits.append(action)
        return emits
    
    def get_all_nts(self):
        ''' return a list of all nonterminal type actions '''
        nts = []
        for action in self.actions:
            if action.is_nonterminal():
                nts.append(action)
        return nts
                
class iform_t(object):
    """One form of an instruction"""
    def __init__(self, map_info,
                 iclass, enc_conditions, enc_actions, modal_patterns, uname=None,
                 real_opcode=True,
                 isa_set=None):
        self.iclass = iclass
        self.uname = uname
        self.enc_conditions = enc_conditions # [ operand_t ]
        self.enc_actions = enc_actions  # [ blot_t ]
        self.modal_patterns = modal_patterns # [ string ]
        self.real_opcode = real_opcode
        self.isa_set = isa_set

        # the emit phase action pattern is a comma separated string of
        # strings describing emit activity, created by ins_emit.py.
        self.emit_actions = None 
        
        #the FB actions pattern
        self.fb_ptrn = None
        
        self._fixup_vex_conditions()
        self._find_legacy_map(map_info)
        self.rule = self.make_rule()

    def _find_legacy_map(self, map_info):
        """Set self.legacy_map to the map_info_t record that best matches"""
        if self.encspace == 0:
            s = []
            self.legacy_map = None
            for act in self.enc_actions:
                if act.type == 'bits':
                    s.append(act.value)
            if s:
                found = False
                default_map = None
                for m in map_info:
                    if m.space == 'legacy':
                        if m.legacy_escape == 'N/A':  # 1B map (map 0)
                            default_map = m
                        elif m.legacy_escape_int == s[0]:
                            if m.legacy_opcode == 'N/A':   # 2B maps (map-1 like)
                                found = True
                                self.legacy_map = m
                                break
                            elif len(s)>=2 and m.legacy_opcode_int == s[1]:   # 3B maps
                                self.legacy_map = m
                                found = True
                                break
                if not found:
                    self.legacy_map = default_map
            if not self.legacy_map:
                genutil.die("Could not set legacy map.")
            
    def _fixup_vex_conditions(self):
        """if action has VEXVALID=1, add modal_pattern MUST_USE_AVX512=0. 
           The modal_patterns become conditions later on."""
        self.encspace=0 # legacy 
        for act in self.enc_actions:
            if act.field_name == 'VEXVALID':
                self.encspace=act.value
                if act.value == 1:
                    self.modal_patterns.append( "MUST_USE_EVEX=0" )

    
    def make_operand_name_list(self):
        """Make an ordered list of operand storage field names that
        drives encode operand order checking. """
        operand_names = []
        for opnd in self.enc_conditions:
            if voperand2():
                msg( "EOLIST iclass %s opnd %s vis %s" % (self.iclass, opnd.var, opnd.vis))
            if opnd.vis == 'SUPP':
                continue
            if opnd.vis == 'ECOND':
                continue
            if self._check_encoder_input(opnd.var):
                operand_names.append(opnd.var)
        # 2007-07-05 We do not need to add MEM_WIDTH, since that does
        # not affect operand order. It is checked for memops by
        # encode.
        return operand_names
            

    def compute_binding_strings_for_emit(self):
        """Gather up *all* the conditions (suppressed or not) and
        include them as possible canditates for supplying bits for the
        encoder."""

        captures = []
        for opnd in self.enc_conditions: # each is an operand_t
            if opnd.type == 'binding':
                if letter_and_underscore_pattern.match(opnd.value):
                    captures.append((opnd.var, no_underscores(opnd.value)))
                else:
                    pass
                    #msge("SKIPPING BINDING " + str(opnd))

        # add the C decoration to the field name for emitting code.
        decorated_captures = []
        for (f,b) in captures:
            decorated_captures.append((operand_storage.get_op_getter_fn(f),b))
        return decorated_captures

    def _check_encoder_input(self,name):
        """Return True for things that are storage field encoder inputs"""
        global storage_fields
        if name in storage_fields and storage_fields[name].encoder_input:
            return True
        return False

    def find_encoder_inputs(self):
        """Return a set of encoder input field names"""
        s = set()
        ns = set()
        for mp in self.modal_patterns:
            if self._check_encoder_input(mp):
                s.add(mp)
                
        for op in self.enc_conditions:
            # The encoder ignores SUPP operands.
            if op.vis == 'SUPP':
                continue
            if op.type == 'token' or op.type == 'binding' or op.type == 'ntluf':
                if self._check_encoder_input(op.var):
                    s.add(op.var)
            if op.lencode != '?':
                s.add('MEM_WIDTH')
            if op.ntluf:
                ns.add(op.value)
        return (s,ns)

    def make_rule(self):
        """Return a rule_t based on the conditions and action_list."""
        if vrule():
            msgb("MAKE RULE","for %s" % str(self))
        action_list = []  # [ string ]
        for blot in self.enc_actions:
            a = blot.make_action_string()
            if a:
                action_list.append(a)

        cond = conditions_t()
        for mp in self.modal_patterns:
            if vrule():
                msgb("Adding MODAL_PATTERN", mp)
            c = condition_t(mp)
            cond.and_cond(c)

        for opnd in self.enc_conditions:
            # some conditions we ignore: like for SUPP registers...
            if vrule():
                msge("OPERAND: %s" % (str(opnd)))
            c = opnd.make_condition()
            if c:
                if vrule():
                    msge("\t MADE CONDITION")
                for subc in c:
                    if vrule():
                        msge("\t\tANDCOND %s" % str(subc))
                    cond.and_cond(subc)
            else:
                if vrule():
                    msge("\t SKIPPING OPERAND in the AND CONDITIONS")
        #here we are handling only instructions.
        #Do not need to specify the nt name since the instructions have 
        #their own emit function and this nt name is not used      
        rule = rule_t(cond,action_list, None)
        self._remove_overlapping_actions(rule.actions)
        return rule
    
    
    def _remove_overlapping_actions(self, action_list):
        ''' for some actions the generated code looks exactly the same.
            for example:
            action1: MOD=0 
            action2: MOD[0b00]
            
            the generated code for both of them in the BIND phase is the same
            and for action1 we do nothing in the EMIT phase.
            
            we are itereting over all the field binding to see if we have
            overlapping emit action.
            
            modifying to input action_list
        '''
        
        emit_actions = list(filter(lambda x: x.type == 'emit', action_list))
        fb_actions = list(filter(lambda x: x.type == 'FB', action_list))
        
        #iterate to find overlapping actions
        action_to_remove = []
        for fb in fb_actions:
            for emit in emit_actions:
                if fb.field_name.lower() == emit.field_name and \
                  emit.emit_type == 'numeric':
                    if fb.int_value == emit.int_value:
                        # overlapping actions, recored this action
                        # and remove later
                        action_to_remove.append(fb)
                    else:
                        err = "FB and emit action for %s has different values"
                        genutil.die(err % fb.field_name) 
        
        #remove the overlapping actions
        for action in action_to_remove:
            action_list.remove(action)
            
    def __str__(self):
        s = []
        s.append("ICLASS: %s" % self.iclass)
        s.append("CONDITIONS:")
        for c in self.enc_conditions:
            s.append("\t%s" % str(c))
        s.append( "ACTIONS:")
        for a in self.enc_actions:
            s.append("\t%s" % str(a))
        return '\n'.join(s)

def key_rule_tuple(x):
    (a1,a2) = x
    return a1

class nonterminal_t(object):
    def __init__(self, name, rettype=None):
        """
        The return type is for the NLTUFs only.
        """
        self.name = name
        self.rettype = rettype # if non None, then this is a NTLUF
        self.rules = []
        #FIXME: this will be used in the future
        #self.otherwise = actions.action_t('error=XED_ERROR_GENERAL_ERROR')
        self.otherwise = [actions.gen_return_action('0')]
        
    def _default_rule(self):
        ''' return a rule_t object, where the conditions are: 'otherewise'
            and the actions are taken from the otherwise attribute
        '''
        
        conds = conditions_t()
        conds.and_cond('otherwise')
        rule = rule_t(conds,self.otherwise,self.name)
        rule.default = True
        return rule
    
    def is_ntluf(self):
        if self.rettype:
            return True
        return False
    
    def add(self,rule):
        self.rules.append(rule)
    def __str__(self):
        s = [ self.name , "()::\n" ]
        for r in self.rules:
            s.extend(["\t" , str(r) , "\n"])
        return ''.join(s)
    
    def multiple_otherwise_rules(self):
        c = 0
        for r in self.rules:
            if r.has_otherwise_rule():
                c = c + 1
        if c > 1:
            return True
        return False

    def sort_for_size(self):
        tups = []
        # PERF: want the 'nothing' bindings to occur before the error
        # bindings because the errors are less frequent. (Only one
        # "nothing" emit will occur and "error" actions do not show up
        # in the "emit" phase.)
        for rule in self.rules:
            if rule.has_otherwise_rule():
                weight = 99999 # make it last
            elif rule.has_nothing_action():
                weight = 99997 
            elif rule.has_error_action():
                weight = 99998 
            else:
                weight = len(rule.actions) # try to get shortest form first...
                _vmsgb("RULE WEIGHT %d" % (weight), str(rule))
            tups.append((weight,rule))
        tups.sort(key=key_rule_tuple)
        newrules = []
        for (x,y) in tups:
            newrules.append(y)
        self.rules = newrules
        
    def create_function(self, bind_or_emit):
        if self.is_ntluf(): # bind_or_emit should be 'NTLUF'
            fname = 'xed_encode_ntluf_%s' %  self.name
        else:
            fname = 'xed_encode_nonterminal_%s_%s' % (self.name, bind_or_emit)
        if vntname():
            msgb("NTNAME", self.name)
        fo = function_object_t(fname,"xed_uint_t")
        fo.add_arg("%s* xes" % xed_encoder_request)
        if self.is_ntluf():
            fo.add_arg("xed_reg_enum_t arg_reg") # bind this to OUTREG below
        fo.add_comment(self.__str__())
        fo.add_code_eol("xed_uint_t okay=1")
        if bind_or_emit == 'BIND' or bind_or_emit == 'NTLUF':
            fo.add_code_eol( "xed_uint_t conditions_satisfied=0" )

        has_emit_action = False
        if bind_or_emit == 'EMIT':
            for r in self.rules:
                if r.has_emit_action():
                    has_emit_action = True
                    break
                
        has_nonterminal_action = False
        if bind_or_emit == 'EMIT':
            for r in self.rules:
                if r.has_nonterminal_action():
                    has_nonterminal_action = True
                    break
                
        # FIXME: PERF using OUTREG to hold arg_reg is the easiest way
        # to not change any of the condition code generation stuff. I
        # could easily optimize this later. 2007-04-10

        nt_name = self.name

        if self.is_ntluf():
            fo.add_code_eol( "%s = arg_reg" % (outreg()))

        # setup or read the IFORM variable if we are binding or emitting.
        if bind_or_emit == 'BIND' or bind_or_emit == 'NTLUF':
            if len(self.rules)>0:
                if self.rules[0].uses_bit_vector():
                    fo.add_code_eol( "xed_encoder_request_iforms(xes)->x_%s=0" % (nt_name) )
                    iform_builder.remember_iforms(nt_name)
                
        else: # EMIT
            if has_emit_action or has_nonterminal_action:
                fo.add_code_eol( "unsigned int iform = xed_encoder_request_iforms(xes)->x_%s" % (nt_name) )
                iform_builder.remember_iforms(nt_name)
            else:
                # nothing to emit, so skip this...
                fo.add_code_eol('return 1')
                fo.add_code_eol('(void) okay')
                fo.add_code_eol('(void) xes')
                return fo

        #_vmsgb("EMITTING RULES FOR", nt_name)
        
        emitted_nothing_action=False
        for i,rule in enumerate(self.rules):
            #_vmsgb("EMITTING RULE %d" % (i+1))
            emitr = True
            if bind_or_emit == 'EMIT' and rule.has_nothing_action():
                if emitted_nothing_action:
                    emitr = False
                emitted_nothing_action = True
            if emitr:
                lines = rule.emit_rule(bind_or_emit,i+1, nt_name)
                fo.add_lines(lines)
        default_rule = self._default_rule()
        lines = default_rule.emit_rule(bind_or_emit,0, nt_name)
        fo.add_lines(lines)
        
        fo.add_code('return 0; /*pacify the compiler*/')
        fo.add_code_eol('(void) okay')
        fo.add_code_eol('(void) xes')
        if bind_or_emit == 'EMIT':
            fo.add_code_eol('(void) iform')

        if bind_or_emit == 'BIND' or bind_or_emit == 'NTLUF':
            fo.add_code_eol("(void) conditions_satisfied")
        return fo

class sequencer_t(object):
    def __init__(self, name):
        self.name = name
        self.nonterminals = []
    def add(self,nt):
        t = nt_name_pattern.search(nt)
        if t:
            self.nonterminals.append(t.group('ntname'))
        else:
            self.nonterminals.append(nt)
    def __str__(self):
        s = ["SEQUENCE " , self.name , "\n"]
        for nt in self.nonterminals:
            s.extend(["\t" , str(nt) , "()\n"])
        return ''.join(s)
    def create_function(self,sequences):
        fname = 'xed_encode_nonterminal_' +  self.name
        lst = []
        for x in self.nonterminals:
            # FIXME 2007-06-29 Mark Charney: This looks odd
            if x in sequences:
                lst.append("xed_encode_nonterminal_%s" % x)
            else:
                lst.append("xed_encode_nonterminal_%s" % x)

        arg ='xes'
        fo = function_call_sequence_conditional(fname,lst,arg)
        fo.add_arg('%s* xes' % xed_encoder_request)
        return fo

    
def group_bits_and_letter_runs(s):
    """
    @type s: string
    @param s: string of the form [01a-z]+
    
    @rtype: list of strings
    @return: list of binary bit strings and distinct letter runs
    """
    out = []
    run = None
    last_letter = None
    last_was_number  = False
    # remove underscores from s
    for i in list(s.replace('_','')):
        if i=='0' or i=='1':
            if last_was_number:
                run += i
            else:
                if run:
                    out.append(run) # end last run
                run = i
            last_was_number = True
            last_letter = None

        else: # i is a letter

            if last_letter and last_letter == i:
                run += i
            else:
                if run:
                    out.append(run) # end last run
                run = i
            last_was_number = False
            last_letter = i
    if run:
        out.append(run)
    return out
        

class encoder_input_files_t(object):
    def __init__(self, options):
        self.xeddir = options.xeddir
        self.gendir = options.gendir            
        self.storage_fields_file = options.input_fields
        self.regs_input_file = options.input_regs
        self.decoder_input_files = options.enc_dec_patterns
        self.encoder_input_files = options.enc_patterns
        self.state_bits_file = options.input_state
        self.instructions_file = options.isa_input_file
        self.map_info_file = options.map_descriptions_input_fn
        self.chip_model_info_file = options.chip_models_input_fn

        # dict of operand_order_t indexed by special keys stored in iform.operand_order_key
        self.all_operand_name_list_dict = None

                                     
    def input_file(self,s):
        """Join the xeddir and the datafiles dir to s"""
        return  os.path.join(self.xeddir,'datafiles',s)

class operand_order_t(object):
    def __init__(self,n,lst):
        self.n = n # index in to the encode_order array
        self.lst = lst # list of nonsuppressed operands

class encoder_configuration_t(object):
    #   decode: ipatterns -> operands
    #   encode: conditions -> actions

    # normally ipatterns become actions.
    # normally operands become conditions.
    # however,
    #          some ipatterns become conditions
    #    and   some operands become actions.
    #
    #    and finally, some operands get dropped entirely.
    
    def __init__(self, encoder_input_files, chip='ALL', amd_enabled=True):
        self.amd_enabled = amd_enabled
        self.files = encoder_input_files
        self.gendir = self.files.gendir
        self.xeddir = self.files.xeddir

        def _call_chip_model(fn):
            chips, isa_set_db = chipmodel.read_database(fn)
            chipmodel.add_all_chip(isa_set_db)
            return isa_set_db
        self.isa_set_db = _call_chip_model(encoder_input_files.chip_model_info_file)
        self.chip = chip
        
        global storage_fields
        lines = open(self.files.storage_fields_file,'r')
        operands_storage = operand_storage.operands_storage_t(lines) 
        storage_fields = operands_storage.get_operands()

        self.map_info = map_info_rdr.read_file(self.files.map_info_file)
        self.state_bits = None
        
        self.sequences = {}
        self.nonterminals = {}

        self.decoder_nonterminals = {}
        self.decoder_ntlufs = {}
        
        self.functions = []

        # the main ISA decode rules are stored here before conversion
        # to the encode rules
        self.iarray = {} # dictionary by iclass of [ iform_t ]

        self.deleted_instructions = {} # by iclass
        self.deleted_unames = {}       # by uname

        cmkdir(self.gendir)

    def dump_output_file_names(self):
        global output_file_emitters
        ofn = os.path.join(self.gendir,"ENCGEN-OUTPUT-FILES.txt")
        o = open(ofn,"w")
        for fe in output_file_emitters:
            o.write(fe.full_file_name + "\n")
        o.close()

    def parse_decode_rule(self, conds,actions ,line, nt_name):
        # conds   -- rhs, from an encode perspective (decode operands)
        # actions -- lhs, from an encode perspective (decode patterns)

        # move some special actions to the conditions
        new_actions = []
        for a in actions: # decode patterns
            if veparse():
                msgb("parse_decode_rule actions", str(a))
            q = lhs_pattern.match(a)
            if q:
                lhs_a = q.group('name')
                if lhs_a in storage_fields and storage_fields[lhs_a].encoder_input == True:
                    if veparse():
                        msgb("CVT TO ENCODER CONDITION", lhs_a)
                    conds.append(a)
                    continue
            opcap = lhs_capture_pattern_end.match(a)
            if opcap:
                synth_cap = "%s=%s" % (opcap.group('name'), opcap.group('bits'))
                conds.append( synth_cap )
                if veparse():
                    msge("SYNTH CONDITION FOR " + a + " --> " + synth_cap )
                new_actions.append(a)
                continue
            if veparse():
                msge("NEWACTION " + a)
            new_actions.append(a)
        del actions

        # Move some special encode conditions to the encode
        # actions if they are not encoder inputs. This solves
        # a problem with encoding IMM0SIGNED on SIMMz()
        # nonterminals.
        new_conds = []
        for c in conds: # were decode operands (rhs)
            if veparse():
                msgb("parse_decode_rule conditions", str(c))
            if c.find('=') == -1:
                trimmed_cond = c
            else:
                ep = equals_pattern.match(c) # catches  "=", but not "!="
                if ep:
                    trimmed_cond = ep.group('lhs')
                else:
                    die("Bad condition: %s" % c)
            if veparse():
                msgb("TESTING COND", "%s --> %s" % (c, trimmed_cond))
            keep_in_conds = True
            try:
                if storage_fields[trimmed_cond].encoder_input == False:
                    if veparse():
                        msgb("DROPPING COND", c)
                    keep_in_conds = False # 2007-08-01
            except:
                pass
            
            # if we have the constraint: OUTREG=some_nt() and it is not the 
            # single constraint we want to move 
            # the nt: some_nt() to the actions side.
            # e.g. the constraint: MODE=3 OUTREG=GPRv_64() -> nothing
            #      becomes:        MODE=3 -> GPRv_64()
            if trimmed_cond == 'OUTREG':
                nt = nt_name_pattern.match(c.split('=')[1])
                if nt and len(conds) > 1:
                    c = "%s(OUTREG)" % nt.group('ntname')
                    keep_in_conds = False
                    
            if keep_in_conds:
                new_conds.append(c)
            else:
                if veparse():
                    msge("COND->ACTION " +  c) # FIXME: REMOVEME
                new_actions.append(c)
        conds = new_conds

        # signal it is okay if there is no action
        if len(new_actions) == 0:
            new_actions.append('nothing')

        if len(conds) == 0:
            conds = ['otherwise']

        if len(conds) > 0:
            conditions = conditions_t()
            for c in conds:
                #msge("COND " +  c) # FIXME: REMOVEME
                xr = xed_reg_pattern.match(c) # FIXME: not general enough
                if xr:
                    conditions.and_cond("OUTREG=%s" % (xr.group('regname')))
                else:
                    conditions.and_cond(c)
            # only add a rule if we have conditions for it!    
            rule = rule_t(conditions, new_actions, nt_name)
            return rule
        else:
            _vmsgb("DROP DECODE LINE (NO eCONDS)", "%s\nin NT: %s" %(line,nt_name))
        return None


    def parse_decode_lines(self, lines):
        """ Read the flat decoder files (not the ISA file).
        
        Return a tuple:
            ( dict of nonterminals, dict of nonterminal lookup functions )
            
            This parses the so-called flat format with the vertical
            bar used for all the non-instruction tables.

            For decode the semantics are:
               preconditions | dec-actions
            However for encode, the semantics change to:
               enc-actions  | conditions

            And we must take some of the "enc-actions"  and add them to the preconditions.
            These include the actions associated with: MODE,SMODE,EOSZ,EASZ
        """
        nts = {}
        ntlufs = {}

        while len(lines) > 0:
            line = lines.pop(0)
            #msge("LINEOUT:" + line)
            line = comment_pattern.sub("",line)
            line = leading_whitespace_pattern.sub("",line)
            line = line.rstrip()
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)

            p = ntluf_pattern.match(line)
            if p:
                nt_name =  p.group('ntname')
                ret_type = p.group('rettype')
                if nt_name in ntlufs:
                    # reuse an existing NTLUF, extending it.
                    # FIXME: confirm same ret_type
                    nt = ntlufs[nt_name]
                else:
                    # create a new nonterminal to use

                    nt = nonterminal_t(nt_name, ret_type)
                    ntlufs[nt_name] = nt
                continue
            
            p = nt_pattern.match(line)
            if p:
                nt_name =  p.group('ntname')
                if nt_name in nts:
                    # reuse an existing NTLUF, extending it.
                    nt = nts[nt_name]
                else:
                    # create a new nonterminal to use
                    nt = nonterminal_t(nt_name)
                    nts[nt_name] = nt
                continue
            
            p = decode_rule_pattern.match(line)
            if p:
                conds = p.group('cond').split() # rhs, from an encode perspective (decode operands)
                actions = p.group('action').split() # lhs, from a encode perspective (decode patterns)
                rule = self.parse_decode_rule(conds,actions,line,nt.name)
                if rule:
                    nt.add(rule)
                if nt.multiple_otherwise_rules():
                    die("Multiple otherwise rules in %s -- noninvertible" % (nt_name))
                continue
            
            die("Unhandled line: %s" % line)
            
        return  (nts, ntlufs)
    
    def parse_encode_lines(self,lines):
        """
        Returns a tuple of two dictionaries: (1) a dictionary of
        sequencer_t's and (2) a dictionary of nonterminal_t's
        """
        nts = {} # nonterminals_t's
        ntlufs = {} # nonterminals_t's
        seqs = {} # sequencer_t's 
        while len(lines) > 0:
            line = lines.pop(0)
            line = comment_pattern.sub("",line)
            line = leading_whitespace_pattern.sub("",line)
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)
            c =  curly_pattern.search(line)
            if c:
                line = re.sub("{", " { ", line)
                line = re.sub("}", " } ", line)

            sequence = sequence_pattern.match(line)
            if sequence:
                seq = sequencer_t(sequence.group('seqname'))
                seqs[seq.name] = seq
                #msg("SEQ MATCH %s" % seq.name)
                nt = None
                continue

            p =  ntluf_pattern.match(line)
            if p:
                nt_name =  p.group('ntname')
                ret_type = p.group('rettype')
                # create a new nonterminal to use
                nt = nonterminal_t(nt_name, ret_type)
                ntlufs[nt_name] = nt
                seq = None
                continue

            m = nt_pattern.match(line)
            if m:
                nt_name =  m.group('ntname')
                if nt_name in nts:
                    nt = nts[nt_name]
                else:
                    nt = nonterminal_t(nt_name)
                    nts[nt_name] = nt
                seq = None
                continue
            a = arrow_pattern.match(line)
            if a:
                conds = a.group('cond').split()
                actns = a.group('action').split()
                #msg("ARROW" + str(conds) + "=>" + str(actions))
                conditions = conditions_t()
                for c in conds:
                    conditions.and_cond(c)
                rule = rule_t(conditions, actns, nt_name)
                if seq:
                    seq.add(rule)
                else:
                    # we do not need the rules otherwise->error/nothing in the 
                    # new encoding structure (hash tables). 
                    # instead we are holding this info in a matching attribute
                    if rule.conditions.and_conditions[0].is_otherwise():
                        if rule.actions[0].is_nothing():
                            nt.otherwise = [actions.gen_return_action('1')] 
                        elif rule.actions[0].is_error():
                            nt.otherwise = [actions.gen_return_action('0')]
                        else:
                            nt.otherwise = [ actions.action_t(x) for x in actns]
                            # in case we have valid action for the otherwise
                            # rule we should finish it with returnning 1
                            # which is "not an error"
                            nt.otherwise.append(actions.gen_return_action('1'))
                    else:
                        nt.add(rule)
            else:
                for nt in line.split():
                    seq.add(nt)
        return (seqs,nts,ntlufs)
        
    def parse_state_bits(self,lines):
        d = []
        state_input_pattern = re.compile(r'(?P<key>[^\s]+)\s+(?P<value>.*)')
        while len(lines) > 0:
            line = lines.pop(0)
            line = comment_pattern.sub("",line)
            line = leading_whitespace_pattern.sub("",line)
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)
            p = state_input_pattern.search(line)
            if p:
                #_vmsgb(p.group('key'), p.group('value'))
                #d[p.group('key')] = p.group('value')
                s = r'\b' + p.group('key') + r'\b'
                pattern = re.compile(s) 
                d.append( (pattern, p.group('value')) )
            else:
                die("Bad state line: %s"  % line)
        return d

    def expand_state_bits_one_line(self,line):
        new_line = line
        for k,v in self.state_bits:
            new_line = k.sub(v,new_line)
        return new_line

    def expand_state_bits(self,lines):
        new_lines = []
        # n^2 algorithm
        for line in lines:
            new_line = line
            for k,v in self.state_bits:
                new_line = k.sub(v,new_line)
            new_lines.append(new_line)
        return new_lines
    
    def update(self,seqs,nts,ntlufs):
        """Update the sequences and nonterminals dictionaries"""
        self.sequences.update(seqs)
        self.nonterminals.update(nts)
        self.decoder_ntlufs.update(ntlufs)
    
    def read_encoder_files(self):
        
        for f in self.files.encoder_input_files:
            lines = open(f,'r').readlines()
            lines = self.expand_state_bits(lines)
            (seqs,nts,ntlufs) = self.parse_encode_lines(lines)
            del lines
            self.update(seqs,nts,ntlufs)
            

    def reorder_encoder_rules(self,nts):
        """reorder rules so that any rules with ENCODER_PREFERRED is first
        """
        for nt in nts.values():
            first_rules = []
            rest_of_the_rules = []
            for r in nt.rules:
                if r.conditions.contains("ENCODER_PREFERRED"):
                    first_rules.append(r)
                else:
                    rest_of_the_rules.append(r)
            nt.rules = first_rules  + rest_of_the_rules


    ##################################################


    def make_nt(self,ntname): 
        blot = blot_t('nt')
        blot.nt = ntname
        return blot

    def make_hex(self,s,field_name=None):
        """
        @param s: string with a 2 nibble hex number
        @rtype: blot_t
        @return: blot containing the integer value
        """
        blot = blot_t('bits')
        blot.value = int(s,16)
        blot.length = 8
        blot.field_name = field_name
        return blot
    def make_binary(self,s,field_name=None): 
        """
        @param s: string with a binary number
        @rtype: blot_t
        @return: blot containing the integer value
        """
        blot = blot_t('bits')
        if re.search(r'^0b',s):
            s = re.sub('0b','',s)
        s = re.sub('_','',s)
        blot.value = int(s,2)
        blot.length = len(s)
        blot.original_bits = s # FIXME: 2007-04-20
        blot.field_name = field_name
        return blot
    
    def make_bits_and_letters(self,s, field_name=None):
        """
        @type s: string
        @param s: string of letters or binary digits representing the blot_t
        @type field_name: string
        @param field_name: name of the storage field (optional)

        @rtype: list of blot_t's
        @return:  list of blot_t's
        """
        #_vmsgb("MBAL","%s" % s)
        blots = []
        bit_offset_in_field = 0
        runs = group_bits_and_letter_runs(s)
        _vmsgb("RUNS\t",str(runs))
        for r in runs:
            #_vmsgb("\t",str(r))
            if len(r) == 0:
                die("Bad run in  " + str(s))
            blot = blot_t()
            if r[0] == '0' or r[0] == '1':
                blot.type = 'bits'
                blot.value = int(r,2)
            else:
                blot.type = 'letters'
                blot.letters = r
            blot.length = len(r)
            blot.field_name = field_name
            blot.field_offset = bit_offset_in_field
            bit_offset_in_field += blot.length
            blots.append(blot)
        return blots
    def make_decider_blot(self, lhs,rhs,equals):
        blot = blot_t('od')
        blot.field_name = lhs
        rhs  = re.sub(r':.*','',rhs)
        blot.value = make_numeric(rhs,"%s %s %s" % (str(lhs),str(equals),str(rhs)))
        blot.od_equals = equals
        return blot
    
    def make_decode_patterns(self,s):
        """ return one or more subpatterns of type.

        Sometimes we specify an decode pattern like MOD[mm] or
        MOD[11_]. The 2nd part of the return tuple is a list of the
        implied decode operands such as MOD=mm or MOD=11_.
        
        @rtype: tuple
        @returns: (list of blot_t's representing patterns,\
                    a list of tuples of field bindings)
        """
        decode_patterns = []
        field_bindings = []
        while 1:
            nt = nt_name_pattern.match(s)
            if nt:
                decode_patterns.append(self.make_nt(nt.group('ntname')))
                break
            opcap = lhs_capture_pattern_end.match(s)
            if opcap:
                # MOD[mm] REG[0b000] 
                bits = opcap.group('bits')
                field_name = opcap.group('name')
                if binary_pattern.match(bits):
                    decode_patterns.append(self.make_binary(bits, field_name))
                elif hex_pattern.match(bits):
                    decode_patterns.append(self.make_hex(bits, field_name))
                elif letter_pattern.match(bits):
                    o = self.make_bits_and_letters( bits, field_name) 
                    decode_patterns.extend(o)
                else:
                    genutil.die("Unrecognaized pattern '{}' for {}".format( bits, s))
                field_bindings.append(  opcap.group('name','bits') )
                break
            if hex_pattern.match(s):
                decode_patterns.append(self.make_hex(s))
                break
            s_nounder = no_underscores(s)
            if binary_pattern.match(s_nounder):
                decode_patterns.append(self.make_binary(s_nounder))
                break
            if bits_and_letters_pattern.match(s_nounder):
                decode_patterns.extend(self.make_bits_and_letters(s_nounder))
                break
            if letter_pattern.match(s_nounder):
                decode_patterns.extend(self.make_bits_and_letters(s_nounder))
                break
            equals = equals_pattern.match(s)
            if equals:
                (lhs,rhs) = equals.group('lhs','rhs')
                decode_patterns.append(self.make_decider_blot(lhs,rhs,equals=True))
                break
            not_equals = not_equals_pattern.match(s)
            if not_equals:
                (lhs,rhs) = not_equals.group('lhs','rhs')
                decode_patterns.append(self.make_decider_blot(lhs,rhs,equals=False))
                break
            
            die("Could not process decode pattern %s" % s)
        
        return (decode_patterns, field_bindings)

    def force_vl_encoder_output(self, iclass, operand_str, pattern_str):
        """Return true if we should treat VL as an encoder_output (EO)"""
        if 'VEXVALID=1' in pattern_str or 'VEXVALID=2' in pattern_str:
            if 'XMM' in operand_str or 'YMM' in operand_str or 'ZMM' in operand_str:
                return False
            if ':vv' in operand_str:
                return False
            if 'VL=' in pattern_str:
                #print("SETTING FORCE_VL_ENCODER_OUTPUT FOR {}".format(iclass))
                #print("\t PATTERN:  {}".format(pattern_str))
                #print("\t OPERANDS: {}".format(operand_str))
                return True
        return False
            
        
    def parse_one_decode_rule(self, iclass, operand_str, pattern_str):
        """Read the decoder rule from the main ISA file and package it
        up for encoding. Flipping things around as necessary.
        
        @type operand_str: string
        @param operand_str: decode operands

        @type pattern_str: string
        @param pattern_str: decode pattern (bits, nts, ods, etc.)
        
        @rtype: tuple
        @return: (list decode-operands/encode-conditions as operand_t's, \
                  list decode-patterns/encode-actions as blot_t's \
                  list of modal patterns strings that should become encode condition_t objs)
        """
        # generally:
        #
        #  decode-pattern  --become--> encode-action
        #  decode-operands --become--> encode-condition
        #
        # but there are special cases:
        #
        #  1) Some decode-pattern stuff needs to become encode-conditions
        #     as they are encoder inputs
        #  2) Some decode-operand stuff needs to become encode-actions
        #     as they are encoder outputs
        
        global storage_fields
        patterns = []

        # The extra_bindings_list is a list of implied bindings deduced
        # from the decode pattern, for things like  MOD[mm] (etc.) that do
        # field captures in the pattern. We use them to create
        # new (decode) operands (which then become encode conditions).
        extra_bindings = []

        # Some decode patterns become encode conditions.  These are
        # the fields that are listed as "EI" (encoder inputs) in the
        # "fields description" file.
        modal_patterns = []

        # decode-patterns *mostly* become encode-actions, except for
        # fields that are encoder inputs.
        for p in pattern_str.split(): 
            p_short = rhs_pattern.sub('', p)  # grab the lhs

            # special cases

            # VL is generally an encoder input, except in some cases
            # (VZERO*, BMI, KMASKS, etc.)
            do_encoder_input_check = True
            if p_short in ['VL'] and self.force_vl_encoder_output(iclass, operand_str, pattern_str):
                do_encoder_input_check = False
                
            if do_encoder_input_check:
                if p_short in storage_fields and storage_fields[p_short].encoder_input:
                    if voperand():
                        msgb("MODAL PATTERN", p_short)
                    modal_patterns.append(p)
                    continue

            if p_short in storage_fields and p == 'BCRC=1':
                # FIXME: 2016-01-28: MJC: HACK TO ENCODE ROUNDC/SAE CONSTRAINTS
                if 'SAE' in pattern_str:
                    modal_patterns.append("SAE!=0")
                elif 'AVX512_ROUND' in pattern_str:
                    modal_patterns.append("ROUNDC!=0")
            
            # The pattern_list is a list of blot_t's covering the
            # pattern.  The extra_bindings_list is a list of
            # implied bindings deduced from the decode patterns.
            ##
            # The extra bindings are for MOD[mm] (etc.) that do
            # field captures in the pattern. We use them to create
            # new operands.
            _vmsgb("PARSING DECODE PATTERN", str(p))
            # pattern_list is a list of blot_t
            # extra_bindings is list list of tuples (name,bits)
            (pattern_list, extra_bindings_list) = self.make_decode_patterns(p) 
            s = []
            for p in pattern_list:
                s.append(str(p))
            _vmsgb("PATTERN LIST", ", ".join(s))
            _vmsgb("EXTRABINDING LIST", str(extra_bindings_list))
            patterns.extend(pattern_list)
            extra_bindings.extend(extra_bindings_list)
            
        # Decode operands are type:rw:[lencode|SUPP|IMPL|EXPL|ECOND]
        # where type could be X=y or MEM0.  Most decode operands
        # become encode conditions, but some of them get converted in
        # to extra encode actions.
        
        operands = []  # to become encoder inputs, conditions
        extra_actions = [] # to become encoder outputs
        for x in operand_str.split(): # the encode conditions (decode operands)
            x_short = rhs_pattern.sub('', x) # grab the lhs

            # Some "operands" are really side effects of decode.  They
            # are also side effects of encode and so we move them to
            # the list of actions.
            
            special_encode_action = False 
            try:
                # Move some decode operands (the ones that are not
                # encoder inputs) to the extra encode actions.
                if storage_fields[x_short].encoder_input== False:
                    if voperand():
                        msgb("ENCODER OUTPUT FIELD", x_short)
                    special_encode_action = True
            except:
                pass

            if special_encode_action:
                if voperand():
                    msgb("SPECIAL_ENCODE_ACTION ATTRIBUTE", x)
                extra_actions.append(x)
            else:
                if voperand():
                    msgb("MAKING A DECODE-OPERAND/ENC-ACTION FROM", x)
                operands.append(operand_t(x))


                
        # Add the extra encode conditions (decode-operands) implied
        # from the instruction decode patterns (MOD[mm] etc.). We
        # ignore the ones for constant bindings!
        for (field_name,value) in extra_bindings:
            if genutil.numeric(value):
                #msgerr("IGNORING %s %s" % (field_name, value))
                pass # we ignore things that are just bits at this point.
            else:
                extra_operand = operand_t("%s=%s:SUPP" % (field_name, value))
                _vmsgb("EXTRA BINDING", "%s=%s:SUPP" % (field_name, value))
                operands.append(extra_operand)

        # Add the extra_actions were part of the decode operands as
        # side-effects but are really side-effects of encode too.
        for raw_action in extra_actions:
            okay = False
            equals = equals_pattern.match(raw_action)
            if equals:
                (lhs,rhs) = equals.group('lhs','rhs')
                new_blot = self.make_decider_blot(lhs,rhs,equals=True)
                okay = True
            not_equals = not_equals_pattern.match(raw_action)
            if not_equals:
                (lhs,rhs) = equals.group('lhs','rhs')
                new_blot = self.make_decider_blot(lhs,rhs,equals=False)
                okay = True
            if not okay:
                die("Bad extra action: %s" % raw_action)
            #msgerr("NEW BLOT: %s" % str(new_blot))
            patterns.append(new_blot)


        # return:  (decode-operands are encode-conditions,
        #            decode-patterns are encode-actions [blot_t],
        #              modal-patterns that become encode-conditions [string])

        #msgerr("OPERANDS %s" % ' '.join( [str(x) for x in operands]))
        return (operands, patterns, modal_patterns)

    def print_iclass_info(self,iclass, operands, ipattern, conditions, 
                          actions, modal_patterns):
        msg(iclass + ':\t' +  operands +   '->' + ipattern)
        msg( "CONDITIONS:")
        for c in conditions:
            msg("\t" + str(c) )
        msg("ACTIONS:")
        for a in actions:
            msg("\t" +  str(a))
        msg("MODAL PATTERNS:")
        for a in modal_patterns:
            msg("\t" +  str(a))
    
    def finalize_decode_conversion(self,iclass, operands, ipattern, uname=None,
                                   real_opcode=True,
                                   isa_set=None):
        if ipattern  == None:
            die("No ipattern for iclass %s and operands: %s" % 
                (str(iclass), operands ))
        if iclass  == None:
            die("No iclass for " + operands)
        # the encode conditions are the decode operands (as [ operand_t ])
        # the encode actions are the decode patterns    (as [ blot_t ])
        # the modal_patterns are things that should become encode conditions
        (conditions, actions, modal_patterns) = \
                      self.parse_one_decode_rule(iclass, operands, ipattern)
        if vfinalize():
            self.print_iclass_info(iclass, operands, ipattern, conditions, 
                                   actions, modal_patterns)
        # FIXME do something with the operand/conditions and patterns/actions
        iform = iform_t(self.map_info, iclass, conditions, actions, modal_patterns, uname,
                        real_opcode, isa_set)

        if uname == 'NOP0F1F':
            # We have many fat NOPS, 0F1F is the preferred one so we
            # give it a higher priority in the iform sorting. 
            iform.priority = 0
        elif 'VEXVALID=2' in ipattern:  # EVEX
            # FIXME: 2016-01-28: MJC: hack. 1st check patterns w/ ROUNDC/SAE.
            # (See other instance of BCRC=1 in this file)
            if 'BCRC=1' in ipattern:
                iform.priority = 0
            else:
                iform.priority = 2
        elif 'VEXVALID=3' in ipattern: # XOP
            iform.priority = 3
        elif 'VEXVALID=4' in ipattern: # KNC
            iform.priority = 3
        else:  # EVERYTHING ELSE
            iform.priority = 1

        try:
            self.iarray[iclass].append ( iform )
        except:
            self.iarray[iclass] = [ iform ]
        
    def read_decoder_instruction_file(self):
        """Taking a slightly different tack with the ISA file because
        it is so large. Processing each line as we encounter it rather
        than buffering up the whole file. Also, just storing the parts
        I need. """
        continuation_pattern = re.compile(r'\\$')
        _vmsgb("READING",self.files.instructions_file)
        lines = open(self.files.instructions_file,'r').readlines()
        lines = process_continuations(lines)
        nts = {}
        nt = None
        iclass = None
        uname = None
        unamed = None
        ipattern = None
        started = False
        real_opcode = True
        extension = None # used  if no isa_set found/present
        isa_set = None
        
        while len(lines) > 0:
            line = lines.pop(0)
            line = comment_pattern.sub("",line)
            #line = leading_whitespace_pattern.sub("",line)
            line=line.strip()
            if line == '':
                continue
            line = slash_expand.expand_all_slashes(line)
            #_vmsgb("INPUT", line)

            if udelete_pattern.search(line):
                m = udelete_full_pattern.search(line)
                unamed = m.group('uname')
                _vmsgb("REGISTER BAD UNAME", unamed)
                self.deleted_unames[unamed] = True
                continue

            if delete_iclass_pattern.search(line):
                m = delete_iclass_full_pattern.search(line)
                iclass = m.group('iclass')
                self.deleted_instructions[iclass] = True
                continue
      
            
            line = self.expand_state_bits_one_line(line)
            p = nt_pattern.match(line)
            if p:
                nt_name =  p.group('ntname')
                if nt_name in nts:
                    nt = nts[nt_name]
                else:
                    nt = nonterminal_t(nt_name)
                    nts[nt_name] = nt
                continue

            if left_curly_pattern.match(line):
                if started:
                    die("Nested instructions")
                started = True
                iclass = None
                uname = None
                real_opcode = True
                extension = None # used  if no isa_set found/present
                isa_set = None

                continue
            
            if right_curly_pattern.match(line):
                if not started:
                    die("Mis-nested instructions")
                started = False
                iclass = None
                uname = None
                continue
            ic = iclass_pattern.match(line)
            if ic:
                iclass = ic.group('iclass')
                continue
            
            un = uname_pattern.match(line)
            if un:
                uname = un.group('uname')
                continue

            realop = real_opcode_pattern.match(line)
            if realop:
                realop_str = realop.group('yesno')
                if realop_str != 'Y':
                    real_opcode=False
                
            extp = extension_pattern.match(line)
            if extp:
                extension = extp.group('ext')
                
            isasetp = isa_set_pattern.match(line)
            if isasetp:
                isa_set = isasetp.group('isaset')
            
            ip = ipattern_pattern.match(line)
            if ip:
                ipattern = ip.group('ipattern')
                continue
            
            if no_operand_pattern.match(line):
                if not isa_set:
                    isa_set = extension
                self.finalize_decode_conversion(iclass,'', 
                                                ipattern, uname,
                                                real_opcode, isa_set)
                continue

            op = operand_pattern.match(line)
            if op:
                operands = op.group('operands')
                if not isa_set:
                    isa_set = extension
                self.finalize_decode_conversion(iclass, operands, 
                                                ipattern, uname,
                                                real_opcode, isa_set)
                continue

        return
            
            
    def remove_deleted(self):
        bad =  list(self.deleted_unames.keys())
        _vmsgb("BAD UNAMES", str(bad))
        for ic,v in self.iarray.items():
            x1 = len(v)
            l = []
            for i in v:
                if i.uname not in bad:
                    l.append(i)
                else:
                    _vmsgb("PRE-DELETING IFORMS", "%s %s" % (ic, i.uname))
            x2 = len(l)
            if x1 != x2:
                _vmsgb("DELETING IFORMS", "%s %d -> %d" % (ic,x1,x2))
            self.iarray[ic]=l
    
        for k in self.deleted_instructions.keys():
            if k in self.iarray:
                _vmsgb("DELETING", k)
                del self.iarray[k] 
    
    def add_iform_indices(self):
        ''' add iform's index to all iforms.
            flatten all the iforms to a single list '''
        
        all_iforms_list = []
        i = 0
        for iforms in self.iarray.values():
            for iform in iforms:
                iform.rule.iform_id = i
                all_iforms_list.append(iform)
                i += 1
        self.total_iforms = i
        return all_iforms_list
        
    def read_decoder_files(self):
        """Read the flat decoder input files and 'invert' them. Build
        two dictionaries: the NTLUFs and the NTs"""

        # read the main ISA tables
        self.read_decoder_instruction_file() # read_isa_
        self.all_iforms = self.add_iform_indices()
        self.remove_deleted()

        # Read the other decoder format tables.
        nts = {}
        ntlufs = {}
        for f in self.files.decoder_input_files:
            lines = open(f,'r').readlines()
            lines = self.expand_state_bits(lines)
            (some_nts, some_ntlufs) = self.parse_decode_lines(lines) # read_flat_
            nts.update(some_nts)
            ntlufs.update(some_ntlufs)
            del lines

        # reorder rules so that any rules with ENCODER_PREFERRED is first
        self.reorder_encoder_rules(nts)
        self.reorder_encoder_rules(ntlufs)
        if vread():
            msgb("NONTERMINALS")
            for nt in nts.values():
                msg( str(nt))
            msgb("NTLUFS")
            for ntluf in ntlufs.values():
                msg( str(ntluf))
        _vmsgb("DONE","\n\n")
        
        self.decoder_nonterminals.update(nts)
        self.decoder_ntlufs.update(ntlufs)

    def make_isa_encode_group(self, group_index, ins_group):
        """Make the function object for encoding one (ins_emit.py) ins_group_t
        group.  The generated function tests operand order and type,
        then more detailed conditions. Once conditions_satisfied is
        true, we attempt to do more detailed bindings operations for
        the nonterminals in the pattern.

        @rtype: function_object_t
        @returns: an encoder function object that encodes group

        """
        if vencode():
            msgb("ENCODING GROUP", " %s  -- %s" % (group_index, ins_group))
        fname = "xed_encode_group_%d" % (group_index)
        fo = function_object_t(fname,'xed_bool_t')
        fo.add_arg("%s* xes" % xed_encoder_request)
        fo.add_code_eol( "xed_bool_t okay=1")
        fo.add_code_eol( "xed_ptrn_func_ptr_t fb_ptrn_function" )

        #import pdb; pdb.set_trace()

        ins_group.sort() # call before emitting group code

        # iform initialization table
        iform_ids_table = ins_group.gen_iform_ids_table()  # table initialization data
        iclasses_number = len(ins_group.get_iclasses())
        iforms_number = len(ins_group.iforms)
        table_type = 'static const xed_uint16_t '
        table_decl = 'iform_ids[%d][%d] = {' % (iclasses_number,
                                                iforms_number)
        fo.add_code(table_type + table_decl)
        for line in iform_ids_table:
            fo.add_code(line)
        fo.add_code_eol('}')

        # isa-set initialization table set 1/0 values to help limit
        # encode to producing the isa-sets present on the specified
        # self.chip.  The all_ones and all_zeros are Very frequently
        # useful optimizations to reduce code size and speed up
        # checking.
        isa_set_table, all_ones, all_zeros = ins_group.gen_iform_isa_set_table( self.isa_set_db[self.chip] )
        if  all_ones==False and all_zeros==False:
            table_type = 'static const xed_bool_t '
            table_decl = 'isa_set[{}][{}] = {{'.format(iclasses_number, iforms_number)
            fo.add_code(table_type + table_decl)
            for line in isa_set_table:
                fo.add_code(line)
            fo.add_code_eol('}')
        
        get_iclass_index = 'xed_encoder_get_iclasses_index_in_group'
        obj_name = encutil.enc_strings['obj_str']
        code = 'xed_uint8_t iclass_index = %s(%s)' % (get_iclass_index,obj_name)
        fo.add_code_eol(code)
        pad4 = ' '*4
        pad8 = ' '*8

        for i,iform in enumerate(ins_group.iforms):
            # FIXME:2007-07-05 emit the iform.operand_order check of
            # the xed_encode_order[][] array

            # emit code that checks the operand order
            
            # made special operand orders for 0 1 and 2
            # operands. store the dictionary of operand orders,
            # look up the list. If there are zero entries, no
            # memcmp is needed. If there is one entry, replace the
            # memcmp with an equality check. If there are two
            # operands, replace the memcmp with two equality
            # tests. Otherwise use the memcmp.

            # FIXME 2007-09-11 use the static count of the values of
            # the number of operands rather than looking it up in
            # xed_encode_order_limit. Save many array derefs per
            # encode. 2014-04-15: xed_encode_order_limit[] does not
            # currently show up in the generated code so the above
            # fixme is moot.

            
            # This "if" is for encoder chip checking. if ENCODE_FORCE
            # is set, we let everything encode.  Otherwise we use the
            # isa_set array set using the specified --encoder-chip at
            # comple time.
            if  all_ones:
                fo.add_code('if (1) { // ALL ONES')
            elif all_zeros:
                fo.add_code('if (xed3_operand_get_encode_force(xes)) { // ALL ZEROS')
            else:
                fo.add_code('if (xed3_operand_get_encode_force(xes) || isa_set[iclass_index][{}]) {{ // MIXED'.format(i))
                
            try:
                operand_order = self.all_operand_name_list_dict[iform.operand_order_key]
            except:
                operand_order = None
            cond1 = None
            nopnd = None
            optimized = False
            if operand_order:
                nopnd = len(operand_order.lst)
                if 0:
                    msge("OPNDORDER for group %d is (%d) %s " % (
                        group_index, 
                        nopnd, 
                        str(operand_order.lst)))
                cond1 = "xes->_n_operand_order == %d" % (nopnd)
                if nopnd==0:
                    optimized = True
                    fo.add_code(pad4 +  "if (%s) {" % (cond1))
                elif nopnd ==1:
                    optimized = True
                    cond2 = "xes->_operand_order[0] == XED_OPERAND_%s"
                    cond2 = cond2 % (operand_order.lst[0])
                    fo.add_code(pad4 + "if (%s && %s) {" % (cond1,cond2))
                elif nopnd ==2:
                    optimized = True
                    cond2 = "xes->_operand_order[0] == XED_OPERAND_%s" 
                    cond2 = cond2 % (operand_order.lst[0])
                    cond3 = "xes->_operand_order[1] == XED_OPERAND_%s"
                    cond3 = cond3 % (operand_order.lst[1])
                    fo.add_code(pad4 + "if (%s && %s && %s) {" % (cond1,cond2,cond3))

            memcmp_type = 'xed_uint8_t' 
            if not optimized:
                if cond1 == None:
                    cond1 = "xed_encode_order_limit[%d]==xes->_n_operand_order"
                    cond1 = cond1 % (iform.operand_order)
                if nopnd == None:
                    cond2 = ("memcmp(xed_encode_order[%d], " +
                            "xes->_operand_order, " +
                            "sizeof(%s)*xed_encode_order_limit[%d])==0")
                    cond2 = cond2 % (iform.operand_order, memcmp_type, 
                                     iform.operand_order)
                else:
                    cond2 = ("memcmp(xed_encode_order[%d], " +
                            "xes->_operand_order, sizeof(%s)*%d)==0")
                    cond2 = cond2 % (iform.operand_order, memcmp_type, nopnd)

                fo.add_code(pad4 + "if (%s && %s) {" % (cond1, cond2))
            if viform():
                msgb("IFORM", str(iform))

            
            # For binding, this emits code that sets
            # conditions_satisfied based on some long expression and
            # then tests it and sets some operand storage fields. For
            # emitting, it checks the iform and emits bits.
            captures = None
            lines = iform.rule.emit_isa_rule(i,ins_group)
            fo.add_code_eol(pad8 + "xed_bool_t conditions_satisfied=0" )
            for  line in lines:
                fo.add_code(pad8 + line)
            
            fo.add_code(pad4 + '} // initial conditions')
            fo.add_code('} // xed_enc_chip_check ')
        
        fo.add_code_eol('return 0')
        fo.add_code_eol("(void) okay")
        fo.add_code_eol("(void) xes")
        return fo
    
    def emit_encode_function_table_init(self):
        ''' emit the functions that inits encoders look up tables. '''
        global output_file_emitters
        func_name = "xed_init_encode_table"
        fo = function_object_t(func_name,"void")
        init_table = []
        template = "    xed_enc_iclass2group[XED_ICLASS_%s] = %d;"
        
        iclass2group = self.ins_groups.get_iclass2group()
        for iclass,group_index in list(iclass2group.items()):
            code = template % (iclass.upper(),group_index) 
            init_table.append(code)
        
        template = "    xed_enc_iclass2index_in_group[XED_ICLASS_%s] = %d;"
        iclass2index_in_group = self.ins_groups.get_iclass2index_in_group()
        for iclass,index in list(iclass2index_in_group.items()):
            code = template % (iclass.upper(),index) 
            init_table.append(code)
        fo.add_lines(init_table)
        filename = 'xed-encoder-init.c'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, 
                                filename, shell_file=False)
        fe.add_header("xed-encoder.h") # FIXME confusing file name.
        fe.start()
        fo.emit_file_emitter(fe)
        fe.close()
        output_file_emitters.append(fe)
                
    def make_isa_encode_functions(self):
        # each iarray dictionary entry is a list: of iform_t objects
        
        ins_code_gen = ins_emit.instruction_codegen_t(self.all_iforms, 
                                                      self.iarray,
                                                      self.gendir,
                                                      self.amd_enabled)
        ins_code_gen.work()
        
        # copy stuff back to this class's members vars
        ins_code_gen.get_values(self) 
        
        i=0
        group_fos = []
        for group in self.ins_groups.get_groups():
            #generate the function object for the group bind function    
            fo = self.make_isa_encode_group(i,group)
            group_fos.append(fo)
            i += 1
        
        self.group_fos = group_fos

    def emit_iforms(self):
        global output_file_emitters
        s = iform_builder.emit_header() # FIXME GLOBAL
        filename = 'xed-encoder-iforms.h'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, filename, shell_file=False)
        fe.headers.remove('xed-internal-header.h')
        fe.add_header("xed-types.h")
        fe.start()
        fe.write(s)
        fe.close()
        output_file_emitters.append(fe)

    def find_nt_by_name(self,nt_name):
        # returns nonterminal_t object that represents the nt name  
        if nt_name in self.nonterminals:
            return self.nonterminals[nt_name]
        elif nt_name in self.decoder_nonterminals:
            return self.decoder_nonterminals[nt_name]
        elif nt_name in self.decoder_ntlufs:
            return self.decoder_ntlufs[nt_name]

        die('could not find nt object for nt name %s\n' % nt_name)
    
    def replace_outreg(self,cond_nt,conds_list):
        '''cond_nt: the condition with nt
        cond_list:  list of conditions that replaces the nt
        
        if the field name of cond_nt is different than OUTREG,
        replace the field name OUTREG in the conds_list '''
        
        if cond_nt.field_name == 'OUTREG':
            return
        for c in conds_list:
            if c.field_name == 'OUTREG':
                c.field_name = cond_nt.field_name
    
    def inline_nt(self,rule,cond_nt,dfile):
        ''' merges the conditions & actions in rule with the 
        conditions & actions in the cond_nt, returns a list of merged rules
        
        rule:    is a rule with nt in the conds list (called UPPER) 
        cond_nt: is the condition with the nt that we want to 
                 inline (called N()) '''
        
        nt = self.find_nt_by_name(cond_nt.rvalue.value)
        dfile.write("working rule:\n %s\n" % str(rule))
        dfile.write("inlining rule: %s\n" % str(nt))
        
        #remove the nt from the conds list
        rule.conditions.and_conditions.remove(cond_nt)
        
        inlined_rules = []
        #add all the rules from N() to UPPER rule 
        for r in nt.rules:
            #copying the conditions & actions 
            #since we are going to modify them later
            conds = copy.deepcopy(r.conditions.and_conditions)
            actions = copy.deepcopy(r.actions)
            
            #replace field name OUTREG in the cond_nt with the original 
            #field name in the rule  
            self.replace_outreg(cond_nt,conds)
            
            if conds[0].is_otherwise() and actions:
                if actions[0].is_nothing() or actions[0].is_error():
                    # for otherwise -> nothing/error we do nothing.
                    # if we have not succeeded to satisfy the lower nt ( N() ) 
                    # the UPPER rule will simply be rejected, 
                    # and we will continue to try satisfy the next rule.
                    continue
                else:
                    err = ("otherwise condition may get only error or"+
                           "nothing actions in NT: " + nt.name)
                    die(err)      

            new_upper_rule = copy.deepcopy(rule)
            new_upper_rule.conditions.and_conditions.extend(conds)
            
            if actions and actions[0].is_error():
                #if we have error action in the canonical nt take it as 
                #the only action and do not append it to other actions
                new_upper_rule.actions = actions
            elif actions and actions[0].is_nothing():
                #appending nothing actions does not have any affect
                pass 
            elif new_upper_rule.actions and new_upper_rule.actions[0].is_nothing():
                new_upper_rule.actions = actions 
            else:
                upper_actions = new_upper_rule.actions
                new_upper_rule.actions = actions
                new_upper_rule.actions.extend(upper_actions)
            dfile.write("new rule %s\n" % str(new_upper_rule))
            inlined_rules.append(new_upper_rule)
        return inlined_rules
    
    def inline_conditions(self,nt_map,dfile):
        '''we are going to inline all the nt in the condition list
        example:
        the rule(lets call it UPPER): 
            A=1 BASE=N() -> X=0
        the nt N() is: 
            OUTREG=EAX -> Z=1    
            OUTREG=RAX -> Z=2  
        the inlined rule are: 
            A=1 BASE=EAX -> X=0 Z=1
            A=1 BASE=RAX -> X=0 Z=2    
            
        nt_map is a map of nt name to nonterminal_t  '''    

        for nt_name in nt_map:
            nt = nt_map[nt_name]
            rules_with_nt = []
            dfile.write('nt: %s\n' % nt_name)
            for rule in nt.rules:
                cond_nt = rule.get_nt_in_cond_list()
                if cond_nt:
                    #collect all the rules with nt
                    rules_with_nt.append(rule)
                    
                    #we have a nt in the condtion list
                    #create new inlined ruels
                    inlined_rules = self.inline_nt(rule,cond_nt,dfile)
                    nt.rules.extend(inlined_rules)
            
            #now delete all the rules with nt in the condition list
            for rule in rules_with_nt:
               nt.rules.remove(rule)

    def run(self):
        # this is the main loop

        # read the state bits 
        f = self.files.state_bits_file
        lines = open(f,'r').readlines()
        self.state_bits = self.parse_state_bits(lines)
        del lines

        # writes self.sequences and self.nonterminals
        self.read_encoder_files()
        # writes self.decoder_nonterminals and self.decoder_ntlufs
        self.read_decoder_files()

        if vdumpinput():
            self.dump()
        
        ## inline all the nt in the conditions section
        dfile = open(mbuild.join(self.gendir,'inline_nt.txt'),'w')
        self.inline_conditions(self.nonterminals,dfile)
        self.inline_conditions(self.decoder_ntlufs,dfile)
        dfile.close()
        
        self.make_sequence_functions()
        
        f_gen = nt_func_gen.nt_function_gen_t(self,storage_fields)
        fos, operand_lu_fos = f_gen.gen_nt_functions()
        self.emit_lu_functions(operand_lu_fos)
        self.functions.extend(fos)
        
        self.make_nonterminal_functions(self.nonterminals)
        self.make_nonterminal_functions(self.decoder_ntlufs)
        self.make_nonterminal_functions(self.decoder_nonterminals)

        self.make_encode_order_tables()# FIXME  too early?
        # emit the per instruction bind & emit functions
        self.make_isa_encode_functions()
        self.emit_group_encode_functions()
        
        self.emit_lu_tables()
        self.emit_encoder_iform_table()
        # write the dispatch table initialization function
        self.emit_encode_function_table_init()
        
        self.emit_function_bodies_and_header_numbered()

        self.emit_iforms()

    def look_for_encoder_inputs(self): 
        encoder_inputs_by_iclass = {}  # dictionary mapping iclass -> set of field names
        encoder_nts_by_iclass = {}  # dictionary mapping iclass -> set of nt names
        for iclass,iform_list in self.iarray.items():
            encoder_field_inputs = set()
            encoder_nts = set()
            for iform  in iform_list:
                (field_set,nt_set) = iform.find_encoder_inputs()
                #msg("FIELDS: %s" % ' '.join(field_set))
                #msg( "NTS: %s" % ' '.join(nt_set))
                encoder_field_inputs |= field_set
                encoder_nts |= nt_set
                #msg("FIELDS: %s" % ' '.join(encoder_field_inputs))
                #msg( "NTS: %s" % ' '.join(encoder_nts))
            encoder_inputs_by_iclass[iclass] = encoder_field_inputs
            encoder_nts_by_iclass[iclass] = encoder_nts

        for iclass in encoder_inputs_by_iclass.keys():
            fld_set = encoder_inputs_by_iclass[iclass]
            nt_set  = encoder_nts_by_iclass[iclass]
            if vinputs():
                msg("EINPUTS: %15s FIELDS: %s \tNTS: %s" %
                    (iclass, ", ".join(fld_set), ", ".join(nt_set)))

    def make_encode_order_tables(self):
        global output_file_emitters
        self.all_operand_name_list_dict = self._collect_ordered_operands()
        (init_order_fo,max_entries, max_operands) = \
                self._emit_operand_order_array(self.all_operand_name_list_dict)
        filename = 'xed-encoder-order-init.c'
        fe = xed_file_emitter_t(self.xeddir, self.gendir,filename, 
                                shell_file=False)
        fe.start()
        init_order_fo.emit_file_emitter(fe)
        fe.close()
        self.max_operand_order_entries = max_entries
        self.max_operand_order_operands = max_operands
        output_file_emitters.append(fe)


    def emit_encode_defines(self):
        global output_file_emitters
        filename = 'xed-encoder-gen-defs.h'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, filename, shell_file=False)
        fe.headers.remove('xed-internal-header.h')
        fe.start()
        fe.write("#define XED_ENCODE_ORDER_MAX_ENTRIES  %d\n" % 
                 self.max_operand_order_entries)
        fe.write("#define XED_ENCODE_ORDER_MAX_OPERANDS %d\n" % 
                 self.max_operand_order_operands)
        fe.write("#define XED_ENCODE_MAX_FB_PATTERNS %d\n" % 
                 self.max_fb_ptrns)
        fe.write("#define XED_ENCODE_MAX_EMIT_PATTERNS %d\n" % 
                 self.max_emit_ptrns)
        fe.write("#define XED_ENCODE_FB_VALUES_TABLE_SIZE %d\n" % 
                 self.fb_values_table_size)
        fe.write("#define XED_ENCODE_MAX_IFORMS %d\n" % self.total_iforms)
        fe.write("#define XED_ENC_GROUPS %d\n" % 
                 self.ins_groups.num_groups())
        fe.close()
        output_file_emitters.append(fe)
        
    def _collect_ordered_operands(self):
        """Return a dictionary of ordered operand name lists that
        include just the encoder inputs. We denote the key to index
        this dictionary in each iform as iform.operand_order"""

        all_operand_name_list_dict = {}
        for iclass,iform_list in self.iarray.items():
            for niform,iform  in enumerate(iform_list):
                ordered_operand_name_list =  iform.make_operand_name_list()
                key = "-".join(ordered_operand_name_list)
                if key in all_operand_name_list_dict:
                    n = all_operand_name_list_dict[key].n
                else:
                    n = len(all_operand_name_list_dict)
                    all_operand_name_list_dict[key] = operand_order_t(n,
                                                                      ordered_operand_name_list)
                iform.operand_order = n
                iform.operand_order_key = key
        _vmsgb("TOTAL ENCODE OPERAND SEQUENCES: %d" % (len(all_operand_name_list_dict)))

        if vopseq():
            for iclass,iform_list in self.iarray.items():
                for niform,iform  in enumerate(iform_list):
                        msg("OPSEQ: %20s-%03d: %s" % 
                            (iclass, niform+1,
                             ", ".join(all_operand_name_list_dict[iform.operand_order_key].lst)))
        return all_operand_name_list_dict

    def _emit_operand_order_array(self, all_operand_name_list_dict):
        """Return a function that initializes the encode order array"""
        fname = "xed_init_encoder_order"
        fo = function_object_t(fname, 'void')
        operands = 0 # columns
        entries = 0 # rows
        for oo in all_operand_name_list_dict.values(): # stringkeys -> operand_order_t's
            for j,o in enumerate(oo.lst):
                fo.add_code_eol("xed_encode_order[%d][%d]=XED_OPERAND_%s" % (oo.n,j,o))
            t = len(oo.lst)
            fo.add_code_eol("xed_encode_order_limit[%d]=%d" % (oo.n,t))

            if entries < oo.n+1:
                entries = oo.n+1
            if operands < t:
                operands = t
        return (fo, entries, operands)

    def dump(self):
        msgb("NONTERMINALS")
        for nt in self.nonterminals.values():
            msg(str(nt))
        msgb("SEQUENCERS")
        for s in self.sequences.values():
            msg(str(s))

    def make_sequence_functions(self):
        # we pass in the list of known sequences so that we know to
        # call the right kind of function from the sequence function
        # we are creating.
        for s in self.sequences.values():
            fo = s.create_function(self.sequences)
            self.functions.append(fo)

    def make_nonterminal_functions(self, nts):
        """For each nonterminal, we create two versions if it is not a
        NTLUF. One version does the required bindings. The other
        version emits the required bytes"""
        
        for nt in nts.values():
            _vmsgb("SORTING FOR SIZE", nt.name)
            nt.sort_for_size()
            if nt.is_ntluf():
                if nt.name in nt_func_gen.get_complicated_nt():
                    fo = nt.create_function(bind_or_emit='NTLUF')
                    self.functions.append(fo)
            else:
                if nt.name in nt_func_gen.get_complicated_nt():
                    fo = nt.create_function(bind_or_emit='BIND')
                    self.functions.append(fo)
                fo = nt.create_function(bind_or_emit='EMIT')
                self.functions.append(fo)
                
    def emit_function_headers(self,fname_prefix,fo_list):
        global output_file_emitters
        filename = fname_prefix + '.h'
        gendir = os.path.join(self.gendir, 'include-private')
        fe = xed_file_emitter_t(self.xeddir, gendir, 
                                filename, shell_file=False)
        fe.start()
        for fo in fo_list:
            s = fo.emit_header()
            fe.write(s)
        fe.close()
        output_file_emitters.append(fe)
        
    def emit_function_bodies_and_header(self,fname_prefix,headers,fo_list):
        global output_file_emitters
        filename = fname_prefix+ '.c'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, 
                                filename, shell_file=False)
        fe.add_header(headers)
        fe.start()
        for fo in fo_list:
            s = fo.emit()
            fe.write(s)
        fe.close()
        self.emit_function_headers(fname_prefix,fo_list)
        output_file_emitters.append(fe)

    def emit_function_bodies_and_header_numbered(self):
        filename_prefix = 'xed-encoder'
        
        headers = ['xed-encode-private.h', 'xed-enc-operand-lu.h',
                   'xed-operand-accessors.h']
        fe_list = emit_function_list(self.functions,
                                     filename_prefix,
                                     self.xeddir,
                                     self.gendir,
                                     os.path.join(self.gendir, 'include-private'),
                                     other_headers=headers)
        if 0:
            # move the generated header file to the private generated headers
            efile = os.path.join(self.gendir, 'include-private', 'xed-encoder.h')
            remove_file(efile)
            os.rename(os.path.join(self.gendir, 'xed-encoder.h'), efile)
        output_file_emitters.extend(fe_list)
        
    def emit_lu_functions(self, fos):
        ''' emit the list of lookup functions '''
        filename_prefix = 'xed-enc-operand-lu'
        headers = ["xed-encode.h", "xed-operand-accessors.h"]
        self.emit_function_bodies_and_header(filename_prefix,headers,fos)
        
    def _emit_functions_lu_table(self,fe, type, values, table_name, 
                                 size_def, per_line=1):
        table_def = "const %s %s[%s] = {" % (type,table_name,size_def)
        fe.write(table_def)
        indent = ' '*12
        fe.write(indent)
        for i,val in enumerate(values):
            if i % per_line == 0:
                fe.write('\n%s' % indent)
            fe.write("%s," % val)
        fe.write('\n};\n')
        
    def emit_lu_tables(self):
        '''emit the function pointers tables '''
        
        filename_prefix = 'xed-enc-patterns'
        headers = ['xed-encode.h','xed-encoder.h','xed-operand-accessors.h']
        fos = self.fb_ptrs_fo_list + self.emit_ptrs_fo_list
        self.emit_function_bodies_and_header(filename_prefix,headers,fos)
        
        h_filename = "%s.h" % filename_prefix
        filename = 'xed-encoder-pattern-lu.c'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, 
                                filename, shell_file=False)
        headers = [h_filename, 'xed-encoder-gen-defs.h', 'xed-encoder.h',
                   'xed-enc-groups.h']
        fe.add_header(headers)
        fe.start()
        
        f_names = [ x.function_name for x in self.fb_ptrs_fo_list]
        self._emit_functions_lu_table(fe, 'xed_ptrn_func_ptr_t', 
                                      f_names, 'xed_encode_fb_lu_table', 
                                      'XED_ENCODE_MAX_FB_PATTERNS')
        fe.write('\n\n\n')
        f_names = [ x.function_name for x in  self.emit_ptrs_fo_list]
        self._emit_functions_lu_table(fe, 'xed_ptrn_func_ptr_t',
                                      f_names, 'xed_encode_emit_lu_table',
                                      'XED_ENCODE_MAX_EMIT_PATTERNS')
        
        fe.write('\n\n\n')
        self._emit_functions_lu_table(fe,'xed_uint8_t', 
                                      self.fb_values_list, 
                                      'xed_encode_fb_values_table',
                                      'XED_ENCODE_FB_VALUES_TABLE_SIZE',20)
        
        fe.write('\n\n\n')
        f_names = [  x.function_name for x in  self.group_fos]
        self._emit_functions_lu_table(fe,'xed_encode_function_pointer_t', 
                                      f_names, 'xed_encode_groups',
                                      'XED_ENC_GROUPS')

        
        fe.close()
        output_file_emitters.append(fe)
        
    def emit_encoder_iform_table(self):
        filename = 'xed-encoder-iforms-init.c'
        fe = xed_file_emitter_t(self.xeddir, self.gendir, 
                                filename, shell_file=False)
        fe.add_header('xed-ild.h')
        fe.add_header('xed-ild-enum.h')        
        fe.start()
        
        ptrn = ("/*(%4d)%20s*/  {%4d, %4d, %4s, %4d}")
        iform_definitions = []
        for iform in self.all_iforms:#iforms:
            iform_init = ptrn % (iform.rule.iform_id,
                                 iform.iclass,
                                 iform.bind_func_index,
                                 iform.emit_func_index,
                                 hex(iform.nominal_opcode),
                                 iform.fb_index)
            iform_definitions.append(iform_init)
        
        self._emit_functions_lu_table(fe, 'xed_encoder_iform_t', 
                                      iform_definitions, 'xed_encode_iform_db', 
                                      'XED_ENCODE_MAX_IFORMS')
        fe.close()
        output_file_emitters.append(fe)
            
    def emit_group_encode_functions(self):
        filename_prefix = 'xed-enc-groups'
        
        headers = ['xed-encode-private.h', 'xed-enc-operand-lu.h',
                   'xed-operand-accessors.h','xed-encoder.h']
        
        self.emit_function_bodies_and_header(filename_prefix,headers,
                                             self.group_fos) 

##############################################################################
def setup_arg_parser():
    arg_parser = optparse.OptionParser()

    arg_parser.add_option('--gendir',
                      action='store', dest='gendir', default='obj',
                      help='Directory for generated files')
    arg_parser.add_option('--xeddir',
                      action='store', dest='xeddir', default='.',
                      help='Directory for generated files')

    arg_parser.add_option('--input-fields',
                      action='store', dest='input_fields', default='',
                      help='Operand storage description  input file')
    arg_parser.add_option('--input-state',
                      action='store', dest='input_state', default='xed-state-bits.txt',
                      help='state input file')
    arg_parser.add_option('--input-regs',
                      action='store', dest='input_regs', default='',
                      help='Encoder regs file')
    arg_parser.add_option('--enc-patterns',
                      action='append', dest='enc_patterns', default=[],
                      help='Encoder input files')
    arg_parser.add_option('--enc-dec-patterns',
                      action='append', dest='enc_dec_patterns', default=[],
                      help='Decoder input files used by the encoder')
    arg_parser.add_option('--isa',
                      action='store', dest='isa_input_file', default='',
                      help='Read structured input file containing the ISA INSTRUCTIONS() nonterminal')
    arg_parser.add_option('--map-descriptions',
                          action='store',
                          dest='map_descriptions_input_fn',
                          default='',
                          help='map descriptions input file')
    arg_parser.add_option('--no-amd',
                      action='store_false', dest='amd_enabled', default=True,
                      help='Omit AMD instructions')
    arg_parser.add_option('--verbosity', '-v',
                      action='append', dest='verbosity', default=[],
                      help='list of verbosity tokens, repeatable.')
    arg_parser.add_option('--chip-models',
                          action='store', 
                          dest='chip_models_input_fn', 
                          default='',
                          help='Chip models input file name')
    arg_parser.add_option('--chip',
                          action='store', 
                          dest='chip', 
                          default='ALL',
                          help='''Name of the target chip. Default is ALL.  Setting the target chip
                                limits what encode will produce to
                                only those instructions valid for that
                                chip.''')
    return arg_parser


if __name__ == '__main__':
    arg_parser = setup_arg_parser()
    (options, args) = arg_parser.parse_args()
    set_verbosity_options(options.verbosity)
    enc_inputs = encoder_input_files_t(options)
    enc = encoder_configuration_t(enc_inputs, options.chip, options.amd_enabled)
    enc.run()
    enc.look_for_encoder_inputs()      # exploratory stuff
    enc.emit_encode_defines()  # final stuff after all tables are sized
    enc.dump_output_file_names()
    sys.exit(0)
