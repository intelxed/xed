# Building Intel&reg; XED for Python Integration

This guide provides instructions to build the Intel&reg; XED shared library for Python integration. The resulting built library will export all XED API functions (including originally inlined APIs) with a suffix. This enables Python to interact with XED by loading it as a dynamic library.

## Building XED with Python Export Support

To ensure that the Intel&reg; XED shared library is built with Python bindings, you need to use specific build options.

Run the following command from the root directory:

```bash
python mfile.py --shared --py-export
```

This command will:
- **Generate Python bindings**: The `--py-export` flag ensures that the necessary C functions from XED are wrapped and exported with a `_py` suffix, making them accessible from Python.
- **Build XED as a shared library**: A dynamically loadable shared object will be created.

### Python-Exported Functions

All XED APIs that are exported for Python use have a unique `_py` suffix appended to their names. For example:
- `xed_tables_init()` becomes `xed_tables_init_py()`.
- `xed_get_version()` becomes `xed_get_version_py()`.

These Python-specific function names allow seamless integration with the dynamically loaded Intel&reg; XED library in a Python environment.

## Usage Examples

Once you’ve built Intel&reg; XED with Python support, you can refer to the Python examples scripts for details on how to load and use the Intel&reg; XED library.
Currently, the examples include limited Python bindings for the XED C APIs.

### Specifying the Intel&reg; XED Shared Library Path

The Python examples provided allow you to specify the location of the XED shared library using the `--xed-lib` option. If this option is not used, the default location for the shared library is assumed to be `obj/`.

For the `cffi` script, you have to specify any of the --decode or --encode knobs (or both) to run their respective examples.

```bash
python examples/xedpy_ex_cffi.py --xed-lib /path/to/libxed.so --decode --encode
```

### Example Python Scripts:
- **`xedpy_ex_ctypes.py`**: Demonstrates loading and interacting with XED using Python's `ctypes`.
- **`xedpy_ex_cffi.py`**: Shows how to load XED using `cffi` and work with the Python-exported APIs.
