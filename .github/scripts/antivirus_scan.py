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

from pathlib import Path
import platform
import re
import sys
import os
import utils
import argparse

def setup():
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='anti-virus scan argument parser')
    parser.add_argument('--path',
                        dest='av_path',
                        help='Path to anti-virus scan',
                        type=Path,
                        default='')
    env = vars(parser.parse_args())
    return env

def get_infected_files(avscan_path: Path) -> int:
    """
    Returns the number of possibly infected files

    Args:
        avscan_path (Path): a path to malware scan results file
    """
    with open(avscan_path, 'r') as f:
        lines = f.readlines()

    pattern = r"Possibly Infected:.............\s+(\d+)$"

    for line in lines:
        line = " ".join(line.split())
        match = re.match(pattern, line)
        if match:
            return int(match.group(1))

    assert False, 'Malware scan summary not found.'  # normally shouldn't get here


if __name__ == '__main__':

    env = setup()

    os.makedirs('logs', exist_ok=True)
    avscan_res_path = Path('logs', 'avscan.txt')
    avscan_sum_path = Path('logs', 'antivirus_summary.txt')
    # delete previous anti-virus scan results and summary
    if avscan_res_path.exists(): os.remove(avscan_res_path)
    if avscan_sum_path.exists(): os.remove(avscan_sum_path)

    os = platform.system()
    
    assert os == 'Linux', 'Anti-virus scan is currently only supported on Linux'
    
    avargs = '--VERBOSE --RECURSIVE --SUMMARY'
    av_scan_cmd = f"{env['av_path']} {avargs} {Path('./')} > {avscan_res_path}"
    retval, retlines = utils.run_subprocess(av_scan_cmd)
    
    # the summary yields number of suspicious files
    infected_files = get_infected_files(avscan_res_path)

    with open(avscan_sum_path, 'w') as f:
        f.write(f'{infected_files} possibly infected files.')
    
    sys.exit(retval)
