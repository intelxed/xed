#BEGIN_LEGAL
#
#Copyright (c) 2021 Intel Corporation
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
from distutils.core import setup, Extension

# need a symlink called xedkit pointing to a XED kit in the current
# directory
module1 = Extension('xed',
                    # define_macros = [('XEDFOO', '1') ],
                    include_dirs = ['xedkit/include'],
                    libraries = ['xed' ],
                    library_dirs = ['xedkit/lib'],
                    sources = ['xed.c'])

setup (name = 'xed',
       version = '1.0',
       description = 'This is a XED extension package',
       ext_modules = [module1])

