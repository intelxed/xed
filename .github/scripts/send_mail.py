#!/usr/bin/env python3
# -*- python -*-
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
import argparse
from pathlib import Path
import smtplib
from email.mime.text import MIMEText

GITHUB_USERS_MAIL = { 
    'marjevan'  : 'maor.arjevani@intel.com',
    'kkhalail'  : 'kamal.khalaily@intel.com',
    'atal96'    : 'ady.tal@intel.com',
    'mberezal'  : 'michael.berezalsky@intel.com', }


def send(mail_from, recipients_list, subject, text,
         is_text_html=False,
         do_raise_exceptions=True):
    """ Send an email, as simple as that! UPD: ok, one caveat:
    you must run from EC Linux node, otherwise you might get "ConnectionRefusedError: [Errno 111] Connection refused"
    (The function was taken from the AVI team)
    """
    if not isinstance(recipients_list, list):
        recipients_list = [recipients_list]  # in case a single string address is passed instead of list by mistake
    print(f"-D- sending mail from '{mail_from}' to {recipients_list} with subject '{subject}'")

    # ATTN: smtp mail servers have their own standards and limits, e.g. 990 (or even 78?) chars limit per line.
    #       Now, practically, it is not (or rarely is?) an issue with plain text, because it usually has line breaks.
    #       But, in case of html text, it only has "<br>", so the WHOLE message is considered a single line by smtp.
    #       So, what happens is the body of your mail gets line breaks in random places with exclamation marks ("!").
    #       Fix: let's try to mitigate that by adding "\n" (or maybe "\r\n") before (or after?) every "<br>".
    # if is_text_html:
    #     text = text.replace("<br>", "<br>\r\n")  # no random breaks ("!"), but 2 extra breaks after every line :(
    #     text = text.replace("<br>", "\r\n")  # no random breaks ("!"), but 1 extra break after every line - better!
    #     text = text.replace("<br>", "\n")  # no random breaks ("!"), but still 1 extra break after every line :(
    #     UPD: it's not really extra break, more like a paragraph end, i.e. no real line between this and next lines
    #       Fix1: creating MIMEText with "_charset='utf-8'" magically solves the problem - no "!", no extra line breaks!
    #             It has something to do with "msg['Content-Transfer-Encoding']" header which is set to "base64"...
    try:
        msg = MIMEText(text, 'html', _charset='utf-8') if is_text_html else MIMEText(text, 'plain')
        msg['Subject'] = subject
        msg['From']    = mail_from
        msg['To']      = "; ".join(recipients_list)
        content = msg.as_string()  # as_bytes()  # works OK both ways? yes, at least for html => keep as_string() TBOTSS
        smtp = smtplib.SMTP('smtp.intel.com', 25)
        smtp.sendmail(mail_from, recipients_list, content)
        smtp.quit()
    except Exception as e:
        print(f"-E- failed to send an email to user: {e}")
        if do_raise_exceptions:
            raise

def setup():
    parser = argparse.ArgumentParser(description='send mail')

    # one and only of text option can be used (limited by mutually exclusive args group)
    text_group = parser.add_mutually_exclusive_group(required=False)
    text_group.add_argument('--text-from-file',
                        dest='text_file',
                        help='take the mail content from a file',
                        action='store', 
                        type=Path)
    text_group.add_argument('--text',
                        help='mail\'s body',
                        action='store', 
                        type=str,
                        default='')
    
    # add standard parser arguments:
    parser.add_argument('--to',
                        help='set recipients mail address',
                        action='append', 
                        default=[])
    parser.add_argument('--to-user',
                    dest='to_user',
                    help='set recipients mail address by github username',
                    action='append', 
                    default=[])
    parser.add_argument('--from',
                        help='set "from" mail address',
                        action='store', 
                        type=str,
                        default='xed.team@intel.com')
    parser.add_argument('--subject',
                        help='mail subject',
                        action='store', 
                        type=str)
    parser.add_argument('--html',
                        help='indicate whether the content is both html and text',
                        action='store_true', 
                        default=False)

    args = parser.parse_args()
    env = vars(args)
    return env


if __name__ == "__main__":
    env = setup()
    # set mail's text body
    text = env['text']
    if env['text_file']:
        env['text_file'] = env['text_file'].resolve(strict=True)
        text = env['text_file'].read_text()

    # set 'TO' list
    mail_to = env['to']
    for user in env['to_user']:
        if user not in GITHUB_USERS_MAIL:
            print(f'-E- Unknown user: {user}\n')
            print('exit...')
            exit(1)
        mail_to.append(GITHUB_USERS_MAIL[user])

    assert mail_to, "Mail recipient was not set"

    send(env['from'], env['to'], env['subject'], text, env['html'])
