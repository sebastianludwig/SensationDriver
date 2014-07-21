#!/usr/bin/env python3.4

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

  server.handler = messagehandler.MessageHandler(logger)
else:
  import messagelogger
  server.handler = messagelogger.MessageLogger()


server.listen('', 10000)
server.loop()
