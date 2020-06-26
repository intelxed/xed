#!/usr/bin/env python3
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


import re
import os
import smtplib
import sys
import argparse

def msg(s):
   sys.stdout.write(s  + "\n")
def msgb(s, t=''):
   sys.stdout.write('[{}] {}\n'.format(s, t))
def die(s):
   msgb('FAILING',s)
   sys.exit(1)
def warn(m):
   msg("[WARNING] " + m)

############################################################################
# Stuff for sending mail or just a making an note file


def _check_muttrc():
   if 'HOME' in os.environ:
      home = os.environ['HOME']
      muttrc = os.path.join(home,'.muttrc')
      if os.path.exists(muttrc):
         f = open(muttrc,"r")
         lines = f.readlines()
         f.close()
         for line in lines:
            g= re.search(r'set[ ]+from[ ]*[=][ ]*(?P<email>[A-Za-z0-9_.@]+)',
                         line)
            if g:
               sender = g.group('email')
               return sender
         warn("Cannot find \'from\' setting in .muttrc." +
              " Please set it to your email address.")
         return None
      else:
         warn("Cannot find " + muttrc + " file where you " +
              "should set your email address.")
         return None
   warn("Cannot find your HOME environment variable. " +
        "Cannot look for your .muttrc file.")
   return None
            
def check_smtp_host_env_var():
   servers = []
   if 'SMTP_HOST' in os.environ:
      servers.append(os.environ['SMTP_HOST'])
   else:
       servers.append('ecsmtp.hd.intel.com')
       servers.append('ecsmtp.iil.intel.com')
   return servers


def check_reply_to_env_var():
   if 'REPLYTO' in os.environ:
      return os.environ['REPLYTO']
   sender = _check_muttrc()
   if sender:
      return sender
   die("Please either set your REPLYTO environment variable " +
              "to your @intel.com\n " +
              "email address or have a\n\tset " +
              "from=YOUR-EMAIL-ADDRESS@intel.com\n"  +
              "in your $HOME/.muttrc.\n\n")
def find_sender():
    return check_reply_to_env_var()

############################################################

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def _send_email(recipients_list,
                sender,
                subject,
                body,
                attachments_list = [],
                cc_recipients_list = [],
                verbose = 0):
   
    """Send the body string and any attachments to the list of
    recipients. The attachments_list is a list of tuples (real_name,
    attachment_name)"""
    
    if verbose>50:
       msgb('email 0.0')
    all_recipients = recipients_list + cc_recipients_list
    #recipients = ", ".join(all_recipients)
    recipients = ", ".join(recipients_list)
    cc_recipients = ", ".join(cc_recipients_list)
    # Create the enclosing (outer) message
    outer = MIMEMultipart()
    outer['Subject'] = subject
    outer['To'] = recipients
    outer['Cc'] = cc_recipients
    outer['From'] = sender
    if verbose:
       msgb("FROM", sender)
       msgb("TO", recipients)
       msgb("CC", cc_recipients)
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
    if verbose > 50:
       msgb('email 0.5')
    msg = MIMEText(body, _subtype='plain')
    msg.add_header('Content-Disposition', 'inline')
    outer.attach(msg)
    if verbose  > 50:
       msgb('email 1.0')
    for (real_name,attachment_name) in attachments_list:
       if verbose > 50:
          msgb('email 2.0', real_name + " " + attachment_name      )
       if not os.path.exists(real_name):
          die("Cannot read attachment named: " + real_name)
       fp = open(real_name,'r')
       msg = MIMEText(fp.read(), _subtype='plain')
       fp.close()
       if verbose > 50:
          msgb('3.0')
       msg.add_header('Content-Disposition', 'attachment',
                      filename=attachment_name)
       outer.attach(msg)
    if verbose > 50:
       msgb('4.0')
    # Now send or store the message
    composed = outer.as_string()
    s = smtplib.SMTP()
    if verbose > 50:
        s.set_debuglevel(1)

    # try connecting to a server from the list
    mail_server_list = check_smtp_host_env_var()
    connected = False
    for outgoing_mail_server in mail_server_list:
        try:
           msgb("MAIL SERVER", outgoing_mail_server)
           s.connect(outgoing_mail_server)
           connected = True
           break
        except:
           continue

    # last resort try the default
    if not connected:
        s.connect()
    rdict = s.sendmail(sender, all_recipients, composed)
    s.quit()
    if rdict and len(rdict) > 0:
       die("MAIL FAILED FOR " + str(rdict))


def mail(note,
         sender,
         recipients,
         cc_recipients=[],
         attachments=[],
         subject = '',
         verbosity = 0):
   """mail note to the to_recipient and the cc_recipient"""
   if verbosity  > 1:
      msgb("SENDING EMAIL")
   note = [x.rstrip() for x in note]
   body = '\n'.join(note)
   att = []
   for  attachment in attachments:
      att.append( (attachment, os.path.basename(attachment)) )
   try:
      _send_email(recipients,
                  sender,
                  subject,
                  body,
                  att,
                  cc_recipients,
                  verbosity)
   except:
      die("Sending email failed")
   return 0

def getargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", 
                        dest="message",
                        default=[],
                        action="append",
                        help="Message to send")
    parser.add_argument("-f", 
                        dest="sender",
                        help="Sender")
    parser.add_argument("-t", 
                        dest="recipients",
                        action="append",
                        default=[],
                        help="Recipient")
    parser.add_argument("-v", 
                        dest="verbosity",
                        default=0,
                        type=int,
                        help="Verbosity")
    args = parser.parse_args()
    return args

def main():
    args = getargs()
    r = mail(args.message, args.sender, args.recipients,
             verbosity=args.verbosity)
    return r

if __name__ == '__main__':
    r = main()
    sys.exit(r)
