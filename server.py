#!/usr/bin/env python

import os

def is_raspberry():
  return os.popen('uname').read() == 'Linux\n'

import socket
import sensationserver

if is_raspberry():
  import messagehandler
  handler = messagehandler.MessageHandler()
else:
  import messagelogger
  handler = messagelogger.MessageLogger()


server = sensationserver.SensationServer()
server.handler = handler
server.listen('', 10000)
server.loop()
