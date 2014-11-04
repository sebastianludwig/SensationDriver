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
from sensationdriver import message
from sensationdriver import handler
from sensationdriver import actors
from sensationdriver import protocol
from sensationdriver import platform

if platform.is_raspberry():
    from adafruit import wirebus
    from adafruit import pca9685
else:
    from sensationdriver.dummy import wirebus
    from sensationdriver.dummy import pca9685
    

def file_logger(filename):    # used in logging_conf.yaml
    return logging.FileHandler(project.relative_path('log', filename))

with open(project.relative_path('conf', 'logging_conf.yaml')) as f:
    logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('default')


def excepthook(*args):
  logger.critical('Uncaught exception:', exc_info=args)

sys.excepthook = excepthook


def main():
    wirebus.I2C.configurePinouts(logger)
    pca9685.Driver.softwareReset()


    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)


    with open(project.relative_path('conf', 'actor_conf.json')) as f:
        actor_config = actors.parse_config(yaml.load(f), logger=logger)

    server = sensationdriver.Server(loop=loop, logger=logger)

    numerator = pipeline.Numerator()
    patter_handler = handler.Pattern(inlet=numerator, logger=logger)

    server.handler = message.Parser() >> numerator >> pipeline.Parallelizer(loop=loop) >> message.Logger() >> [message.TypeFilter(protocol.Message.VIBRATION) >> handler.Vibration(actor_config, logger=logger),
                                                                                                        message.TypeFilter(protocol.Message.LOAD_PATTERN) >> pipeline.Dispatcher(patter_handler.load),
                                                                                                        message.TypeFilter(protocol.Message.PLAY_PATTERN) >> pipeline.Dispatcher(patter_handler.play)]

    for element in server.handler:
        element.logger = logger

    try:
        with server:
            loop.run_forever()
    finally:
        loop.close()



if __name__ == '__main__':
    main()

