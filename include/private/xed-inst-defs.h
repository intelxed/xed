/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
  
END_LEGAL */
#define XED_BIT_PAIR(x,y,z,w) {{ x , y , z, w }}
/* ignoring iclass(ic), category(ca), and extension(ex) now that they are in the iform map. */
#define XED_DEF_INST(ic, ca, ex, cpl, iforme, opnd_idx, opnd_cnt, flg_indx, flg_cmplx, attr, exceptions) \
    {  opnd_cnt, cpl, flg_cmplx, (xed_uint8_t) exceptions, flg_indx, (xed_uint16_t) iforme, opnd_idx , attr   }

#define XED_DEF_DGRAPH(node_type, ok, decider_bits, skipped_bits, backup_pos, od,  capfunc, nt_name, max_next, next_base) \
    { capfunc,  max_next, next_base, node_type, ok, decider_bits, skipped_bits, backup_pos, od, nt_name  }

#define XED_DEF_OPND(name, vis, rw, oc2, type, xtype, cvt_idx, imm_nt_reg, nt) \
    { (xed_uint8_t)name, (xed_uint8_t)vis, (xed_uint8_t)rw, (xed_uint8_t)oc2, (xed_uint8_t)type, (xed_uint8_t)xtype, cvt_idx, nt, { imm_nt_reg }  }
