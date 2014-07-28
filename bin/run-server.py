#!/usr/bin/env python3.4

import logging
import logging.config
import yaml

import asyncio
import signal
import functools

import project
import sys
sys.path.append(project.relative_path('src'))
del sys

import sensationdriver
from sensationdriver import messages
from sensationdriver import handler
from sensationdriver.protocol import sensationprotocol_pb2 as sensationprotocol


def file_logger(filename):    # used in logging_conf.yaml
    return logging.FileHandler(project.relative_path('log', filename))

with open(project.relative_path('conf', 'logging_conf.yaml')) as f:
    logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('default')


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)


    actor_config_path = project.relative_path('conf', 'actor_conf.yaml')

    server = sensationdriver.Server(loop=loop, logger=logger)
    server.handler = messages.Parser() >> messages.Logger() >> [messages.TypeFilter(sensationprotocol.Message.VIBRATION) >> handler.Vibration(actor_config_path, logger=logger),
                                                                messages.TypeFilter(sensationprotocol.Message.LOAD_PATTERN)]
    for element in server.handler:
        element.logger = logger

    server.start()

    try:
        loop.run_forever()
    finally:
        server.stop()
        loop.close()


if __name__ == '__main__':
    main()

