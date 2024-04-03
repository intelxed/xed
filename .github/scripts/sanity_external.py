#BEGIN_LEGAL
#
#Copyright (c) 2024 Intel Corporation
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
""""XED External Sanity Check"""
from pathlib import Path
import platform
import sys
import utils


def main(env):
    cwd = Path.cwd().resolve()
    # clean test dirs
    kits_dir = Path(cwd, 'kits')
    print('Cleaning old sanity kits...\n', flush=True)
    utils.clean_test_kits(kits_dir)

    # Prepare |
    # Generate build commands
    commands: list = []
    xed_builder: str = 'mfile.py'
    secure_build: str = '--security-level=3'
    flags: str = 'test ' + secure_build
    # {32b,64b} x {shared,dynamic} link
    for host in ['ia32', 'x86-64']:
        link_options = [('static', ''), ('dynamic', ' --shared')]
        if env['compiler'] == utils.CLANG and platform.system() == 'Windows':
            # TODO - Fix clang dynamic build on windows
            link_options = [('static', '')]
        for linkkind, link in link_options:
            dir = f'obj-general-{env["pyver"]}-{host}-{linkkind}'
            build_dir = Path(kits_dir, utils.KIT_PREFIX_PATT + dir)
            cmd = utils.gen_build_cmd(env, xed_builder, '', build_dir, host, flags + link)
            commands.append(cmd)

    # do a build with asserts enabled
    host64 = 'x86-64'
    dir = f'obj-assert-{env["pyver"]}-{host64}'
    build_dir = Path(kits_dir, utils.KIT_PREFIX_PATT + dir)
    cmd = utils.gen_build_cmd(env, xed_builder, '', build_dir, host64, flags + ' --assert')
    commands.append(cmd)

    # No-future build (For no-APX validation)
    dir = f'obj-no-future-{env["pyver"]}-{host64}'
    build_dir = Path(kits_dir, utils.KIT_PREFIX_PATT + dir)
    cmd = utils.gen_build_cmd(env, xed_builder, '', build_dir, host64, flags + ' --no-future --assert')
    commands.append(cmd)

    # Test opt=3 build
    dir = f'obj-opt3-{env["pyver"]}-{host64}'
    build_dir = Path(kits_dir, utils.KIT_PREFIX_PATT + dir)
    cmd = utils.gen_build_cmd(env, xed_builder, '', build_dir, host64, flags + ' --opt=3')
    commands.append(cmd)

    # enc2test - test encode-decode path of all instructions
    cmd_enc2test_ext = utils.gen_enc2test_cmd(
        env, xed_builder, kits_dir, '', flags='test ' + secure_build)
    commands = [cmd_enc2test_ext] + commands  # enc2test is a long test, run it first

    # run
    res_mp = utils.run_multiprocess(env, commands)
    exit_status = utils.report_multiprocess(res_mp)

    # Finalize
    if exit_status == 0:
        print(f'[Validation PASSED] Cleaning test kits...\n', flush=True)
        utils.clean_test_kits(kits_dir)

    return exit_status


if __name__ == "__main__":
    parser = utils.setup()
    env = utils.process_args(parser)
    exit_status = main(env)
    sys.exit(exit_status)
