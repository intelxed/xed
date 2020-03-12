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
/// @file xed-flags.h
/// 

#ifndef XED_FLAGS_H
# define  XED_FLAGS_H

#include "xed-types.h"
#include "xed-portability.h"
#include "xed-flag-enum.h"
#include "xed-flag-action-enum.h"
#include "xed-gen-table-defs.h"


////////////////////////////////////////////////////////////////////////////
/// @ingroup FLAGS
/// a union of flags bits
union  xed_flag_set_s {
    xed_uint32_t flat;
    struct {
        xed_uint32_t cf:1; ///< bit 0
        xed_uint32_t must_be_1:1;
        xed_uint32_t pf:1;
        xed_uint32_t must_be_0a:1;
        
        xed_uint32_t af:1; ///< bit 4
        xed_uint32_t must_be_0b:1;
        xed_uint32_t zf:1;
        xed_uint32_t sf:1;
        
        xed_uint32_t tf:1;  ///< bit 8
        xed_uint32_t _if:1;  ///< underscore to avoid token clash
        xed_uint32_t df:1;
        xed_uint32_t of:1;
        
        xed_uint32_t iopl:2; ///< A 2-bit field, bits 12-13
        xed_uint32_t nt:1;
        xed_uint32_t must_be_0c:1;
        
        xed_uint32_t rf:1; ///< bit 16
        xed_uint32_t vm:1;
        xed_uint32_t ac:1;
        xed_uint32_t vif:1;
        
        xed_uint32_t vip:1; ///< bit 20
        xed_uint32_t id:1;   ///< bit 21
        xed_uint32_t must_be_0d:2;  ///< bits 22-23
        
        xed_uint32_t must_be_0e:4;  ///< bits 24-27

        // fc0,fc1,fc2,fc3 are not really part of rflags but I put them
        // here to save space. These bits are only used for x87
        // instructions.
        xed_uint32_t fc0:1;  ///< x87 flag FC0 (not really part of rflags)
        xed_uint32_t fc1:1;  ///< x87 flag FC1 (not really part of rflags)
        xed_uint32_t fc2:1;  ///< x87 flag FC2 (not really part of rflags)
        xed_uint32_t fc3:1;  ///< x87 flag FC3 (not really part of rflags)
    } s;

};

typedef union xed_flag_set_s xed_flag_set_t;
/// @ingroup FLAGS
/// @name Flag-set accessors
//@{
/// @ingroup FLAGS
/// print the flag set in the supplied buffer
XED_DLL_EXPORT int  xed_flag_set_print(const xed_flag_set_t* p, char* buf, int buflen);
/// @ingroup FLAGS
/// returns true if this object has a subset of the flags of the
/// "other" object.
XED_DLL_EXPORT xed_bool_t xed_flag_set_is_subset_of(const xed_flag_set_t* p,
                               const xed_flag_set_t* other);
//@}


////////////////////////////////////////////////////////////////////////////

/// @ingroup FLAGS
/// Associated with each flag field there can be one action.
typedef struct xed_flag_enum_s {
    xed_flag_enum_t flag;
    // there are at most two actions per flag. The 2nd may be invalid.
    xed_flag_action_enum_t action;
}  xed_flag_action_t;




/// @ingroup FLAGS
/// @name Lowest-level flag-action accessors
//@{
/// @ingroup FLAGS    
/// get the name of the flag
XED_DLL_EXPORT xed_flag_enum_t
xed_flag_action_get_flag_name(const xed_flag_action_t* p);
/// @ingroup FLAGS        
/// return the action
XED_DLL_EXPORT xed_flag_action_enum_t
xed_flag_action_get_action(const xed_flag_action_t* p, unsigned int i);
/// @ingroup FLAGS    
/// returns true if the specified action is invalid. Only the 2nd flag might be invalid.
XED_DLL_EXPORT xed_bool_t 
xed_flag_action_action_invalid(const xed_flag_action_enum_t a);
/// @ingroup FLAGS    
/// print the flag & actions
XED_DLL_EXPORT int xed_flag_action_print(const xed_flag_action_t* p, char* buf, int buflen);
/// @ingroup FLAGS    
/// returns true if either action is a read
XED_DLL_EXPORT xed_bool_t 
xed_flag_action_read_flag(const xed_flag_action_t* p );
/// @ingroup FLAGS    
/// returns true if either action is a write
XED_DLL_EXPORT xed_bool_t 
xed_flag_action_writes_flag(const xed_flag_action_t* p);
  
/// @ingroup FLAGS    
/// test to see if the specific action is a read 
XED_DLL_EXPORT xed_bool_t 
xed_flag_action_read_action( xed_flag_action_enum_t a);
/// @ingroup FLAGS    
/// test to see if a specific action is a write
XED_DLL_EXPORT xed_bool_t 
xed_flag_action_write_action( xed_flag_action_enum_t a);
//@}

////////////////////////////////////////////////////////////////////////////

/// @ingroup FLAGS
/// A collection of #xed_flag_action_t's and unions of read and written flags
typedef struct  xed_simple_flag_s 
{
    ///number of flag actions associated with this record
    xed_uint8_t nflags; 

    xed_uint8_t may_write; /* 1/0,  only using one bit */
    xed_uint8_t must_write;  /* 1/0,  only using one bit */

    ///union of read flags
    xed_flag_set_t read;

    /// union of written flags (includes undefined flags);
    xed_flag_set_t written;

    /// union of undefined flags;
    xed_flag_set_t undefined;

    // index in to the xed_flag_action_table. nflags limits the # of entries.
    xed_uint16_t fa_index;

} xed_simple_flag_t;

/// @ingroup FLAGS
/// @name Accessing the simple flags (Mid-level access)
//@{
/// @ingroup FLAGS
/// returns the number of flag-actions
XED_DLL_EXPORT unsigned int 
xed_simple_flag_get_nflags(const xed_simple_flag_t* p);

/// @ingroup FLAGS
/// return union of bits for read flags
XED_DLL_EXPORT const xed_flag_set_t* 
xed_simple_flag_get_read_flag_set(const xed_simple_flag_t* p);

/// @ingroup FLAGS  
/// return union of bits for written flags
XED_DLL_EXPORT const xed_flag_set_t*
xed_simple_flag_get_written_flag_set(const xed_simple_flag_t* p);


/// @ingroup FLAGS  
/// return union of bits for undefined flags
XED_DLL_EXPORT const xed_flag_set_t*
xed_simple_flag_get_undefined_flag_set(const xed_simple_flag_t* p);

/// @ingroup FLAGS
/// Indicates the flags are only conditionally written. Usually MAY-writes
/// of the flags instructions that are dependent on a REP count.
XED_DLL_EXPORT xed_bool_t xed_simple_flag_get_may_write(const xed_simple_flag_t* p);

/// @ingroup FLAGS
/// the flags always written
XED_DLL_EXPORT xed_bool_t xed_simple_flag_get_must_write(const xed_simple_flag_t* p);

/// @ingroup FLAGS
/// return the specific flag-action. Very detailed low level information
XED_DLL_EXPORT const xed_flag_action_t*
xed_simple_flag_get_flag_action(const xed_simple_flag_t* p, unsigned int i);

/// @ingroup FLAGS    
/// boolean test to see if flags are read, scans the flags
XED_DLL_EXPORT xed_bool_t
xed_simple_flag_reads_flags(const xed_simple_flag_t* p);

/// @ingroup FLAGS    
/// boolean test to see if flags are written, scans the flags
XED_DLL_EXPORT xed_bool_t xed_simple_flag_writes_flags(const xed_simple_flag_t* p);

/// @ingroup FLAGS    
/// print the flags
XED_DLL_EXPORT int xed_simple_flag_print(const xed_simple_flag_t* p, char* buf, int buflen);

/// @ingroup FLAGS    
/// Return the flags as a mask
static XED_INLINE unsigned int xed_flag_set_mask(const xed_flag_set_t* p) {
    return p->flat; // FIXME: could mask out the X87 flags
}

//@}

////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////

#endif
