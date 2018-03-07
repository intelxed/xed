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
/// @file xed-disas.c


////////////////////////////////////////////////////////////////////////////
#include "xed-internal-header.h"
#include "xed-decoded-inst.h"
#include "xed-decoded-inst-api.h"
#include "xed-decoded-inst-private.h"

#include "xed-disas.h"
#include "xed-disas-private.h"
#include "xed-util.h"
#include "xed-util-private.h"
#include "xed-format-options.h"
#include "xed-reg-class.h"

#include "xed-operand-ctype-enum.h"
#include "xed-operand-ctype-map.h"
#include "xed-init-pointer-names.h"
#include "xed-print-info.h"
#include "xed-convert-table-init.h" //generated
#include "xed-isa-set.h" 
#include "xed-ild.h"

#include <string.h> // memset
#define XED_HEX_BUFLEN 200

int
xed_get_symbolic_disassembly(xed_print_info_t* pi,
                             xed_uint64_t address, 
                             char* buffer, 
                             xed_uint_t buffer_length,
                             xed_uint64_t* offset)

{
    // use the common registered version of the callback if non is supplied
    // by the user.
    xed_disassembly_callback_fn_t fn = 0;
    if (pi->disassembly_callback)
        fn = pi->disassembly_callback;
    
    if (fn) {
        int r = (*fn)(address,
                      buffer,
                      buffer_length,
                      offset,
                      pi->context);
        return r;
    }
    return 0;
}


////////////////////////////////////////////////////


static xed_bool_t  stringop_memop(const xed_decoded_inst_t* p,
                                  const xed_operand_t* o) {
    xed_bool_t stringop = (xed_decoded_inst_get_category(p) ==
                           XED_CATEGORY_STRINGOP);
    if (stringop)  {
        xed_operand_enum_t   op_name = xed_operand_name(o);
        if (op_name == XED_OPERAND_MEM0 || op_name == XED_OPERAND_MEM1)
            return 1;
    }
    return 0;
}

static xed_bool_t xed_decoded_inst_explicit_memop(const xed_decoded_inst_t* p) {
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)  {
        const xed_operand_t* o = xed_inst_operand(inst,i);
        switch(xed_operand_name(o)) {
          case XED_OPERAND_MEM0:
          case XED_OPERAND_MEM1:
          case XED_OPERAND_AGEN:
            if (xed_operand_operand_visibility(o) != XED_OPVIS_SUPPRESSED) 
                return 1;
            if (stringop_memop(p,o))
                return 1;
          default:
            break;
        }
    }
    return 0;
}

static xed_bool_t
xed_decoded_inst_explicit_operand(const xed_decoded_inst_t* p)
{
    const xed_inst_t* inst = p->_inst;
    const unsigned int noperands = xed_inst_noperands(inst);
    unsigned int i;
    for( i=0;i<noperands;i++)  {
        const xed_operand_t* o = xed_inst_operand(inst,i);
        if (xed_operand_operand_visibility(o) == XED_OPVIS_SUPPRESSED) {
            /* we print stringop memops so no need to print the 66/67 prefixes */
            if (stringop_memop(p,o)) 
                return 1;
            continue;
        }

        return 1;
    }
    return 0;
}


void
xed_decoded_inst_dump(const xed_decoded_inst_t* p, char* buf, int buflen)
{
    char ibuf[XED_HEX_BUFLEN];
    unsigned int i;
    const xed_inst_t* xi = xed_decoded_inst_inst(p);
    unsigned int noperands;
    xed_bool_t okay;
    char* t=buf;
    int blen = buflen;
    if (!xi) {
        (void) xed_strncpy(buf,"NOT DECODED YET", blen);
        return;
    }
    blen = xed_strncpy(t,
                       xed_iclass_enum_t2str(xed_decoded_inst_get_iclass(p)),
                       blen);
    blen = xed_strncat(t, " ",blen);
    blen = xed_strncat(t,
                       xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(p)),
                       blen);
    
    blen = xed_strncat(t, " ",blen);

    t = buf + xed_strlen(buf);
    xed_operand_values_print_short( xed_decoded_inst_operands_const(p), t, blen);
    blen = buflen - xed_strlen(buf);

    blen = xed_strncat(buf,"\n",blen);
    noperands = xed_inst_noperands(xi);
    for( i=0;i<noperands;i++) {
        const xed_operand_t* op;
        t = buf+xed_strlen(buf);
        op = xed_inst_operand(xi,i);
        blen = xed_itoa(t,i,blen);
        blen = xed_strncat(buf,"\t\t",blen);
        xed_operand_print(op,buf+xed_strlen(buf),blen);
        blen = buflen - xed_strlen(buf);
        blen = xed_strncat(buf,"\n",blen);
    }

    okay = xed_format_context(XED_SYNTAX_INTEL,
                              p,ibuf,sizeof(ibuf),0,0,0);
    if (okay) {
        blen = xed_strncat(buf,"YDIS: ",blen);
        (void) xed_strncat(buf,ibuf,blen);
    }
}


xed_bool_t
xed_decoded_inst_dump_xed_format(const xed_decoded_inst_t* p, 
                                 char* buf, 
                                 int buflen,
                                 xed_uint64_t runtime_address)
{
    const xed_inst_t* xi = xed_decoded_inst_inst(p);
    char* s;
    const xed_operand_values_t* co = xed_decoded_inst_operands_const(p);  
    int blen = buflen;
    if (!xi) 
        return 0;
    if (blen < 16)
        return 0;
    blen = xed_strncpy(buf, xed_iclass_enum_t2str(xed_inst_iclass(xi)),blen);

    // Find the end of the buffer so that we can put the disassembly in it.
    blen = xed_strncat(buf, " ", blen);
    s = buf + xed_strlen(buf);
    xed_operand_values_print_short(co,s,blen);
    return 1;
    (void) runtime_address;
}

static const char* xed_decoded_inst_print_ptr_size(xed_uint_t bytes) {
    extern const char* xed_pointer_name[XED_MAX_POINTER_NAMES];
    if (bytes < XED_MAX_POINTER_NAMES)
        if (xed_pointer_name[bytes])
            return xed_pointer_name[bytes];
    return "";
}

static const char* instruction_suffix_att(const xed_decoded_inst_t* p) {
    extern const char* xed_pointer_name_suffix[XED_MAX_POINTER_NAMES];
    if (xed_decoded_inst_number_of_memory_operands(p)) {
        xed_uint_t bytes = xed_decoded_inst_get_memory_operand_length(p,0);
        if (bytes < XED_MAX_POINTER_NAMES)
            if (xed_pointer_name_suffix[bytes])
                return xed_pointer_name_suffix[bytes];
    }
    return 0;
}

static xed_format_options_t xed_format_options = { 
    1, /* symblic names with hex address */
    0, /* xml_a */
    0, /* xml_f flags */
    0, /* omit scale */
    0, /* no_sign_extend_signed_immediates */
    1, /* writemask with curly brackets, omit k0 */
    1, /* lowercase hexadecimal */
};

void xed_format_set_options(xed_format_options_t format_options) {
    xed_format_options = format_options;
}


static int
xml_print_flags(const xed_decoded_inst_t* xedd, char* buf, int blen)
{
    if (xed_decoded_inst_uses_rflags(xedd)) {
        // KW complains because it thinks rfi could be null.
        //    Cannot happen by design.
        const xed_simple_flag_t* rfi = xed_decoded_inst_get_rflags_info(xedd);
        unsigned int nflags = xed_simple_flag_get_nflags(rfi);
        unsigned int i;
        blen = xed_strncat(buf,"<FLAGS>",blen);
        for( i=0;i<nflags ;i++) {
            char tbuf[XED_HEX_BUFLEN];
            const xed_flag_action_t* fa = xed_simple_flag_get_flag_action(rfi,i);
            if (i>0)
                blen = xed_strncat(buf, " ",blen);
            (void) xed_flag_action_print(fa,tbuf,XED_HEX_BUFLEN);
            blen = xed_strncat(buf, tbuf,blen);

        }
        blen = xed_strncat(buf,"</FLAGS>",blen);
    }
    return blen;
}




static void xed_pi_strcat(xed_print_info_t* pi,
                          char const* str)
{
    pi->blen = xed_strncat(pi->buf, str, pi->blen);
}



static void xed_prefixes(xed_print_info_t* pi,
                         char const* prefix)
{
    if (pi->emitted == 0 && pi->format_options.xml_a)
        xed_pi_strcat(pi,"<PREFIXES>");
    if (pi->emitted)
        xed_pi_strcat(pi," ");
    xed_pi_strcat(pi,prefix);
    pi->emitted=1;
}

static void
xml_print_end(xed_print_info_t* pi,
              char const* s)
{
    if (pi->format_options.xml_a) {
        xed_pi_strcat(pi,"</");
        xed_pi_strcat(pi,s);
        xed_pi_strcat(pi,">");
    }
}

static void
xed_decoded_inst_dump_common(xed_print_info_t* pi)
{
    const xed_operand_values_t* ov = xed_decoded_inst_operands_const(pi->p);  

    int long_mode = xed_operand_values_get_long_mode(ov);
    const xed_uint32_t dmode = xed_decoded_inst_get_machine_mode_bits(pi->p);
    int dmode16 = (dmode == 16);
    int dmode32 = (dmode == 32);

    if (xed_decoded_inst_has_mpx_prefix(pi->p))
        xed_prefixes(pi,"bnd");
    if (xed_decoded_inst_is_xacquire(pi->p))
        xed_prefixes(pi,"xacquire");
    if (xed_decoded_inst_is_xrelease(pi->p))
        xed_prefixes(pi,"xrelease");
    if (xed_operand_values_has_lock_prefix(ov))
        xed_prefixes(pi,"lock");
    if (xed_operand_values_has_real_rep(ov)) {
        if (xed_operand_values_has_rep_prefix(ov))
            xed_prefixes(pi,"rep");
        if (xed_operand_values_has_repne_prefix(ov))
            xed_prefixes(pi,"repne");
    }
    else if (xed_operand_values_branch_not_taken_hint(ov))
        xed_prefixes(pi,"hint-not-taken");
    else if (xed_operand_values_branch_taken_hint(ov))
        xed_prefixes(pi,"hint-taken");

    if (xed_operand_values_has_address_size_prefix(ov)) {
        if (xed_decoded_inst_explicit_memop(pi->p) == 0) {
            if (long_mode || dmode16)
                xed_prefixes(pi,"addr32");
            else
                xed_prefixes(pi,"addr16");
        }
    }
    if (xed_operand_values_has_operand_size_prefix(ov)) {
        if (xed_decoded_inst_explicit_operand(pi->p) == 0) {
            if (long_mode || dmode32)
                xed_prefixes(pi,"data16");
            else
                xed_prefixes(pi,"data32");
        }
    }
    if (pi->emitted)
        xml_print_end(pi,"PREFIXES");
    if (pi->emitted)
        xed_pi_strcat(pi," ");
    
    // reset the spacing-is-required indicator after handling prefixes
    pi->emitted = 0;
}


static const char* instruction_name_att(const xed_decoded_inst_t* p)

{
    xed_iform_enum_t iform = xed_decoded_inst_get_iform_enum(p);
    return xed_iform_to_iclass_string_att(iform);
}

static const char* instruction_name_intel(const xed_decoded_inst_t* p)
{
    xed_iform_enum_t iform = xed_decoded_inst_get_iform_enum(p);
    return xed_iform_to_iclass_string_intel(iform);
}


///////////////////////////////////////////////////////////////////////////////
static int xed_print_cvt(const xed_decoded_inst_t* p, 
                         char* buf,
                         int blen,
                         xed_operand_convert_enum_t    cvt) {
    // 32bit var is enough since the only operand wider than 32b disp/imm 
    // and we are not decorating those
    xed_uint_t opvalue;
    xed_operand_enum_t index_operand = xed_convert_table[cvt].opnd;
    xed3_get_generic_operand(p,index_operand,&opvalue);
    if (opvalue < xed_convert_table[cvt].limit) {
        const char* s = xed_convert_table[cvt].table_name[ opvalue ];
        blen = xed_strncat(buf,s,blen);
    }
    else 
        blen = xed_strncat(buf,"BADCVT",blen);
    return blen;
}

static int xml_tag(char* buf, int blen, char const* tag, xed_uint_t value) {
    char tbuf[XED_HEX_BUFLEN];

    blen = xed_strncat(buf,"<",blen);
    blen = xed_strncat(buf,tag,blen);
    blen = xed_strncat(buf," bits=\"",blen); 

    xed_sprintf_uint32(tbuf, value, XED_HEX_BUFLEN);
    blen = xed_strncat(buf,tbuf,blen); 

    blen = xed_strncat(buf,"\">",blen);
    return blen;
}

static void xml_tag_pi(xed_print_info_t* pi,
                      char const* tag,
                      xed_uint_t value)
{
    pi->blen = xml_tag(pi->buf, pi->blen, tag, value);
}


static void xed_operand_spacer(xed_print_info_t* pi) {
    if (pi->emitted) {
        pi->blen = xed_strncat(pi->buf,", ",pi->blen);
    }
}


static void print_seg_prefix_for_suppressed_operands(
    xed_print_info_t* pi,
    const xed_operand_values_t* ov,
    const xed_operand_t*        op)
{
    int i;
    xed_operand_enum_t op_name = xed_operand_name(op);
    /* suppressed memops with nondefault segments get their segment printed */
    const xed_operand_enum_t names[] = { XED_OPERAND_MEM0,XED_OPERAND_MEM1};
    for(i=0;i<2;i++) {
        if (op_name == names[i]) {
            xed_reg_enum_t seg = XED_REG_INVALID;
            switch(i) {
              case 0: seg = xed3_operand_get_seg0(ov); break;
              case 1: seg = xed3_operand_get_seg1(ov); break;
            }
            if (seg != XED_REG_INVALID &&
                xed_operand_values_using_default_segment(ov, i) == 0) {
                xed_operand_spacer(pi);
                if (pi->format_options.xml_a)
                    xed_pi_strcat(pi,"<OPERAND><REG bits=\"16\">");
                pi->blen = xed_strncat_lower(pi->buf,
                                             xed_reg_enum_t2str(seg),
                                             pi->blen); 
                xml_print_end(pi,"REG");
                xml_print_end(pi,"OPERAND");
                pi->emitted = 1;
            }
        }
    }
}

static void
xed_print_operand_decorations(
    xed_print_info_t* pi,
    xed_operand_t const* const op)
{
    xed_uint32_t cvt_idx = op->_cvt_idx;

    if (cvt_idx && cvt_idx < XED_MAX_CONVERT_PATTERNS)  {
        int i;
        for( i=0; i<XED_MAX_DECORATIONS_PER_OPERAND; i++ )  {
            xed_operand_convert_enum_t v = xed_operand_convert[cvt_idx][i];
            if (v == XED_OPERAND_CONVERT_INVALID)
                break;
            pi->blen = xed_print_cvt(pi->p, pi->buf, pi->blen, v);
        }
    }
}


static void
xml_reg_prefix(xed_print_info_t* pi, xed_reg_enum_t reg)
{
    if (pi->format_options.xml_a) 
        xml_tag_pi(pi,
                   "REG",
                   xed_get_register_width_bits(reg));
}

static void
print_reg(xed_print_info_t* pi,
          xed_reg_enum_t reg)
{
    char const* s;
    
    if (pi->syntax == XED_SYNTAX_ATT)
        xed_pi_strcat(pi,"%");

    if (reg == XED_REG_ST0 && pi->implicit)
        s = "st";
    else    
        s = xed_reg_enum_t2str(reg);

    pi->blen = xed_strncat_lower(pi->buf, s, pi->blen);
}

static void
print_reg_xml(xed_print_info_t* pi,
          xed_reg_enum_t reg)
{
    xml_reg_prefix(pi,reg);
    print_reg(pi,reg);
    xml_print_end(pi,"REG");
}


#if defined(XED_SUPPORTS_AVX512)
static xed_uint_t
operand_is_writemask(
    xed_operand_t const* const op)
{

    xed_operand_enum_t op_name = xed_operand_name(op);
    // for memops dests, writemask is REG0.
    // for reg-dest instr, writemask is REG1.
    if (op_name == XED_OPERAND_REG1 || op_name == XED_OPERAND_REG0)
        if (xed_operand_nonterminal_name(op) == XED_NONTERMINAL_MASK1)
            return 1;

    return 0;
}

static void
print_decoration(xed_print_info_t* pi,
                 xed_uint_t indx)
{
    xed_inst_t const* xi = xed_decoded_inst_inst(pi->p);
    xed_operand_t const* const kop = xed_inst_operand(xi,indx);
    xed_print_operand_decorations(pi, kop);
}



static xed_reg_enum_t
printing_writemasked_operand(
    xed_print_info_t* pi)
{
    // return XED_REG_INVALID if next operand is not a writemask
    // else return the XED_REG_K0...K7 if it is a writemask.
    // (We treat k0 as a write mask, but it won't get printed)

    // write masked operand must be first
    if (pi->operand_indx > 0)
        return XED_REG_INVALID;
    else
    {
        xed_inst_t const* xi = xed_decoded_inst_inst(pi->p);
        xed_uint_t noperands = xed_inst_noperands(xi);
        
        // we have another operand
        xed_uint_t nxt_opnd = pi->operand_indx + 1;
        if (nxt_opnd < noperands)
        {
            xed_operand_t const* const op = xed_inst_operand(xi,nxt_opnd);
            if (operand_is_writemask(op))
            {
                xed_operand_enum_t op_name = xed_operand_name(op);
                xed_reg_enum_t reg;
                xed3_get_generic_operand(pi->p,op_name,&reg);
                return reg;
            }

        }
    }
    return XED_REG_INVALID;
}

static void
print_write_mask_reg(
    xed_print_info_t* pi,
    xed_reg_enum_t writemask)
{
    // print the write mask if not k0
    if (writemask != XED_REG_K0)
    {
        pi->blen = xed_strncat(pi->buf,"{",pi->blen);
        print_reg(pi,writemask);
        pi->blen = xed_strncat(pi->buf,"}",pi->blen);
        
        // write mask operand might have decorations.  print them.
        print_decoration(pi, pi->operand_indx + 1);
    }
}
#endif // XED_SUPPORTS_AVX512


static void
print_write_mask_generic(
    xed_print_info_t* pi)
{
#if defined(XED_SUPPORTS_AVX512)
    if (pi->format_options.write_mask_curly_k0)
    {
        xed_reg_enum_t writemask;
        writemask = printing_writemasked_operand(pi);
        if (writemask != XED_REG_INVALID)
        {
            print_write_mask_reg(pi, writemask);
            // tell operand loop to skip emitting write mask operand on
            // next iteration (for any write mask reg, k0 or otherwise)
            pi->skip_operand = 1;
        }
    }
#endif
   (void) pi;
}


static void
print_reg_writemask(
    xed_print_info_t* pi,
    xed_reg_enum_t reg)
{
    xml_reg_prefix(pi,reg);
    print_reg(pi,reg);
#if defined(XED_SUPPORTS_AVX512)
    print_write_mask_generic(pi);
#endif
    xml_print_end(pi,"REG");
}

#define XED_SYMBOL_LEN 512

static const xed_bool_t print_address=1;
static const xed_bool_t no_print_address=0;
static const xed_bool_t branch_displacement=0;
static const xed_bool_t memory_displacement=1;

static void
print_rel_sym(xed_print_info_t* pi,
              xed_bool_t arg_print_address,
              xed_bool_t arg_memory_displacement)
{
     xed_int64_t disp;
     xed_uint64_t instruction_length = xed_decoded_inst_get_length(pi->p);
     xed_uint64_t pc = pi->runtime_address + instruction_length;
     xed_uint64_t effective_addr;
     xed_bool_t long_mode, symbolic;
     xed_uint_t bits_to_print;
     char symbol[XED_SYMBOL_LEN];
     xed_uint64_t offset;
     const xed_bool_t leading_zeros = 0;

     if (arg_memory_displacement)
         disp = xed_decoded_inst_get_memory_displacement(pi->p,0); //first memop only
     else
         disp = xed_decoded_inst_get_branch_displacement(pi->p);

     long_mode = xed_operand_values_get_long_mode(
                            xed_decoded_inst_operands_const(pi->p));
              
     bits_to_print = long_mode ? 8*8 :4*8;

     effective_addr = (xed_uint64_t) ((xed_int64_t)pc  + disp);

     symbolic = xed_get_symbolic_disassembly(pi,
                                             effective_addr, 
                                             symbol,
                                             XED_SYMBOL_LEN,
                                             &offset);

     if (arg_print_address) // print the numeric address
     {
         if (symbolic==0 ||
             pi->format_options.hex_address_before_symbolic_name)
         {
             xed_pi_strcat(pi,"0x");                      
             pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                              effective_addr,
                                              bits_to_print, 
                                              leading_zeros,
                                              pi->blen,
                                              pi->format_options.lowercase_hex);
         }
     }

      if (symbolic)
      {
         if (pi->format_options.xml_a)
             xed_pi_strcat(pi," &lt;");
         else
             xed_pi_strcat(pi," <");

          xed_pi_strcat(pi,symbol);                      
          if (offset)
          {
              xed_pi_strcat(pi,"+0x");                      
              pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                               offset,
                                               bits_to_print,
                                               leading_zeros,
                                               pi->blen,
                                               pi->format_options.lowercase_hex);
          }
         if (pi->format_options.xml_a)
             xed_pi_strcat(pi," &gt;");
         else
             xed_pi_strcat(pi,">");
      }
}

static void
xml_print_imm(xed_print_info_t* pi,
              unsigned int bits)
{
    if (pi->format_options.xml_a)
        xml_tag_pi(pi, "IMM", bits);
}

static void
print_relbr(xed_print_info_t* pi)
{
    if (pi->format_options.xml_a)
         xed_pi_strcat(pi,"<RELBR>");

    print_rel_sym(pi,print_address, branch_displacement);

    xml_print_end(pi,"RELBR");
}

static void xed_print_operand( xed_print_info_t* pi )
{
    const xed_inst_t*           xi = xed_decoded_inst_inst(pi->p);
    const xed_operand_values_t* ov = xed_decoded_inst_operands_const(pi->p);  
    const xed_operand_t*        op = xed_inst_operand(xi,pi->operand_indx);
    xed_operand_enum_t     op_name = xed_operand_name(op);
    const xed_bool_t leading_zeros = 0;
    
    if (xed_operand_operand_visibility(op) == XED_OPVIS_SUPPRESSED) {
        if (stringop_memop(pi->p,op)) {
            /* allow a fall through to print the memop for stringops to
             * match dumpbin */
        }
        else {
            print_seg_prefix_for_suppressed_operands(pi, ov, op);
            return;
        }
    }

    // for mangling name of x87 implicit operand
    pi->implicit = (xed_operand_operand_visibility(op) == XED_OPVIS_IMPLICIT);

    xed_operand_spacer(pi);
    pi->emitted = 1;
    if (pi->format_options.xml_a)
        xed_pi_strcat(pi,"<OPERAND>");
    
    switch(xed_operand_name(op)) {
      case XED_OPERAND_AGEN:
      case XED_OPERAND_MEM0: {
          xed_bool_t no_base_index = 0;
          xed_reg_enum_t base = xed3_operand_get_base0(pi->p);
          xed_reg_enum_t seg = xed3_operand_get_seg0(pi->p);
          xed_reg_enum_t index = xed3_operand_get_index(pi->p);

          xed_int64_t disp =
              xed_operand_values_get_memory_displacement_int64(ov);
          unsigned int disp_bits =
              xed_operand_values_get_memory_displacement_length_bits(ov);

          xed_bits_t scale = xed3_operand_get_scale(pi->p);
          xed_bool_t started = 0;
          xed_uint_t bytes =
              xed_decoded_inst_operand_length_bits(pi->p, pi->operand_indx)>>3;
          if (pi->format_options.xml_a) {
              if (xed_operand_name(op) == XED_OPERAND_AGEN)
                  xed_pi_strcat(pi,"<AGEN>");
              else
                  xml_tag_pi(pi, "MEM", bytes << 3);
          }

          if (xed_operand_name(op) != XED_OPERAND_AGEN)
              pi->blen = xed_strncat_lower(
                  pi->buf,
                  xed_decoded_inst_print_ptr_size(bytes),
                  pi->blen);

          xed_pi_strcat(pi,"ptr ");
          if (seg != XED_REG_INVALID &&
              !xed_operand_values_using_default_segment(ov, 0))
          {
              if (xed_operand_name(op) != XED_OPERAND_AGEN) {
                  pi->blen = xed_strncat_lower(pi->buf,
                                               xed_reg_enum_t2str(seg),
                                               pi->blen);
                  pi->blen = xed_strncat(pi->buf,":",pi->blen);
              }
          }

          xed_pi_strcat(pi,"[");
          if (base != XED_REG_INVALID) {
              pi->blen = xed_strncat_lower(pi->buf,
                                           xed_reg_enum_t2str(base),
                                           pi->blen);
              started = 1;
          }
          
          if (index != XED_REG_INVALID)
          {
#if defined(XED_MPX)
              if (xed_decoded_inst_get_attribute(
                      pi->p,
                      XED_ATTRIBUTE_INDEX_REG_IS_POINTER))
              {
                  // MPX BNDLDX/BNDSTX instr are unusual in that they use
                  // the index reg as distinct operand.

                  pi->extra_index_operand = index;
              }
              else  // normal path
#endif
              {
                  if (started)
                      xed_pi_strcat(pi,"+");
                  started = 1;
                  pi->blen = xed_strncat_lower(pi->buf,
                                               xed_reg_enum_t2str(index),
                                               pi->blen);
                  
                  if (scale != 1 || pi->format_options.omit_unit_scale==0) {
                      xed_pi_strcat(pi,"*");
                      pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf),
                                          XED_STATIC_CAST(xed_uint_t,scale),
                                          pi->blen);
                  }
              }
          }
          
          no_base_index = (base == XED_REG_INVALID) &&
                          (index == XED_REG_INVALID);

          if (xed_operand_values_has_memory_displacement(ov))
          {
              if (disp_bits && (disp || no_base_index))
              {
                  xed_uint_t negative = (disp < 0) ? 1 : 0;
                  if (started)
                  {
                      if (negative)
                      {
                          xed_pi_strcat(pi,"-");
                          disp = - disp;
                      }
                      else
                          xed_pi_strcat(pi,"+");
                  }
                  xed_pi_strcat(pi,"0x");
                  pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                                   disp,
                                                   disp_bits,
                                                   leading_zeros,
                                                   pi->blen,
                                                   pi->format_options.lowercase_hex);
              }
          }
          xed_pi_strcat(pi,"]");
          
          print_write_mask_generic(pi);
          if (base == XED_REG_RIP && xed_operand_values_has_memory_displacement(ov))
              print_rel_sym(pi,no_print_address, memory_displacement);

          if (xed_operand_name(op) == XED_OPERAND_AGEN)
              xml_print_end(pi,"AGEN");
          else
              xml_print_end(pi,"MEM");
          break;
      }

      case XED_OPERAND_MEM1: {
          xed_reg_enum_t base = xed3_operand_get_base1(pi->p);
          xed_reg_enum_t seg = xed3_operand_get_seg1(pi->p);
          xed_uint_t bytes =
              xed_decoded_inst_operand_length_bits(pi->p, pi->operand_indx)>>3;

          if (pi->format_options.xml_a)
              xml_tag_pi(pi, "MEM", bytes << 3);

          pi->blen = xed_strncat_lower(pi->buf,
                                       xed_decoded_inst_print_ptr_size(bytes),
                                       pi->blen);
          
          xed_pi_strcat(pi,"ptr ");

          if (seg != XED_REG_INVALID &&
              !xed_operand_values_using_default_segment(ov, 1))
          {
              pi->blen = xed_strncat_lower(pi->buf,
                                           xed_reg_enum_t2str(seg),
                                           pi->blen);
              xed_pi_strcat(pi,":");
          }
          xed_pi_strcat(pi,"[");
          if (base != XED_REG_INVALID) 
              pi->blen = xed_strncat_lower(pi->buf,
                                           xed_reg_enum_t2str(base),
                                           pi->blen);
          xed_pi_strcat(pi,"]");
          xml_print_end(pi,"MEM");
          break;
      }
      case XED_OPERAND_IMM0: {
          if ( xed3_operand_get_imm0signed(pi->p) &&
               pi->format_options.no_sign_extend_signed_immediates == 0 )
          {
              // sign-extend imm to effective operand width
              xed_int32_t imm;
              unsigned int eff_bits = xed_decoded_inst_get_operand_width(pi->p);
              imm = XED_STATIC_CAST(xed_int32_t,
                                  xed_operand_values_get_immediate_int64(ov));
              xml_print_imm(pi,eff_bits);
              xed_pi_strcat(pi,"0x");
              pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf), 
                                               imm,
                                               eff_bits,
                                               leading_zeros,
                                               pi->blen,
                                               pi->format_options.lowercase_hex);
          }
          else {
              // how many bits of imm hold imm values. Sometimes we use upper bits
              // for other things (like register specifiers)
              unsigned int real_bits = xed_decoded_inst_operand_element_size_bits(
                                               pi->p,
                                               pi->operand_indx);

              xed_uint64_t imm = xed_operand_values_get_immediate_uint64(ov);
              xml_print_imm(pi, real_bits);
              xed_pi_strcat(pi,"0x");
              pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf), 
                                         imm,
                                         real_bits,
                                         leading_zeros,
                                         pi->blen,
                                         pi->format_options.lowercase_hex);
          }
          xml_print_end(pi,"IMM");
          break;
      }
      case XED_OPERAND_IMM1: { // The ENTER instruction
          xed_uint64_t imm = xed3_operand_get_uimm1(pi->p);
          xml_print_imm(pi, 8);
          xed_pi_strcat(pi,"0x");
          pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                           imm,
                                           8,
                                           leading_zeros,
                                           pi->blen,
                                           pi->format_options.lowercase_hex);
          xml_print_end(pi,"IMM");
          break;
      }

      case XED_OPERAND_PTR: {        
          unsigned int disp =(unsigned int)
                        xed_operand_values_get_branch_displacement_int32(ov);
          
          xed_bool_t long_mode = xed_operand_values_get_long_mode(
                                      xed_decoded_inst_operands_const(pi->p));
          
          xed_uint_t bits_to_print = long_mode ? 8*8 :4*8;
          if (pi->format_options.xml_a)
              xed_pi_strcat(pi,"<PTR>");

          xed_pi_strcat(pi,"0x");
          pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                           disp,
                                           bits_to_print,
                                           leading_zeros,
                                           pi->blen,
                                           pi->format_options.lowercase_hex);
          xml_print_end(pi,"PTR");
          break;

      }
      case XED_OPERAND_RELBR:
          print_relbr(pi);
          break;

      default: {
          xed_operand_ctype_enum_t  ctype = xed_operand_get_ctype(op_name);
          switch(ctype) {
            case XED_OPERAND_CTYPE_XED_BITS_T: {
                xed_bits_t b;
                xed3_get_generic_operand(pi->p,op_name,&b);

                pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf),
                                    XED_STATIC_CAST(xed_uint_t,b),
                                    pi->blen);
                break;
            }
            case XED_OPERAND_CTYPE_XED_UINT8_T: {
                xed_uint32_t b;
                xed3_get_generic_operand(pi->p,op_name,&b);
                pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf), b, pi->blen);

                break;
            }
            case XED_OPERAND_CTYPE_XED_ERROR_ENUM_T: {
                /* THIS DOES NOT HAPPEN */
                xed_pi_strcat(pi,"NDY");
                break;
            }
            case XED_OPERAND_CTYPE_XED_ICLASS_ENUM_T: {
                /* THIS DOES NOT HAPPEN */
                xed_iclass_enum_t b = xed3_operand_get_iclass(pi->p);
                xed_pi_strcat(pi,xed_iclass_enum_t2str(b));
                break;
            }
            case XED_OPERAND_CTYPE_XED_REG_ENUM_T: {
                /* THIS ONE IS IMPORTANT -- IT PRINTS THE REGISTERS */
                xed_reg_enum_t reg;
                xed3_get_generic_operand(pi->p,op_name,&reg);
                print_reg_writemask(pi,reg);
                break;
            }
                                        
            default:
              xed_pi_strcat(pi, "NOT HANDLING CTYPE ");
              xed_pi_strcat(pi, xed_operand_ctype_enum_t2str(ctype));
              xed_assert(0);
          } // inner switch
      } // default case of outer switch
    } // outer switch


    xed_print_operand_decorations(pi, op);
    xml_print_end(pi,"OPERAND");
}


static void
setup_print_info(xed_print_info_t* pi)
{
    // init the internal fields
    pi->emitted = 0;
    pi->operand_indx = 0;
    pi->skip_operand = 0;
    pi->implicit = 0;    
    pi->extra_index_operand = XED_REG_INVALID; 

    pi->buf[0]=0; /* allow use of strcat for everything */

    if (pi->format_options_valid==0) {
        // grab the defaults.
        pi->format_options_valid = 1;
        pi->format_options = xed_format_options;
    }
}

//exported
void xed_init_print_info(xed_print_info_t* pi)
{
    memset(pi, 0, sizeof(xed_print_info_t));
    pi->syntax = XED_SYNTAX_INTEL;
}


static xed_bool_t
xed_decoded_inst_dump_intel_format_internal(xed_print_info_t* pi)
{
    unsigned int i;
    unsigned int noperands;
    const char* instruction_name=0 ;
    const xed_inst_t* xi = xed_decoded_inst_inst(pi->p);
    
    if (!xi)
        return 0;

    setup_print_info(pi);

    if (pi->format_options.xml_a)
        xed_pi_strcat(pi,"<INS>");

    xed_decoded_inst_dump_common(pi);
    
    instruction_name = instruction_name_intel(pi->p);
    if (pi->format_options.xml_a)
        xed_pi_strcat(pi,"<ICLASS>");
    pi->blen = xed_strncat_lower(pi->buf, instruction_name, pi->blen);
    xml_print_end(pi,"ICLASS");
    
    noperands = xed_inst_noperands(xi);
    // to avoid printing the space in the no-operands case, it is
    // sufficient to test noperands because the skip_operand and
    // extra_index_operand cases are guaranteed to have other printed
    // operands.
    if (noperands)
        xed_pi_strcat(pi," ");

    /* print the operands */

    for( i=0;i<noperands;i++)
    {
        if (pi->skip_operand)
        {
            pi->skip_operand = 0;
        }
        else
        {
            pi->operand_indx=i;
            xed_print_operand(pi);
        }
    }
    
    if (pi->extra_index_operand != XED_REG_INVALID) {
        xed_operand_spacer(pi);
        if (pi->format_options.xml_a)
            xed_pi_strcat(pi,"<OPERAND>");
        print_reg_xml(pi,pi->extra_index_operand);
        xml_print_end(pi,"OPERAND");
    }


    if (pi->format_options.xml_f) 
        pi->blen = xml_print_flags(pi->p, pi->buf, pi->blen);
    xml_print_end(pi,"INS");
    return 1;
}



static xed_bool_t
xed_decoded_inst_dump_att_format_internal(
    xed_print_info_t* pi)
{
    int i,j,intel_way, noperands;
    const int leading_zeros=0;
    const xed_inst_t* xi = xed_decoded_inst_inst(pi->p);
    const xed_operand_values_t* ov = xed_decoded_inst_operands_const(pi->p);  
    const char* instruction_name = 0;
    const char* suffix = 0;
    
    if (!xi)
        return 0;

    setup_print_info(pi);
    xed_decoded_inst_dump_common(pi);
    
    instruction_name = instruction_name_att(pi->p);
    pi->blen = xed_strncat_lower(pi->buf, instruction_name, pi->blen);
    suffix = instruction_suffix_att(pi->p);
    if (suffix) {
        xed_pi_strcat(pi,suffix);
    }
    
    noperands = xed_inst_noperands(xi);    
    if (noperands)
        xed_pi_strcat(pi," ");

    intel_way = 0;
    if (xed_inst_get_attribute(xi, XED_ATTRIBUTE_ATT_OPERAND_ORDER_EXCEPTION))
        intel_way = 1;

#if defined(XED_MPX)
    if (xed_decoded_inst_get_attribute(
            pi->p,
            XED_ATTRIBUTE_INDEX_REG_IS_POINTER))
    {

        for( j=0;j<noperands;j++)
        {
            const xed_operand_t* op;

            i = noperands - j - 1;  // never intel_way

            op = xed_inst_operand(xi,i);
            switch(xed_operand_name(op))
            {
              case XED_OPERAND_MEM0: {
                  xed_reg_enum_t indx = xed3_operand_get_index(pi->p);
                  xed_pi_strcat(pi,"%");                      
                  pi->blen = xed_strncat_lower(pi->buf,
                                              xed_reg_enum_t2str(indx),
                                              pi->blen);
                  
                  pi->emitted=1;
              } // case
              default:
                break; // ignore everything else
                
            } // switch
        } //for
    }
#endif

    for( j=0;j<noperands;j++) {
        const xed_operand_t* op;
        xed_operand_enum_t op_name;

        if (intel_way)
            i = j;
        else
            i = noperands - j - 1;

        op = xed_inst_operand(xi,i);
        op_name = xed_operand_name(op);
        
        // for mangling name of x87 implicit operand
        pi->implicit = (xed_operand_operand_visibility(op) == XED_OPVIS_IMPLICIT);

        pi->operand_indx=i; // use the Intel numbering
#if defined(XED_SUPPORTS_AVX512)
        if (pi->format_options.write_mask_curly_k0 &&
            operand_is_writemask(op))
        {
            continue;
        }
#endif

        if (xed_operand_operand_visibility(op) == XED_OPVIS_SUPPRESSED) {
            if (stringop_memop(pi->p,op)) {
                /* print the memop */
            }
            else {
                /* suppressed memops with nondefault segments get their
                 * segment printed */
                if (xed_operand_name(op) == XED_OPERAND_MEM0) {
                    if (xed_operand_values_using_default_segment(ov, 0) == 0) {
                        xed_reg_enum_t seg = xed3_operand_get_seg0(pi->p);
                        pi->blen = xed_strncat_lower(pi->buf,
                                                     xed_reg_enum_t2str(seg),
                                                     pi->blen);
                        xed_pi_strcat(pi,":");
                        pi->emitted=1;
                    }
                }
                else if (xed_operand_name(op) == XED_OPERAND_MEM1) {
                    if (xed_operand_values_using_default_segment(ov, 1) == 0) {
                        xed_reg_enum_t seg = xed3_operand_get_seg1(pi->p);
                        pi->blen = xed_strncat_lower(pi->buf,
                                                     xed_reg_enum_t2str(seg),
                                                     pi->blen);
                        xed_pi_strcat(pi, ":");
                        pi->emitted=1;
                    }
                }
                continue;
            }
        }

        if (pi->emitted)
            xed_pi_strcat(pi,", ");
        pi->emitted=1;

        switch(xed_operand_name(op)) {
          case XED_OPERAND_AGEN:
          case XED_OPERAND_MEM0: {
              xed_reg_enum_t base = xed3_operand_get_base0(pi->p);
              xed_reg_enum_t seg = xed3_operand_get_seg0(pi->p);
              xed_reg_enum_t index = xed3_operand_get_index(pi->p);
              xed_int64_t disp =
                  xed_operand_values_get_memory_displacement_int64(ov);
              unsigned int disp_bits =
                  xed_operand_values_get_memory_displacement_length_bits(ov);
              
              xed_bits_t scale = xed3_operand_get_scale(pi->p);
              
              if (seg != XED_REG_INVALID &&
                  !xed_operand_values_using_default_segment(ov, 0))
              {
                  if (xed_operand_name(op) != XED_OPERAND_AGEN) {
                      xed_pi_strcat(pi,"%");
                      pi->blen = xed_strncat_lower(pi->buf,
                                                   xed_reg_enum_t2str(seg),
                                                   pi->blen);
                      xed_pi_strcat(pi,":");                      
                  }
              }
              if (xed_operand_values_has_memory_displacement(ov))
              {
                  if (disp_bits && disp) {
                      if (disp<0) {
                          if ( (base != XED_REG_INVALID) ||
                               (index != XED_REG_INVALID) ) {
                              xed_pi_strcat(pi,"-");                      
                              disp = - disp;
                          }
                      }
                      xed_pi_strcat(pi,"0x");
                      pi->blen =
                          xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                                disp,
                                                disp_bits,
                                                leading_zeros,
                                                pi->blen,
                                                pi->format_options.lowercase_hex);
                  }
              }
              
              if (base != XED_REG_INVALID || index != XED_REG_INVALID)
                  xed_pi_strcat(pi,"(");                      
              if (base != XED_REG_INVALID) {
                  xed_pi_strcat(pi,"%");                      
                  pi->blen = xed_strncat_lower(pi->buf,
                                               xed_reg_enum_t2str(base),
                                               pi->blen);
              }
              if (index != XED_REG_INVALID)
              {
#if defined(XED_MPX)
                  if (xed_decoded_inst_get_attribute(
                          pi->p,
                          XED_ATTRIBUTE_INDEX_REG_IS_POINTER))
                  {
                      // MPX BNDLDX/BNDSTX instr are unusual in that they use
                      // the index reg as distinct operand.
                      
                      // HANDLED ABOVE!
                  }
                  else
#endif
                  {
                      xed_pi_strcat(pi,",%");                      
                      pi->blen = xed_strncat_lower(pi->buf,
                                                  xed_reg_enum_t2str(index),
                                                  pi->blen);
                      xed_pi_strcat(pi,",");                      
                      pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf),
                                         XED_STATIC_CAST(xed_uint_t,scale),
                                         pi->blen);
                  }
              }
              if (base != XED_REG_INVALID || index != XED_REG_INVALID)
                  xed_pi_strcat(pi,")");
              
              print_write_mask_generic(pi);
              if (base == XED_REG_RIP && xed_operand_values_has_memory_displacement(ov))
                  print_rel_sym(pi,no_print_address, memory_displacement);

              break;
          }

          case XED_OPERAND_MEM1: {
              xed_reg_enum_t base = xed3_operand_get_base1(pi->p);
              xed_reg_enum_t seg = xed3_operand_get_seg1(pi->p);
              if (seg != XED_REG_INVALID &&
                  !xed_operand_values_using_default_segment(ov, 1))
              {
                  xed_pi_strcat(pi,"%");                      
                  pi->blen = xed_strncat_lower(pi->buf,
                                               xed_reg_enum_t2str(seg),
                                               pi->blen);
                  xed_pi_strcat(pi,":");                      
              }

              if (base != XED_REG_INVALID) {
                  xed_pi_strcat(pi,"(%");                      
                  pi->blen = xed_strncat_lower(pi->buf,
                                               xed_reg_enum_t2str(base),
                                               pi->blen);
                  xed_pi_strcat(pi,")");                      
              }
              break;
          }
          case XED_OPERAND_IMM0: {
              xed_pi_strcat(pi,"$0x");                      
              if ( xed3_operand_get_imm0signed(pi->p) &&
                   pi->format_options.no_sign_extend_signed_immediates == 0 )
              {
                  // sign-extend imm to effective operand width
                  unsigned int eff_bits = xed_decoded_inst_get_operand_width(pi->p);
                  xed_int32_t imm = XED_STATIC_CAST(xed_int32_t,
                                   xed_operand_values_get_immediate_int64(ov));
                  pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                             imm,
                                             eff_bits,
                                             leading_zeros,
                                             pi->blen,
                                             pi->format_options.lowercase_hex);
              }
              else {
                  // how many bits of imm hold imm values. Sometimes we use upper bits
                  // for other things (like register specifiers)
                  unsigned int real_bits = xed_decoded_inst_operand_element_size_bits(
                                               pi->p,
                                               pi->operand_indx);
                  xed_uint64_t imm =xed_operand_values_get_immediate_uint64(ov);
                  pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                             imm,
                                             real_bits,
                                             leading_zeros,
                                             pi->blen,
                                             pi->format_options.lowercase_hex);
              }
              break;
          }
          case XED_OPERAND_IMM1: { // The ENTER instruction
              xed_uint64_t imm = xed3_operand_get_uimm1(pi->p);
              xed_pi_strcat(pi,"$0x");                      
              pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                               imm,
                                               8,
                                               leading_zeros,
                                               pi->blen,
                                               pi->format_options.lowercase_hex);
              break;
          }

          case XED_OPERAND_PTR: {
              unsigned int disp =
                  xed_decoded_inst_get_branch_displacement(pi->p);
              xed_bool_t long_mode =  
                       xed_operand_values_get_long_mode(
                              xed_decoded_inst_operands_const(pi->p));
              
              xed_uint_t bits_to_print = long_mode ? 8*8 :4*8;
              xed_pi_strcat(pi,"$0x");                      
              pi->blen = xed_itoa_hex_ul(pi->buf+xed_strlen(pi->buf),
                                               disp,
                                               bits_to_print,
                                               leading_zeros,
                                               pi->blen,
                                               pi->format_options.lowercase_hex);
              break;
          }

          case XED_OPERAND_RELBR:
              print_relbr(pi);
              break;

          default: {
              xed_operand_ctype_enum_t  ctype = xed_operand_get_ctype(op_name);
              switch(ctype) {
                case XED_OPERAND_CTYPE_XED_BITS_T: {
                    xed_bits_t b;
                    xed3_get_generic_operand(pi->p,op_name,&b);

                    pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf),
                                       XED_STATIC_CAST(xed_uint_t,b),
                                       pi->blen);
                    break;
                }
                case XED_OPERAND_CTYPE_XED_UINT8_T: {
                    xed_uint32_t b;
                    xed3_get_generic_operand(pi->p,op_name,&b);
                    pi->blen = xed_itoa(pi->buf+xed_strlen(pi->buf),
                                        b,
                                        pi->blen);
                    break;
                }
                case XED_OPERAND_CTYPE_XED_ERROR_ENUM_T: {
                    /* DOES NOT OCCUR */
                    xed_pi_strcat(pi,"NDY");                      
                    break;
                }
                case XED_OPERAND_CTYPE_XED_ICLASS_ENUM_T: {
                    /* DOES NOT OCCUR */
                    xed_iclass_enum_t b = xed3_operand_get_iclass(pi->p);
                    pi->blen = xed_strncat_lower(pi->buf,
                                                xed_iclass_enum_t2str(b),
                                                pi->blen);
                    break;
                }
                case XED_OPERAND_CTYPE_XED_REG_ENUM_T: { 
                    /* THIS IS IMPORTANT - THIS IS WHERE REGISTERS GET
                     * PRINTED */
                    xed_reg_enum_t reg;
                    xed3_get_generic_operand(pi->p,op_name,&reg);
                    print_reg_writemask(pi, reg);
                    break;
                }
                                        
                default:
                  xed_pi_strcat(pi,"NOT HANDLING CTYPE ");
                  xed_pi_strcat(pi, xed_operand_ctype_enum_t2str(ctype));
                  xed_assert(0);
              }
          }
        }
        xed_print_operand_decorations(pi, op);
    } /* for operands */

    
    return 1;
}


////////////////////////////////////////////////////////////////////////////
static xed_bool_t
validate_print_info(xed_print_info_t* pi)
{
    if (pi->p == 0)
        return 1; // fail
    if (pi->buf == 0) 
        return 1; // fail
    if (pi->blen < 16)
        return 1; // fail
    return 0;
}


xed_bool_t
xed_format_context(xed_syntax_enum_t syntax,
                   const xed_decoded_inst_t* xedd,
                   char* out_buffer,
                   int  buffer_len,
                   xed_uint64_t runtime_instruction_address,
                   void* context,
                   xed_disassembly_callback_fn_t symbolic_callback)
{
    xed_print_info_t pi;
    xed_init_print_info(&pi);
    pi.p = xedd;
    pi.blen = buffer_len;
    pi.buf = out_buffer;

    // passed back to symbolic disassembly function
    pi.context = context;
    pi.disassembly_callback = symbolic_callback;
    
    pi.runtime_address = runtime_instruction_address;
    pi.syntax = syntax;
    pi.format_options_valid = 0; // use defaults
    pi.buf[0]=0; //allow use of strcat
    return xed_format_generic(&pi);
}


// preferred interface (fewer parameters, most flexible)

xed_bool_t xed_format_generic( xed_print_info_t* pi )
{
    if (validate_print_info(pi))
        return 0;

    if (pi->syntax == XED_SYNTAX_INTEL)
        return xed_decoded_inst_dump_intel_format_internal(pi);
    else if (pi->syntax == XED_SYNTAX_ATT)
        return xed_decoded_inst_dump_att_format_internal(pi);
    else if (pi->syntax == XED_SYNTAX_XED)
        return xed_decoded_inst_dump_xed_format(pi->p,
                                                pi->buf,
                                                pi->blen,
                                                pi->runtime_address);
    return 0;
}
