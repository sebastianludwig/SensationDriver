import logging
import asyncio

from . import pipeline
from .protocol import sensationprotocol_pb2 as sensationprotocol


class Parser(pipeline.Element):
    @asyncio.coroutine
    def _process(self, data):
        message = sensationprotocol.Message()
        message.ParseFromString(data)

        return message


class Logger(pipeline.Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.level = logging.INFO

    @asyncio.coroutine
    def _process(self, message):
        self.logger.log(self.level, 'received:\n--\n%s--', message)

        return message


class TypeFilter(pipeline.Element):
    def __init__(self, message_type, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.message_type = message_type

    @asyncio.coroutine
    def _process(self, message):
        if message.type != self.message_type:
            raise pipeline.TerminateProcessing()

        attribute = message.MessageType.Name(self.message_type).lower()

        return getattr(message, attribute)
