#!/usr/bin/env python

import os

def is_raspberry():
  return os.popen('uname').read() == 'Linux\n'

import socket
import sensationserver

server = sensationserver.SensationServer()

if is_raspberry():
  import messagehandler
  import gpio
  
  reset_pin = gpio.GPIOOutput(17)
  reset_pin.high

  server.handler = messagehandler.MessageHandler()
  # server.on_client_connect = reset_pin.low
  # server.on_client_disconnect = reset_pin.high
else:
  import messagelogger
  server.handler = messagelogger.MessageLogger()


server.listen('', 10000)
server.loop()
