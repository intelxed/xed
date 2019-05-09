/// compilation:  
///    clang       -I kits/kit/include  ex-enc2-1.c  -L kits/kit/lib -lxed -lxed-enc2-m64-a64
/// or with the decoder (larger binary)
///    clang -DECO -I kits/kit/include  ex-enc2-1.c  -L kits/kit/lib -lxed -lxed-enc2-m64-a64

#include "xed/xed-interface.h"
#include "xed/xed-enc2-m64-a64.h"
#include <stdio.h>
#include <stdlib.h>

static xed_uint32_t test_0_xed_enc_lea_rm_q_bisd32_a64(xed_uint8_t* output_buffer)
{
    xed_enc2_req_t* r;
    xed_reg_enum_t reg0;
    xed_reg_enum_t base;
    xed_reg_enum_t index;
    xed_uint_t scale;
    xed_int32_t disp32;
    xed_enc2_req_t request;
    xed_enc2_req_t_init(&request, output_buffer);
    r = &request;
    reg0 = XED_REG_R11;
    base = XED_REG_R12;
    index = XED_REG_R13;
    scale = 1;
    disp32 = 0x11223344;
    xed_enc_lea_rm_q_bisd32_a64(r /*req*/,reg0 /*gpr64*/,base /*gpr64*/,index /*gpr64*/,scale /*scale*/,disp32 /*int32*/);
    return xed_enc2_encoded_length(r);
}

// The decoder drags in a lot of stuff to the final executable.
//#define DECO

#if defined(DECO)
static void disassemble(xed_decoded_inst_t* xedd)
{
    xed_bool_t ok;
    xed_print_info_t pi;
#define XBUFLEN 200
    char buf[XBUFLEN];
    
    xed_init_print_info(&pi);
    pi.p = xedd;
    pi.blen = XBUFLEN;
    pi.buf = buf;
    pi.buf[0]=0; //allow use of strcat
    
    ok = xed_format_generic(&pi);
    if (ok) 
        printf("Disassembly: %s\n", buf);
    else
        printf("Disassembly: %%ERROR%%\n");
}
#endif

static void dump(xed_uint8_t* buf, xed_uint32_t len) {
    xed_uint_t i;
    for(i=0;i<len;i++) 
        printf("%02x ",buf[i]);
}


int main(int argc, char** argv) {
#if defined(DECO)
    xed_decoded_inst_t xedd;
    xed_error_enum_t err;
    xed_state_t dstate;
#endif
    xed_uint8_t output_buffer[XED_MAX_INSTRUCTION_BYTES];
    xed_uint32_t enclen;
    
#if defined(DECO)
    xed_tables_init();       
    xed_state_zero(&dstate);
    dstate.mmode=XED_MACHINE_MODE_LONG_64;
#endif

    enclen = test_0_xed_enc_lea_rm_q_bisd32_a64(output_buffer);
    
    printf("Encoded: ");
    dump(output_buffer, enclen);
    printf("\n");

#if defined(DECO)
    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    err = xed_decode(&xedd, output_buffer, enclen);
    if (err == XED_ERROR_NONE) {
        disassemble(&xedd);
        return 0;
    }
    printf("ERROR: %s\n", xed_error_enum_t2str(err));
    return 1;
#endif
}
