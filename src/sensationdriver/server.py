import sys
import signal
import asyncio
import logging

from . import messages
from . import platform


class Server(object):
    def __init__(self, loop=None, logger=None):
        self._server = None     # asyncio.Server
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._clients = {}      # asyncio.Task -> (asyncio.StreamReader, asyncio.StreamWriter)

        self.logger = logger if logger is not None else logging.getLogger('root')
        if platform.is_raspberry():
            self.handler = messages.Handler(logger=logger)
        else:
            self.handler = messages.Logger(logger=logger)

    def _accept_client(self, client_reader, client_writer):
        if not self._clients:               # first client connects
            self.handler.set_up()

        def client_disconnected(task):
            del self._clients[task]
            print("done callback")
            if not self._clients:           # last client disconnected
                self.handler.tear_down()

        # schedule a new Task to handle this specific client connection
        task = asyncio.Task(self._handle_client(client_reader, client_writer), loop=self._loop)
        task.add_done_callback(client_disconnected)

        self._clients[task] = (client_reader, client_writer)

    def client_ip(self, client_writer):
        return client_writer.get_extra_info('peername')[0]

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer):
        client_ip = self.client_ip(client_writer)
        self.logger.info("connection from {0}".format(client_ip))
        try:
            while True:
                data = yield from client_reader.readexactly(4)
                message_size = int.from_bytes(data, byteorder='big')

                message = yield from client_reader.readexactly(message_size)

                self.handler.process_message(message)
        except asyncio.CancelledError:
            self.logger.info('disconnecting client {0}'.format(client_ip))
        except asyncio.IncompleteReadError:
            self.logger.info('client {0} disconnected'.format(client_ip))


    def start(self, ip='', port=10000):
        # start asyncio.Server
        future_server = asyncio.start_server(self._accept_client, ip, port, loop=self._loop)
        # wait until server socket is set up
        self._server = self._loop.run_until_complete(future_server)
        self.logger.info('server started, listening on {0}:{1}'.format(ip, port))

    def stop(self):
        if self._server is None:
            return

        for task in self._clients:
            task.cancel()

        # wait for clients to be disconnected
        if self._clients:
            done, pending = self._loop.run_until_complete(asyncio.wait(self._clients.keys(), loop=self._loop, timeout=2))

            if pending:
                for task in pending:
                    client_writer = self._clients[task][1]
                    self.logger.error("could not disconnect client {0}".format(self.client_ip(client_writer)))

        self._server.close()
        self._loop.run_until_complete(self._server.wait_closed())
        self._server = None
        self.logger.info('server stopped')
