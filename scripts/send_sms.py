#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#INTEL CONFIDENTIAL
#
#Copyright (c) 2020, Intel Corporation. All rights reserved.
#
#The source code contained or described herein and all documents
#related to the source code ("Material") are owned by Intel Corporation
#or its suppliers or licensors. Title to the Material remains with
#Intel Corporation or its suppliers and licensors. The Material
#contains trade secrets and proprietary and confidential information of
#Intel or its suppliers and licensors. The Material is protected by
#worldwide copyright and trade secret laws and treaty provisions. No
#part of the Material may be used, copied, reproduced, modified,
#published, uploaded, posted, transmitted, distributed, or disclosed in
#any way without Intel's prior express written permission.
#
#No license under any patent, copyright, trade secret or other
#intellectual property right is granted to or conferred upon you by
#disclosure or delivery of the Materials, either expressly, by
#implication, inducement, estoppel or otherwise. Any license under such
#intellectual property rights must be express and approved by Intel in
#writing.
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

def _send_email_gateway(message, recipients):
    sender = recipients[0]
    zmail.mail([message], sender, recipients)

def _setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('message', help='message')
    args = parser.parse_args()
    return args

def _main(args):
    recipient = _getenv_phone()
    if recipient:
        _send_email_gateway(args.message,[recipient])
        return 0
    return 1

if __name__ == '__main__':
    args = _setup()
    r = _main(args)
    sys.exit(r)
