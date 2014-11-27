import asyncio
import logging
import traceback


class Server(object):
    def __init__(self, ip='', loop=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self.ip = ip
        self.port = 10000

        self.handler = None
        self._handler_set_up = False
        self._server = None     # asyncio.Server
        self._clients = {}      # asyncio.Task -> (asyncio.StreamReader, asyncio.StreamWriter)

    def _set_up_handler(self):
        if self._handler_set_up or self.handler is None:
            return

        set_up_future = asyncio.async(self.handler.set_up())
        self._loop.run_until_complete(set_up_future)
        self._handler_set_up = True

    def _tear_down_handler(self):
        if self._handler_set_up == False or self.handler is None:
            return

        tear_down_future = asyncio.async(self.handler.tear_down())
        self._loop.run_until_complete(tear_down_future)
        self._handler_set_up = False

    def _accept_client(self, client_reader, client_writer):
        def client_disconnected(task):
            if task.exception():
                ex = task.exception()
                output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
                self.logger.critical(''.join(output))

            del self._clients[task]

        # schedule a new Task to handle this specific client connection
        # TODO use self._loop.create_task once Python 3.4.2 is released
        task = asyncio.Task(self._handle_client(client_reader, client_writer), loop=self._loop)
        task.add_done_callback(client_disconnected)

        self._clients[task] = (client_reader, client_writer)

    def _client_ip(self, client_writer):
        return client_writer.get_extra_info('peername')[0]

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer):
        client_ip = self._client_ip(client_writer)
        self.logger.info("connection from {0}".format(client_ip))

        # This could be written much shorter, but the Pi performance is very deficient. 
        # The used operations are chosen considerately.
        try:
            buffer = bytes()
            message_size = None

            start_index = 0
            buffer_length = len(buffer)
            while True:
                new_data = yield from client_reader.read(4096)
                if not new_data:
                    self.logger.info('client %s disconnected', client_ip)
                    break

                new_data_length = len(new_data)

                buffer = buffer[start_index:buffer_length] + new_data
                buffer_length = buffer_length - start_index + new_data_length
                start_index = 0

                # parse everything we received
                while True:
                    if message_size is None and buffer_length - start_index >= 4:            # message_size to parse
                        message_size = int.from_bytes(buffer[start_index:start_index + 4], byteorder='big')
                        start_index += 4
                    elif message_size and buffer_length - start_index >= message_size:      # message to parse
                        message = buffer[start_index:start_index + message_size]
                        if self.handler is not None:
                            yield from self.handler.process(message)
                        start_index += message_size
                        message_size = None
                    else:        # neither -> need more data
                        break

        except asyncio.CancelledError:
            self.logger.info('disconnecting client %s', client_ip)
            

    def __enter__(self):
        """Ought to be called with no asyncio event loop running"""

        self._set_up_handler()

        # start asyncio.Server
        future_server = asyncio.start_server(self._accept_client, self.ip, self.port, loop=self._loop)
        # wait until server socket is set up
        self._server = self._loop.run_until_complete(future_server)
        self.logger.info('server started, listening on %s:%s', self.ip, self.port)

        return self

    def __exit__(self, type, value, traceback):
        """Ought to be called with no asyncio event loop running"""

        self._tear_down_handler()

        if self._server is None:
            return False

        # wait for clients to be disconnected
        if self._clients:
            for task in self._clients:
                task.cancel()

            done, pending = self._loop.run_until_complete(asyncio.wait(self._clients.keys(), loop=self._loop, timeout=2))

            if pending:
                for task in pending:
                    client_writer = self._clients[task][1]
                    self.logger.error("could not disconnect client %s", self._client_ip(client_writer))

        self._server.close()
        self._loop.run_until_complete(self._server.wait_closed())
        self._server = None
        self.logger.info('server stopped')

        return False
