#BEGIN_LEGAL
#INTEL CONFIDENTIAL
#
#Copyright (c) 2009-2010, Intel Corporation. All rights reserved.
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


import re
import os
import smtplib
import sys
import find_dir
sys.path = [ find_dir.find_dir('mbuild') ] + sys.path
import mbuild

def msg(s):
   sys.stdout.write(s  + "\n")

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
      
   servers.append('ecsmtp.hd.intel.com')
   servers.append('ecsmtp.iil.intel.com')
   return servers


def check_reply_to_env_var():
   if 'REPLYTO' in os.environ:
      return os.environ['REPLYTO']
   sender = _check_muttrc()
   if sender:
      return sender
   mbuild.die("Please either set your REPLYTO environment variable " +
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
       mbuild.msgb('email 0.0')
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
       mbuild.msgb("FROM", sender)
       mbuild.msgb("TO", recipients)
       mbuild.msgb("CC", cc_recipients)
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
    if verbose > 50:
       mbuild.msgb('email 0.5')
    msg = MIMEText(body, _subtype='plain')
    msg.add_header('Content-Disposition', 'inline')
    outer.attach(msg)
    if verbose  > 50:
       mbuild.msgb('email 1.0')
    for (real_name,attachment_name) in attachments_list:
       if verbose > 50:
          mbuild.msgb('email 2.0', real_name + " " + attachment_name      )
       if not os.path.exists(real_name):
          mbuild.die("Cannot read attachment named: " + real_name)
       fp = open(real_name,'r')
       msg = MIMEText(fp.read(), _subtype='plain')
       fp.close()
       if verbose > 50:
          mbuild.msgb('3.0')
       msg.add_header('Content-Disposition', 'attachment',
                      filename=attachment_name)
       outer.attach(msg)
    if verbose > 50:
       mbuild.msgb('4.0')
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
           mbuild.msgb("MAIL SERVER", outgoing_mail_server)
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
       mbuild.die("MAIL FAILED FOR " + str(rdict))


def mail(note,
         sender,
         recipients,
         cc_recipients=[],
         attachments=[],
         subject = '',
         verbosity = 0):
   """mail note to the to_recipient and the cc_recipient"""
   if verbosity  > 1:
      mbuild.msgb("SENDING EMAIL")
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
      mbuild.die("Sending email failed")

