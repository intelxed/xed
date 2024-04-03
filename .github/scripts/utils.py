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

import argparse
from collections import defaultdict
import itertools
from multiprocessing import Pool, cpu_count
from os import stat
from pathlib import Path
import platform
import shutil
import subprocess
from typing import List, Optional, Tuple
from job_status import *
from gen_matrix import get_latest_version

######### Globals #########
GCC = 'gcc'
GNU = 'gnu'
MSVS = 'msvs'
CLANG = 'clang'
SUPPORTED_COMPILERS = [GCC, GNU, MSVS, CLANG]
KIT_PREFIX_PATT = 'xed-test-kit-'  # prefix name of the test kit directories


########## Setup ###########
def get_compiler_build_flags(env):
    """
    Generates build string that specifies compiler and version
    Use this string later as arguments for XED builder scripts
    """
    os_ver = platform.system()
    compiler = env['compiler']
    version = env['compiler_version'] if env['compiler_version'] else get_latest_version(compiler, os_ver)

    if compiler == MSVS:
        # Let mbuild find the needed toolchain
        build_args = f'--compiler=ms --msvs-version={version}'
    
    elif compiler in [GNU, GCC]:
        tool = f'/usr/local/{GCC}-{version}/bin/'
        build_args = f'--toolchain={tool} '
        build_args += f'--compiler={GNU} --{GCC}-version={version}'

    elif compiler in [CLANG]:
        if os_ver == "Linux":
            tool = f'/usr/local/{compiler}-{version}/bin/'
        elif os_ver == "Windows":
            tool = f'C:\\tools\\LLVM_{version}\\bin\\'
        assert tool, 'Could not find CLANG path'
        build_args = f'--toolchain={tool} '
        build_args += f'--compiler={compiler}'

    return build_args


def setup():
    """Define the common parser arguments"""
    parser = argparse.ArgumentParser(
        description='setup sanity for xed-group repository')
    parser.add_argument('-j',
                        dest='num_of_builds',
                        help='number of parallel builds. Default = #of cores',
                        type=int,
                      default=int(cpu_count()/2))  # == Number Of Cores
    parser.add_argument('--compiler',
                        dest='compiler',
                        help='set compiler',
                        type=str,
                        default='',
                        choices=SUPPORTED_COMPILERS)
    parser.add_argument('--version',
                        dest='compiler_version',
                        help='set compiler version. Default is the latest supported version',
                        type=str,
                        default='')
    parser.add_argument('--extra-build-args',
                        dest='extra_build_args',
                        type=str,
                        default='')
    return parser
    

def process_args(parser):
    """Parse input arguments and return env dict"""
    args = parser.parse_args()
    env = vars(args)
    env['compiler_flags'] = ''
    if env['compiler']:
        env['compiler_flags'] = get_compiler_build_flags(env)

    env['pyver'], env['pycmd'] = ('3.x', 'python3')
    return env


##### Run process #######
def ensure_string(x):
    """handle non unicode output"""
    if isinstance(x, bytes):
        try:
            return x.decode('utf-8')
        except:
            return ''
    return x


def run_subprocess(cmd, **kwargs):
    """front end to running subprocess"""
    sub = subprocess.Popen(cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           **kwargs)
    lines = sub.stdout.readlines()
    lines = [ensure_string(x) for x in lines]
    sub.wait()
    return sub.returncode, lines


def run_worker(cmd_in: str, cwd: Optional[str] = None,
               required: bool = False) -> Tuple[JobStatus, str]:
    """
  run cmd_in as a single subprocess
  Arguments:
      cmd_in: string of commands to execute. use ';' as a serialized multi commands separator
      cwd:    process's correct working directory
  Returns:
      Tuple of (JabStatus object, run output)
  """
    res = []
    if ';' in cmd_in:
        # execute several commands serially
        commands = cmd_in.split(';')
    else:
        commands = [cmd_in]

    for c in commands:
        status = JobStatus()
        print(f'[RUNNING] {c}', flush=True)
        retval, output = run_subprocess(c, cwd=cwd)
        if retval == 0:
            status.success(retval, c)
        else:
            status.fail(retval, c)
            if required:
                print(''.join(output))
                print(f"[FAIL] retval = {retval}\nExit...")
                sys.exit(status.print_report())
        res.append((status, output))

    return res


def run_multiprocess(env, commands):
    """
  run commands in parallel
  return a list of (JabStatus object, run output) tuple 
  """
    CORES = env['num_of_builds']
    if env['extra_build_args']:
        print(f'Build with extra flags: {env["extra_build_args"]}')
    if env['compiler_flags']:
        print(f'Compiler build flags:\n {env["compiler_flags"].split()}\n')
    print(f'Running {CORES} parallel builds...', flush=True)
    with Pool(CORES) as pool:
        res = pool.map(run_worker, commands)
        pool.close()  # Call the garbage collector
        pool.join()

    # res can include list within a list - convert to a flat list
    res = list(itertools.chain(*res))
    commands_len = len(list(itertools.chain(*[c.split(';') for c in commands])))
    # check that we received status for all commands
    assert len(res) == commands_len
    return res


def report_multiprocess(res_mp):
    status = JobStatus()
    # build status object and print cmd output for failed commands
    for run_status, run_output in res_mp:
        status.merge(run_status)
        if run_status.fails:
            print(f'[BUILD FAILED] {run_status.commands[0][1]}')
            print(''.join(run_output), sep='')

    exit_status = status.print_report()
    return exit_status


########## Generate build commands ##########
def gen_build_cmd(env, builder, kind, build_dir, host, flags):
    """Generate XED build command using a given python builder script"""
    cmd = f'{env["pycmd"]} {builder} '
    if kind:
        cmd += f'--kind={kind} '
    cmd += f'--build-dir={build_dir} host_cpu={host} {flags} '
    cmd += '{extra_build_args} {compiler_flags}'.format(**env)
    return cmd


def gen_enc2test_cmd(env, builder, kits_dir, kind, flags='', enc2ref: Path=''):
    """Generate enc2 build+test to validate enc-dec of all the kind's instructions"""
    commands = []
    host = 'x86-64'
    build_dir = Path(kits_dir, f'obj-{kind}-{host}-static-enc2test')
    enc2comp = Path(__file__).parent.joinpath('enc2compare.py')
    cmd = gen_build_cmd(env, builder, kind, build_dir, host,
                        '--enc2-test-checked ' + flags)
    commands.append(cmd)

    output = f'enc2tester-{kind}'
    enc2tester = Path(build_dir, 'enc2-m64-a64', 'enc2tester-enc2-m64-a64')
    cmd = f'{enc2tester} --reps 1 --main --gnuasm > {output}.c'
    commands.append(cmd)

    # compare enc2 unsupported ISA-SETs (make sure enc2 didn't break)
    cmd = f'{env["pycmd"]} {enc2comp} --build-dir={build_dir} --verbose'
    if enc2ref:
        # replace the script's default enc2ref path (enc2unsupported_ref.json)
        # which contains all XED instructions unsupported by enc2
        cmd += f' --ref-path {enc2ref}'
    commands.append(cmd)

    if platform.system() == 'Linux':  # TBD - Add Windows and custom gcc version support
        cmd = f'gcc {output}.c -o {output}.out'
        commands.append(cmd)

        cmd = f'{build_dir}/wkit/bin/xed -i {output}.out > all.dis'
        commands.append(cmd)
    return '; '.join(commands)


def gen_gen_enc_layer_cmd(features: list, build_cmd: str, kit_name: str, script_path: Path) -> str:
    """Generate gen_enc_layer script tests; groups the build cmd with the test commands since they're dependent"""
    commands = [build_cmd]
    for feature in features:
        gen_enc_cmd = f'python3 {script_path} --feature {feature} --xed-kit {kit_name} --json'
        commands.append(gen_enc_cmd)
    return '; '.join(commands)

############# extra #############

def clean_test_kits(kits_dir: Path):
    """clean the test build kits"""
    if not kits_dir.exists():
        kits_dir.mkdir()
        return

    test_kits = kits_dir.glob(f'{KIT_PREFIX_PATT}*')
    for kit in test_kits:
        try:
            shutil.rmtree(kit.resolve(strict=True))
        except:
            pass  # no need to stop if cleaning failed
