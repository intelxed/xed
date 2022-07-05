import argparse
import json
from pathlib import Path

##### Parse input arguments #####
parser = argparse.ArgumentParser(description='Generate test matrix for GitHub Actions workflows')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--sanity',
                    help='Print test matrix for sanity workflows',
                    action="store_true")
group.add_argument('--nightly',
                    help='Print test matrix for nightly workflows',
                    action="store_true")
args = parser.parse_args()
#################################

##### Init test matrix DB #####
sanity_matrix = {
    'include': 
    [
      {
        'os': 'Linux',
        'compiler': 'gcc',
        'ver': '9.4'
      },
      {
        'os': 'Windows',
        'compiler': 'msvs',
        'ver': '17' # Visual Studio 2022
      },
    ]
}

# Nightly extends the sanity matrix
nightly_matrix = { 'include': sanity_matrix['include'] + 
      [
        {
        'os': 'Windows',
        'compiler': 'msvs',
        'ver': '16' # Visual Studio 2019
        },
      ]
    }

#######################################

matrix_json = json.dumps(sanity_matrix if args.sanity else nightly_matrix)
print(matrix_json)
