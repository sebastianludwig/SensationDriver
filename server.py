#! python

import os

def is_raspberry():
  os.popen('uname').read() == 'Linux\n'

import socket

import sensationserver

if is_raspberry():
  import messagehandler
else:
  import messagelogger as messagehandler


server = sensationserver.SensationServer()
server.handler = messagehandler.MessageHandler()
server.listen('', 10000)
server.loop()
