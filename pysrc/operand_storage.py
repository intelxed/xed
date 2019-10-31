#!/usr/bin/env python
# -*- python -*-
################################################################################
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

import os
import re
import codegen
import genutil
import ildutil
import math


class operand_field_t(object): 
   def __init__(self,
                name,
                aggtype,
                ctype,
                bitwidth,
                default_visibility=None,
                default_initializer=None,
                xprint='NOPRINT',
                internal_or_public="INTERNAL",
                dio="DO",
                eio="EO",):

      self.name = name
      self.aggtype = aggtype
      self.ctype = ctype
      self.bitwidth = int(bitwidth)
      self.default_visibility = default_visibility
      self.xprint = xprint
      self.internal_or_public = internal_or_public
      self.dio = dio
      self.eio = eio
      
      if self.eio in ['EI','EO']:
         pass
      else:
          err = "Bad Encoder IO value: %s -- need one of {EI,EO}"
          genutil.die(err % self.eio)

      if self.dio in ['DI','DO','DS']:
         pass
      else:
          err = "Bad decoder IO value: %s -- need one of {DI,DO,DS}"
          genutil.die(err % self.eio)
         
      if self.eio == 'EI':
         self.encoder_input = True
      else:
         self.encoder_input = False

      if self.dio == 'DS':
         self.decoder_skip = True
      else:
         self.decoder_skip = False
         
      #NOTE: this next field is only used if initialize_each_field is True.
      self.default_initializer = default_initializer
      self.is_enum = 'enum' in self.ctype
      
      # this is the C type that will be used in the operand storage struct.
      self.storage_type = None 
      
      #if True using bit fields 
      self.compressed = False
      
   def print_field(self):
      if self.xprint == 'PRINT':
         return True
      return False

def key_operand_name(a):
    return a.name
def key_bitwidth(a):
    return a.bitwidth

def sort_cmp_operands(a):
    b = sorted(a, key=key_operand_name)
    c = sorted(b, key=key_bitwidth)
    return c
 
class operands_storage_t(object):
    """This is where we build up the storage for the fields that hold
    the operand values. 
    """

    def __init__(self,lines,compress_operands=False):
        #a dict of operand name to operand_field_t
        self.operand_fields = self._read_storage_fields(lines)
        
        self.compressed = compress_operands
        # the prefix of the accessor function
        self.xed_accessor_fn_pfx = ildutil.xed_strings['op_accessor']
        
        #list of bin, each bin is operands
        #used for squeezing operands with a few bits to one 32 bit variable 
        self.bins = []
        
      
    def _read_storage_fields(self,lines):
        ''' Return a dictionary of operand_field_t objects 
            indexed by field name '''
        
        comment_pattern = re.compile(r'[#].*$')
        operand_types = {}
        for line in lines:
            pline = comment_pattern.sub('',line).strip()
            if pline == '':
                continue
            wrds = pline.split()
            if len(wrds) != 9:
                genutil.die("Bad number of tokens on line: " + line)
            # aggtype is "SCALAR"
            (name, aggtype, ctype, width, default_visibility,
             xprint, internal_or_public, dio, eio) = wrds
            if name in operand_types:
                genutil.die("Duplicate name %s in input-fields file." % (name))
            
            if aggtype != 'SCALAR':
                err = ("type different than SCALAR is not" +
                       " supported in: %s" % (line))
                genutil.die(err)    
            
            if ctype == 'xed_reg_enum_t':
               default_initializer = 'XED_REG_INVALID'
            elif ctype == 'xed_iclass_enum_t':
               default_initializer = 'XED_ICLASS_INVALID'
            else:
               default_initializer = '0'
            operand_types[name] = operand_field_t(name, aggtype,
                                                  ctype, width,
                                                  default_visibility,
                                                  default_initializer,
                                                  xprint,
                                                  internal_or_public,
                                                  dio,
                                                  eio,)
        return operand_types    
        
    def get_operand(self,opname):
        return self.operand_fields[opname]
    
    def get_operands(self):
        return self.operand_fields
    
    def decoder_skip(self,operand):
        return self.operand_fields[operand].decoder_skip
    
    def get_ctype(self,operand):
        return self.operand_fields[operand].ctype
    
    def get_storage_type(self,operand):
        return self.operand_fields[operand].storage_type
    
    def _gen_op_getter_fo(self,opname):
        ''' generate the function object for the getter accessors
            adding cast to the C type according to the data files(ctype)'''
        inst = 'd'
        fname = get_op_getter_fn(opname)
        ret_type = self.get_ctype(opname)
        fo = codegen.function_object_t(fname,
                                           return_type=ret_type,
                                           static=True,
                                           inline=True)
        fo.add_arg('const xed_decoded_inst_t* %s' % inst)
        op = opname.lower()
        fo.add_code_eol('return (%s)%s->_operands.%s' % (ret_type,inst, op))
        return fo

    def _gen_op_setter_fo(self,opname):
        ''' generate the function object for the setter accessors
            adding cast to the C type according to the data files(ctype)'''
        inst = 'd'
        opval = 'opval'
        fname = get_op_setter_fn(opname)
        fo = codegen.function_object_t(fname,
                                           return_type='void',
                                           static=True,
                                           inline=True)
        fo.add_arg('xed_decoded_inst_t* %s' % inst)
        fo.add_arg('%s %s' % (self.get_ctype(opname),opval))
        op = opname.lower()
        type = self.get_storage_type(opname)
        fo.add_code_eol('%s->_operands.%s = (%s)%s' % (inst, op, type ,opval))
        return fo

    def _gen_generic_getter(self):
        ''' for xed's internal usage (printing) we need to be able to 
            get an operand based on its index.
            generating here a switch/case over the operand index to call the 
            correct getter function '''   
        inst = 'd'
        fname = 'xed3_get_generic_operand'
        ret_arg = 'ret_arg'
        
        fo = codegen.function_object_t(fname,
                                       return_type='void',
                                       static=False,
                                       inline=False,
                                       dll_export=True)
        fo.add_arg('const xed_decoded_inst_t* %s' % inst)
        fo.add_arg('xed_operand_enum_t operand')
        fo.add_arg('void* %s' % ret_arg)
        
        switch_gen = codegen.c_switch_generator_t('operand',fo)
        op_names = sorted(self.operand_fields.keys())
        for op in op_names:
            switch_key = "XED_OPERAND_%s" % op
            ctype = self.get_ctype(op)
            func_getter = "%s(d)" % get_op_getter_fn(op)
            code = "*((%s*)%s)=%s;" % (ctype,ret_arg,func_getter)
            switch_gen.add_case(switch_key,[code]) 
        switch_gen.add_default(['xed_assert(0);'])
        switch_gen.finish()    
        return fo
    
    def _gen_generic_setter(self):
        ''' generating a switch/case over the operand index to call the 
            correct setter function '''   
        inst = 'd'
        fname = 'xed3_set_generic_operand'
        in_value = 'val'
        
        fo = codegen.function_object_t(fname,
                                       return_type='void',
                                       static=False,
                                       inline=False, 
                                       dll_export=True)
        fo.add_arg('xed_decoded_inst_t* %s' % inst)
        fo.add_arg('xed_operand_enum_t operand')
        fo.add_arg('xed_uint32_t %s' % in_value)
        
        switch_gen = codegen.c_switch_generator_t('operand',fo)
        op_names = sorted(self.operand_fields.keys())
        for op in op_names:
            switch_key = "XED_OPERAND_%s" % op
            ctype = self.get_ctype(op)
            func_setter = get_op_setter_fn(op)
            code = "%s(%s,(%s)%s);" % (func_setter,inst,ctype,in_value)
            switch_gen.add_case(switch_key,[code]) 
        switch_gen.add_default(['xed_assert(0);'])
        switch_gen.finish()    
        return fo
        
    def dump_operand_accessors(self,agi):
        
        ''' Dump operand accessor to inspect the data 
            structure xed_operand_storage_t '''
        fo_list = []
        h_fname = get_operand_accessors_fn()
        c_fname = h_fname.replace('.h', '.c') 
        
        for opname in self.operand_fields.keys():
            getter_fo = self._gen_op_getter_fo(opname)
            setter_fo = self._gen_op_setter_fo(opname)
            fo_list.append(getter_fo)
            fo_list.append(setter_fo)
        
        # generate a generic getter
        generic_getter = self._gen_generic_getter()
        generic_setter = self._gen_generic_setter()
        xeddir = os.path.abspath(agi.common.options.xeddir)
        gendir = agi.common.options.gendir
    
        h_file = codegen.xed_file_emitter_t(xeddir,gendir,
                                    h_fname, shell_file=False,
                                    is_private=False)
        
        h_file.add_header(['xed-decoded-inst.h','xed-operand-storage.h'])
        h_file.start()
    
        for fo in fo_list:
            decl = fo.emit_header()
            h_file.add_code(decl)
        h_file.add_code(generic_getter.emit_header())
        h_file.add_code(generic_setter.emit_header())    
        
        
        for fo in fo_list:
            fo.emit_file_emitter(h_file)
        

        h_file.close()
        
        c_file = codegen.file_emitter_t(gendir,
                                    c_fname, shell_file=False)
        c_file.add_header(h_fname)
        c_file.start()
        generic_getter.emit_file_emitter(c_file)
        generic_setter.emit_file_emitter(c_file)
        c_file.close()
        
    def _fix_bit_width_for_enums(self,agi):
        ''' the default width of the nums is to big and wasteful.
            we get the list of all values for each enum in agi 
            and set the bitwidth to the minimal width needed.
         '''
        
        # mx_bits is a mapping from enum name to the minimal number 
        # of bits required to represent it 
        max_bits_for_enum = self._gen_max_bits_per_enum(agi.all_enums)
        for op in list(self.operand_fields.values()):
            if op.ctype in max_bits_for_enum:
                needed_bits = max_bits_for_enum[op.ctype]
                if op.bitwidth < needed_bits:
                    # verify that the specified bitwidth form the data files 
                    # is not smaller than the calculated 
                    vals = agi.all_enums[op.ctype]
                    err = 'bit width for % is to small, has %d values' 
                    genutil.die(err % (op.name,vals))
                else:
                    op.bitwidth = max_bits_for_enum[op.ctype]
            
    def _compute_type_in_storage(self):
       ''' detect the minimal C type data type can be used to represent 
           the operand. 
           the accessors will cast the operand to its C type according to the 
           data files'''
       
       for op in list(self.operand_fields.values()):
           width = op.bitwidth
           if width <= 8:
               op.storage_type = 'xed_uint8_t'
           elif width <=16:
               op.storage_type ='xed_uint16_t'
           elif width <=32:
               op.storage_type = 'xed_uint32_t'
           elif width <=64:
               op.storage_type = 'xed_uint64_t'
           else:
               genutil.die("unhandled width")           
             
    def emit(self,agi):
        ''' emit the date type xed_operand_storage_t'''
        
        filename = 'xed-operand-storage.h'
        
        xeddir = agi.common.options.xeddir
        gendir = agi.common.options.gendir
        fe = codegen.xed_file_emitter_t(xeddir, gendir, filename)
        fe.headers.remove('xed-internal-header.h')
        headers = ['xed-chip-enum.h', 'xed-error-enum.h', 'xed-iclass-enum.h',
                   'xed-reg-enum.h','xed-operand-element-type-enum.h']
        fe.add_header(headers)
        
        fe.start()
        
        cgen = codegen.c_class_generator_t('xed_operand_storage_t',
                                           var_prefix='')
        
        #compute the minimal ctype required to represent each enum
        self._fix_bit_width_for_enums(agi)
        
        #compute the ctype of the operand ad represented in the operand storage
        self._compute_type_in_storage()
        
        if self.compressed:
            self.bins = self._compress_operands()
            
            operands = list(self.operand_fields.values())
            un_compressed = list(filter(lambda x: x.compressed == False, operands ))
            un_compressed = sort_cmp_operands(un_compressed)
            
            # first emit all the operands that does not use bit fields 
            for op in un_compressed:
                cgen.add_var(op.name.lower(), op.storage_type, 
                             accessors='none')
            
            #emit the operand with bit fields
            for i,xbin in enumerate(self.bins):
                for op in xbin.operands:
                    cgen.add_var(op.name.lower(), xbin.storage_ctype, 
                                 bit_width=op.bitwidth, accessors='none')
        
        else:
            operands_sorted = list(self.operand_fields.values())
            operands_sorted = sort_cmp_operands(operands_sorted)
            for op in operands_sorted:
                cgen.add_var(op.name.lower(), op.storage_type, 
                             accessors='none')
        
        lines = cgen.emit_decl()
        fe.writelines(lines)
        
        fe.close()
    
    def _get_num_elements_in_enum(self,values_list):
        ''' return the number of elements in the enum.
            is the elements does not have the x_LAST enum add it'''
        has_last = False
        for val in values_list:
            if 'LAST' in val:
                has_last = True
        if has_last:
            return len(values_list)
        return len(values_list) + 1  
    
    def _gen_max_bits_per_enum(self,all_enums):
        ''' calculate the number of bits required to capture the each enum.
            returning a dict of enum name to the number of required bits '''
        widths = {}
        for (enum_name, values_list) in list(all_enums.items()):
            num_values = self._get_num_elements_in_enum(values_list)
            log2 = math.log(num_values,2)
            needed_bits = int(math.ceil(log2))
            widths[enum_name]= needed_bits
        # special handling for xed_error_enum_t.
        # this width is hard coded since we can not capture the values
        # of this enum in the generator
        widths['xed_error_enum_t'] = 4
        return widths
    
    def _get_candidates_for_compression(self):
        ''' collect all the operands that we need to compress.
            the operands that we need to compress has bitwidth smaller then 
            their ctype can hold. '''
        
        candiadtes = []
        for op in list(self.operand_fields.values()):
            # for optimization those operands are not using bit with
            # FIXME: add field to the operands for excluding hot fields 
            # form being compressed
            #if op.name.lower() in ['error','outreg','mode']:
            #    continue
            if op.bitwidth != 32 and op.bitwidth != 64:
                candiadtes.append(op)
        return candiadtes
    
    def _place_operand_in_bin(self,op,bins):
        ''' find a bin that has place for the operand '''
        for xbin in bins:
            if xbin.operand_fits(op):
                xbin.add_operand(op)
                return
        
        #did not find any matching bin, need to create new one
        xbin = operands_bin_t()
        xbin.add_operand(op)
        bins.append(xbin)
        return
            
    def _partition_to_bins(self,ops_sorted):
        ''' partition all the operands in bins '''
        bins = []
        for op in ops_sorted:
            self._place_operand_in_bin(op,bins)
            op.compressed = True
        return bins
            
    def _compress_operands(self):
        ''' most of the operands's width are less than their c type.
        in order to save space we are bin packing the operands.
        each bin is 32bit width.
        using First Fit Decreasing(FFD) strategy '''
        
        operands = self._get_candidates_for_compression()
        operands = sort_cmp_operands(operands)
        bins = self._partition_to_bins(operands)
        return bins
    
class operands_bin_t(object):
    ''' This class represents a single bin that aggregates a list of operands
        into single c struct '''
    def __init__(self):
        self.operands = []  #list of operands
        self.size = 0       #total width in bits
        self.max_size = 32  #the max width
        self.storage_ctype = 'xed_uint32_t' #the C type used for the operands
    
    def add_operand(self,op):
        ''' adding single operand to this bin'''
        self.operands.append(op)
        self.size += op.bitwidth
        
    def operand_fits(self,operand):
        ''' checks if the given operand can be inserted into this bin '''
        return operand.bitwidth + self.size <= self.max_size

################
# Those are global functions that are accessed for places that do not have the 
# operands_storage_t type
################                
def get_operand_accessors_fn():             
    return 'xed-operand-accessors.h'

def get_op_getter_full_func(opname,strings_dict):
    obj_name = strings_dict['obj_str']
    accessor = get_op_getter_fn(opname) 
    return '%s(%s)' % (accessor,obj_name) 

def get_op_getter_fn(opname):
    xed_accessor_fn_pfx = ildutil.xed_strings['op_accessor']
    return '%s_get_%s' % (xed_accessor_fn_pfx, opname.lower())

def get_op_setter_fn(opname):
    xed_accessor_fn_pfx = ildutil.xed_strings['op_accessor']
    return '%s_set_%s' % (xed_accessor_fn_pfx, opname.lower())       
        

    
