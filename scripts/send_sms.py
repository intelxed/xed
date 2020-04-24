#!/usr/bin/env python3
# -*- python -*-
#BEGIN_LEGAL
#INTEL CONFIDENTIAL
#
#Copyright (c) 2013, Intel Corporation. All rights reserved.
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
import itertools
import zmail
import os
import sys


class Recipient(object):
    def __init__(self, phone, service='wintel'):
        self.phone = phone
        self.service = service

def _getenv_phone():
    if 'SMS_PHONE' in os.environ:
      return os.environ['SMS_PHONE']
    sys.stderr.write("No phone number in SMS_PHONE env var\n")
    sys.exit(1)


phone_book = {
   'mark'       : Recipient(_getenv_phone(),'att'),
   'mjc'        : Recipient(_getenv_phone(),'att'),
   'mjcharne'   : Recipient(_getenv_phone(),'att'),
   }


def _send_att(message, recipients, sender, userid):
    """
    Sends sms through AT&T.

    Simply sends email to the 10 digit phone number followed by @txt.att.net
    Example: xxxxxxxxxx@txt.att.net
    """
    recipients = ['%s@txt.att.net' % phone for phone in recipients]
    sender = '%s@txt.att.net' % sender
    zmail.mail([message], sender, recipients)


def send(message, recipients, sender=None, userid='automated-script'):
    """
    Sends SMS message to a list of recipients.

    :param message: sms message
    :param recipients: recipients' phone number list
    :param sender: sender's phone number
    :param userid: unused.
    :return:
    """

    def _name_to_recipient(name):
        return phone_book.get(name, Recipient(name))

    def _recipient_service(recipient):
        return recipient.service

    recipients = list(map(_name_to_recipient, recipients))

    # by default, the sender is the (first) recipient
    if not sender:
        sender = recipients[0].phone
    else:
        sender = _name_to_recipient(sender).phone

    send_function_map = {
                            'att'    : _send_att,
                        }
    recipients_by_service = itertools.groupby(recipients, _recipient_service)

    for (service,recipients_in_group) in recipients_by_service:
        phones = [recipient.phone for recipient in recipients_in_group]
        send_func = send_function_map[service]
        send_func(message, phones, sender, userid)


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--to', action='append', required=True, type=str,
                        help='recipient phone number or name',
                        metavar='phone_num|name')
    parser.add_argument('-s', '--sender', type=str,
                        help='sender phone number or name', metavar='phone_num|name',
                        default=None)
    parser.add_argument('-m', '--msg', required=True, type=str,
                        help='sms message body')
    args = parser.parse_args()
    return args



def main(args):
    send(args.msg, recipients=args.to, sender=args.sender)

if __name__ == '__main__':
    args = setup()
    main(args)
