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

import sys
import argparse
import utils
from pathlib import Path

def setup():
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='Protex scan argument parser')
    parser.add_argument("--project-id",
                      action="store",
                      dest="project_id",
                      help="Protex project ID")
    parser.add_argument("--user",
                      action="store",
                      dest="user",
                      help="Protex username")
    parser.add_argument("--pass",
                      action="store",
                      dest="pass",
                      help="Protex password")
    parser.add_argument('--tool-path',
                      dest='bdstool',
                      help='bdstool path',
                      type=Path)
    parser.add_argument("--url",
                      action="store",
                      dest="url",
                      help="Protex server url")
    env = vars(parser.parse_args())
    return env

if __name__ == '__main__':

    env = setup()

    # login
    login_cmd = login_cmd = '{bdstool} --server {url} --user {user} --password {pass} login'.format(**env)
    utils.run_subprocess(login_cmd)
    
    # set XED project (basically chooses which project to analyze and create a new workflow for)
    set_project_cmd = '{bdstool} new-project {project_id}'.format(**env)
    utils.run_subprocess(set_project_cmd)

    # analyze XED
    analyze_cmd = f'{env["bdstool"]} analyze --verbose --path .'
    utils.run_subprocess(analyze_cmd)

    # logout
    logout_cmd = f'{env["bdstool"]} logout'
    utils.run_subprocess(logout_cmd)

    sys.exit(0)
