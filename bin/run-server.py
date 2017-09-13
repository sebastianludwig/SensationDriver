#!/usr/bin/env python3.4

import cProfile

import logging
import logging.config
import yaml

import asyncio
import signal
import sys
import functools
import datetime

import project

sys.path.append(project.relative_path('src'))

import sensationdriver
from sensationdriver import pipeline
from sensationdriver import message
from sensationdriver import handler
from sensationdriver import actor
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


def excepthook(logger, *args):
  logger.critical('Uncaught exception:', exc_info=args)


def protobuf_implementation():
    from google.protobuf.internal import api_implementation
    return api_implementation._default_implementation_type


def main():
    mode = None
    if sys.argv[-1] in ["profile", "debug", "production"]:
        mode = sys.argv[-1]

    if (len(sys.argv) >= 2 and mode is None) or len(sys.argv) >= 3:
        ip = sys.argv[1]
    else:
        ip = ''

    if mode is None:
        mode = "production"

    with open(project.relative_path('conf', 'logging_conf.yaml')) as f:
        logging.config.dictConfig(yaml.load(f))

    if mode == "debug":
        logger = logging.getLogger('debug')
    else:
        logger = logging.getLogger('production')

    if __debug__:
        sys.excepthook = functools.partial(excepthook, logger)
    else:
        logger = None


    if protobuf_implementation() != 'cpp' and logger is not None:
        logger.warning("Not using C++ Protocol Buffer implementation. Things will be slow!")


    wirebus.I2C.configurePinouts(logger)
    pca9685.Driver.softwareReset()


    loop = asyncio.get_event_loop()
    loop.set_debug(mode == "debug")

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)


    with open(project.relative_path('conf', 'actor_conf.json')) as f:
        actor_config = actor.parse_config(yaml.load(f), loop=loop, logger=logger)


    server = sensationdriver.Server(ip=ip, loop=loop, logger=logger)

    noop_inlet = pipeline.Element()
    patter_handler = handler.Pattern(inlet=noop_inlet, loop=loop, logger=logger)

    server.handler = message.Splitter() >> message.Parser() >> noop_inlet >> pipeline.Logger(logger=logger) >> [message.TypeFilter(protocol.Message.VIBRATION) >> pipeline.Counter(5000) >> message.DeprecatedFilter() >> handler.Vibration(actor_config),
                                                                                                                message.TypeFilter(protocol.Message.LOAD_PATTERN) >> pipeline.Dispatcher(patter_handler.load),
                                                                                                                message.TypeFilter(protocol.Message.PLAY_PATTERN) >> pipeline.Dispatcher(patter_handler.play)]
    
    for element in server.handler:
        element.logger = logger

    profiler = None
    if mode == "profile":
        profiler = sensationdriver.Profiler()

        if server.handler is not None:
            for element in server.handler:
                element.profiler = profiler

    try:
        with server:
            up_and_running = "Server running with configuration %s on interface '%s'" % (mode, ip)
            if logger is None:
                print(up_and_running)
            else:    
                logger.critical(up_and_running)     # TODO find a better way to log the server start than to use `critical`

            loop.run_forever()
    finally:
        loop.close()
        if profiler is not None:
            if logger is not None:
                logger.info("Saving profiling data...")
            profile_data_path = project.relative_path('log', "sensation_server_profile_{:%Y%m%d_%H%M}.txt".format(datetime.datetime.now()))
            profiler.save_data(profile_data_path)



if __name__ == '__main__':
    main()
    # cprofile_path = project.relative_path('log', "c_profile_{:%Y%m%d_%H%M}.prof".format(datetime.datetime.now()))
    # cProfile.run('main()', cprofile_path)

