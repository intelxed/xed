# General
Intel® Advanced Performance Extensions (Intel® APX) expands the Intel® 64 instruction set architecture with
access to more registers and adds various new features that improve general-purpose performance. The
extensions are designed to provide efficient performance gains across a variety of workloads without
significantly increasing silicon area or power consumption of the core.
The main features of Intel® APX include:
• 16 additional general-purpose registers (GPRs) R16–R31, also referred to as Extended GPRs (EGPRs)
in this document;
• Three-operand instruction formats with a new data destination (NDD) register for many integer
instructions;
• Conditional ISA improvements: New conditional load, store and compare instructions, combined
with an option for the compiler to suppress the status flags writes of common instructions;
• Optimized register state save/restore operations;
• A new 64-bit absolute direct jump instruction

This file describes XED's support status and comments for APX

## APX instructions definition by XED
#### Legacy
- Instructions with REX2 prefix are not defined with new iforms or new ISA-SETs
#### EVEX
- Existing (non-APX) EVEX instructions with EGPRs are not defined with new iforms or new ISA-SETs
- Promoted and new instructions are defined with new iforms, using the `_apx` suffix
- Introduce new `APX_NDD` XED attribute For NDD (new data destination) instructions with 3 operands
- Introduce new `APX_NF` XED attribute For No-Flags instructions

# XED support status
## Decoder support
XED decoder currently supports:
#### Legacy
- REX2 prefix and APX extended GPRs (EGPRs)
#### EVEX 
- EGPRs decoding for existing instructions
- All APX-Promoted instructions
- All APX new instructions

## Encoder support
XED encoder supports status:
#### Legacy
- :x: No REX2 support
#### EVEX 
- :x: No EGPRs support
- All APX-Promoted instructions
- All APX new instructions. Note:
  - {CF,}CMOVcc - Partial support, need to set the NF XED operand for forms with EVEX.NF=1
#### ENC2 XED module
- :x: No ENC2 support for APX. Users should not use this module for APX encoding


## APX CPUID support
XED defines only the Foundational APX CPUID bit for promoted/new EVEX instructions.
APX-Promoted instructions require the equivalent Legacy CPUID as well - Those Legacy 
CPUIDs are not listed by XED yet (TBD)


## Chip-Check support
XED's chip-check supports the detection of all APX instructions and flavors.
APX instruction can be:
- New APX instruction
- Legacy instruction with REX2 prefix
- EVEX instruction with EGPR as one of its operands (register or memory)
- EVEX instruction with ignored EGPR encoding (EVEX.B4 or EVEX.X4 bit is set but ignored). Such encoding causes illegal instruction on non-APX chips. 


# Useful APIs
Numerous examples and vivid explanations regarding APX features can be found in the xed-ex1 example tool.

## Decoder
1. Users can dynamically disable APX support using the `NO_APX` API:
    ```c
    void xed3_operand_set_no_apx(xed_decoded_inst_t* d, 1)
    ```
    The API disables support for all APX architecture, including:
    - EGPRs for Legacy instructions (actually disables REX2 support)
    - EGPRs for EVEX instructions (for both APX and no-APX instructions). It means no support for the reinterpreted EVEX bits (EGPRs, NDD/NF and more...)
    - APX new/promoted EVEX instructions


 ## Encoder
 1. The `MUST_USE_EVEX` API forces encoding request to the EVEX space. Use it for APX promoted instructions:
 
    <sub>C Library API</sub>
    ```c
    void xed3_operand_set_must_use_evex(xed_decoded_inst_t* d, 1)
    ```

    <sub>XED command-line tool</sub>
    ```bash
    $ xed.exe -set MUST_USE_EVEX 1 ....
    ```

2. Encode request for promoted No-Flags instruction should be built with the `NF` operand:

    <sub>C Library API</sub>
    ```c
    void xed3_operand_set_nf(xed_decoded_inst_t* d, 1)
    ```

    <sub>XED command-line tool</sub>
    ```bash
    $ xed.exe -set NF 1 ....
    ```

## CCMPcc/CTESTcc (Encode/Decode)
- Introduce new `DFV` 4-bit pseudo-register for "Default Flags Values" (EVEX.[OF, SF, ZF, CF])
- The register index represents the default flags bits. For example: `DFV10.index == 10 == 0b1010  ->  OF=1, SF=0, ZF=1, CF=0`
- The DFV pseudo-register should be explicitly defined in an encoder request. For example:
    ```bash
    $ xed -64 -e CCMPB r8b r9b dfv14
    Request: CCMPB MODE:2, REG0:R8B, REG1:R9B, REG2:DFV14, SMODE:2
    OPERAND ORDER: REG0 REG1 REG2 
    Encodable! 6254740238C8
    .byte 0x62,0x54,0x74,0x02,0x38,0xc8
    ```
- the official APX assembly syntax is not support yet. 
Current XED syntax is: `<MNEMONIC> <reg/mem>, <reg/mem/imm>, <dfv>`

