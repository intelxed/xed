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
from collections import defaultdict
import dataclasses
import json
from pathlib import Path
from typing import List


##### Init test matrix DB #####
# GitHub workflow YML configuration file expects the below data structure: dict('include':list)
# Change it carefully if needed!!!
@dataclasses.dataclass
class Axis:
  os: str
  compiler: str
  ver: str

  def __lt__(self, other):
    assert (self.compiler ==
            other.compiler), 'Can not compare different compiler versions'
    default_ver = [0, 0, 0]
    # Convert string to array of integers
    my_ver = [int(i) for i in self.ver.split('.')]
    other_ver = [int(i) for i in other.ver.split('.')]
    # Force 3 elements list (Major, minor, patch)
    # If element is missing, fill with zeros
    my_ver = [my_ver + default_ver][:3]
    other_ver = [other_ver + default_ver][:3]
    return my_ver < other_ver


@dataclasses.dataclass
class Matrix:
  include: List[Axis]


sanity_matrix = Matrix(
    include=[
        # Linux
        Axis(
            os='Linux',
            compiler='gcc',
            ver='12.1.0'
        ),
        Axis(
            os='Linux',
            compiler='clang',
            ver='15.0.4'
        ),
        # Windows
        Axis(
            os='Windows',
            compiler='clang',
            ver='15.0.2'
        ),
        Axis(
            os='Windows',
            compiler='msvs',
            ver='17'  # Visual Studio 2022
        ),
    ]
)

# Nightly extends the sanity matrix
nightly_matrix = Matrix(
    include=sanity_matrix.include +
    [
        # Linux
        Axis(
            os='Linux',
            compiler='gcc',
            ver='11.2.0'
        ),
        Axis(
            os='Linux',
            compiler='clang',
            ver='14.0.6'
        ),
        # Windows
        Axis(
            os='Windows',
            compiler='clang',
            ver='14.0.6'
        ),
        Axis(
            os='Windows',
            compiler='msvs',
            ver='16'  # Visual Studio 2019
        ),
    ]
)

#######################################


def setup():
    parser = argparse.ArgumentParser(
      description='Generate test matrix for GitHub Actions workflows')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sanity',
                     help='Print test matrix for sanity workflows',
                     action="store_true")
    group.add_argument('--coverity',
                     help='Print test matrix for coverity check',
                     action="store_true")
    group.add_argument('--nightly',
                     help='Print test matrix for nightly workflows',
                     action="store_true")
    parser.add_argument('--html',
                  help='Generate html table to stdout',
                  action='store_true', 
                  default=False)
    args = parser.parse_args()
    return args


def get_latest_version(compiler, os):
  '''return a string of the latest supported compiler version for the given os'''
  zero_v = '0'
  latest = Axis(os='', compiler=compiler, ver=zero_v)
  for d in nightly_matrix.include:
    if d.compiler == compiler and d.os == os and latest < d:
      latest = d

  assert latest.ver != zero_v, f'Could not find latest version of {compiler}'
  return str(latest.ver)


def get_coverity_matrix() -> Matrix:
    """iterates over the sanity matrix and yields the desired Coverity environments
    with the latest compiler version"""
    coverity_matrix = Matrix(
        include=[
            Axis(os='Linux', compiler='gcc', ver=''),
            Axis(os='Windows',compiler='msvs',ver='')
        ]
    )
    for config in coverity_matrix.include:  #retrieve the latest version defined in our nightly matrix
        config.ver = get_latest_version(config.compiler, config.os)
    return coverity_matrix


def gen_tests_table(matrix):
    """Generate GitHub test matrix in a format of HTML table"""
    os_set = set()
    compiler_set = set()
    for m in matrix:
        os_set.add(m.os)                # store all unique operating systems
        compiler_set.add(m.compiler)    # store all unique compilers
    
    #keys of db are operating systems, values are dictionaries with compilers as keys
    db = {o: defaultdict(list) for o in os_set}    
    
    # map all versions to the respective operating system and compiler
    for m in matrix:
        db[m.os][m.compiler].append(m.ver)
    
    # Generate the html table
    table = '<th>\t</th>'
    table += ''.join('<th>' + x + '</th>' for x in compiler_set)    #generate the table's header
    for o in os_set:  # Append row
        table += f'<tr><td>{o}</td>'
        for c in compiler_set:  # Append column
            table += '<td>' + ', '.join(db[o][c]) + '</td>'
        table += '</tr>'
    html = '<table border=1 class="stocktable" id="table1">' + table + '</table>'
    return html

if __name__ == "__main__":
    args = setup()
    if args.sanity:
        matrix = sanity_matrix
    elif args.nightly:
        matrix = nightly_matrix
    else:
        matrix = get_coverity_matrix()
  
    if args.html:
        print(gen_tests_table(matrix.include))
    else:
        print(json.dumps(dataclasses.asdict(matrix)))

