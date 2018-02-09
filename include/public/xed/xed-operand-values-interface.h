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
/// @file xed-operand-values-interface.h
/// 

#if !defined(XED_OPERAND_VALUES_INTERFACE_H)
# define XED_OPERAND_VALUES_INTERFACE_H

#include "xed-common-hdrs.h"
#include "xed-common-defs.h"
#include "xed-portability.h"
#include "xed-util.h"
#include "xed-types.h"
#include "xed-state.h" // a generated file
#include "xed-operand-enum.h" // a generated file
#include "xed-decoded-inst.h" 
#include "xed-reg-enum.h"  // generated
#include "xed-iclass-enum.h"  // generated
/// @name Initialization
//@{
/// @ingroup OPERANDS
/// Initializes operand structure
XED_DLL_EXPORT void xed_operand_values_init(xed_operand_values_t* p);

/// @ingroup OPERANDS
/// Initializes the operand storage and sets mode values.
XED_DLL_EXPORT void xed_operand_values_init_set_mode(xed_operand_values_t* p,
                                                     const xed_state_t* dstate);

/// @ingroup OPERANDS
/// Set the mode values
XED_DLL_EXPORT void
xed_operand_values_set_mode(xed_operand_values_t* p,
                            const xed_state_t* dstate);

/// @ingroup OPERANDS
/// Initializes dst operand structure but preserves the existing
/// MODE/SMODE values from the src operand structure.
XED_DLL_EXPORT void
xed_operand_values_init_keep_mode( xed_operand_values_t* dst,
                                   const xed_operand_values_t* src );
//@}
    
///////////////////////////////////////////////////////////
/// @name String output
//@{
/// @ingroup OPERANDS
/// Dump all the information about the operands to buf.
XED_DLL_EXPORT void
xed_operand_values_dump(const xed_operand_values_t* ov,
                        char* buf,
                        int buflen);
/// @ingroup OPERANDS
/// More tersely dump all the information about the operands to buf.
XED_DLL_EXPORT void
xed_operand_values_print_short(const xed_operand_values_t* ov,
                               char* buf,
                               int buflen);
//@}
    
/// @name REP/REPNE Prefixes
//@{     
/// @ingroup OPERANDS    
/// True if the instruction has a real REP prefix. This returns false if
/// there is no F2/F3 prefix or the F2/F3 prefix is used to refine the
/// opcode as in some SSE operations.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_real_rep(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// True if the instruction as a F3 REP prefix (used for opcode refining,
/// for rep for string operations, or ignored).
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_rep_prefix(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// True if the instruction as a F2 REP prefix (used for opcode refining,
/// for rep for string operations, or ignored).
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_repne_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// DO NOT USE - DEPRECATED. The  correct way to do remove a rep prefix is by changing the iclass
XED_DLL_EXPORT void xed_operand_values_clear_rep(xed_operand_values_t* p);

//@}

/// @name Atomic / Locked operations
//@{     
/// @ingroup OPERANDS    
/// Returns true if the memory operation has atomic read-modify-write
/// semantics. An XCHG accessing memory is atomic with or without a
/// LOCK prefix.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_get_atomic(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// Returns true if the memory operation has a valid lock prefix.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_lock_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS
/// Returns true if the instruction could be re-encoded to have a lock
/// prefix but does not have one currently.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_lockable(const xed_operand_values_t* p);
//@}


/// @ingroup OPERANDS    
/// Indicates if the default segment is being used.
/// @param[in] p   the pointer to the #xed_operand_values_t structure.
/// @param[in] i   0 or 1, indicating which memory operation.
/// @return true if the memory operation is using the default segment for
/// the associated addressing mode base register.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_using_default_segment(const xed_operand_values_t* p,
                                         unsigned int i);



/// @ingroup OPERANDS    
/// Returns The effective operand width in bits: 16/32/64. Note this is not
/// the same as the width of the operand which can vary! For 8 bit
/// operations, the effective operand width is the machine mode's default
/// width. If you also want to identify byte operations use the higher
/// level function #xed_decoded_inst_get_operand_width() .
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_effective_operand_width(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// Returns The effective address width in bits: 16/32/64. 
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_effective_address_width(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// Returns The stack address width in bits: 16/32/64. 
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_stack_address_width(const xed_operand_values_t* p);


/// @ingroup OPERANDS    
/// True if there is a memory displacement
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_memory_displacement(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// True if there is a branch displacement
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_branch_displacement(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
/// True if there is a memory or branch displacement
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_displacement(const xed_operand_values_t* p);


/// @ingroup OPERANDS    
/// Deprecated. Compatibility function for XED0. See has_memory_displacement().
XED_DLL_EXPORT xed_bool_t
xed_operand_values_get_displacement_for_memop(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// Return true if there is an immediate operand
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_immediate(const xed_operand_values_t* p);  


/// @ingroup OPERANDS    
/// ALIAS for has_displacement().
/// Deprecated. See has_memory_displacement() and
/// has_branch_displacement().
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_disp(const xed_operand_values_t* p);  

/// @ingroup OPERANDS    
/// This indicates the presence of a 67 prefix.
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_has_address_size_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// This does not include the cases when the 66 prefix is used an
/// opcode-refining prefix for multibyte opcodes.
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_has_operand_size_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// This includes any 66 prefix that shows up even if it is ignored.
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_has_66_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// This instruction has a REX prefix with the W bit set.
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_has_rexw_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_has_segment_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// Return the segment prefix, if any, as a #xed_reg_enum_t value.
XED_DLL_EXPORT xed_reg_enum_t
xed_operand_values_segment_prefix(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_is_prefetch(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_get_long_mode(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_get_real_mode(const xed_operand_values_t* p);

/// @name Memory Addressing
//@{
/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_accesses_memory(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT unsigned int 
xed_operand_values_number_of_memory_operands(const xed_operand_values_t* p);

/// return bytes
/// @ingroup OPERANDS    
XED_DLL_EXPORT unsigned int
xed_operand_values_get_memory_operand_length(const xed_operand_values_t* p,
                                             unsigned int memop_idx);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_reg_enum_t
xed_operand_values_get_base_reg(const xed_operand_values_t* p,
                                unsigned int memop_idx);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_reg_enum_t
xed_operand_values_get_index_reg(const xed_operand_values_t* p,
                                 unsigned int memop_idx);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_reg_enum_t
xed_operand_values_get_seg_reg(const xed_operand_values_t* p,
                               unsigned int memop_idx);

/// @ingroup OPERANDS    
XED_DLL_EXPORT unsigned int
xed_operand_values_get_scale(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// Returns true if the instruction access memory but without using a MODRM
/// byte limiting its addressing modes.
XED_DLL_EXPORT xed_bool_t 
xed_operand_values_memop_without_modrm(const xed_operand_values_t* p);
/// @ingroup OPERANDS
/// Returns true if the instruction has a MODRM byte.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_modrm_byte(const xed_operand_values_t* p);

/// @ingroup OPERANDS
/// Returns true if the instruction has a SIB byte.
XED_DLL_EXPORT xed_bool_t
xed_operand_values_has_sib_byte(const xed_operand_values_t* p);
//@}

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_branch_not_taken_hint(const xed_operand_values_t* p);
/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_branch_taken_hint(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_bool_t
xed_operand_values_is_nop(const xed_operand_values_t* p);


/// @name Immediates
//@{
/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_int64_t
xed_operand_values_get_immediate_int64(const xed_operand_values_t* p);


/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_uint64_t
xed_operand_values_get_immediate_uint64(const xed_operand_values_t* p);

/// @ingroup OPERANDS
/// Return true if the first immediate (IMM0) is signed
XED_DLL_EXPORT xed_uint_t
xed_operand_values_get_immediate_is_signed(const xed_operand_values_t* p);

    
/// @ingroup OPERANDS    
/// Return the i'th byte of the immediate
XED_DLL_EXPORT xed_uint8_t 
xed_operand_values_get_immediate_byte(const xed_operand_values_t* p,
                                      unsigned int i);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_uint8_t 
xed_operand_values_get_second_immediate(const xed_operand_values_t* p);
//@}

/// @name Memory Displacements
//@{
/// @ingroup OPERANDS
/// Return the memory displacement width in BYTES
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_memory_displacement_length(const xed_operand_values_t* p);
/// @ingroup OPERANDS
/// Return the memory displacement width in BITS
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits(
    const xed_operand_values_t* p);

/// @ingroup OPERANDS
/// Return the raw memory displacement width in BITS(ignores scaling)
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_memory_displacement_length_bits_raw(
    const xed_operand_values_t* p);

/// Returns the potentially scaled value of the memory
/// displacement. Certain AVX512 memory displacements are scaled before
/// they are used.  @ingroup OPERANDS
XED_DLL_EXPORT xed_int64_t
xed_operand_values_get_memory_displacement_int64(const xed_operand_values_t* p);

/// Returns the unscaled (raw) memory displacement. Certain AVX512 memory
/// displacements are scaled before they are used.  @ingroup OPERANDS
XED_DLL_EXPORT xed_int64_t
xed_operand_values_get_memory_displacement_int64_raw(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_uint8_t 
xed_operand_values_get_memory_displacement_byte(const xed_operand_values_t* p,
                                                unsigned int i);
//@}

/// @name Branch Displacements
//@{
/// @ingroup OPERANDS
/// Return the branch displacement width in bytes
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_branch_displacement_length(const xed_operand_values_t* p);
/// @ingroup OPERANDS
/// Return the branch displacement width in bits
XED_DLL_EXPORT xed_uint32_t
xed_operand_values_get_branch_displacement_length_bits(
    const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_int32_t
xed_operand_values_get_branch_displacement_int32(const xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_uint8_t 
xed_operand_values_get_branch_displacement_byte(const xed_operand_values_t* p,
                                                unsigned int i);
//@}


/// @ingroup OPERANDS    
XED_DLL_EXPORT xed_iclass_enum_t
xed_operand_values_get_iclass(const xed_operand_values_t* p);
    
////////////////////////////////////////////////////
// ENCODE API
////////////////////////////////////////////////////
/// @name Encoding
//@{
/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_zero_immediate(xed_operand_values_t* p);
/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_zero_branch_displacement(xed_operand_values_t* p);
/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_zero_memory_displacement(xed_operand_values_t* p);

/// @ingroup OPERANDS    
XED_DLL_EXPORT void xed_operand_values_set_lock(xed_operand_values_t* p);
/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_zero_segment_override(xed_operand_values_t* p);


/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_set_iclass(xed_operand_values_t* p,
                              xed_iclass_enum_t iclass);

/// @ingroup OPERANDS
/// width is bits 8, 16, 32, 64
XED_DLL_EXPORT void
xed_operand_values_set_effective_operand_width(xed_operand_values_t* p,
                                               unsigned int width);

/// @ingroup OPERANDS
/// width is bits 16, 32, 64
XED_DLL_EXPORT void
xed_operand_values_set_effective_address_width(xed_operand_values_t* p,
                                               unsigned int width);
/// takes bytes, not bits, as an argument
/// @ingroup OPERANDS    
XED_DLL_EXPORT void
xed_operand_values_set_memory_operand_length(xed_operand_values_t* p,
                                             unsigned int memop_length);

   
/// @ingroup OPERANDS    
/// Set the memory displacement using a BYTES length
XED_DLL_EXPORT void
xed_operand_values_set_memory_displacement(xed_operand_values_t* p,
                                           xed_int64_t x, unsigned int len);
/// @ingroup OPERANDS    
/// Set the memory displacement using a BITS length
XED_DLL_EXPORT void
xed_operand_values_set_memory_displacement_bits(xed_operand_values_t* p,
                                                xed_int64_t x,
                                                unsigned int len_bits);

/// @ingroup OPERANDS    
/// Indicate that we have a relative branch.
XED_DLL_EXPORT void xed_operand_values_set_relbr(xed_operand_values_t* p);

/// @ingroup OPERANDS    
/// Set the branch displacement using a BYTES length
XED_DLL_EXPORT void
xed_operand_values_set_branch_displacement(xed_operand_values_t* p,
                                           xed_int32_t x,
                                           unsigned int len);
/// @ingroup OPERANDS    
/// Set the branch displacement using a BITS length
XED_DLL_EXPORT void
xed_operand_values_set_branch_displacement_bits(xed_operand_values_t* p,
                                                xed_int32_t x,
                                                unsigned int len_bits);

/// @ingroup OPERANDS    
/// Set the signed immediate using a BYTES length
XED_DLL_EXPORT void
xed_operand_values_set_immediate_signed(xed_operand_values_t* p,
                                        xed_int32_t x,
                                        unsigned int bytes); 
/// @ingroup OPERANDS    
/// Set the signed immediate using a BITS length
XED_DLL_EXPORT void
xed_operand_values_set_immediate_signed_bits(xed_operand_values_t* p,
                                             xed_int32_t x,
                                             unsigned int bits); 


/// @ingroup OPERANDS    
/// Set the unsigned immediate using a BYTE length.
XED_DLL_EXPORT void
xed_operand_values_set_immediate_unsigned(xed_operand_values_t* p,
                                          xed_uint64_t x,
                                          unsigned int bytes);
/// @ingroup OPERANDS    
/// Set the unsigned immediate using a BIT length.
XED_DLL_EXPORT void
xed_operand_values_set_immediate_unsigned_bits(xed_operand_values_t* p,
                                               xed_uint64_t x,
                                               unsigned int bits);



/// @ingroup OPERANDS    
XED_DLL_EXPORT void xed_operand_values_set_base_reg(xed_operand_values_t* p,
                                                    unsigned int memop_idx,
                                                    xed_reg_enum_t new_base);

/// @ingroup OPERANDS    
XED_DLL_EXPORT void xed_operand_values_set_seg_reg(xed_operand_values_t* p,
                                                   unsigned int memop_idx,
                                                   xed_reg_enum_t new_seg);

/// @ingroup OPERANDS    
XED_DLL_EXPORT void xed_operand_values_set_index_reg(xed_operand_values_t* p,
                                                     unsigned int memop_idx,
                                                     xed_reg_enum_t new_index);

/// @ingroup OPERANDS    
XED_DLL_EXPORT void xed_operand_values_set_scale(xed_operand_values_t* p, 
                                                 xed_uint_t memop_idx,
                                                 xed_uint_t new_scale);


/// @ingroup OPERANDS    
/// Set the operand storage field entry named 'operand_name' to the
/// register value specified by 'reg_name'.
XED_DLL_EXPORT void
xed_operand_values_set_operand_reg(xed_operand_values_t* p,
                                   xed_operand_enum_t operand_name,
                                   xed_reg_enum_t reg_name);

//@}
#endif

