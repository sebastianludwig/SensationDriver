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
from sensationdriver import pipeline
from sensationdriver import messages
from sensationdriver import handler
from sensationdriver import protocol


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


    actor_config_path = project.relative_path('conf', 'actor_conf.json')

    server = sensationdriver.Server(loop=loop, logger=logger)

    server.handler = pipeline.Parallelizer(loop=loop) >> messages.Parser() >> messages.Logger() >> [messages.TypeFilter(protocol.Message.VIBRATION) >> handler.Vibration(actor_config_path, logger=logger),
                                                                                                   messages.TypeFilter(protocol.Message.LOAD_PATTERN)]


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

