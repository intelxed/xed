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

import genutil

# ild and  operand_storage
xed_strings = {'key_str'      : 'key', 
               'hidx_str'     : 'hidx', 
               'key_type'     : 'xed_uint64_t', 
               'hidx_type'    : 'xed_uint64_t',
               'op_accessor'  : 'xed3_operand',
               'table_name'   : 'lu_table',
               'lu_entry'     : 'lu_entry_t',
               'luf_name'     : 'xed_find_func_t',
               'operand_type' : 'xed_operand_values_t',
               'return_type'  : 'xed_uint32_t'}
# ild
ild_c_type          = 'xed_decoded_inst_t*'
ild_c_op_type       = 'xed_bits_t'

# ild and dec_dyn
ild_header          = 'xed-ild.h'
# ild
ild_private_header  = 'xed-ild-private.h'

#ild_imm, ild_eosz, ild_easz, ild_disp
l1_ptr_typename     = 'xed_ild_l1_func_t'

# dec_dyn
xed3_decoded_inst_t = 'xed_decoded_inst_t'
xed3_operand_t      = 'xed_operand_values_t'

def ild_err(msg):
    genutil.die("ILD_PARSER ERROR: %s\n" % (msg))

def ild_warn(msg):
    genutil.msgb("ILD_PARSER WARNING", msg)
    
