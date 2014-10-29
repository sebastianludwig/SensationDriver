#!/usr/bin/env python3.4

import logging
import logging.config
import yaml

import asyncio
import signal
import sys

import project

sys.path.append(project.relative_path('src'))

import sensationdriver
from sensationdriver import pipeline
from sensationdriver import messages
from sensationdriver import handler
from sensationdriver import protocol
from sensationdriver import platform

if platform.is_raspberry():
    from adafruit import wirebus
else:
    from sensationdriver.dummy import wirebus


def file_logger(filename):    # used in logging_conf.yaml
    return logging.FileHandler(project.relative_path('log', filename))

with open(project.relative_path('conf', 'logging_conf.yaml')) as f:
    logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('default')


def excepthook(*args):
  logger.critical('Uncaught exception:', exc_info=args)

sys.excepthook = excepthook


def main():
    wirebus.I2C.initialize(logger)

    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)


    actor_config_path = project.relative_path('conf', 'actor_conf.json')

    server = sensationdriver.Server(loop=loop, logger=logger)

    parallelizer = pipeline.Parallelizer(loop=loop)
    patter_handler = handler.Patterns(inlet=parallelizer, logger=logger)

    server.handler = messages.Parser() >> parallelizer >> messages.Logger() >> [messages.TypeFilter(protocol.Message.VIBRATION) >> handler.Vibration(actor_config_path, logger=logger),
                                                                                messages.TypeFilter(protocol.Message.LOAD_PATTERN) >> pipeline.Dispatcher(patter_handler.load),
                                                                                messages.TypeFilter(protocol.Message.PLAY_PATTERN) >> pipeline.Dispatcher(patter_handler.play)]

    for element in server.handler:
        element.logger = logger

    try:
        with server:
            loop.run_forever()
    finally:
        loop.close()



if __name__ == '__main__':
    main()

