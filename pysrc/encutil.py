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

import ildutil


# dictionary of string to string.
# used to provided a layer of abstraction

enc_strings = {'key_str':'key', 
                'hidx_str':'hidx', 
                'key_type':'xed_uint64_t', 
                'hidx_type':'xed_uint64_t',
                'obj_str':'xes',
                'obj_type':'xed_encoder_request_t',
                'nt_prefix':'xed_encode_nonterminal',
                'ntluf_prefix':'xed_encode_ntluf',
                'fb_type':'xed_int8_t',
                'nt_fptr':'xed_nt_func_ptr_t',
                'ntluf_fptr':'xed_ntluf_func_ptr_t',
                'obj_const': '',
                'lu_namespace':'enc',
                'emit_util_function':'xed_encoder_request_encode_emit',
                'static':False
               }
enc_strings.update(ildutil.xed_strings)


