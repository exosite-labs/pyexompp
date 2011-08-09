#==============================================================================
# xmppchat.py
# Implements XMPP chat class and buffering class for using XMPP chat to send
# data to Exosite's Data Platform.
#==============================================================================
## Tested with python 2.6.5
##
## Copyright (c) 2010, Exosite LLC
## All rights reserved.
##


"""
Functions and classes that support the Exosite XMPP Chat interface.
"""

import sys
import time
import threading
import xmpp

global devices
global datasources
global connection
global options
global threads_running
global outputBox


kill_threads = False

#===============================================================================
class PublishToExosite ( threading.Thread ):
#===============================================================================
#-------------------------------------------------------------------------------
  def __init__ ( self, connection = {'user_id':'', 'password':'', 'exosite_bot':''}):
    threading.Thread.__init__ ( self )
    self.ringHead = 0
    self.ringTail = 0
    self.ringItems = 0
    self.ringSize = 256
    self.ring = {}
    self.exompp = Exompp(connection)
    ## try to connect to Exosite
    if -1 == self.exompp.connect():
      print "Could not connect to Exosite - check your server settings"
      return -1
    self.datasources = {}

#-------------------------------------------------------------------------------
  def stop ( self ):
    global kill_threads
    kill_threads = True

#-------------------------------------------------------------------------------
  def addData ( self, device_cik, resource, value ):
    if self.ringItems + 1 > self.ringSize:
      #we just overran our buffer.  means we are getting data faster than we
      #can feed it to Exosite.  
      #wipe the buffer and just start doing the best we can with new data
      print "Warning - rx'ing data faster than publishing, wiping buffers."
      self.ringItems = 0
      self.ringHead = 0
      self.ringTail = 0
    # write values into buffer
    self.ring[self.ringHead] = {'device_cik':device_cik,'res_name':resource,'res_value':value}
    self.ringItems += 1
    if self.ringHead + 1 > self.ringSize:
      #wrap head
      self.ringHead = 0
    else: self.ringHead += 1

#-------------------------------------------------------------------------------
  def run ( self ):
    global kill_threads
    lastcik = ''
    lastringsize = 0
    message_output = True
    print "Buffering started..."
    while False == kill_threads:
      if self.ringItems > 0:
        device_cik = self.ring[self.ringTail]['device_cik']
        try:
          self.datasources[device_cik]
        except:
          self.datasources[device_cik] = self.exompp.listdatasources(device_cik)
        res_name = self.ring[self.ringTail]['res_name']
        res_value = self.ring[self.ringTail]['res_value']
        if self.ringTail + 1 > self.ringSize:
          #wrap tail
          self.ringTail = 0
        else: self.ringTail += 1
        # note interlocked vulnerability here - TODO figure out python
        # interlocked calls/mutexes
        if self.ringItems > 0: #just in case we overflowed in the meantime
          self.ringItems -= 1
        #set up device channel
        if lastcik != device_cik: 
          lastcik = device_cik
          if -1 == self.exompp.setcik(device_cik):
            message_output = True
            print "Failed to set CIK %s" % device_cik
            lastcik = ''
            continue
        #find resource number from resource name
        try:
          res_number = self.datasources[device_cik][res_name]
        except:
          message_output = True
          print "No datasource named %s, creating..." % res_name
          res_number = 0
          try: 
            for a,b in self.datasources[device_cik].iteritems():
              if int(b) > int(res_number): res_number = int(b)
            res_number += 1
          except:
            res_number = 1
          if -1 == self.exompp.createdatasource(res_name,res_number):
            print "Data source problem (%s) - check limits, check name & resource # pairing" % res_name
            continue
          else:
            self.datasources[device_cik] = self.exompp.listdatasources(device_cik)
        #write nfo. if write fails, try re-sending cik next go-around
        if -1 == self.exompp.write(res_number, res_value):
          message_output = True
          lastcik=''
          continue
        else: 
          #all of this is just to create a buffer size indicator on stdout
          if True == message_output:
            print "======================"
            sys.stdout.write('BUFFER: ')
            message_output = False
          currentringitems = self.ringItems
          if lastringsize != currentringitems:
            bufstring = ''
            rewstring = ''
            if lastringsize < currentringitems:
              sizediff = currentringitems - lastringsize
              while sizediff > 0:
                bufstring += '*'
                sizediff -= 1
              sys.stdout.write(bufstring)
            else:
              sizediff = lastringsize - currentringitems
              while sizediff > 0:
                bufstring += ' '
                rewstring += '\x08'
                sizediff -= 1
              sys.stdout.write(rewstring)
              sys.stdout.write(bufstring)
              sys.stdout.write(rewstring)
            lastringsize = currentringitems
          sys.stdout.flush()
      else: # if self.ringItems > 0
        time.sleep(1) # go to sleep for a second before looking again

#===============================================================================
class Exompp():
#===============================================================================
#-------------------------------------------------------------------------------
  def __init__(self, connection):
    self.connection = connection
    self.duplicate = False
    self.dsname = ''
    self.dsresource = ''

#-------------------------------------------------------------------------------
  def connect (self):
    retry = 1
    while 0 != retry:
      if retry > 1:
        time.sleep(10)
      try:
        jid = xmpp.protocol.JID(self.connection['user_id'])
      except:
        print "Unable to establish XMPP connection"
        retry += 1
        continue
      cl = xmpp.Client(jid.getDomain(), debug=0)
      self.messenger = Messenger(cl)
      try:
        con = cl.connect()
      except:
        print "Connection request was not reciprocated."
        retry += 1
        continue
      auth = 0
      try:
        auth = cl.auth(jid.getNode(), self.connection['password'])
      except:
        print "Authentication failed"
        retry += 1
        continue
      if not auth:
        print "Authentication failed"
        retry += 1
        continue
      cl.RegisterHandler('message', self.messenger.message_handler)
      #check for API version compatibility
      msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                  body='commanderid',
                                  typ='chat')
      self.messenger.send(msg, self.stdcallback, '')
      if self.messenger.wait() == -1: 
        print "Connection error or timed out. connect()"
        retry += 1
        continue
      else:
        if retry > 1: print "Connection re-established"
        retry = 0

#-------------------------------------------------------------------------------
  def setcik (self, cikvalue):
    retval = self.rawwrite('setcik %s\n' % cikvalue, 'ok')
    if -1 == retval: 
      print "Error in setcik (%s)" % cikvalue
    return retval

#-------------------------------------------------------------------------------
  def createdatasource (self, name, resource):
    self.dsname = name  
    self.dsresource = resource
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body='dslist full',
                                typ='chat')
    self.messenger.send(msg, self.checkdsexistscallback)
    if self.messenger.wait() == -1:
      print "Connection error or timed out. createdatasource dslist(%s,%s)" % (name,resource)
      self.connect()
      return -1
    
    if self.duplicate:
      print "Data source %s is already setup, continuing..." % name
      self.duplicate = False
    else:
      msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                  body='dscreate %s %s na 0' % (name, resource),
                                  typ='chat')

      self.messenger.send(msg, self.cdscallback)
      if self.messenger.wait() == -1:
        print "Connection error or timed out. createdatasource dscreate(%s,%s)" % (name,resource)
        self.connect()
        return -1

#-------------------------------------------------------------------------------
  def rawwrite (self, messagebody, expected=''):
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body=messagebody,
                                typ='chat')
    self.messenger.send(msg, self.stdcallback, expected)
    if self.messenger.wait() == -1:
      print "Connection error or timed out. rawwrite(%s)" % messagebody.strip()
      self.connect()
      return -1

#-------------------------------------------------------------------------------
  def write (self, resource, data):
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body='write %s %s' % (resource, data),
                                typ='chat')
    self.messenger.send(msg, self.stdcallback, 'ok')
    if self.messenger.wait() == -1:
      print "Connection error or timed out.  write(%s)" % resource
      self.connect()
      return -1

#-------------------------------------------------------------------------------
  def dsread (self, ds_name, points):
    if 1 != points:
      print "Warning, dsread(): currently only supports reading one point."
      points = 1
    self.readmessage = {}
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body='dsread %s %s\n' % (ds_name, points),
                                typ='chat')
    self.messenger.send(msg, self.readcallback)
    if self.messenger.wait() == -1:
      print "Connection error or timed out.  dsread(%s)" % ds_name
      self.connect()
      return -1
    return self.readmessage

#-------------------------------------------------------------------------------
  def read (self, resource):
    self.readmessage = {}
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body='read %s\n' % resource,
                                typ='chat')
    self.messenger.send(msg, self.readcallback)
    if self.messenger.wait() == -1:
      print "Connection error or timed out.  read(%s)" % resource
      self.connect()
      return -1
    return self.readmessage

#-------------------------------------------------------------------------------
  def listdatasources (self, cik):
    self.dslist = {}
    self.setcik(cik)
    msg = xmpp.protocol.Message(to=self.connection['exosite_bot'],
                                body='dslist full',
                                typ='chat')
    self.messenger.send(msg, self.dslistcallback)
    if self.messenger.wait() == -1:
      print "Connection error or timed out. listdatasources(%s)" % cik
      self.connect()
      return -1
    return self.dslist

#-------------------------------------------------------------------------------
  def stdcallback (self, response, expected):
    if expected != '':
      if response != expected: return -1

#-------------------------------------------------------------------------------
  def cdscallback (self, response, expected):
    if response.find("error") != -1:
      print "CreateDataSource Error: response: %s" % response
      return -1

#-------------------------------------------------------------------------------
  def checkdsexistscallback (self, response, expected):
    start = response.find(self.dsname)
    if start != -1:
      end = response.find(',',start)
      #if the found name was just a subset of another name, it isn't duplicate
      if end - start > len(self.dsname): return 
      self.duplicate = True
      start = response.find(',',start) + 1
      end = response.find(',',start)
      if self.dsresource != response[start:end]:
        print "Error: Duplicate resource name, but resource # does not match."
        return -1

#-------------------------------------------------------------------------------
  def dslistcallback (self, response, expected):
    #possible that the device doesn't have any datasources setup yet
    if -1 == response.find('error'): 
      start = 0
      end = 1
      while -1 != start:
        end = response.find(',',start)
        dsname = response[start:end]
        start = end + 1
        end = response.find(',',start)
        self.dslist[dsname] = response[start:end]
        start = response.find('\x0A',end)
        if -1 != start: start += 1

#-------------------------------------------------------------------------------
  def readcallback (self, response, expected):
    if -1 == response.find('error'):
      start = 0
      #strip double quotes - CSV formatting inserts a second quote
      #to escape any quotes in the entry
      response = response.replace('\"\"','\"')
      length = len(response)
      start = response.find(',',start) + 1
      if '\"' == response[start]: start += 1
      end = length
      if '\"' == response[end - 1]: end -= 1
      self.readmessage = response[start:end]
    else:
      print "Error in read response"
      return -1
  

#===============================================================================
class Messenger(object):
#===============================================================================
#-------------------------------------------------------------------------------
  def __init__(self, client):
    self.wait_for_response = False
    self.callback = None
    self.client = client
    self.start = 0


#-------------------------------------------------------------------------------
  def wait(self):
    self.start = time.clock()
    while self.wait_for_response:
      if time.clock() - self.start > 10:
        self.wait_for_response = False 
        return -1
      if not self.client.Process(1):
        print 'Disconnected'
        return -1

#-------------------------------------------------------------------------------
  def message_handler(self, con, event):
    response = event.getBody()
    if self.callback:
      if -1 == self.callback(response,self.callbackexpected):
        print "WARNING: XMPP response: %s" % response
        self.start = time.clock() - 11
      else:
        self.wait_for_response = False
    else:
      if response.find("ok") == -1:
        print "ERROR: XMPP response: %s" % response
        self.start = time.clock() - 11
      else:
        self.wait_for_response = False

#-------------------------------------------------------------------------------
  def send(self, message, callback=None, callbackexpected=''):
    self.wait_for_response = True
    self.callback = callback
    self.callbackexpected = callbackexpected
    self.client.send(message)

#===============================================================================        
if __name__ == '__main__':
  sys.exit(main())
