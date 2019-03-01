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
/// @file xed-flags.cpp
/// 
#include "xed-flags.h"
#include "xed-flags-private.h"
#include "xed-portability.h"
#include "xed-util.h"
#include "xed-tables-extern.h"

xed_bool_t 
xed_flag_set_is_subset_of(const xed_flag_set_t* p, const xed_flag_set_t* other)
{
    xed_uint32_t conj = p->flat & other->flat;
    return (conj == p->flat);
}


int  xed_flag_set_print(const xed_flag_set_t* p, char* buf, int buflen) {
    int blen = buflen;
    *buf = 0; // start w/null terminated
    if (p->s.of) { blen = xed_strncat(buf, "of ",blen);}
    if (p->s.sf) { blen = xed_strncat(buf, "sf ",blen);}
    if (p->s.zf) { blen = xed_strncat(buf, "zf ",blen);}
    if (p->s.af) { blen = xed_strncat(buf, "af ",blen);}
    if (p->s.pf) { blen = xed_strncat(buf, "pf ",blen);}
    if (p->s.cf) { blen = xed_strncat(buf, "cf ",blen);}
    if (p->s.df) { blen = xed_strncat(buf, "df ",blen);}
    if (p->s.vif) { blen = xed_strncat(buf, "vif ",blen);}
    if (p->s.iopl) { blen = xed_strncat(buf, "iopl ",blen);}
    if (p->s._if) { blen = xed_strncat(buf, "if ",blen);}
    if (p->s.ac) { blen = xed_strncat(buf, "ac ",blen);}
    if (p->s.vm) { blen = xed_strncat(buf, "vm ",blen);}
    if (p->s.rf) { blen = xed_strncat(buf, "rf ",blen);}
    if (p->s.nt) { blen = xed_strncat(buf, "nt ",blen);}
    if (p->s.tf) { blen = xed_strncat(buf, "tf ",blen);}
    if (p->s.id) { blen = xed_strncat(buf, "id ",blen);}
    if (p->s.vip) { blen = xed_strncat(buf, "vip ",blen);}
    if (p->s.fc0) { blen = xed_strncat(buf, "fc0 ",blen);}
    if (p->s.fc1) { blen = xed_strncat(buf, "fc1 ",blen);}
    if (p->s.fc2) { blen = xed_strncat(buf, "fc2 ",blen);}
    if (p->s.fc3) { blen = xed_strncat(buf, "fc3 ",blen);}
    return blen;
}



/// @name Flag accessors
//@{
    
/// get the name of the flag
xed_flag_enum_t
xed_flag_action_get_flag_name(const xed_flag_action_t* p)  {
    return p->flag;
}
    
/// return the action
xed_flag_action_enum_t
xed_flag_action_get_action(const xed_flag_action_t* p, unsigned int i)   {
    return p->action;
    (void)i; // pacify compiler warnings
}

/// returns 1 if the specified action is invalid. Only the 2nd flag might
/// be invalid.
xed_bool_t 
xed_flag_action_action_invalid(const xed_flag_action_enum_t a) {
    return (a == XED_FLAG_ACTION_INVALID);
}

/// print the flag & actions
int xed_flag_action_print(const xed_flag_action_t* p, char* buf, int buflen)  {
    int blen = buflen;
    blen  = xed_strncpy(buf, xed_flag_enum_t2str(p->flag),blen);
    if (p->action != XED_FLAG_ACTION_INVALID) {
        blen = xed_strncat(buf, "-",blen);
        blen = xed_strncat(buf, xed_flag_action_enum_t2str(p->action), blen);
    }
    return blen;
}

/// returns 1 if either action is a read
xed_bool_t 
xed_flag_action_read_flag(const xed_flag_action_t* p ) {
    return xed_flag_action_read_action(p->action);
}

/// returns 1 if either action is a write
xed_bool_t 
xed_flag_action_writes_flag(const xed_flag_action_t* p)  {
    return xed_flag_action_write_action(p->action);
}
  

/// test to see if the specific action is a read 
xed_bool_t 
xed_flag_action_read_action( xed_flag_action_enum_t a)  {
    return (a == XED_FLAG_ACTION_tst);
}

/// test to see if a specific action is a write
xed_bool_t 
xed_flag_action_write_action( xed_flag_action_enum_t a)  {
    switch(a) {
      case XED_FLAG_ACTION_mod:
      case XED_FLAG_ACTION_0:
      case XED_FLAG_ACTION_1:    
      case XED_FLAG_ACTION_ah:
      case XED_FLAG_ACTION_pop:
      case XED_FLAG_ACTION_u:
        return 1;
      default:
        return 0;
    }
}
//@}

////////////////////////////////////////////////////////////////////////////


/// @name Accessing the flags
//@{
/// returns the number of flag-actions
unsigned int 
xed_simple_flag_get_nflags(const xed_simple_flag_t* p)  {
    return p->nflags;
}

/// return union of bits for read flags
const xed_flag_set_t* 
xed_simple_flag_get_read_flag_set(const xed_simple_flag_t* p) {
    return &(p->read);
}
  
/// return union of bits for written flags
const xed_flag_set_t*
xed_simple_flag_get_written_flag_set(const xed_simple_flag_t* p) {
    return &(p->written);
}

/// return union of bits for undefined flags
const xed_flag_set_t*
xed_simple_flag_get_undefined_flag_set(const xed_simple_flag_t* p) {
    return &(p->undefined);
}

xed_bool_t     xed_simple_flag_get_may_write(const xed_simple_flag_t* p)     {
    return p->may_write;
}

xed_bool_t     xed_simple_flag_get_must_write(const xed_simple_flag_t* p)     {
    return p->must_write;
}


/// return the specific flag-action
const xed_flag_action_t*
xed_simple_flag_get_flag_action(const xed_simple_flag_t* p, unsigned int i)  {
    xed_assert(i < p->nflags);
    return xed_flag_action_table + p->fa_index+i;
}

/// boolean test to see if flags are read, scans the flags
xed_bool_t
xed_simple_flag_reads_flags(const xed_simple_flag_t* p)     {
    int i;
    for( i=0;i<p->nflags ;i++) 
        if ( xed_flag_action_read_flag(xed_flag_action_table + p->fa_index+i) )
            return 1;
    return 0;
}

/// boolean test to see if flags are written, scans the flags
xed_bool_t    xed_simple_flag_writes_flags(const xed_simple_flag_t* p)     {
    int i;
    for( i=0;i<p->nflags ;i++) 
        if ( xed_flag_action_writes_flag(xed_flag_action_table +p->fa_index+i))
            return 1;
    return 0;
}
/// print the flags
int   xed_simple_flag_print(const xed_simple_flag_t* p, char* buf, 
                            int buflen)    
{
    unsigned int i,n;
    char tbuf[100];
    int blen = buflen;
    if (xed_simple_flag_get_may_write(p))
        blen = xed_strncat(buf, "MAY-WRITE ",blen);
    if (xed_simple_flag_get_must_write(p))
        blen = xed_strncat(buf, "MUST-WRITE ",blen);
    n = p->nflags;
    for( i=0;i<n ;i++) {
        const xed_flag_action_t* f = xed_simple_flag_get_flag_action(p,i);
        (void) xed_flag_action_print(f,tbuf,100);
        blen = xed_strncat(buf,tbuf,blen);
        if (i < (n-1)) 
            blen = xed_strncat(buf," ",blen);
    }
    
    blen = xed_strncat(buf,"\n\tFlags read: ",blen);
    (void) xed_flag_set_print(&p->read, tbuf,100);
    blen = xed_strncat(buf,tbuf,blen);
    blen = xed_strncat(buf,"\n\tFlags written: ",blen);
    (void) xed_flag_set_print(&p->written, tbuf, 100);
    blen = xed_strncat(buf,tbuf,blen);
    return blen;
}
//@}


