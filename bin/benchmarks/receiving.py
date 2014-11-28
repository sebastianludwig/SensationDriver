#!/usr/bin/env python3.4

import socket
import time


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 10001))
server.listen(1)

connection = None

connection, client_address = server.accept()
print('Connected by', client_address)

start = None

counter = 0

try:
    while True:
        data = connection.recv(1024)
        counter += len(data)
        if start == None:
            start = time.time()
        if not data or counter == 95000:
            duration = (time.time() - start) * 1000
            print("received %d everything in %f ms" % (counter, duration))
            break
finally:
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()
    server.close()


# original asyncio handler

# start = None
# counter = 0
# while True:
#     data = yield from client_reader.readexactly(4)
#     if start is None:
#         start = time.time()
#     message_size = int.from_bytes(data, byteorder='big')
#     counter += message_size + 4

#     message = yield from client_reader.readexactly(message_size)

#     # if self.handler is not None:
#     #     yield from self.handler.process(message)

#     if counter == 95000:
#         duration = (time.time() - start) * 1000
#         print("received %d in %.0f ms" % (counter, duration))
#         counter = 0
#         start = None
