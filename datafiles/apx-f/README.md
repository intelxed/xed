# Intel&reg; XED support status
## Decoder/Encoder support
Intel&reg; XED decoder and encoder fully support APX. 
It includes:
#### Legacy
- REX2 prefix and APX extended GPRs (EGPRs)
#### EVEX 
- APX extended GPRs (EGPRs)
- All APX-Promoted instructions
- All APX new instructions

#### ENC2 module 
- :x: No ENC2 support for APX. Users should not use this module for APX encoding


## APX CPUID support
Intel&reg; XED defines only the Foundational APX CPUID bit for promoted/new EVEX instructions.
APX-Promoted instructions require the equivalent Legacy CPUID as well - Those Legacy 
CPUIDs are not listed by Intel&reg; XED yet (TBD)


# Useful APIs
Numerous examples and vivid explanations regarding APX features can be found in the xed-ex1 example tool.

Encode request for promoted No-Flags instruction should be built with the `NF` operand:

    <sub>C Library API</sub>
    ```c
    void xed3_operand_set_nf(xed_decoded_inst_t* d, 1)
    ```

    <sub>XED command-line tool</sub>
    ```bash
    $ xed.exe -set NF 1 ....
    ```

## CCMPcc/CTESTcc (Encode/Decode)
The official APX assembly syntax is not supported yet. 
Current syntax is: `<MNEMONIC> <reg/mem>, <reg/mem/imm>, <dfv>`

