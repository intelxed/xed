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
/// @file xed-state.h
/// 



#ifndef XED_STATE_H
# define XED_STATE_H
#include "xed-types.h"
#include "xed-portability.h"
#include "xed-address-width-enum.h" // generated
#include "xed-machine-mode-enum.h" // generated


/// Encapsulates machine modes for decoder/encoder requests.
/// It specifies the machine operating mode as a 
/// #xed_machine_mode_enum_t 
/// for decoding and encoding. The machine mode corresponds to the default
/// data operand width for that mode. For all modes other than the 64b long
/// mode (XED_MACHINE_MODE_LONG_64), a default addressing width, and a
/// stack addressing width must be supplied of type
/// #xed_address_width_enum_t .  @ingroup INIT
typedef struct xed_state_s {
  /// real architected machine modes
  xed_machine_mode_enum_t mmode; 
  /// for 16b/32b modes
  xed_address_width_enum_t stack_addr_width; 
} xed_state_t;

/// @name Initialization
//@{
/// Constructor.
/// DEPRECATED: use #xed_state_init2(). 
/// The mode, and addresses widths are enumerations that specify the number
/// of bits.  In 64b mode (#XED_MACHINE_MODE_LONG_64) the address width and
/// stack address widths are 64b (#XED_ADDRESS_WIDTH_64b). In other machine
/// modes, you must specify valid addressing widths.
///
/// @param p the pointer to the #xed_state_t type
/// @param arg_mmode the machine mode of type #xed_machine_mode_enum_t
/// @param arg_ignored Ignored. The addressing width is now implied by the machine mode implied by arg_mmmode.
/// @param arg_stack_addr_width the stack address width of type #xed_address_width_enum_t (only required if not the mode is not #XED_MACHINE_MODE_LONG_64)
/// @ingroup INIT
static XED_INLINE void xed_state_init(xed_state_t* p,
                                      xed_machine_mode_enum_t arg_mmode,
                                      xed_address_width_enum_t arg_ignored,
                                      xed_address_width_enum_t arg_stack_addr_width) {
    p->mmode=arg_mmode;
    p->stack_addr_width=arg_stack_addr_width;
    (void) arg_ignored; //pacify compiler unused arg warning
}

/// Constructor.
/// The mode, and addresses widths are enumerations that specify the number
/// of bits.  In 64b mode (#XED_MACHINE_MODE_LONG_64) the address width and
/// stack address widths are 64b (#XED_ADDRESS_WIDTH_64b). In other machine
/// modes, you must specify valid addressing widths.
///
/// @param p the pointer to the #xed_state_t type
/// @param arg_mmode the machine mode of type #xed_machine_mode_enum_t
/// @param arg_stack_addr_width the stack address width of type #xed_address_width_enum_t (only required if not the mode is not #XED_MACHINE_MODE_LONG_64)
/// @ingroup INIT
static XED_INLINE void xed_state_init2(xed_state_t* p,
                                      xed_machine_mode_enum_t arg_mmode,
                                      xed_address_width_enum_t arg_stack_addr_width) {
    p->mmode=arg_mmode;
    p->stack_addr_width=arg_stack_addr_width;
}

/// clear the xed_state_t
/// @ingroup INIT
static XED_INLINE void xed_state_zero(xed_state_t* p) {
    p->mmode= XED_MACHINE_MODE_INVALID;
    p->stack_addr_width=XED_ADDRESS_WIDTH_INVALID;
}

//@}

/// @name Machine mode
//@{
/// return the machine mode
/// @ingroup INIT
static XED_INLINE xed_machine_mode_enum_t   xed_state_get_machine_mode(const xed_state_t* p) {
    return p->mmode; 
}


/// true iff the machine is in LONG_64 mode
/// @ingroup INIT
static XED_INLINE xed_bool_t xed_state_long64_mode(const xed_state_t* p) { 
    return xed_state_get_machine_mode(p) == XED_MACHINE_MODE_LONG_64;
}

/// @ingroup INIT
static XED_INLINE xed_bool_t xed_state_real_mode(const xed_state_t* p) {
    return (xed_state_get_machine_mode(p) == XED_MACHINE_MODE_REAL_16);
}

/// @ingroup INIT
static XED_INLINE xed_bool_t xed_state_mode_width_16(const xed_state_t* p) {
    return (xed_state_get_machine_mode(p) == XED_MACHINE_MODE_LEGACY_16) ||
        (xed_state_get_machine_mode(p) == XED_MACHINE_MODE_LONG_COMPAT_16);
}

/// @ingroup INIT
static XED_INLINE xed_bool_t xed_state_mode_width_32(const xed_state_t* p) {
    return (xed_state_get_machine_mode(p) == XED_MACHINE_MODE_LEGACY_32) ||
        (xed_state_get_machine_mode(p) == XED_MACHINE_MODE_LONG_COMPAT_32);
}
  

/// Set the machine mode which corresponds to the default data operand size
/// @ingroup INIT
static XED_INLINE void  xed_state_set_machine_mode( xed_state_t* p,
                        xed_machine_mode_enum_t arg_mode)  {
    p->mmode = arg_mode;
}
//@}

/// @name Address width
//@{

/// return the address width
/// @ingroup INIT
static XED_INLINE xed_address_width_enum_t
xed_state_get_address_width(const xed_state_t* p)
{
    switch(xed_state_get_machine_mode(p)) {
      case XED_MACHINE_MODE_LONG_64:
        return XED_ADDRESS_WIDTH_64b;

      case XED_MACHINE_MODE_REAL_16:
        /* should be 20b... but if you are working w/real mode then you're
           going to have to deal with somehow. Could easily make this be
           20b if anyone cares. */
        return XED_ADDRESS_WIDTH_32b; 

      case XED_MACHINE_MODE_LEGACY_32:
      case XED_MACHINE_MODE_LONG_COMPAT_32:
        return XED_ADDRESS_WIDTH_32b;
      case XED_MACHINE_MODE_LEGACY_16:
      case XED_MACHINE_MODE_LONG_COMPAT_16:
        return XED_ADDRESS_WIDTH_16b;
      default:
        return XED_ADDRESS_WIDTH_INVALID;
    }
}

//@}

/// @name Stack address width
//@{
/// set the STACK address width
/// @ingroup INIT
static XED_INLINE void
xed_state_set_stack_address_width(xed_state_t* p,
                                  xed_address_width_enum_t arg_addr_width)
{
    p->stack_addr_width = arg_addr_width;
}


/// Return the STACK address width
/// @ingroup INIT
static XED_INLINE xed_address_width_enum_t  xed_state_get_stack_address_width(const xed_state_t* p) {
    return p->stack_addr_width;
}
//@}

/// @ingroup INIT
XED_DLL_EXPORT int xed_state_print(const xed_state_t* p, char* buf, int buflen);

#endif

