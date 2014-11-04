import logging
import asyncio

from . import pipeline
from . import protocol


class Parser(pipeline.Element):
    @asyncio.coroutine
    def _process(self, data):
        message = protocol.Message()
        message.ParseFromString(data)

        return message


class Logger(pipeline.Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.level = logging.INFO

    @asyncio.coroutine
    def _process(self, indexed_message):
        self.logger.log(self.level, 'received:\n--\n%s--', indexed_message[1])

        return indexed_message


class TypeFilter(pipeline.Element):
    def __init__(self, message_type, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.message_type = message_type

    @asyncio.coroutine
    def _process(self, indexed_message):
        message = indexed_message[1]
        if message.type != self.message_type:
            raise pipeline.TerminateProcessing()

        attribute = message.MessageType.Name(self.message_type).lower()

        child_message = getattr(message, attribute)
        return (indexed_message[0], child_message)
