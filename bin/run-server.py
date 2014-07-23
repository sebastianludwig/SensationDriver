#!/usr/bin/env python3.4

import logging
import logging.config
import yaml

import project
import sys
sys.path.append(project.relative_path('src'))
del sys

import sensationdriver
from sensationdriver.platform import is_raspberry

# TODO move these



def file_logger(filename):    # used in logging_conf.yaml
    return logging.FileHandler(project.relative_path('log', filename))

with open(project.relative_path('conf', 'logging_conf.yaml')) as f:
    logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('default')

server = sensationdriver.Server(logger)

if is_raspberry():
    from sensationdriver import messagehandler

    server.handler = messagehandler.MessageHandler(logger)
else:
    from sensationdriver import messagelogger
    server.handler = messagelogger.MessageLogger(logger)


server.listen('', 10000)
server.loop()
