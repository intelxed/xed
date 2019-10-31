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
import math
import collections

import genutil
import ildutil
import codegen
import hashmul
import hashfks
import hashlin
import xedhash
# phash means "perfect hash".

_l1_bucket_max = 8  # FIXME: also in hashfks.py

   
#FIXME: using 64 bits for _hkey_ctype because sometimes 16bi-UIMM00 is
#a constraint and we are out of 32 bits for hashing.
#However, this takes too much space. We can check how many bits
#are used and decide based on that about the key type, and in most cases
#that will be 32 bits.
_notfound_str = '0'
   
class phash_t(object):
    def __init__(self, cdict, hash_f):
        self.cdict = cdict
        self.hash_f = hash_f
        self.x2hx = {}
        self.hx2x = {}

    def is_minimal(self):
        return self.hash_f.get_table_size() == len(self.cdict.tuple2rule)

    #generate the operands getters
    def add_cgen_key_lines(self, fo):
        #declare hash key variable
        key_str = self.cdict.strings_dict['key_str']
        key_type = self.cdict.strings_dict['key_type']
        fo.add_code_eol('%s %s = 0' % (key_type,key_str))
        bit_shift = 0
        nt_lups = []
        for i,cname in enumerate(self.cdict.cnames):
            access_str, lu_name = self.cdict.get_operand_accessor(cname)
            nt_lups.append(lu_name)

            #constraints might have 1,2 or 3 bit widths
            #and we allocate bits in the key vector appropriately
            #e.g REXB operand gets only 1 bit in the key
            #and RM gets 3 bits
            shift_val = ('(%s)' % bit_shift)
            bit_shift += self.cdict.op_widths[cname]
            code = 'key += (%s) << (%s)' % (access_str, shift_val)
            fo.add_code_eol(code)
        fo.add_code_eol('return %s' % key_str)
        return nt_lups

    def add_lookup_lines(self, fo):
        
        key_validation = self.hash_f.add_key_validation(self.cdict.strings_dict)
        fo.add_code('%s {' % key_validation)
                                                 
        actions = self.cdict.action_codegen.emit_actions()
        for a in actions:
            fo.add_code_eol("    " + a)
        if self.cdict.action_codegen.has_fcall():
            fo.add_code_eol("    return res")
        #FIXME: this is a temporary, when we will implement the iform encoding
        # we will be able to remove this code   
        if genutil.field_check(self.cdict, 'ntluf') or \
            genutil.field_check(self.cdict, 'nt'):
            fo.add_code_eol("    return 1")    
        fo.add_code('}') 

        # get the default action that will executed when we did not hit valid 
        # look up table entry
        default = self.cdict.action_codegen.emit_default()
        fo.add_code('else{')
        for line in default:
            fo.add_code_eol("    %s" % line)
        
        fo.add_code('}')

    def add_find_lines(self, fo):

        #apply hash function on the key
        hash_expr = self.hash_f.emit_cexpr(self.cdict.strings_dict['key_str'])
        fo.add_code_eol('%s = %s' % (self.cdict.strings_dict['hidx_str'], hash_expr))
        #lookup entry in the table
        self.add_lookup_lines(fo)

    #emit the operands lookup function
    def add_op_lu_function(self,fo,lu_function):
        if hasattr(self.hash_f,'emit_cvar_decl'):
            fo.add_code_eol(self.hash_f.emit_cvar_decl())

        fo.add_code_eol('%s %s = 0' % (self.cdict.strings_dict['key_type'],
                                       self.cdict.strings_dict['key_str']))
        fo.add_code_eol('%s %s = 0' % (self.cdict.strings_dict['hidx_type'],
                                       self.cdict.strings_dict['hidx_str']))
        
        #Initializing res to 1 since it will not always be read.
        if self.cdict.action_codegen.has_fcall():
            fo.add_code_eol('%s %s = 1' % (self.cdict.strings_dict['hidx_type'],
                                           'res'))
        obj_str = self.cdict.strings_dict['obj_str']
        #FIXME: this is a temporary, when we will implement the iform encoding
        # we will be able to remove this code
        if genutil.field_check(self.cdict, 'ntluf'):
            fo.add_code_eol('xed3_operand_set_outreg(%s,arg_reg)' % obj_str)
            
        lu_code = 'key = %s(%s)' % (lu_function, obj_str)
        fo.add_code_eol(lu_code)

    def add_lu_table(self, fo):
        need_validation = self.hash_f.need_hash_index_validation() 
        if self.cdict.action_codegen.no_actions() and not need_validation:
            #if we do not have any actions and we do not need to do
            #hash index validation, we do not need to add a look up
            #table.
            return
        
        actions_str = self.cdict.action_codegen.get_actions_desc()
        entry_desc = 'typedef struct {'
        if need_validation:
            entry_desc += 'xed_uint32_t key;'
        entry_desc += ' %s} ' % actions_str
        entry_type = self.cdict.strings_dict['lu_entry']
        entry_desc += '%s' % entry_type 
        
        
        fo.add_code_eol(entry_desc)
        arr_def = 'static const %s %s[%d] = {' % (
            entry_type,
            self.cdict.strings_dict['table_name'],
            self.hash_f.get_table_size() )
        fo.add_code(arr_def)

        elems = []

        for hx in range(0, self.hash_f.get_table_size()):
            if hx in self.hx2x:             
                x = self.hx2x[hx]
                t = self.cdict.int2tuple[x]
                actions = self.cdict.action_codegen.get_values(t)
                ptrn = self.cdict.get_ptrn(t)
                
                if need_validation:
                    elem = '/*h(%d)=%d %s*/ {%d, %s}'    
                    elem = elem % (x, hx, ptrn , x, actions)
                else:
                    elem = '/*h(%d)=%d %s*/ {%s}'
                    elem = elem % (x, hx, ptrn , actions)
            else:
                
                #FIXME: make hx signed int and fill empty
                #slots with -1?
                #Seems it is enough to set value=0, saying that it's an
                #illegal instruction
                
                # FIXME: x is always just one slot ['0']. That works
                # correctly but the code logic makes absolutely no
                # sense.
                x =  self.cdict.action_codegen.get_empty_slots()
                empty_val = ['0'] + x
                elem = '/*empty slot1 */ {%s}' % (",".join(empty_val))
            if hx != (self.hash_f.get_table_size()-1):
                elem += ','
            fo.add_code(elem)

        fo.add_code_eol('}')

    def gen_find_fos(self, fname):  # phash_t
        obj_str = self.cdict.strings_dict['obj_str']
        obj_type = self.cdict.strings_dict['obj_type']
        key_str= self.cdict.strings_dict['key_str']
        hidx_str = self.cdict.strings_dict['hidx_str']
        const = self.cdict.strings_dict['obj_const']
        lu_namespace = self.cdict.strings_dict['lu_namespace']
        
        #FIXME: this is a temporary, when we will implement the iform encoding
        # we will be able to remove this code
        if genutil.field_check(self.cdict, 'ntluf') or \
            genutil.field_check(self.cdict, 'nt'):
            return_type = 'xed_uint32_t'
        elif self.hash_f.kind() == 'trivial':
            return_type = 'xed_uint32_t'
        else:
            return_type = self.cdict.action_codegen.get_return_type()
        static = self.cdict.strings_dict['static']
        fo = codegen.function_object_t(fname,
                                       return_type=return_type,
                                       static=static,
                                       inline=False)

        lu_operands = '_'.join(self.cdict.cnames)
        # temporary function name. we override this later
        lu_operands_fn = 'xed_lu_%s' % lu_operands 
        key_ctype = self.cdict.strings_dict['key_type']

        ild_arg = "%s%s* %s" % (const, obj_type, obj_str)
        fo.add_arg(ild_arg)
        
        if self.hash_f.kind() == 'trivial':
            operand_lu_fo = None
            # rule is a pattern_t
            fo.add_code_eol("return {}".format(self.cdict.rule.ii.inum))
            # avoid parmameter-not-used warnings with compilers that
            # care (like MSVS)
            fo.add_code_eol("(void)d") 
        else:
            operand_lu_fo = codegen.function_object_t(lu_operands_fn,
                                           return_type=key_ctype,
                                           static=False,
                                           inline=False,
                                           force_no_inline=True)
            operand_lu_fo.add_arg(ild_arg)
            if genutil.field_check(self.cdict, 'ntluf'):
                fo.add_arg('xed_reg_enum_t arg_reg')

            #add key-computing code (constraints tuple to integer)
            nt_lups = self.add_cgen_key_lines(operand_lu_fo)
            #Several nonterminals have special getter functions.  The
            #add_cgen_key_lines function returns a list of all the
            #nt_lups and regular cnames.  (lu_operands is not always
            #the same as the underscore-joined nt_lups.)
            lu_operands_fn = 'xed_%s_lu_%s' % (lu_namespace,'_'.join(nt_lups))
            operand_lu_fo.set_function_name(lu_operands_fn)
        
            #add the operands lookup function
            self.add_lu_table(fo)
            self.add_op_lu_function(fo,lu_operands_fn)
            self.add_find_lines(fo)
            
        
        return ([fo],operand_lu_fo)
                            
    def __str__(self):
        lines = ['-----------PHASH-------------']
        lines.append('tuple scheme:')
        line = ''
        lines.append(' '.join(self.cdict.cnames))
        lines.append('m=%d' % self.hash_f.get_table_size())
        lines.append('%s' % self.hash_f)
        lines.append('tuple x -> value')
        for tuple_val in self.tuple_dict.keys():
            x = self.t2x[tuple_val]
            value = self.tuple_dict[tuple_val]
            line = '%s %s -> %s' % (tuple_val,x, str(value))
            lines.append(line)
        lines.append('-------------------------------------')
        return '\n'.join(lines)+ '\n'

    def get_size(self):
        return self.hash_f.get_table_size()

    def update_stats(self, stats):
        stats['3. #hashes'] += 1
        size = self.get_size()
        stats['2. #hentries'] += size
        stats['4. #min_hashes'] += self.is_minimal()
        if size <= 10:
            stats['5. #cdict_size_1_to_10'] += 1
        elif  10 < size and size <= 20:
            stats['6. #cdict_size_10_to_20'] += 1
        elif  20 < size and size <= 100:
            stats['7. #cdict_size_20_to_100'] += 1
        else:
            stats['8. #cdict_size_at_least_100'] += 1

class l1_phash_t(phash_t):
    def __init__(self, cdict, hash_f):
        phash_t.__init__(self, cdict, hash_f)
        for t,x in cdict.tuple2int.items():
            hash_val = self.hash_f.apply(x)
            if hash_val in list(self.x2hx.values()):
                msg = "l1_phash_t: %s\n function is not perfect!\n"
                msg += 'hashval=%d , x2hx: %s' % (hash_val, self.x2hx)
                ildutil.ild_err(msg)
            self.x2hx[x] = hash_val
            self.hx2x[hash_val] = x
           
            # the index attribute is used to determine the ordinal of the emit 
            # rule, adding 1 since legal hash values starts in 0 but 
            # legal ordinal starts at 1 
            self.cdict.tuple2rule[t].index = hash_val + 1 
            

    def __str__(self):
        lines = ['-----------1-LEVEL-PHASH-------------']
        lines.append('tuple scheme:')
        line = ''
        lines.append(' '.join(self.cdict.cnames))
        lines.append('m=%d' % self.hash_f.get_table_size())
        lines.append('%s' % self.hash_f)
        lines.append('tuple x h(x) ->  value')
        for tuple_val in sorted(self.cdict.tuple2rule.keys()):
            x = self.cdict.tuple2int[tuple_val]
            ptrn = self.cdict.get_ptrn(tuple_val)
            action = self.cdict.action_codegen.get_values(tuple_val)
            hx = self.x2hx[x]
            line = '%s %s %s -> %s, %s' % (tuple_val,x, hx, ptrn, action)
            lines.append(line)
        lines.append('-------------------------------------')
        return '\n'.join(lines) + '\n'

class l2_phash_t(phash_t):
    def __init__(self, cdict, hash_f):
        global _l1_bucket_max
        phash_t.__init__(self, cdict, hash_f)

        hx2tuples = collections.defaultdict(list)
        for t,x in self.cdict.tuple2int.items():
            hx = self.hash_f.apply(x)
            if len(hx2tuples[hx]) >= _l1_bucket_max: 
                msg = "l2_phash_t: function does not distribute well!\n"
                msg += 'hashval=%d , hx2tuples: %s' % (hx, hx2tuples)
                ildutil.ild_err(msg)
            hx2tuples[hx].append(t)
            self.x2hx[x] = hx
            self.hx2x[hx] = x

        self.hx2phash = {}
        for hx,tuples in hx2tuples.items():
            new_cdict = self.cdict.filter_tuples(tuples)
            
            # try (1)linear, then (2)hashmul then (3) fks for the 2nd
            # level of hash function.
            phash = None
            if _is_linear(list(new_cdict.int2tuple.keys())):
                phash = _get_linear_hash_function(new_cdict)
            if not phash:
                phash = _find_l1_phash_mul(new_cdict)
            if not phash:
                phash = _find_l1_phash_fks(new_cdict)
                
            if phash:
                self.hx2phash[hx] = phash
            else:
                lines = []
                for k,v in list(new_cdict.tuple2rule.items()):
                    lines.append('%s -> %s'% ((k,), v))
                str = '\n'.join(lines)
                ildutil.ild_err("Failed to find l1 phash for dict %s" %
                                str)
    
    def add_lu_type(self, fo):
        if genutil.field_check(self.cdict, 'ntluf') or \
            genutil.field_check(self.cdict, 'nt'):
            ret_type = 'xed_uint32_t'
        else:
            ret_type = self.cdict.action_codegen.get_return_type()
        fname = self.cdict.strings_dict['luf_name']
        param_name = "%s%s*" % (self.cdict.strings_dict['obj_const'],
                                self.cdict.strings_dict['obj_type'])
        luf_type = "typedef %s (*%s)(%s)" % (ret_type, fname, param_name)
        fo.add_code_eol(luf_type)
        
        lu_entry = self.cdict.strings_dict['lu_entry']
        entry_desc = 'typedef struct {xed_uint32_t key;'
        entry_desc += ' %s l2_func;} %s' % (fname, lu_entry)
        fo.add_code_eol(entry_desc)
        
    def add_lu_table(self, fo, hx2fo):
        self.add_lu_type(fo)
        tname = self.cdict.strings_dict['table_name']
        entry = self.cdict.strings_dict['lu_entry']
        arr_def = 'static const %s %s[%d] = {' % (entry, tname, self.hash_f.get_table_size())
        fo.add_code(arr_def)

        elems = []
        #invert the x2hx mapping
        hx2x = dict((hx,x) for x,hx in self.x2hx.items())

        for hx in range(0, self.hash_f.get_table_size()):
            if hx in hx2fo:
                l1_fo = hx2fo[hx]
                x = hx2x[hx]
                elem = '/*h(%d)=%d */ {%d, %s},'
                elem = elem % (x, hx, x, l1_fo.function_name)
            else:
                #FIXME: make hx signed int and fill empty
                #slots with -1?
                #Seems it is enough to set value=0, saying that it's an
                #illegal instruction
                if self.cdict.strings_dict['obj_const']:
                    elem = '/*empty slot2 */ {0, xed_phash_invalid_const},'
                else:
                    elem = '/*empty slot2 */ {0, xed_phash_invalid},'
                    
            fo.add_code(elem)

        fo.add_code_eol('}')

    def add_lookup_lines(self, fo):
        hentry_str ='%s[%s]' % (self.cdict.strings_dict['table_name'], 
                                self.cdict.strings_dict['hidx_str'])
        #fo.add_code('if(%s.key != 0) {' % hentry_str)
        fo.add_code_eol('return (*%s.l2_func)(%s)' % (
            hentry_str, 
            self.cdict.strings_dict['obj_str'] ))
        #fo.add_code('}')
        #fo.add_code_eol('return %s' % _notfound_str)

    def gen_find_fos(self, fname):  # L2 phash
        obj_str = self.cdict.strings_dict['obj_str']
        obj_type = self.cdict.strings_dict['obj_type']
        const = self.cdict.strings_dict['obj_const']
        hx2fo = {}
        for hx,phash in list(self.hx2phash.items()):
            fid = '%s_%d_l1' % (fname, hx)
            (hx2fo_list,operand_lu_fo) = phash.gen_find_fos(fid)
            if not operand_lu_fo:
               genutil.die("L2 hash cannot have trivial operand lu fn")             
            hx2fo[hx] = hx2fo_list[0]

        fname = '%s' % fname
        if genutil.field_check(self.cdict, 'ntluf') or \
            genutil.field_check(self.cdict, 'nt'):
            return_type = 'xed_uint32_t'
        else:
            return_type = self.cdict.action_codegen.get_return_type()
        
        static = self.cdict.strings_dict['static']
        fo = codegen.function_object_t(fname,
                                       return_type=return_type,
                                       static=static,
                                       inline=False)
        fo.add_arg('%s%s* %s' % (const,obj_type,obj_str))
        self.add_lu_table(fo, hx2fo)
        #we only need to override add_lookup_lines
        lu_fname = operand_lu_fo.function_name
        self.add_op_lu_function(fo, lu_fname)
        self.add_find_lines(fo)
        fos = list(hx2fo.values())
        fos.append(fo)
        #all the operand_lu_fo going to be the same so we just take the last one
        return fos,operand_lu_fo

    def get_size(self):
        size = self.hash_f.get_table_size()
        for phash in list(self.hx2phash.values()):
            size += phash.get_size()
        return size

    def __str__(self):
        lines = ['-----------2-LEVEL-PHASH-------------']
        lines.append('m=%d' % self.hash_f.get_table_size())
        lines.append('%s' % self.hash_f)
        for tuple_val in self.cdict.tuple2rule.keys():
            lines.append('-------------------------------------')
            lines.append('tuple x h(x) ->  l1_phash')
            x = self.cdict.tuple2int[tuple_val]
            hx = self.hash_f.apply(x)
            phash = self.hx2phash[hx]
            line = '%s %s %s ->\n%s' % (tuple_val,x, hx, phash)
            lines.append(line)
        lines.append('-------------------------------------')
        return '\n'.join(lines) + '\n'


def _zero_constraints(cdict):
    if len(cdict.cnames)==0:
        return True
    return False

class trivial_hash_func_t(xedhash.hash_fun_interface_t):
    """This is a hash function that works with no inputs. Always returns true"""
    def __init__(self):
        pass
    def kind(self):
        return "trivial"
    def get_table_size(self):
        return 1
    def apply(self,x):
        return 0 # not used
    def emit_cexpr(self, key_str='key'):
        return '0' # not used
    
    def need_hash_index_validation(self):
        return False
    def __str__(self):
        return "h(x) = always true"
    
def _get_zero_constraint_hash(cdict):
    ''' returns a l1_phash_t that generate a trivial function that is always true'''
    hash_f = trivial_hash_func_t()
    return l1_phash_t(cdict, hash_f)
    
def _is_linear(keys):
    ''' @param keys: list of keys
        @return: True is the keys in the input list are sequential 
    '''
    
    max_key = max(keys)
    min_key = min(keys)
    if (max_key - min_key + 1) == len(keys):
        return True
    return False

def _get_linear_hash_function(cdict):
    ''' returns phash_t object with a linear_funct_t as the hash function'''
    keylist = list(cdict.int2tuple.keys())
    hash_f = hashlin.get_linear_hash_function(keylist)
    return l1_phash_t(cdict, hash_f)    
    


def _find_l1_phash_fks(cdict):
    hashfn =  hashfks.find_fks_perfect(list(cdict.tuple2int.values()))
    if hashfn:
        return l1_phash_t(cdict, hashfn)
    return None


def _find_candidate_lengths_mul(lst):
    """Return integer lengths n, n*1.1, n*1.2, ... n*1.9, n*2"""
    n = len(lst)
    r = [ int(math.ceil((1 + x/10.0)*n)) for x in range(0,11)]
    # avoid duplicates
    s = set()
    for a in r:
        # we avoid length 1 tables for hashmul since they throw away
        # all the bits and should really use the linear hash function
        # stuff.
        if a > 1:
            s.add(a)
    return sorted(list(s))

def _find_l1_phash_mul(cdict):
    candidate_lengths = _find_candidate_lengths_mul(cdict.tuple2int)
    for p in candidate_lengths:
        hash_f = hashmul.hashmul_t(p)
        if hash_f.is_perfect(iter(cdict.tuple2int.values())):
            return l1_phash_t(cdict, hash_f)
        del hash_f
    return None
    


def _find_l2_hash_mul(cdict):
    """Similar to the _find_l1_phash_mul, but not looking for perfection, just
    well distributed stuff"""
    global _l1_bucket_max
    candidate_lengths = _find_candidate_lengths_mul(cdict.tuple2int)
    for p in candidate_lengths:
        hash_f = hashmul.hashmul_t(p)
        if xedhash.is_well_distributed(cdict.tuple2int, hash_f, _l1_bucket_max):
            return hash_f
        del hash_f
    return None
    

def _find_l2_phash(cdict):
    """Find a 2 level hash table for more complex cases"""

    # try hashmul first for the first level of the 2 level
    # hash function.
    hash_f = _find_l2_hash_mul(cdict)
    if hash_f:
        return l2_phash_t(cdict, hash_f)

    # otherwise try a FKS for the first level of the 2 level hash
    # function.
    hash_f = hashfks.find_fks_well_distributed(cdict.tuple2int)
    if hash_f:
        return l2_phash_t(cdict, hash_f)

    ildutil.ild_warn("Failed to find L2 hash function for %s" % cdict)
    return None


def _gen_hash_one_level(cdict):
    """Generate a 1 level hash function or give up"""

    if _zero_constraints(cdict):
        return _get_zero_constraint_hash(cdict)
    
    # linear means all keys are sequential. not required to be zero-based. 
    if _is_linear(list(cdict.int2tuple.keys())):
        return _get_linear_hash_function(cdict)

    phash = _find_l1_phash_mul(cdict)
    if phash:
        return phash

    phash = _find_l1_phash_fks(cdict)
    if phash:
        return phash

    return None

def gen_hash(cdict):
    """ Main entry point for generating hash functions."""

    phash = _gen_hash_one_level(cdict)
    if phash:
        return phash

    l2_phash = _find_l2_phash(cdict)
    if l2_phash:
        return l2_phash
    
    return None

