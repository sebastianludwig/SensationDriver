#!/usr/bin/env python3.4

import socket
import time
import asyncio
import signal

loop = asyncio.get_event_loop()


@asyncio.coroutine
def handle_client_serialized(client_reader, client_writer):
    start = None
    counter = 0
    while True:
        data = yield from client_reader.readexactly(4)
        if start is None:
            start = time.time()
        message_size = int.from_bytes(data, byteorder='big')
        counter += message_size + 4

        message = yield from client_reader.readexactly(message_size)

        # if self.handler is not None:
        #     yield from self.handler.process(message)

        if counter == 95000:
            duration = (time.time() - start) * 1000
            print("received %d in %.0f ms" % (counter, duration))
            counter = 0
            start = None


@asyncio.coroutine
def handle_client_batch(client_reader, client_writer):
    try:
        start = None
        counter = 0
        while True:
            data = yield from client_reader.read(4096)

            if start is None:
                start = time.time()

            if not data:
                break

            counter += len(data)

            # if self.handler is not None:
            #     yield from self.handler.process(data)

            if counter == 95000:
                duration = (time.time() - start) * 1000
                print("received %d in %.0f ms" % (counter, duration))
                counter = 0
                start = None
    except asyncio.CancelledError:
        pass


def accept_client(client_reader, client_writer):
    asyncio.Task(handle_client_serialized(client_reader, client_writer), loop=loop)
    # asyncio.Task(handle_client_batch(client_reader, client_writer), loop=loop)


for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, loop.stop)

future_server = asyncio.start_server(accept_client, '10.0.0.2', 10000, loop=loop)
server = loop.run_until_complete(future_server)

try:
    print("Server running")
    loop.run_forever()
finally:
    loop.close()

print("Server stopped")
