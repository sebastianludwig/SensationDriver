#!/usr/bin/env python3.4

import project
import time
import asyncio
import signal
import fileinput
import line_profiler

import sys
sys.path.append(project.relative_path('src'))

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


do_stuff2()
