/*BEGIN_LEGAL 

Copyright (c) 2019 Intel Corporation

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

// more natural assembly language parser

#include <assert.h>
#include <stdint.h>
#include <string.h> // strcmp, strncmp
#include <stdlib.h> // malloc, free
#include <stdio.h>  // vprintf, fprintf
#include <ctype.h>  // isspace, isdigit, isalnum
#include <stdarg.h>

#include "xed-examples-util.h" // xed_upcase_buf
#include "xed-asmparse.h"

static int asp_dbg_verbosity = 1;

/* PROTOTYPES */
static char* asp_strdup(const char* s);
static void upcase(char* s);
static void delete_slist_t(slist_t* s);
static slist_t* get_slist_node(void);
static void clean_out_memparse_rec_t(memparse_rec_t* p);
static void delete_opnd_list_t(opnd_list_t* s);
static opnd_list_t* get_opnd_list_node(void);
static void add_decorator(opnd_list_t* onode, char* d);
static void grab_prefixes(char**p, xed_enc_line_parsed_t* v);
static void study_prefixes(xed_enc_line_parsed_t* v);
static void grab_inst(char**p, xed_enc_line_parsed_t* v);
static void grab_operand(char**p, xed_enc_line_parsed_t* v);
//static slist_t* reverse_list(slist_t* head);
static int isreg(char* s);
static int isdecorator(char* s);
static int64_t letter_cvt(char a, char base);
static int asm_isnumber(char* s, int64_t* onum, int arg_negative);
static int ismemref(char* s);
static int valid_decorator(char const* s);
static int grab_decorator(char* s, unsigned int pos, char** optr);
static void parse_reg(xed_enc_line_parsed_t* v, char* s, opnd_list_t* onode);
static void parse_decorator(char* s, opnd_list_t* onode);
static void parse_memref(char* s, opnd_list_t* onode);
static void refine_operand(xed_enc_line_parsed_t* v, char* s);
static void refine_operands(xed_enc_line_parsed_t* v);
static unsigned int skip_spaces(char *s, unsigned int offset);

/////////////////////////


static char* asp_strdup(char const* s) {
    return xed_strdup(s);
}

/* Verbosity levels:
   0 - only errors and end result
   1 - informational messages about implicit decision made by encoder,
       such as correction of operand sizes, bitness etc
   2 - debugging info */
void asp_set_verbosity(int v) {
    asp_dbg_verbosity = v;
}

void asp_printf(const char* format, ...) {
    if (asp_dbg_verbosity < 1)
        return;
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

void asp_dbg_printf(const char* format, ...) {
    if (asp_dbg_verbosity < 2)
        return;
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
}

/* Errors are always printed to stderr */
void asp_error_printf(const char* format, ...) {
    va_list args;
    va_start(args, format);
    fprintf(stderr, "ERROR: ");
    vfprintf(stderr, format, args);
    va_end(args);
}

static void upcase(char* s) {
    (void)xed_upcase_buf(s);
}


static void delete_slist_t(slist_t* s) {
    slist_t* p = s;
    
    while(p) {
        slist_t* t = p;
        p=p->next;
        free(t->s);  // FIXME: might free static stuff!
        free(t);
    }
}

static slist_t* get_slist_node() {
    slist_t* node = (slist_t*)malloc(sizeof(slist_t));
    assert(node != 0);
    node->s = 0;
    node->next = 0;
    return node;
}



static void clean_out_memparse_rec_t(memparse_rec_t* p) {
    if (p->seg)
        free(p->seg);
    if (p->base)
        free(p->base);
    if (p->index)
        free(p->index);
    if (p->disp)
        free(p->disp);
    if (p->scale)
        free(p->scale);
    p->mem_size = 0; // not allocated!
    p->mem_bits = 0; 
    p->ndisp = 0; 
}


static void delete_opnd_list_t(opnd_list_t* s) {
    opnd_list_t* p = s;
    while(p) {
        opnd_list_t* t = p;
        free(p->s);
        clean_out_memparse_rec_t(&p->mem);
        delete_slist_t(p->decorators);
        p = p->next;
        free(t);
    }
}


xed_enc_line_parsed_t* asp_get_xed_enc_node(void) {
    xed_enc_line_parsed_t*  v = (xed_enc_line_parsed_t*)
                                  malloc(sizeof(xed_enc_line_parsed_t));
    assert(v != 0);
    memset(v, 0, sizeof(xed_enc_line_parsed_t));
    return v;
}

void asp_delete_xed_enc_line_parsed_t(xed_enc_line_parsed_t* v) {
    if (v->iclass_str)
        free(v->iclass_str);
    if (v->input) 
        free(v->input);

    delete_slist_t(v->operands);
    delete_slist_t(v->prefixes);
    delete_opnd_list_t(v->opnds);
    free(v);
}

static opnd_list_t* get_opnd_list_node() {
    opnd_list_t* p  = (opnd_list_t*)malloc(sizeof(opnd_list_t));
    assert(p != 0);
    memset(p, 0, sizeof(opnd_list_t));
    p->type = OPND_INVALID;
    return p;
}

static void add_decorator(opnd_list_t* onode, char* d) {
    slist_t* dnode = get_slist_node();
    dnode->s = d;
    dnode->next = onode->decorators;
    onode->decorators = dnode;
}

static char const* decorators[] = {
    "{K0}",
    "{K1}",
    "{K2}",
    "{K3}",
    "{K4}",
    "{K5}",
    "{K6}",
    "{K7}",
    "{Z}",
    "{RNE-SAE}",
    "{RD-SAE}",
    "{RU-SAE}",
    "{RZ-SAE}",
    "{SAE}",
    "{1TO2}",
    "{1TO4}",
    "{1TO8}",
    "{1TO16}",
    "{1TO32}",
    "{1TO64}",
    0 };

static char const* mem_size_qualifiers[] = {
    "BYTE",
    "WORD",
    "DWORD",
    "QWORD",
    "XMMWORD",
    "YMMWORD",
    "ZMMWORD",
    0
};

static char const* scales[] = {
    "1",
    "2",
    "4",
    "8",
    0
};

static void study_prefixes(xed_enc_line_parsed_t* v) {
    slist_t* p = v->prefixes;
    while(p) {
        if (strcmp("REPNE",p->s) == 0) 
            v->seen_repne = 1;
        else if (strcmp("REPE",p->s) == 0) 
            v->seen_repe = 1;
        else if (strcmp("REP",p->s) == 0) 
            v->seen_repe = 1;
        else if (strcmp("LOCK",p->s) == 0) 
            v->seen_lock = 1;
        p = p->next;
    }
}

static void grab_prefixes(char**p, xed_enc_line_parsed_t* v)
{
    // grab any matching strings up to next space
    char const* prefixes[] = { "DATA16", "DATA32",
                               "ADDR16", "ADDR32",
                               "REX", "REWXW",
                               "XACQUIRE", "XRELEASE",
                               "LOCK",
                               "REP", "REPE", "REPNE", 
                               0 };
    char* h = asp_strdup(*p);
    char* q = h;
    char* r = h;
    
    unsigned int found=1;

    do {
        unsigned int i=0;

        r = q;
        while(*q) {
            if (isspace(*q)) {
                *q = 0; // jam a null
                q++;
                break;
            }
            q++;
        }
        found = 0;
        for (i=0; prefixes[i]; i++) {
            if (strcmp(r, prefixes[i]) == 0) {
                slist_t* node = 0;
                // matched a prefix
                found = 1;
                //grab the string, pointed to by r
                asp_dbg_printf("PREFIX [%s]\n",r);
                node = get_slist_node();
                node->s = asp_strdup(r);
                if (v->prefixes) 
                    node->next = v->prefixes;
                v->prefixes = node;
                
                // advance q to next nonspace
                while(*q && isspace(*q))
                    q++;
                break;
            }
        }
    }
    while(found); 

    // r-h is the distance in the copy of the string we've advanced through so far.
    *p = *p + (r-h);
    free(h);
}

static void grab_inst(char**p, xed_enc_line_parsed_t* v)
{
        
    // grab next non-whitespace string
    char* q = *p;
    while(*q) {
        if (isspace(*q)) {
            *q = 0; // jam a null
            q++;
            break;
        }
        q++;
    }
    v->iclass_str = asp_strdup(*p);
    /* Note that it is not the final iclass as it may require mangling */
    asp_dbg_printf("MNEMONIC [%s]\n",v->iclass_str);
    *p = q;
}

static void grab_operand(char**p, xed_enc_line_parsed_t* v)
{
    // grab next operand string (reg, memop) with decorations
    slist_t* node = 0;
        
    char* q = *p;
    char* r = 0;
    while(*q && isspace(*q))
        q++;
    // grab until next comma or end-of-string
    r = q;
    while(*q && *q != ',')
        q++;
    if (*q) {
        *q = 0; // jam null or overwrite null
        q++;
    }
    // remove trailing white space
    if (q>r) {
        char *z = q-1; // start at null
        while (z > r) {
            if (*z == 0) {
                z--;
                continue;
            }
            if (isspace(*z)) {
                *z = 0;
                z--;
                continue;
            }
            break;
        }
    }
    asp_dbg_printf("OPERAND: [%s]\n", r);
    node = get_slist_node();
    node->s = asp_strdup(r);
    if (v->operands) 
        node->next = v->operands;
    v->operands = node;
    *p  = q;
}


#if 0
/*

      a->b->c->d->0
      p  q
      
   0<-a  b->c->d->0
      p  q
      
   0<-a<-b c->d->0
      p  q t

   0<-a<-b<-c d->0
         p  q t
            
   0<-a<-b<-c<-d 0
            p  q t
      
   0<-a<-b<-c<-d 0
               p q
      
 */

static slist_t* reverse_list(slist_t* head) {
    slist_t* p = head;  // prev
    slist_t* q = 0;     // current
    slist_t* t = 0;     // dangling head of rest of list

    if (p && p->next) {
        q = p->next;
        p->next = 0; // new end of list
    }
    else
        return p;

    while(q) {
        t = q->next;
        q->next = p;
        p = q;
        q = t;
    }
    return p;
}
#endif

static int isreg(char* s) {  // including decorators
    if (s) {
        if (isalpha(s[0])) {
            int i;
            for(i=1;s[i];i++)
                // allow alnum, dash & parens (x87), curlies, else bail
                if ( !isalnum(s[i])  &&
                     s[i] != '{'     &&
                     s[i] != '('     &&
                     s[i] != ')'     &&
                     s[i] != '-'     &&
                     s[i] != '}'      )
                    return 0;
            return 1;
        }
    }
    return 0;
}
static int isdecorator(char* s) {  
    if (s) {
        if (s[0] == '{') {
            int i;
            for(i=1;s[i];i++)
                // allow alnum, dash & right-curly, else bail
                if ( !isalnum(s[i])  &&
                     s[i] != '-'     &&
                     s[i] != '}'      )
                    return 0;
            return 1;
        }
    }
    return 0;
}

/* Return true if s matches pattern "num:num" */
static int islongptr(char *s) {
    if (!s)
        return 0;
    /* skip optional "far" */
    if (s[0] == 'F' && s[1] == 'A' && s[2] == 'R') {
        s += 3;
        s += skip_spaces(s, 0);
    }
    
    int column_pos = -1;
    for (int i = 0; s[i]; i++) {
        if (s[i] == ':') {
            column_pos = i;
            break;
        }
    }
    if (column_pos < 0)
        return 0;
    char *first = s;
    char *second = s + column_pos + 1;
    s[column_pos] = '\0'; // temporarily split the string
    int64_t unused = 0;
    int res = asm_isnumber(first, &unused, 0) 
              && asm_isnumber(second, &unused, 0); // both parts are numbers
    s[column_pos] = ':'; // restore the separator
    return res;
}

static int64_t letter_cvt(char a, char base) {
    return (int64_t)(a-base);
}


static int asm_isnumber(char* s, int64_t* onum, int arg_negative) {
    // return 1/0 if the string s is a number, and store the number in
    // onum. Handles base10, binary (0b prefix), octal (0 prefix) and hex
    // (0x prefix) number strings.

    // The arg_negative will normally be zero, but I encountered a case
    // when parsing displacements where the minus sign was already eaten by
    // the parser and I didn't want to reallocate the string just to
    // reassociate the minus sign with the number. So for that case, I
    // added a arg_negative to allow me to force the number to be negative
    // without there being an actual leading minus sign present.
    
    
    int binary = 0;
    int hex = 0;
    int octal = 0;
    int negative = 0;
    unsigned int i = 0;
    unsigned int j = 0;
    unsigned int len = xed_strlen(s);
    int64_t val = 0;
    
    if (arg_negative) {
        negative = 1;
    }
    if (s[0]=='-') {
        negative = 1;
        i++;
    }
    if (s[0] == '+') {
        i++;
    }
    
    if (i < len && isdigit(s[i]))  {  //first digit
        if (s[i]=='0' && i+1 < len) {
            if (s[i+1] == 'B') {
                binary = 1;
                i+=2;
            }
            else if (s[i+1] == 'X') {
                hex = 1;
                i+=2;
            }
            else {
                octal = 1;
                i++;
            }
        }

        if (binary) {
            for(j=i;j<len;j++) {
                if (s[j] != '0' && s[j] != '1')
                    return 0; // bad binary number
                else
                    val = val << 1 | (s[j] == '1');
            }
        }
        else if (hex) {
            for(j=i;j<len;j++) {
                if (!isdigit(s[j]) && (s[j] < 'A' || s[j] > 'F') )
                    return 0; // bad hex number
                else if (isdigit(s[j]))
                    val = val << 4 | letter_cvt(s[j],'0');
                else
                    val = val << 4 | (letter_cvt(s[j],'A')+10 );
            }
        }
        else if (octal) {
            for(j=i;j<len;j++) {
                if (s[j] < '0' || s[j] > '7') 
                    return 0; // bad octal number
                else
                    val = val << 3 | letter_cvt(s[j],'0');
            }
        }
        else { //decimal
            for(j=i;j<len;j++) {
                if (!isdigit(s[j]))
                    return 0; // bad normal number
                else
                    val = val * 10 + letter_cvt(s[j],'0');
            }
        }
        asp_dbg_printf("IMM value 0x%016llx\n",val);
        if (negative)  {
            if ((val >> 63ULL) == 1) {
                asp_error_printf("Bad immediate operand - too big to be negative: %s\n",s);
                exit(1);
            }
            else {
                val  = - val;  // FIXME: 2018-11-30 wcvt. error negeating unsigned value...
                asp_dbg_printf("IMM value 0x%016llx\n",val);            
            }
        }
        *onum  = val;
        return 1;
    }
    return 0;
}

static unsigned int skip_spaces(char *s, unsigned int offset) {
    while (s[offset] && isspace(s[offset])) {
        offset++;
    }
    return offset;
}

static int ismemref(char* s) {  // FIXME include directorators
    if (s) {
        unsigned int i=0,offset=0;
        for(i=0;mem_size_qualifiers[i];i++) {
            unsigned int len;
            len = xed_strlen(mem_size_qualifiers[i]);
            if (strncmp(mem_size_qualifiers[i],s,len) == 0) {
                offset = len;
                break;
            }
        }
        offset = skip_spaces(s, offset);
        /* skip optional "ptr" part of memref */
        if (!strncmp(s + offset, "PTR", 3)) {
            offset += 3;
            offset = skip_spaces(s, offset);
        }

        if (s[offset] == '[') {
            // search backwards from end as there might be some {...} decorators.
            unsigned int len = xed_strlen(s);
            for(i=len-1;i>offset && i>0;i--) {
                if (s[i] == ']')
                    return 1;
            }
        }
    }
    return 0;
}


#define BLEN 100

static int valid_decorator(char const* s) {
    int i=0;
    while(decorators[i]) {
        if (strcmp(decorators[i],s) == 0)
            return 1;
        i++;
    }
    return 0;
}
static int grab_decorator(char* s, unsigned int pos, char** optr)
{
    char tbuf[BLEN];
    int tpos=0;
    char* p = s+pos;
    int start = 0;
    while(*p) {
        if (start == 0 && *p == '{') {
            start = 1;
            tbuf[tpos++] = *p;
        }
        else if (start) {
            tbuf[tpos++] = *p;
            if (*p == '}') {
                tbuf[tpos]=0;
                if (valid_decorator(tbuf)) {
                    *optr = asp_strdup(tbuf);
                    return (int)(pos+1);
                }
                else {
                    asp_error_printf("Bad decorator: %s\n", tbuf);
                    exit(1);
                }
            }
        }
        else {
            break;
        }
        p++;
        pos++;
    }
    *optr = 0;
    if (start) {  // we started something but didn't finish it.  
        asp_error_printf("Bad decorator: %s\n", tbuf);
        exit(1);
        return -1; //notreached
    }
    return 0;
}

static void parse_reg(xed_enc_line_parsed_t* v, char* s, opnd_list_t* onode)
{
    char tbuf[BLEN];
    unsigned int i=0;
    unsigned int len=0;

    len = xed_strlen(s);

    while(i<len && s[i] && s[i] != '{') {
        tbuf[i] = s[i];
        i++;
    }
    tbuf[i]=0;
    asp_dbg_printf("REGISTER: %s\n",tbuf);
    onode->s = asp_strdup(tbuf);
    onode->type = OPND_REG;
    onode->reg = str2xed_reg_enum_t(onode->s);

    if (onode->reg >= XED_REG_CR0 && onode->reg <= XED_REG_CR15) {
        v->seen_cr = 1;
    }
    if (onode->reg >= XED_REG_DR0 && onode->reg <= XED_REG_DR7) {
        v->seen_dr = 1;
    }
    
    
    while (i<len && s[i] == '{') {
        char* d = 0;
        int r;
        r = grab_decorator(s,i, &d);

        if (r<0) {
            asp_error_printf("Decorator parsing error\n");
            break;
        }
        i = (unsigned int)r;
        if (d)  {
            asp_dbg_printf("DECORATOR: %s\n",d);
            add_decorator(onode,d);
        }
        if (d==0)
            break;
    }
}


static void parse_decorator(char* s, opnd_list_t* onode)
{
    unsigned int i=0;
    unsigned int len=0;

    len = xed_strlen(s);
    onode->s = 0;
    onode->type = OPND_DECORATOR;
    while (i<len && s[i] == '{') {
        char* d = 0;
        int r;
        r = grab_decorator(s,i, &d);

        if (r<0) {
            asp_error_printf("DECORATOR PARSING ERROR\n");
            break;
        }
        i = (unsigned int)r;
        if (d) {
            if (onode->s==0)  {
                asp_dbg_printf("DECORATOR: %s\n",d);
                onode->s = d;
                //add_decorator(onode,d);
            }
            else  {
                asp_error_printf("Too many lone decorators %s\n",s);
                exit(1);
            }
        }
        if (d==0)
            break;
    }
    if (onode->s == 0) {
        asp_dbg_printf("No decorators: %s\n",s);
        exit(1);
    }
}

static void parse_memref(char* s, opnd_list_t* onode)
{
    // [ seg:reg + index * [1,2,4,8]  +/- disp ]
    memparse_rec_t r = { 0 };
    r.len = xed_strlen(s);
    assert(r.len < BLEN);

    char tbuf[BLEN];
    char stmp[BLEN];    
    char *q;
    unsigned int i=0;
    int p=0;
    int plusses=0;
    int last_star=0;
    unsigned int offset=0;

    for(i=0;mem_size_qualifiers[i];i++) {
        unsigned int len;
        len = xed_strlen(mem_size_qualifiers[i]);
        if (strncmp(mem_size_qualifiers[i],s,len) == 0) {
            asp_dbg_printf("MEM SIZE QUALIFIER: %s\n",mem_size_qualifiers[i]);
            r.mem_size = mem_size_qualifiers[i];  // static string, not allocated
            r.mem_bits = 1U << (i+3);
            offset = len;
            break;
        }
    }
    /* skip optional "ptr" part */
    offset = skip_spaces(s, offset);
    if (!strncmp(s+offset, "PTR", 3)) {
        offset += 3;
    }

    // remove spaces -- makes figuring out terminators much easier!
    for(i=0;s[offset+i];i++) {
        unsigned int src_pos = offset + i;
        if (!isspace(s[src_pos]))
            stmp[p++] = s[src_pos];
    }
    stmp[p]=0;
    p=0;
    r.len=xed_strlen(stmp);


    for(i=0;i<r.len;i++) {
        if (stmp[i] == '[') {
            assert(i==0);
            continue;
        }
        else if (stmp[i] == '+') {  // can end base or index or scale
            plusses++;
            tbuf[p++]=0;
            p=0;
            q = asp_strdup(tbuf);
            if (r.base && r.index)
                r.scale=q;
            else if (r.base)
                r.index=q;
            else
                r.base=q;
        }
        else if (stmp[i] == '-') { // can end index or scale
            plusses++;
            r.minus++;
            tbuf[p++]=0;
            p=0;
            q = asp_strdup(tbuf);
            if (r.index)
                r.scale=q;
            else
                r.index=q;
        }
        else if (stmp[i] == ':') { // can only end segment
            tbuf[p++]=0;
            p=0;
            r.seg = asp_strdup(tbuf);
        }
        else if (stmp[i] == '*') { // can end index
            tbuf[p++]=0;
            p=0;
            last_star=1;
            r.index=asp_strdup(tbuf);
            continue;  // skip loop bottom
        }
        else if (stmp[i] == ']') {  // can end base, index, scale or disp
            int start_digit;
            tbuf[p++]=0;
            p=0;
            q = asp_strdup(tbuf);
            start_digit = isdigit(q[0]);
            if (start_digit && (r.scale || r.minus || plusses==2 || last_star==0))  {
                r.disp = q;
                    
                if (!asm_isnumber(q, &r.ndisp, r.minus)) {
                    asp_error_printf("Bad displacement: %s\n", q);
                    exit(1);
                }
            }
            else if (last_star && start_digit)
                r.scale=q;
            else if (r.base==0 && start_digit==0)
                r.base=q;
            else if (r.index==0 && start_digit==0)
                r.index=q;
            else {
                asp_error_printf("Internal error parsing memory operand\n");
                exit(1); // FIXME: better error handling
            }
            i++; // skip over ']'
            break; // done parsing memref
        }
        else if (isalnum(stmp[i])) {
            tbuf[p++]= stmp[i];
        }

        else {
            asp_error_printf("Internal error parsing SIB\n");
            exit(1); // FIXME: better error handling
        }
        // loop bottom
        last_star=0;
    } //for loop over string

    while (i<r.len && stmp[i] == '{') {
        char* d = 0;
        int rr;
        rr = grab_decorator(stmp,i, &d);
        if (rr<0) {
            asp_error_printf("Decorator parsing error\n");
            break;
        }
        i = (unsigned int) rr;
        
        if (d)  {
            asp_dbg_printf("DECORATOR: %s\n",d);
            add_decorator(onode, d);
        }
        if (d==0)
            break;
    }
    if (r.scale) {
        int found = 0;
        for(i=0;scales[i];i++) {
            if (strcmp(r.scale,scales[i]) == 0)  {
                found = 1;
                r.nscale = 1U<<i;
            }
        }
        if (!found) {
            asp_error_printf("bad scale: %s\n",r.scale);
            exit(1);
        }
    }

    if (r.seg)
        asp_dbg_printf("SEG: %s\n",r.seg);
    if (r.base)
        asp_dbg_printf("BASE: %s\n",r.base);
    if (r.index)
        asp_dbg_printf("INDEX: %s\n",r.index);
    if (r.scale)
        asp_dbg_printf("SCALE: %s\n",r.scale);
    if (r.disp)
        asp_dbg_printf("DISP: %s = 0x%016llx\n",r.disp, r.ndisp);
    onode->type = OPND_MEM;
    onode->mem = r;
}

/* Extract semantic values from string: "far number:number" */
static void parse_long_pointer(char* s, opnd_list_t* onode)
{
    /* skip optional "far" part */
    if (s[0] == 'F' && s[1] == 'A' && s[2] == 'R') {
        s += 3;
        s += skip_spaces(s, 0);
    }

    int column_pos = -1;
    for (int i = 0; s[i]; i++) {
        if (s[i] == ':') {
            column_pos = i;
            break;
        }
    }
    assert(column_pos >= 0);
    char *first = s;
    char *second = s + column_pos + 1;
    s[column_pos] = '\0'; // split the string
    int64_t first_num, second_num;
    asm_isnumber(first, &first_num, 0);
    asm_isnumber(second, &second_num, 0);

    onode->farptr.seg = s;
    onode->farptr.offset = s + column_pos + 1;
    onode->farptr.seg_value = first_num;
    onode->farptr.offset_value = second_num;
    onode->type = OPND_FARPTR;
}

static void refine_operand(xed_enc_line_parsed_t* v, char* s)
{
    opnd_list_t* onode = get_opnd_list_node();
    int64_t num = 0;
    
    asp_dbg_printf("REFINE OPERAND [%s]\n", s);
    if (isreg(s)) {
        asp_dbg_printf("REGISTER-ish: %s\n",s);
        parse_reg(v,s,onode);
    }
    else if (asm_isnumber(s,&num,0)) {
        /* Actual meaning depends on opcode */
        asp_dbg_printf("Immediate or displacement: %s\n",s);
        onode->type = OPND_IMM;
        onode->s = asp_strdup(s);
        onode->imm = num;
    }
    else if (ismemref(s)) {
         // [ seg:reg + index * [1,2,4,8]  + disp ]
        asp_dbg_printf("MEMREF-ish\n");
        parse_memref(s,onode);
    }
    else if (isdecorator(s)) {
        asp_dbg_printf("LONE DECORATOR\n");
        parse_decorator(s,onode);
    }
    else if (islongptr(s)) {
        asp_dbg_printf("LONG POINTER\n");
        v->seen_far_ptr = 1;
        parse_long_pointer(s,onode);
    }
    else {
        asp_error_printf("Bad operand: %s\n",s);
        exit(1);
    }
    // add onode to list
    onode->next = v->opnds;
    v->opnds = onode;
}

static void refine_operands(xed_enc_line_parsed_t* v)
{
    slist_t* p = 0;
    if (v->operands) {
        //v->operands = reverse_list(v->operands);        
        p = v->operands;
        while(p) {
            refine_operand(v,p->s);
            p = p->next;
        }
    }
}


void asp_parse_line(xed_enc_line_parsed_t* v)
{
    char* p  = asp_strdup(v->input);
    char* q  = p; // for deletion
    int inst = 0;
    int prefixes = 0;
    upcase(p);
    while(*p) {
        if (isspace(*p)) {
            p++; continue;
        }
        if (prefixes==0) {
            grab_prefixes(&p,v);
            study_prefixes(v);
            prefixes = 1;
            continue;
        }
        if (inst==0) {
            grab_inst(&p,v);
            inst = 1;
            continue;
        }
        if (inst==1) { // grab operands
            grab_operand(&p, v);
            continue;
        }
        
        p++;
    }

    refine_operands(v);
    free(q);
}


void asp_print_parsed_line(xed_enc_line_parsed_t* v) {
    slist_t* p=0;
    opnd_list_t* q=0;
    asp_printf("MODE: %d\n",v->mode);
    asp_printf("MNEMONIC: %s\n",v->iclass_str);
    asp_printf("PREFIXES: ");
    p = v->prefixes;
    while(p) {
        asp_printf("%s ", p->s);
        p = p->next;
    }
    asp_printf("\n");

    asp_printf("OPERANDS: ");
    p = v->operands;
    while(p) {
        asp_printf("<%s> ", p->s);
        p = p->next;
    }
    asp_printf("\n");


    asp_printf("OPERANDS DECODED:\n");
    q = v->opnds;
    while(q) {
        slist_t* d = 0;
        asp_printf("\t");
        if (q->s) asp_printf("%s ", q->s);

        switch (q->type) {
        case OPND_REG: asp_printf("REG "); break;
        case OPND_IMM: asp_printf("IMM 0x%016llx  ", q->imm); break;
        case OPND_DECORATOR: asp_printf("DECORATOR  "); break;
        case OPND_INVALID: asp_printf("INVALID  "); break;
        case OPND_MEM: 
            asp_printf("MEM  "); break;
            asp_printf("%d %s [%s:%s + %s*%s %s %s] ",
                q->mem.len,
                (q->mem.mem_size ? q->mem.mem_size : "n/a"),
                (q->mem.seg ? q->mem.seg : "n/a"),
                (q->mem.base ? q->mem.base : "n/a"),
                (q->mem.index ? q->mem.index : "n/a"),
                q->mem.scale,
                (q->mem.minus ? "-" : "+"),
                (q->mem.disp ? q->mem.disp : "n/a"));
            break;
        case OPND_FARPTR:
            asp_printf("FAR PTR %s:%s", q->farptr.seg, q->farptr.offset);
            break;
        default:
            assert(0 && "Unhandled operand type");
            break;
        }
        d = q->decorators;
        while(d) {
            asp_printf("%s ",d->s);
            d = d->next;
        }
        
        q = q->next;
        asp_printf("\n");
    }

        
}

