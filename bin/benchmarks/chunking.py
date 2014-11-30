#!/usr/bin/env python3.4

import time
import line_profiler

# @profile
def do_stuff():
    counter = 0
    new_data = [i % 255 for i in range(0, 53 * 19)]
    start = time.time()
    for run in range(0, 95):
        buffer = new_data
        message_size = None
        while True:
            buffer_length = len(buffer)
            second_length = len(buffer)
            if message_size is None and buffer_length >= 4:            # message_size to parse
                split_buffer = buffer[:4]
                message_size = int.from_bytes(split_buffer, byteorder='big')
                buffer = buffer[4:]
                message_size = 15
            elif message_size and buffer_length >= message_size:      # message to parse
                message = buffer[:message_size]
                # PROCESS
                counter += 1
                buffer = buffer[message_size:]
                message_size = None
            else:                                                   # neither -> need more data
                break

    duration = (time.time() - start) * 1000
    print("reached %d in %.0f ms" % (counter, duration))

# @profile
def do_stuff2():
    counter = 0
    new_data = [i % 255 for i in range(0, 53 * 25)]
    start = time.time()
    buffer = []
    for run in range(0, 95):
        buffer += new_data
        buffer_length = len(buffer)
        start_index = 0
        message_size = None
        while True:
            if message_size is None and buffer_length - start_index >= 4:       # message_size to parse
                split_buffer = buffer[start_index:start_index + 4]
                message_size = int.from_bytes(split_buffer, 'big')
                start_index += 4
                message_size = 15
            elif message_size and buffer_length - start_index >= message_size:      # message to parse
                message = buffer[start_index:start_index + message_size]
                # PROCESS
                counter += 1
                start_index += message_size
                message_size = None
            else:                                                   # neither -> need more data
                new_buffer = buffer[start_index:]
                buffer = new_buffer
                # print(len(buffer))
                # buffer = []
                break

    duration = (time.time() - start) * 1000
    print("reached %d in %.0f ms" % (counter, duration))

# do_stuff2()

class Splitter():
    def __init__(self):
        self.buffer = bytes()
        self.buffer_length = 0
        self.start_index = 0
        self.message_size = None

        # only for profiling
        self.counter = 0
        self.start = None
        self.message_counter = 0

    # @profile
    def process(self, new_data):
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
                message_size = 15
            elif message_size and buffer_length - start_index >= message_size:      # message to parse
                message = buffer[start_index:start_index + message_size]
                # if self.handler is not None:
                #     yield from self.handler.process(message)
                messages.append(message)
                start_index += message_size
                message_size = None
            else:        # neither -> need more data
                break

        self.message_counter += len(messages)

        if self.counter >= 95000:
            duration = (time.time() - self.start) * 1000
            print("received %d bytes (%d msg) in %.0f ms" % (self.counter, self.message_counter, duration))
            self.counter = 0
            self.start = None

        self.buffer_length = buffer_length
        self.start_index = start_index
        self.message_size = message_size
        self.buffer = buffer

        return messages

data = bytearray([i % 255 for i in range(0, 53 * 25)])
splitter = Splitter()
for run in range(0, 95):
    splitter.process(data)

