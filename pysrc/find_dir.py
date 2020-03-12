#!/usr/bin/env python
#BEGIN_LEGAL
#
#Copyright (c) 2019 Intel Corporation
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

# add the right mbuild dir to the sys.path so that we can import mbuild.

import os
import sys

def find_dir(d):
    directory = os.getcwd()
    last = ''
    while directory != last:
        target_directory = os.path.join(directory,d)
        if os.path.exists(target_directory):
            return target_directory
        last = directory
        directory = os.path.split(directory)[0]
    return None

mbuild_path = find_dir('mbuild')
sys.path = [ mbuild_path ] + sys.path


