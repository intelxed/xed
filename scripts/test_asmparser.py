#!/usr/bin/env python
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2025 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL

import argparse
import re
import subprocess
from pathlib import Path
import sys
from collections import defaultdict
from typing import Optional


def setup():
    """Parses command-line arguments and returns the script environment"""
    parser = argparse.ArgumentParser(description='XED assembly parser validator')
    parser.add_argument("--input",
                      action="store",
                      dest="input_file",
                      type=Path,
                      required=True,
                      help="path of assembly text file to be tested")
    parser.add_argument('--output-dir',
                      dest='output_dir',
                      help='output directory for match or mismatch logging',
                      type=Path,
                      default=Path('logs'))
    parser.add_argument('--xed-kit',
                        action="store",
                        dest="xed_kit",
                        type=Path,
                        default=Path(__file__).parents[1].joinpath('obj/wkit/bin'),
                        help='Path to XED build kit')
    parser.add_argument('--verbose',
                      dest='verbose',
                      help='Print important messages',
                      action="store_true")            
    env = vars(parser.parse_args())

    return env


def encode(instr: str, xed_kit: Path) -> tuple[Optional[str], Optional[str]]:
    """
    Encodes a given instruction using the xed-enc-asmparse example

    Args:
        instr: The assembly instruction.
        xed_kit: Path to the XED binaries

    Returns:
        A tuple of (encoded hex string, error string)
    """
    cmd = [xed_kit / 'xed-enc-asmparse', "-64", "-q", instr]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode == 0:
        return result.stdout.decode().strip(), None
    else:
        return None, result.stderr.decode().strip() or "Unknown error"


def decode(byte_str: str, xed_kit: Path) -> tuple[Optional[str], Optional[str]]:
    """
    Decodes a hex byte string using the xed example

    Args:
        byte_str: A space-separated string of byte values
        xed_kit: Path to the XED binaries

    Returns:
        A tuple of (decoded instruction, error string)
    """
    cmd = [xed_kit / 'xed', "-64", "-d", byte_str]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)

    if result.returncode != 0:
        return None, result.stderr.decode().strip() or "Unknown error"

    lines = [line for line in result.stdout.decode().splitlines() if line.strip()]
    if not lines:
        return None, "No output from decoder"

    disasm = ' '.join(lines[-1].replace("SHORT", "").replace(":", "").split())
    return disasm, None


def encode_instructions_from_file(env) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """
    Encodes all instructions from the input file

    Returns:
        A tuple of (instruction to hex map, list of failed encodes)
    """
    asm2enc = {}
    failed_encodes = []

    with env['input_file'].open('r') as f:
        for line in f:
            instr = line.strip()

            if not instr or instr.startswith((';', '#')):
                continue  # Skip comments

            if env['verbose']:
                print(f"Trying to encode: {instr}")

            encoded, error = encode(instr, env['xed_kit'])
            if error:
                if env['verbose']:
                    print(f"  [ENCODE ERROR] {error}")
                failed_encodes.append((instr, error))
            else:
                asm2enc[instr] = encoded
                if env['verbose']:
                    print(f"  Encoding: {encoded}")

    return asm2enc, failed_encodes


def decode_instructions(env, asm2enc: dict[str, str]) -> tuple[dict[str, str], int]:
    """
    Decodes hex strings back into instructions

    Returns:
        A tuple of (original to decoded map, decoding error count)
    """
    asm2asm = {}
    decoding_errors = 0

    for instr, hex_string in list(asm2enc.items()):
        byte_str = hex_string.replace('.byte', '').replace(',', '').replace('0x', '').strip()
        byte_str = ' '.join(byte_str.split())

        decoded, error = decode(byte_str, env['xed_kit'])
        
        if env['verbose']:
            print(f"Trying to decode: {hex_string}")

        if error:
            asm2asm.pop(instr)
            decoding_errors += 1
            if env['verbose']:
                print(f"   [DECODE ERROR] {error}")
        else:
            asm2asm[instr] = decoded
            if env['verbose']:
                print(f"   Decoded: {decoded}\n")

    return asm2asm, decoding_errors


def normalize_immediates(disasm_str: str) -> str:
    """
    Normalize all immediates to base-10 integers for comparison from a given disassembly string
    """
    tokens = disasm_str.replace(',', ' ').split()

    def normalize_token(tok):
        try:
            return str(int(tok, 0)) if tok.startswith('0x') or tok.isdigit() else tok
        except ValueError:
            return tok

    normalized = ' '.join(normalize_token(tok.lower()) for tok in tokens)
    return normalized.replace(" ", "").lower()


def is_format_equivalent(original: str, decoded: str) -> bool:
    """
    Returns True if the only differences are:
    - insertion of 'ptr'
    - addition of '*1' as a scale factor
    """
    def normalize(s: str) -> str:
        s = re.sub(r'\bptr\b', '', s, flags=re.IGNORECASE)       # remove 'ptr'
        s = re.sub(r'\*1\b', '', s)                              # remove '*1' scale factor
        s = re.sub(r'\s+', ' ', s)                               # normalize whitespace
        return s.strip().lower()

    return normalize(original) == normalize(decoded)


def normalize_numeric_tokens(s: str) -> str:
    # Remove redundant scale, zero displacements, and extra spaces
    s = s.replace('*1', '')
    s = re.sub(r'\+0x0\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\+0\b', '', s)
    s = re.sub(r'\s+', '', s)
    return s


def extract_operands(instr: str) -> list[str]:
    parts = instr.split(None, 1)
    return parts[1].split(',') if len(parts) > 1 else []


def analyze_mismatch(original: str, decoded: str) -> str:
    """Attempts to classify the cause of a mismatch between original and decoded instruction"""
    orig_mnemonic = original.split()[0].lower()
    dec_mnemonic = decoded.split()[0].lower()

    if orig_mnemonic != dec_mnemonic:
        return "ICLASS or mnemonic alias mismatch"

    orig_ops = [normalize_numeric_tokens(op.strip().lower()) for op in extract_operands(original)]
    dec_ops  = [normalize_numeric_tokens(op.strip().lower()) for op in extract_operands(decoded)]

    if len(orig_ops) != len(dec_ops):
        return "Operand count/order mismatch"

    for o_op, d_op in zip(orig_ops, dec_ops):
        # Disp placement: `[rbx+0x1]` vs `0x1[rbx]`
        if re.search(r'^\s*0x[a-f0-9]+\[', o_op) and '[' in d_op:
            return "Displacement placement difference"

        # Base/index/scale structure mismatch
        if ('*' in o_op) != ('*' in d_op):
            return "Scale/index structure mismatch"

        # Disp value difference (after removing +0 or *1, so real difference)
        if o_op != d_op:
            return "Operand value mismatch"

    return "Other Format differences"


def compare_results(asm2asm: dict[str, str]) -> tuple[list[str], int, int, list[tuple[str, str]]]:
    """
    Compares original assembly string vs decoded instructions and classifies results

    Returns:
        A tuple of (match info list, match count, mismatch count, mismatch reasons)
    """
    match_info = []
    matches = 0
    mismatches = 0
    reasons = []

    for original, decoded in asm2asm.items():

        orig_cmp = normalize_immediates(original)
        dec_cmp = normalize_immediates(decoded)

        if orig_cmp == dec_cmp:
            match_info.append(f'[MATCH]   : {original}')
            matches += 1
        elif is_format_equivalent(original, decoded):
            match_info.append(f'[MATCH]   : {original} (matched after reformatting)')
            matches += 1
        else:
            reason = analyze_mismatch(original, decoded)
            match_info.append(f'[MISMATCH] ({reason}): REQUESTED: {original}, RESULT: {decoded}')
            mismatches += 1
            reasons.append((original, reason))

    return match_info, matches, mismatches, reasons


def write_results(output_dir: Path, match_info: list[str], stats: dict[str, int],
                  mismatch_reasons: list[tuple[str, str]], failed_encodes: list[tuple[str, str]]):
    """
    Writes match results and summary statistics to files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group reasons
    mismatch_group = defaultdict(list)
    for instr, reason in mismatch_reasons:
        mismatch_group[reason].append(instr)

    encode_group = defaultdict(list)
    for instr, reason in failed_encodes:
        encode_group[reason].append(instr)

    with open(output_dir / 'amparse_res.txt', 'w') as f:
        f.writelines(line + '\n' for line in match_info)

    with open(output_dir / 'summary.txt', 'w') as f:
        f.write(f"Total instructions processed : {stats['total']}\n")
        f.write(f"Encoding errors              : {stats['encoding_errors']}\n")
        f.write(f"Decoding errors              : {stats['decoding_errors']}\n")
        f.write(f"Successful matches           : {stats['matches']}\n")
        f.write(f"Mismatches                   : {stats['assembly mismatches']}\n")

        if failed_encodes:
            f.write("\nEncoding Failures:\n")
            for reason, instructions in encode_group.items():
                f.write(f" - {reason} ({len(instructions)}):\n")
                for instr in instructions:
                    f.write(f"    - {instr}\n")

        if mismatch_reasons:
            f.write("\nMismatch Reasons:\n")
            for reason, instructions in mismatch_group.items():
                f.write(f" - {reason} ({len(instructions)}):\n")
                for instr in instructions:
                    f.write(f"    - {instr}\n")


def main():
    env = setup()
    assert env['input_file'].exists(), f"Input file not found: {env['input_file']}"
    assert env['xed_kit'].exists(), f"XED kit path not found: {env['xed_kit']}"

    asm2enc, failed_encodes = encode_instructions_from_file(env)
    total_instructions = len(asm2enc) + len(failed_encodes)

    asm2asm, decoding_errors = decode_instructions(env, asm2enc)
    match_info, matches, mismatches, mismatch_reasons = compare_results(asm2asm)

    assert total_instructions == len(failed_encodes) + decoding_errors + mismatches + matches

    stats = {
        'total': total_instructions,
        'encoding_errors': len(failed_encodes),
        'decoding_errors': decoding_errors,
        'matches': matches,
        'assembly mismatches': mismatches
    }

    write_results(env['output_dir'], match_info, stats, mismatch_reasons, failed_encodes)

    print(f"Results written to {env['output_dir'] / 'amparse_res.txt'}")
    print(f"Summary written to {env['output_dir'] / 'amparse_summary.txt'}")

    sys.exit(mismatches + len(failed_encodes))


if __name__ == '__main__':
    main()
