#!/usr/bin/env python 
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2023 Intel Corporation
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
import os
import sys
from pathlib import Path
from typing import Dict, Set
import json

def msge(s):
    print(s, file=sys.stderr, flush=True)

def setup() -> dict:
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='enc2 support comparison argument parser')
    parser.add_argument('--build-dir',
                      dest='build_dir',
                      help='enc2 build results path (XED enc2 already built)',
                      type=Path,
                      default=Path('obj'))
    parser.add_argument('--output-dir',
                      dest='output_dir',
                      help='enc2 unsupported ISA diff results path',
                      type=Path,
                      default=Path('logs', 'enc2'))
    parser.add_argument('--ref-path',
                      dest='ref_path',
                      help='path to enc2 unsupported iforms reference file',
                      type=Path,
                      default=Path(__file__).parent.joinpath('enc2_unsupported_ref.json'))
    parser.add_argument('--ref-update',
                      dest='ref_update',
                      help='Updates the reference file as well',
                      action="store_true")
    parser.add_argument('--smart-ref-update',
                      dest='smart_ref_update',
                      help='Updates the reference file if enc2 does not break and new IFORMs were resolved',
                      action="store_true")
    parser.add_argument('--verbose',
                      dest='verbose',
                      help='Print important messages',
                      action="store_true")
    env = vars(parser.parse_args())
    return env


def combine_json_files(file1: Path, file2: Path) -> Dict[str, Set[str]]:
    """
    combines two json files (mappings from ISA-SETs to set of IFORMs).

    Args:
        file1 (Path): first file to be merged
        file2 (Path): second file to be merged
    
    Returns:
        Dict[str, Set[str]]: the combined data of the two given files
    """
    with open(file1, 'r') as f:
        data1: Dict[str, list] = json.load(f)

    with open(file2, 'r') as f:
        data2: Dict[str, list] = json.load(f)

    all_isa: set = set(data1.keys()) | set(data2.keys())

    merged_data = {isa: set(data1.get(isa, []) + data2.get(isa, [])) for isa in all_isa}

    return merged_data


def enc2_support_diff(reference_file: Path, cur: Dict[str, Set[str]]) -> (Dict[str, Set[str]],Dict[str, Set[str]]):
    """
    Compare two JSON files and identify unique entries (IFORMS) in each file.

    Args:
        reference_file (Path): Path to the reference JSON file
        cur (Dict[str, Set[str]]): current unsupported IFORM content (ISA to set of IFORMs)

    Returns:
       Two dictionaries representing unique entries (IFORMS) for reference list and current list
    """

    with open(reference_file, 'r') as f:
        ref: Dict[str, list] = json.load(f)

    # sets aren't json serializable so we convert to list before dumping content and convert to set after loading it
    ref = {isa : set(iforms) for isa, iforms in ref.items()}

    cur_isa, ref_isa = set(cur.keys()), set(ref.keys())

    common_isa : set = cur_isa & ref_isa
    cur_unique_isa : set = cur_isa - common_isa
    ref_unique_isa : set = ref_isa - common_isa

    # If ISA appears only in ref/cur then all IFORMs are guaranteed to be unique entries
    unique_cur : Dict[str : Set[str]] = {isa : cur[isa] for isa in cur_unique_isa}
    unique_ref : Dict[str : Set[str]] = {isa : ref[isa] for isa in ref_unique_isa}

    for isa in common_isa:
        # if ISA appears in both ref and curr, we look for unique IFORMs for this ISA (in either ref or cur but not both)
        cur_iforms, ref_iforms = cur[isa], ref[isa]
        cur_unique_iforms : set = cur_iforms - ref_iforms
        ref_unique_iforms : set = ref_iforms - cur_iforms
        if cur_unique_iforms: unique_cur[isa] = cur_unique_iforms
        if ref_unique_iforms: unique_ref[isa] = ref_unique_iforms

    return unique_ref, unique_cur


def is_outdated_ref(unique_ref: Dict[str, Set[str]], unique_cur: Dict[str, Set[str]]) -> bool:
    """
    Determines whether the unsupported IFORMs reference file is outdated

    Args:
        unique_ref (Dict[str, Set[str]]): unique IFORM entries from reference file
        unique_cur (Dict[str, Set[str]]): unique IFORM entries from current files
    """    
    # we should update reference only if new IFORMs have been supported and enc2 didn't break

    # The first condition: the new IFORMs should appear in UNIQUE_TO_REFERENCE since it has been
    # removed from the currently supported IFORMs list but is still in reference list.
    if not unique_ref: 
        return False
    
    # The second condition: enc2 breaks if at least one IFORM is in UNIQUE_TO_CURRENT
    if unique_cur:
        return False

    return True # assuming build with same reference chip


if __name__ == '__main__':

    env = setup()

    os.makedirs(env['output_dir'], exist_ok=True)

    assert env['build_dir'].exists(), f'Specified build directory doesn\'t exist: {env["build_dir"]}'
    assert env['ref_path'].exists(),  f'Specified reference file doesn\'t exist: {env["ref_path"]}'

    current_enc2_m32_file = Path(env['build_dir'], "enc2_unsupported_m32.json")
    current_enc2_m64_file = Path(env['build_dir'], "enc2_unsupported_m64.json")

    assert current_enc2_m32_file.exists(), 'enc2 mode32 unsupported iforms file is missing'
    assert current_enc2_m64_file.exists(), 'enc2 mode64 unsupported iforms file is missing'

    # combine enc2 mode 32 and mode 64 unsupported iform files
    all_unsup_iforms = combine_json_files(current_enc2_m32_file, current_enc2_m64_file)

    # find unique IFORM entries for both reference file and current results
    unique_ref, unique_cur = enc2_support_diff(env['ref_path'], all_unsup_iforms)

    if env['ref_update'] or ( env['smart_ref_update'] and is_outdated_ref(unique_ref, unique_cur)):
        with open(env['ref_path'], 'w') as f:
            # sort the results by ISA and IFORMs
            iforms =  {isa : sorted(all_unsup_iforms[isa]) for isa in sorted(all_unsup_iforms.keys())}
            json.dump(iforms, f, indent=2)
        print('Updated reference file')

    # generate the diff results, sort them and pour them into json file
    diff_file = Path(env['output_dir'], 'enc2_support_diff.json')
    with open(diff_file, 'w') as f:
        diff_dict = {
        'UNIQUE_TO_REFERENCE': {isa : sorted(unique_ref[isa]) for isa in sorted(unique_ref.keys())},
        'UNIQUE_TO_CURRENT'  : {isa : sorted(unique_cur[isa]) for isa in sorted(unique_cur.keys())}
        }
        json.dump(diff_dict, f, indent=2)
        print(f'please inspect {diff_file} for results diff')

    # if enc2 breaks (ISA-SETs that are no longer supported) exit with number of ISA-SETs
    if not env['ref_update'] and not env['smart_ref_update']:
        broken_isa = unique_cur.keys() - unique_ref.keys()
        if broken_isa:
            if env['verbose']:
                for isa in broken_isa:
                    msge(f'[BROKEN ENC2] ISA-SET {isa} is no longer fully supported!')
            sys.exit(len(broken_isa))

    sys.exit(0)
