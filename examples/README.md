# Intel® XED Examples

This directory contains standalone examples demonstrating how to use the Intel® XED (X86 Encoder Decoder) library. 

The examples can be used both as command-line utilities for encoding, decoding, and analyzing x86 instructions, and as code samples showing how to integrate Intel® XED into your own project.

The primary example (`xed.c`) is a comprehensive demonstration of Intel® XED's capabilities, including instruction decoding, encoding, binary file disassembly, chip-check functionality, and more.

## Examples Documentation

For detailed documentation and explanation of the example programs, including what each example demonstrates and how to use them, please refer to:

**[Intel® XED Examples Documentation](https://intelxed.github.io/ref-manual/group__EXAMPLES.html)**

## Building the Examples

### Requirements

- **Python 3.9 or later**
- **XED library** (static or shared) installed in a standard location

### Quick Start

#### Building with Static Intel® XED Library

If your XED library is built as a static archive (`.a` on Linux, `.lib` on Windows):

```bash
python mfile.py
```

#### Building with Shared Intel® XED Library

If you are using a shared XED library (`.so` on Linux, `.dll` on Windows), you **must** specify the `--shared` flag:

```bash
python mfile.py --shared
```

### Advanced Build Options

#### Custom Build Directory

To specify a custom build directory:

```bash
./mfile.py --build-dir /path/to/build/dir
```

#### Runtime Library Path (RPATH) for Shared Builds (Linux)

When building examples with a **shared XED library**, the builder automatically sets RPATH to look for `libxed.so` in:
- `$ORIGIN/../lib` (one level up from the executable)
- `$ORIGIN/../../lib` (two levels up)

**If your shared library is in a non-standard location**, you must specify additional RPATH directories using `--example-rpath`:

```bash
# Example: libxed.so is in /opt/xed/lib
./mfile.py --shared --example-rpath /opt/xed/lib

# Multiple paths can be specified
./mfile.py --shared \
  --example-rpath /opt/xed/lib \
  --example-rpath /usr/local/xed/lib
```

**Important Notes:**
- The `--example-rpath` option only works on Linux (not Windows)
- On Windows, ensure `xed.dll` is in your `PATH` or the same directory as the executable

#### Additional Compilation and Link Flags

Add extra compilation flags:

```bash
./mfile.py --example-flags "-O3 -DNDEBUG"
```

Add extra link flags:

```bash
./mfile.py --example-linkflags "-L/custom/lib/path"
```

### Build Commands

#### Clean Build

Remove all build artifacts:

```bash
./mfile.py clean
```

### Getting Help

View all available options:

```bash
./mfile.py --help
```
