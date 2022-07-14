import argparse
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
        Axis(
            os='Linux',
            compiler='gcc',
            ver='12.1.0'
        ),
        Axis(
            os='Linux',
            compiler='clang',
            ver='14.0.6'
        ),
        Axis(
            os='Windows',
            compiler='clang',
            ver='14.0.6'
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
        Axis(
            os='Linux',
            compiler='gcc',
            ver='11.2.0'
        ),
        Axis(
            os='Linux',
            compiler='clang',
            ver='13.0.1'
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
  group.add_argument('--nightly',
                     help='Print test matrix for nightly workflows',
                     action="store_true")
  args = parser.parse_args()
  return args


def get_latest_version(compiler):
  '''return a string of the latest supported compiler version'''
  zero_v = '0'
  latest = Axis(os='', compiler=compiler, ver=zero_v)
  for d in nightly_matrix.include:
    if d.compiler == compiler and latest < d:
      latest = d

  assert latest.ver != zero_v, f'Could not find latest version of {compiler}'
  return str(latest.ver)


if __name__ == "__main__":
  args = setup()
  matrix_json = json.dumps(
      dataclasses.asdict(sanity_matrix if args.sanity else nightly_matrix))
  print(matrix_json)
