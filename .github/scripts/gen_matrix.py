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


@dataclasses.dataclass
class Matrix:
  include: List[Axis]


sanity_matrix = Matrix(
    include=[
        Axis(
            os='Linux',
            compiler='gcc',
            ver='11.2.0'
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
            ver='10.2.1'
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
  latest = float(0)
  for d in nightly_matrix['include']:
    if d['compiler'] == compiler and latest < float(d['version']):
      latest = d['version']

  assert latest, f'Could not find latest version of {compiler}'
  return str(latest)


if __name__ == "__main__":
  args = setup()
  matrix_json = json.dumps(
      dataclasses.asdict(sanity_matrix if args.sanity else nightly_matrix))
  print(matrix_json)
