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
from verbosity import *
import patterns
import genutil
import encutil
import mbuild
import copy

def msgb(s,b=''):
    mbuild.msgb(s,b)

def gen_return_action(ret_val):
    ''' create new action with type return '''
    action = action_t("return {}".format(ret_val))
    return action

def dummy_emit(act_in,name):
    ''' creating new action based on the input action with 
        dummy emit type and name as the field name'''
    
    action = copy.deepcopy(act_in)
    action.emit_type = 'dummy'
    action.field_name = name
    return action
    
def gen_dummy_fb(fb):
    ''' create new fb action that sets the value to -1 '''
    str = "%s=-1" % fb
    action = action_t(str)
    return action

def gen_null_fb():
    ''' create new fb with fake fb name:"null" and value 0
        using this to represent null pointers'''
    str = "null=0" 
    action = action_t(str)
    return action
    
def gen_nt_action(nt):
    ''' create new action with type nt '''
    str = "%s()" % nt
    action = action_t(str)
    return action

class action_t(object):
    """This is the right hand side of the rule_t. It can be a (1)
    field binding (2) a byte encoding, (3) 'error' or (4) 'nothing'."""

    
    def __init__(self, arg_action):
        # field bindings (FB) are OD=value
        self.type = None #  'FB', 'emit', 'nt', 'error', 'nothing', 'return'
        self.field_name = None
        self.value = None
        self.nt = None
        self.ntluf = None
        self.int_value = None
        self.emit_type = None # 'numeric', 'letters', 'reg'
        self.nbits = 0
        if vaction():
            msgb("ARGACTION", arg_action)
        if arg_action in ['nothing', "NOTHING"]:
            self.type = 'nothing'
            return
        
        b = patterns.return_pattern.search(arg_action)
        if b:
            self.type = 'return'
            self.value = b.group('retval')
            return 
        
        # in the inputs, "error" gets expanded to "ERROR=1" via the statebits.
        if arg_action == 'error' or arg_action == "ERROR" or arg_action == 'ERROR=1':
            self.type = 'error'
            return

        b = patterns.bit_expand_pattern.search(arg_action)
        if b:
            expanded = b.group('bitname') * int(b.group('count'))
            action = patterns.bit_expand_pattern.sub(expanded,arg_action)
        else:
            action = arg_action
            
        #msgerr("CHECKING: %s" % action)

        a = patterns.equals_pattern.search(action)
        if a:
            # field binding
            #msgerr("FIELD BINDING: %s" % action)
            self.field_name = a.group('lhs')
            rhs = a.group('rhs')
            if patterns.decimal_pattern.match(rhs) or \
               patterns.binary_pattern.match(rhs) or \
               patterns.hex_pattern.match(rhs):
                self.int_value = genutil.make_numeric(rhs)
                self.value = str(self.int_value)
                #msgb("SET RHS", "%s -> %s" % (rhs,self.value))
            else:
                self.value = rhs
                
            self.type = 'FB'
            return
        
        nt = patterns.nt_name_pattern.match(action)
        if nt:
            # NTLUF or NT. Only shows up on decode-oriented rules
            self.nt = nt.group('ntname')
            self.type = 'nt'
            return
        ntluf = patterns.ntluf_name_pattern.match(action)
        if ntluf:
            # NTLUF or NT. Only shows up on decode-oriented rules
            self.ntluf = ntluf.group('ntname')
            self.type = 'ntluf'
            return
        
        cp = patterns.lhs_capture_pattern_end.match(action) 
        if cp:
            self.type = 'emit'
            self.value = cp.group('bits')
            self.field_name = cp.group('name').lower()
            #msgerr("EMIT ACTION %s" % action)
            self.classify()
            return 
        
        # simple byte encoding
        self.type = 'emit'
        self.field_name = None
        #msgerr("EMIT ACTION %s" % action)
        self.value = action
        self.classify()
        

    def classify(self):
        if patterns.decimal_pattern.match(self.value):
            self.emit_type = 'numeric'
            self.int_value = int(self.value)
            t = hex(self.int_value)
            self.nbits = 4*len(t[2:])
            if vclassify():
                msgb("CLASSIFY", "%s as decimal values" % (self.value))
            return
            
        if patterns.hex_pattern.match(self.value):
            self.emit_type = 'numeric'
            self.int_value = int(self.value,16)
            self.nbits = 4*(len(self.value)-2)  # drop the 0x, convert nibbles to bits
            if vclassify():
                msgb("CLASSIFY", "%s as hex" % (self.value))
            return
        if patterns.letter_and_underscore_pattern.match(self.value):
            self.emit_type = 'letters'
            t = self.value
            t = genutil.no_underscores(t)
            self.nbits = len(t)
            if vclassify():
                msgb("CLASSIFY", "%s as letters" % (self.value))
            return
        b = patterns.binary_pattern.match(self.value)   # leading "0b"
        if b:
            self.emit_type = 'numeric'
            t = '0b' + b.group('bits') # pattern match strips out 0b
            self.int_value = genutil.make_numeric(t)
            bits_str = genutil.make_binary(t)
            self.nbits = len(bits_str)
            if vclassify():
                msgb("CLASSIFY", "%s as explicit-binary -> int = %d nbits=%d [%s,%s]" % (self.value,self.int_value,self.nbits,t,bits_str))
            return
        if patterns.bits_and_letters_underscore_pattern.match(self.value):
            self.emit_type = 'letters'
            v = genutil.no_underscores(self.value)
            self.nbits = len(v)
            if vclassify():
                msgb("CLASSIFY", "%s as mixed-letters" % (self.value))
            return


        if patterns.simple_number_pattern.match(self.value):
            self.emit_type = 'numeric'
            self.int_value = genutil.make_numeric(self.value)
            t = hex(self.int_value)
            self.nbits = 4*len(t[2:])
            if vclassify():
                msgb("CLASSIFY", "%s as simple-number" % (self.value))
            return

        genutil.die("unknown pattern")
            
    def naked_bits(self):
        ''' returns True if the type is emit but there is no field name. '''
        if self.type == 'emit' and self.field_name == None:
            return True
        return False            
            
    def is_nothing(self):
        return self.type == 'nothing'
    def is_error(self):
        return self.type == 'error'
    def is_return(self):
        return self.type == 'return'
    
    def is_nonterminal(self):
        if self.nt:
            return True
        return False
    def is_ntluf(self):
        if self.ntluf:
            return True
        return False
    
    def is_field_binding(self):
        """Return True if this action is a field binding."""
        if self.type == 'FB':
            return True
        return False

    def is_emit_action(self):
        """Return True if this action is an emit action."""
        if self.type == 'emit':
            return True
        return False

    def __str__(self):
        s = []
        s.append(str(self.type))
        if self.nt:
            s.append(" NT[%s]" % (self.nt))
        if self.field_name:
            s.append(" ")
            s.extend([self.field_name,'=',self.value])
        elif self.value != None:
            s.append(" ")
            s.append(self.value)
        if self.emit_type:
            s.append(" emit_type=%s" % self.emit_type)
        if self.int_value != None:
            s.append(" value=0x%x" % self.int_value)
        if self.nbits != 0:
            s.append(" nbits=%d" % self.nbits)
        return ''.join(s)

    def get_str_value(self):
        if self.is_field_binding() or self.is_return():
            return self.value
        if self.is_nonterminal():
            return self.nt
        if self.is_ntluf():
            return self.ntluf
        
        err = "unsupported type: %s for function get_str_value" % self.type
        genutil.die(err)
    
    
    def emit_code(self, bind_or_emit):
        if self.is_error():
            #return [ '    return 0; /* error */' ]
            # FIXME? bind ERROR=1?
            return [ '    okay=0;  /* error */' ]
        elif self.is_nothing():
            return [ '    return 1; /* nothing */' ]

        elif self.is_field_binding():
            return self._generate_code_for_field_binding(bind_or_emit)
            
        elif self.is_emit_action():
            return self._generate_code_for_emit_action(bind_or_emit)
        
        elif self.is_nonterminal():
            return self._emit_nonterminal_code(bind_or_emit)
        
        return [ '/* FIXME action code not done yet for ' + self.__str__() + '*/' ]

    def _generate_code_for_field_binding(self, bind_or_emit):
        if bind_or_emit == 'EMIT':
            return []
        # we are in BIND
        if self.field_name == 'NO_RETURN':
            return [ '/* no code required for NO_RETURN binding */']
        operand_setter = "%s_set_%s" % (encutil.enc_strings['op_accessor'],
                                            self.field_name.lower())
        obj_name = encutil.enc_strings['obj_str']
        s = '    %s(%s,%s);' % (operand_setter,
                            obj_name, self.value)
        if self.field_name == 'ERROR':
            return [ s, "    return 0; /* error */" ]
        return [ s ]
    
    def _generate_code_for_emit_action(self,bind_or_emit):
        """Emit code for emit action """
        if bind_or_emit == 'BIND':
            if self.emit_type == 'letters' or self.field_name == None:
                return ''
            elif self.emit_type == 'numeric':
                op_accessor = encutil.enc_strings['op_accessor']
                operand_setter = "%s_set_%s" % (op_accessor,
                                                self.field_name.lower())
                obj_name = encutil.enc_strings['obj_str']
                hex_val = hex(self.int_value)
                code = "%s(%s, %s);" % (operand_setter, obj_name, hex_val)
                return ['    ' + code]
            else:
                genutil.die("Unknown emit_type %s" % self.emit_type)
        else:  # EMIT
            emit_util_function = encutil.enc_strings['emit_util_function']
            obj_name = encutil.enc_strings['obj_str']
            nbits = self.nbits
            code = ''
            if self.field_name == None:
                if  self.emit_type == 'numeric':
                    hex_val = hex(self.int_value)
                    code = "%s(%s, %d, %s);" % (emit_util_function,obj_name,
                                                nbits,hex_val)
                else:
                    genutil.die("must have field name for letter action")
            else:
                op_accessor = encutil.enc_strings['op_accessor']
                operand_getter = "%s_get_%s(%s)" % (op_accessor, 
                                                    self.field_name.lower(),
                                                    obj_name)
                code = "%s(%s, %d, %s);" % (emit_util_function,
                                            obj_name,nbits,operand_getter)
            return ['    ' + code]
    
    def _emit_nonterminal_code(self,bind_or_emit):
        """Emit code for calling a nonterminal in bind or emit modes"""
        
        nt_prefix = "%s" % encutil.enc_strings['nt_prefix']
        obj_name = encutil.enc_strings['obj_str']
        if bind_or_emit =='BIND':
            s = []
            s.append('    if (okay)')
            s.append('        okay = %s_%s_%s(%s);' %(nt_prefix,self.nt,
                                                       bind_or_emit,obj_name))
            return s
    
        #'EMIT'
        code = '%s_%s_%s(%s);' %(nt_prefix, self.nt, bind_or_emit, obj_name)
        return ['    ' + code] 
