import logging

from . import platform
from . import pipeline
from .protocol import sensationprotocol_pb2 as sensationprotocol


class Parser(pipeline.Element):
    def _process(self, data):
        sensation = sensationprotocol.Sensation()
        sensation.ParseFromString(data)

        return sensation


class Logger(pipeline.Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.level = logging.INFO

    def _process(self, message):
        self.logger.log(self.level, 'received:\n--\n%s--', message)

        return message


class TypeFilter(pipeline.Element):
    def __init__(self, message_type=None, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.message_type = type

    def _process(self, message):
        # if message.type == self.type
        return message      # inner optional type
        # else raise pipeline.TerminateProcessing()
