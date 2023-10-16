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
from pathlib import Path
from datetime import datetime
import utils
import argparse
import os

def setup():
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='Coverity CVSS/Security report argument parser')
    parser.add_argument('--auth-key',
                        dest='auth_key',
                        help='Path to Coverity authentication key file',
                        type=Path,
                        required=True)
    parser.add_argument('--user',
                        action='store',
                        dest='user',
                        help="Coverity username",
                        required=True)
    parser.add_argument('--url',
                        action='store',
                        dest='url',
                        help="Coverity url (includes prod number)",
                        required=True)
    parser.add_argument("--component",
                        action="store",
                        dest="component",
                        default='',
                        help="perform analysis on specified component only. For external branch, use CM-XED main.External")

    env = vars(parser.parse_args())
    return env


def populate_config_file(env: dict) -> str:
    """
    Populates the templated fields of the Coverity report config file

    Args:
        env (dict): environment variables e.g. username

    Returns:
        str: filled out content of the template CVSS/Security report yaml file
    """
    cov_report = Path('.github', 'configs', 'covreport.yml')
    version = datetime.now().strftime('v.%y.%m.%d')

    with open(cov_report, "r") as file:
        report_content = file.read()
    
    new_report_content = report_content.format(user=env["user"], version=version, component=env["component"], url=env["url"])

    return new_report_content


if __name__ == '__main__':

    env = setup()

    # Modify report configuration
    new_report_content = populate_config_file(env)

    os.makedirs('logs', exist_ok=True)

    # Output modified configuration file and both reports in the logs directory
    new_report_config = Path('logs', 'new_report.yml')
    cvss_report = Path('logs', 'cvss_report.pdf')
    security_report = Path('logs', 'security_report.pdf')

    if new_report_config.exists(): os.remove(new_report_config)
    if security_report.exists()  : os.remove(security_report)
    if cvss_report.exists()      : os.remove(cvss_report)

    with open(new_report_config, "w") as file:
        file.write(new_report_content)

    # generate Coverity CVSS report
    cvss_cmd = f'cov-generate-cvss-report {new_report_config} --output {cvss_report} --report --auth-key-file {env["auth_key"]}'
    utils.run_subprocess(cvss_cmd)

    assert cvss_report.exists(), 'CVSS report was not properly generated'

    # generate Coverity Security report
    security_cmd = f'cov-generate-security-report {new_report_config} --output {security_report} --auth-key-file {env["auth_key"]}'
    retval, lines = utils.run_subprocess(security_cmd)

    assert security_report.exists(), 'Security report was not properly generated'
    sys.exit(retval)
