#==============================================================================
# hello_world.py
# Simple "hello world" example application using the exompp library to send
# data to Exosite's Data Platform via XMPP chat.
#==============================================================================
## Tested with python 2.6.5
##
## Copyright (c) 2010, Exosite LLC
## All rights reserved.
##

import sys
import time

from exompp.xmppchat import *

#===============================================================================
def main():
#===============================================================================
  # Setup our connection and client interface key values
  ## NOTE: the ENTERYOURXMPPACCOUNTNAMEHERE should be something like user@xmppserverdomain.com -> a google email account works just fine
  ## NOTE: the ENTERYOURXMPPACCOUNTPASSWORDHERE should be the password associated with ENTERYOURXMPPACCOUNTNAMEHERE -> a google email account password works just fine
  connection = {'exosite_bot':'commander@m2.exosite.com',
                'user_id':'ENTERYOURXMPPACCOUNTNAMEHERE',
                'password':'ENTERYOURXMPPACCOUNTPASSWORDHERE'}
  
  # Setup our Client Interface Key (CIK)
  ## NOTE: PUTA40CHARACTERCIKHERE should be a valid Exosite Client Interface Key
  ## The easiest way to get a CIK the first time is probably from Exosite Portals https://portals.exosite.com -> +Add Device
  cik = 'PUTA40CHARACTERCIKHERE'
  
  publish = PublishToExosite(connection)
  publish.start()
  publish.addData(cik, "hello", "hello world!")  #client interface key, dataport alias, dataport value
  publish.stop()
  
  print "\r\n\r\nSent \"Hello World!\" to your Portal!  View at portals.exosite.com"
  


#===============================================================================
if __name__ == '__main__':
  sys.exit(main())
