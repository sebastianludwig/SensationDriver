import asyncio
import time
import itertools

from . import pipeline
from . import protocol


class Splitter(pipeline.Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.buffer = bytes()
        self.buffer_length = 0
        self.start_index = 0
        self.message_size = None

        # only for profiling - TODO: remove
        self.counter = 0
        self.start = None

    @asyncio.coroutine
    def _process(self, new_data):
        # This could be written much shorter, but the Pi performance is very deficient. 
        # The used operations are chosen considerately.

        new_data_length = len(new_data)

        buffer_length = self.buffer_length
        start_index = self.start_index
        message_size = self.message_size

        # profiling only
        if self.start is None:
            self.start = time.time()
        self.counter += new_data_length

        buffer = self.buffer[start_index:buffer_length] + new_data
        buffer_length = buffer_length - start_index + new_data_length
        start_index = 0

        messages = []

        # parse everything we received
        while True:
            if message_size is None and buffer_length - start_index >= 4:            # message_size to parse
                message_size = int.from_bytes(buffer[start_index:start_index + 4], byteorder='big')
                start_index += 4
            elif message_size and buffer_length - start_index >= message_size:      # message to parse
                message = buffer[start_index:start_index + message_size]
                messages.append(message)
                start_index += message_size
                message_size = None
            else:        # neither -> need more data
                break

        if self.counter == 95000:
            duration = (time.time() - self.start) * 1000
            print("received %d bytes in %.0f ms" % (self.counter, duration))
            self.counter = 0
            self.start = None

        self.buffer_length = buffer_length
        self.start_index = start_index
        self.message_size = message_size
        self.buffer = buffer

        return messages


class Parser(pipeline.Element):
    @asyncio.coroutine
    def _process_single(self, data):
        message = protocol.Message()
        message.ParseFromString(data)
        self._profile('parse', message)

        return message


class TypeFilter(pipeline.Element):
    def __init__(self, message_type, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.message_type = message_type
        self.attribute_name = protocol.Message.MessageType.Name(self.message_type).lower()


    @asyncio.coroutine
    def _process(self, messages):
        message_type = self.message_type
        attribute_name = self.attribute_name

        def should_include(container):
            return container.type == message_type

        def extract_message(container):
            return getattr(container, attribute_name)

        return map(extract_message, filter(should_include, messages))


class DeprecatedFilter(pipeline.Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)

    @asyncio.coroutine
    def _process(self, vibration_messages):
        result = {}
        for vibration in vibration_messages:
            key = vibration.priority * 10000 + vibration.target_region * 100 + vibration.actor_index
            result[key] = vibration
        
        result = result.values()
        return result
