#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#
#Copyright (c) 2020 Intel Corporation
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
import zmail
import os
import sys

def _getenv_phone():
    if 'SMS_PHONE' in os.environ:
        return os.environ['SMS_PHONE']
    sys.stderr.write("No phone number in SMS_PHONE env var\n")
    return None

def _send_email_gateway(message, recipients, verbosity=0):
    sender = recipients[0]
    zmail.mail([message], sender, recipients, verbosity=verbosity)

def _setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('message', help='message')
    parser.add_argument('-v', dest='verbosity', type=int, default=0,
                        help='message')
    args = parser.parse_args()
    return args

def send(message,verbosity=0):
    recipient = _getenv_phone()
    if recipient:
        _send_email_gateway(message,[recipient], verbosity=verbosity)
        return 0
    return 1

def _main(args):
    return send(args.message, args.verbosity)
    
if __name__ == '__main__':
    args = _setup()
    r = _main(args)
    sys.exit(r)
