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

import platform
import re
import sys
import argparse
import json
from typing import List
import utils
import shutil
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

OS_COMPILER_MAP = {'Linux': utils.GCC, 'Windows': utils.MSVS}
OS_VER = platform.system()

def set_stream(env : dict):
    """
    sets Coverity stream according to the operating system
    """
    os = list(OS_COMPILER_MAP.keys())   # list of possible operating systems

    assert OS_VER in os, f'Unsupported os, use one of {os}'

    if not env['compiler']:             # defaultly pick corresponding compiler
        env['compiler'] = OS_COMPILER_MAP[OS_VER]
    
    extern = ' external' if env['is_external'] else ''

    env['stream'] = f'{env["project"]} - {OS_VER}{extern}'


def locate_cov_path() -> str:
    """returns coverity path for Linux lab machines. Windows machine are able to locate it by themselves."""
    cov_path = ''
    if OS_VER == 'Linux':
        hostname_cmd = 'hostname'
        res = utils.run_worker(hostname_cmd)
        assert res[0][1][0], 'hostname command did not run successfully' # result should be [(job status obj, [MACHINE_NAME])]
        if res[0][1][0].startswith('bit'):
            cov_path = '/opt/Coverity/bin/'
    return cov_path


def process_raw_issue(raw_issues, fields) -> List[dict]:
    """
    Processes the list of raw issues into a readable form, converting each issue to a single dictionary

    Args:
        raw_issues (list): a list of lists of dicts, each element is: [{key: "IMPACT", value: "High"}, {key: ...}]
        fields (list): list of important fields
    """    
    issues = []
    for i in range(len(raw_issues)):
        issue = {}  # converts an issue into a dictionary with the given fields as keys
        for j in range(len(fields)):
            issue[fields[j]] = raw_issues[i][j]["value"]
        issues.append(issue)
    
    return issues   


def get_issues(env, snapshot_id) -> List[dict]:
    """
    Uses Web API in order to retrieve all issues from the given snapshot from Coverity Connect Server

    Args:
        env: environment variables e.g. project name and max issues
        snapshot_id: the ID of the snapshot to retrieve the issues from

    Returns:
        list of dictionaries, each dictionary corresponding to an issue, where the fields are the keys
    """
    fields = ["cid","displayImpact","displayType","classification","severity"]
    # match for project name
    matchers = '"matchers": [ { "class": "Project","name": "'+ env['project']+ '", "type": "nameMatcher" } ]'
    # retrieve the specified columns per issue
    columns = '"columns": ["cid","displayImpact","displayType","classification","severity"]'
    filters = '"filters":' + '[ {' + '"columnKey": "project","matchMode": "oneOrMoreMatch",' + matchers + '} ]'
    # retrieve issues for the specified snapshot
    snapshot = '"snapshotScope":{"show":{"scope":'+ str(snapshot_id) + '}}'
    payload = '{' + filters + ',' + snapshot + ',' + columns + '}'
    # make request for json data
    cc_headers = {'Accept':'application/json', 'Content-Type':'application/json'}

    with open(env['auth_key']) as auth_key: # authentication via authentication keys instead of user name and pass
        data = json.load(auth_key)
        user_name = data['username']
        user_pass = data['key']

    issue_view = '/api/v2/issues/search?includeColumnLabels=false&locale=en_us&offset=0&queryType=bysnapshot&rowCount='+str(env['max_issues'])+'&sortOrder=asc'
    rp = requests.post(env['url'] + issue_view, auth=HTTPBasicAuth(user_name,user_pass),data=payload, headers=cc_headers)
    raw_issues =  rp.json()["rows"]

    print("Retreiving " + str(len(raw_issues)) + " issues from project:" + env['project'])

    issues = process_raw_issue(raw_issues, fields)  # process the issues into an easily readable form

    return issues


def filter_issues(issues) -> List[dict]:
    """
    Filters the issues by keeping real issues (e.g. no false-positivies or intentional)

    Args:
        issues:  list of dictionaries, each dictionary corresponding to an issue, where the fields are the keys
    
    Returns:
        filtered list of dictionaries, each dictionary corresponding to an issue, where the fields are the keys
    """    
    real_issues = [issue for issue in issues if issue['classification'] not in ['False Positive', 'Intentional']]
    print(f'Number of issues is: {len(real_issues)}')
    return real_issues


def filter_insignificant_issues(issues) -> List[dict]:  # this is currently not in use
    """
    Filters the issues by keeping high impact/severity ones

    Args:
        issues:  list of dictionaries, each dictionary corresponding to an issue, where the fields are the keys
    
    Returns:
        filtered list of dictionaries, each dictionary corresponding to an issue, where the fields are the keys
    """    
    significant_issues = []
    for issue in issues:
        if issue['classification'] in ['False Positive', 'Intentional']:
            continue
        if issue['severity'] in ['Major']:      # prioritize triaged severe issues
            significant_issues.append(issue)
        elif issue['severity'] in ['Unspecified'] and issue['displayImpact'] in ['High']:
            significant_issues.append(issue)   # untriaged high/critical impact issues
    print(f'Number of severe or high impact issues is: {len(significant_issues)}')
    return significant_issues


def print_issue(issue):
    """prints the type, impact and severity of the issue in an aligned fashion"""
    print(f'ISSUE: {issue["displayType"]:<20}, IMPACT: {issue["displayImpact"]:<10}, SEVERITY: {issue["severity"]:<10}')


def get_snapshot_id(commit_res) -> str:
    """
    processes the return data from the coverity commit command and returns the snapshot id

    Args:
        commit_res (list): a list where the first element is a tuple: (job status data, commit data [list])
        Data about snapshot id can be retrieved from second to last element in commit data list
    """
    assert commit_res[0][1][-2]                                     # validate commit result structure
    snapshot_data = commit_res[0][1][-2]
    assert re.match("^New snapshot ID \d+ added", snapshot_data)    # validate snapshot data structure
    return re.search("\d+", snapshot_data)[0]


def setup():
    """This function sets up the script env according to cmd line knobs."""
    parser = argparse.ArgumentParser(description='Coverity scan argument parser')
    parser.add_argument("--project",
                        action="store",
                        dest="project",
                        default="XED main",
                        help="Coverity project name")
    parser.add_argument('--compiler',
                        dest='compiler',
                        help='set compiler, default depends on os',
                        type=str,
                        choices=[utils.GCC, utils.MSVS])
    parser.add_argument('--version',
                        dest='compiler_version',
                        help='set compiler version. Default is the latest supported version',
                        type=str,
                        default='')
    parser.add_argument('--auth-key',
                        dest='auth_key',
                        help='Path to Coverity authentication key file',
                        type=Path,
                        default='')
    parser.add_argument("--url",
                        action="store",
                        dest="url",
                        required=True,
                        help="Coverity server url")
    parser.add_argument("--idir",
                        action="store",
                        dest="idir",
                        type=Path,
                        default=Path('logs', 'coverity'),
                        help="path for intermediate directory, to store the coverity log files")
    parser.add_argument("--max-issues",
                        action="store",
                        dest="max_issues",
                        default=2000,
                        help="maximum issues to be retrieved from Coverity Server")
    parser.add_argument("--external",
                        action="store_true",
                        dest="is_external",
                        help="perform analysis on external branch")
    env = vars(parser.parse_args())
    return env


if __name__ == '__main__':

    env = setup()
    
    set_stream(env)     # choose stream according to os
    cov_path = Path(locate_cov_path())

    # we don't have to run cov-configure --<COMPILER> command, as it only needs to be performed once
    # and we requested from AVI team to run it as part of the Coverity installation process

    # clean previous Coverity logs
    if env["idir"].exists():
        shutil.rmtree(env["idir"])

    # Capturing stage; showing Coverity what happens when building the project
    extra_build_cmd = utils.get_compiler_build_flags(env)
    cov_build_cmd = f'{cov_path.joinpath("cov-build")} --dir {env["idir"]} python3 mfile.py test clean {extra_build_cmd}'
    utils.run_worker(cov_build_cmd)

    # performing coverity analysis on the code
    cov_analyze_cmd = f'{cov_path.joinpath("cov-analyze")} --dir {env["idir"]} --concurrency --security --rule --enable-constraint-fpp --enable-fnptr --enable-virtual'
    utils.run_worker(cov_analyze_cmd)

    # uploading the defects to coverity connect server
    cov_commit_cmd = f'{cov_path.joinpath("cov-commit-defects")} --dir {env["idir"]} --stream "{env["stream"]}" --url {env["url"]} --auth-key-file {env["auth_key"]}'
    res = utils.run_worker(cov_commit_cmd)
    snapshot_id = get_snapshot_id(res)
    
    issues = get_issues(env, snapshot_id)        # retrieve the issues from coverity server by snapshot id
    significant_issues = filter_issues(issues)   # filters the issues by impact and severity
    
    print('printing possible issues from Coverity Server...')
    for issue in significant_issues:
        print_issue(issue)
    
    # pours the number of important issues into file for automation
    with open(Path(env['idir'], OS_VER + '_cov_issue_sum.txt'), 'w') as f:
        f.write(f'{len(significant_issues)} issues detected.')

    sys.exit(0)
