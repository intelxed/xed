#include <Python.h>

#include <stdio.h>
#include "xed/xed-interface.h"

#if defined(__GNUC__) || defined(__clang__)
#  include <stdint.h>
#else 
typedef unsigned __int32 uint32_t;
typedef unsigned __int64 uint64_t;
#endif

static PyObject *dis(PyObject *self,
                     PyObject *args,
                     xed_machine_mode_enum_t mmode,
                     xed_address_width_enum_t stack_addr_width)
{
    PyObject* byte_list_obj=0;
    PyObject* it=0;
    PyObject* next=0;
    char itext[XED_MAX_INSTRUCTION_BYTES];
    int pos = 0;
    xed_error_enum_t xed_error;
    xed_decoded_inst_t xedd;
#define BUFLEN  1000
    char buffer[BUFLEN];
    int ok;
    uint64_t runtime_addr=0;
    
    if (!PyArg_ParseTuple(args, "O|K", &byte_list_obj, &runtime_addr))
        return NULL;
    if (!(it = PyObject_GetIter(byte_list_obj)))
        return NULL;
    while ((next=PyIter_Next(it)) && pos < XED_MAX_INSTRUCTION_BYTES)
    {
        if (!PyLong_Check(next))
            return NULL;
        itext[pos++] = PyLong_AsUnsignedLong(next);
    }

    xed_decoded_inst_zero(&xedd);
    xed_decoded_inst_set_mode(&xedd, mmode, stack_addr_width);
    xed_error = xed_decode(&xedd, 
                           XED_STATIC_CAST(const xed_uint8_t*,itext),
                           pos);
    
    if (xed_error == XED_ERROR_NONE)
    {
        ok = xed_format_context(XED_SYNTAX_INTEL,
                                &xedd, buffer, BUFLEN, runtime_addr,
                                0, 0);
        if (ok) {
            xed_uint32_t ilen;
            ilen = xed_decoded_inst_get_length(&xedd);

            return Py_BuildValue("si", buffer, ilen);
        }
        else 
            return Py_BuildValue("si", "Disassembly error", 0);
    }
    return Py_BuildValue("si", "Decoding error", 0);
}

static PyObject *
dis64(PyObject *self, PyObject *args)
{
    return dis(self,args,XED_MACHINE_MODE_LONG_64,XED_ADDRESS_WIDTH_64b);
}
static PyObject *
dis32(PyObject *self, PyObject *args)
{
    return dis(self,args,XED_MACHINE_MODE_LEGACY_32,XED_ADDRESS_WIDTH_32b);
}


#define HELPSTR  " Arguments are:\n\t(1) a list of integers representing the code to decode/disassemble,\n\t(2) an optional runtime address.\n\tReturns a disassembly string.\n"
     
static PyMethodDef xed_methods[] = {
    {"dis64",  dis64, METH_VARARGS, "Disassemble in 64b mode."  HELPSTR },
    {"dis32",  dis32, METH_VARARGS, "Disassemble in 32b mode."  HELPSTR },
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef xed = {
    PyModuleDef_HEAD_INIT,
    "xed",    /* name of module */
    NULL,     /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    xed_methods
};


PyMODINIT_FUNC
PyInit_xed(void)
{
    PyObject *m;

    m = PyModule_Create(&xed);
    if (m == NULL)
        return 0;
    xed_tables_init();
    return m;
}

