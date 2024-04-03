# Intel&reg; XED support status
## Decoder/Encoder support
Intel&reg; XED decoder and encoder fully support Intel&reg; APX. 

#### ENC2 module 
- :x: ENC2 supports Intel&reg; APX architecture with a few limitations; EGPRs are only supported in EVEX and thus REX2 is only emitted when necessary
for a couple of legacy instructions.

# Useful APIs
Numerous examples and vivid explanations regarding Intel&reg; APX features can be found in the xed-ex1 example tool.

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
The official Intel&reg; APX assembly syntax is not supported yet. 
Current syntax is: `<MNEMONIC> <reg/mem>, <reg/mem/imm>, <dfv>`

