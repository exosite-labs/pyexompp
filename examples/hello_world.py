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
  ## setup our connection and client interface key values
  connection = {'exosite_bot':'commander@m2.exosite.com','user_id':'hansandroid@m2.exosite.com','password':'spandr01d'}
  cik = '9096951de12835f8c29212b08af95b05e42625de'
  
  publish = PublishToExosite(connection)
  publish.start()
  publish.addData(cik, "hello", "hello world!")  #client interface key, dataport alias, dataport value
  publish.stop()
  
  print "\r\n\r\nSent \"Hello World!\" to your Portal!  View at one.exosite.com"
  


#===============================================================================
if __name__ == '__main__':
  sys.exit(main())

