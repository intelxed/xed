# BEGIN_LEGAL
#
# Copyright (c) 2022 Intel Corporation
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
# END_LEGAL

import os
import sys
from datetime import datetime


class JobStatus:
  """record job status (success, failure and (retval,job) list"""

  def __init__(self):
    self.jobs = 0
    self.fails = 0
    self.successes = 0
    self.start_time = datetime.now()
    self.commands = []  # list of  tuples of (retval, command)

  def __str__(self):
    s = [f"JOBS: {self.jobs}, SUCCESSES: {self.successes}, FAILS: {self.fails}"]

    for index, (r, c) in enumerate(self.commands):
      s.append(f"{index}: status: {r} cmd: {c}")
    return os.linesep.join(s) + os.linesep

  def print_fails(self):
    """prints all failed tests separately"""
    s = ["------------------[FAILED TESTS]------------------"]

    for index, (r, c) in enumerate(self.commands):
      if r != 0:
        s.append(f"{index}: status: {r} cmd: {c}")

    s.append("--------------------------------------------------\n")
    return os.linesep.join(s)

  def addjob(self, retval, cmd):
    """adds a new job to the list of commands"""
    self.jobs += 1
    self.commands.append((retval, cmd))

  def fail(self, retval, cmd):
    """adds a new job to the list of commands and marks it as failed"""
    self.fails += 1
    self.addjob(retval, cmd)

  def success(self, retval, cmd):
    """adds a new job to the list of commands and marks it as successful"""
    self.successes += 1
    self.addjob(retval, cmd)

  def merge(self, status):
    """merge status object"""
    self.jobs += status.jobs
    self.fails += status.fails
    self.successes += status.successes
    self.commands.extend(status.commands)

  def pass_rate_fraction(self):
    """calculate success rate"""
    return f'{self.successes}/{self.jobs}'

  def print_report(self):
    """Print tests summary and return exit status equal to the number of failures"""
    print(f'{"-"*40}\n' + str(self))

    if self.fails:
      print(self.print_fails())

    print("[FINAL STATUS] {}\n".format(
        "PASS" if not self.fails else "FAIL"), flush=True)
    return self.fails
