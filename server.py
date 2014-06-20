#!/usr/bin/env python

import os
import logging
import logging.config
import yaml
import socket
import sensationserver

def file_logger(filename):
  path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
  return logging.FileHandler(path)

def is_raspberry():
  return os.popen('uname').read() == 'Linux\n'

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logging_conf.yaml')) as f:
  logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('default')

server = sensationserver.SensationServer(logger)

if is_raspberry():
  import messagehandler
  import gpio

  reset_pin = gpio.GPIOOutput(17)
  reset_pin.high

  server.handler = messagehandler.MessageHandler(logger)
  server.on_client_connect = reset_pin.low
  server.on_client_disconnect = reset_pin.high
else:
  import messagelogger
  server.handler = messagelogger.MessageLogger()


server.listen('', 10000)
server.loop()
