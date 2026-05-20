# XED Python Source Directory (pysrc)

This directory contains Python scripts used by the XED (X86 Encoder Decoder) library generator and utility scripts for working with XED metadata.

## Overview

The scripts in this directory fall into two main categories:

1. **Generator Infrastructure**: Python modules used internally by the XED build system to generate C code for the encoder, decoder, and instruction length decoder (ILD).

2. **User Utilities**: Standalone scripts that can be run by users to extract information from the XED instruction database.

## User Utility Scripts

These scripts can be run directly to extract information from the XED database. They require a path to the `obj/dgen` directory as an argument.

### General Usage Pattern

```bash
python <script_name>.py <path_to_obj/dgen>
```

For example:
```bash
python gen_dump.py ../obj/dgen
```

### Available Utilities

- **gen_dump.py** - Dump all fields for each instruction definition
  ```bash
  python gen_dump.py ../obj/dgen
  ```

- **gen_inst_list.py** - Generate instruction lists for specific chips and compare between chips
    ```bash
    # List instructions for a specific chip:
    python gen_inst_list.py --chip ALDER_LAKE ../obj/dgen
    
    # Compare two chips:
    python gen_inst_list.py --chip ALDER_LAKE --otherchip FUTURE ../obj/dgen
    ```

- **gen_newer_inst_list.py** - Show instruction differences between two chips
  ```bash
  python gen_newer_inst_list.py --basechip <chip1> --newchip <chip2> ../obj/dgen
  ```

- **gen_cpuid.py** - List CPUID features required for each instruction
  ```bash
  python gen_cpuid.py ../obj/dgen
  ```

- **gen_cpuid_per_chip.py** - Generate JSON database of CPUID features per chip
  ```bash
  python gen_cpuid_per_chip.py ../obj/dgen
  ```

- **gen_flags.py** - Generate CPU flag usages
  ```bash
  python gen_flags.py ../obj/dgen
  ```

- **gen_operands.py** - Generate operand usage histograms
  ```bash
  python gen_operands.py ../obj/dgen
  ```

- **gen_chip_list.py** - Generate instruction statistics per chip
  ```bash
  python gen_chip_list.py ../obj/dgen
  ```

- **gen_py_wrappers.py** - Generate Python wrapper functions for XED API
  ```bash
  python gen_py_wrappers.py --xeddir <xed_source_dir> --gendir <output_dir>
  ```

### Required dgen Directory Structure

The `obj/dgen` directory should contain the following files generated during XED build:
- `all-state.txt` - State bits definitions
- `all-cpuid.txt` - CPUID feature definitions
- `all-dec-instructions.txt` - Decoded instruction definitions
- `all-chip-models.txt` - Chip model definitions
- `all-widths.txt` - Width definitions
- `all-element-types.txt` - Element type definitions
- `all-map-descriptions.txt` - Opcode map descriptions

### Generating the dgen Directory

The `obj/dgen` directory is automatically generated during a standard XED build. However, if you only want to generate the dgen files without building the entire XED library, you can run (from the main XED directory):

```bash
python mfile.py just-prep
```
The `just-prep` target is XED's lightweight preparation mode. It gathers the active XED datafiles, expands the configured input layers, and generates the prepared `all-*.txt` files in `obj/dgen`.
It then stops before decoder or encoder generation, C or C++ compilation, library builds, examples, or tests. In practice, this is the right target when you only need generated metadata for Python utilities and do not need a compiled XED library or compiler-driven build.
After running this command, the `obj/dgen` directory will be ready for use with the utility scripts described above.

### Generating the Instruction JSON Database

The `xed_to_db.py` utility converts a prepared XED `obj/dgen` directory into a JSON instruction database.

From the main XED directory:

```bash
python mfile.py just-prep
python pysrc/xed_to_db.py --xed-dgen=obj/dgen --out=xed_db.json
```

This produces `xed_db.json` in the current directory.

Useful options:
- Add `--validate` to run additional consistency checks while still generating the JSON output.

### Common Options

Most utility scripts accept the `obj/dgen` directory path as their sole required argument. Some scripts may have additional optional parameters - use `--help` to see script-specific options.

## Dependencies

Most scripts depend on:
- **mbuild** - The build system framework (usually in `../mbuild`)
- **Python 3.x** - Required for most scripts
- XED datafiles directory containing instruction definitions

