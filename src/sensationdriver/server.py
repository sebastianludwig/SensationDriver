import asyncio

from . import helper


class Server(object):
    def __init__(self, ip='', loop=None, logger=None):
        self.logger = logger
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
            del self._clients[task]

        # schedule a new Task to handle this specific client connection
        task = helper.create_exception_reporting_task(self._handle_client(client_reader, client_writer), loop=self._loop, logger=self.logger)
        task.add_done_callback(client_disconnected)

        self._clients[task] = (client_reader, client_writer)

    def _client_ip(self, client_writer):
        return client_writer.get_extra_info('peername')[0]

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer):
        client_ip = self._client_ip(client_writer)
        if self.logger is not None:
            self.logger.info("connection from {0}".format(client_ip))


        try:
            while True:
                data = yield from client_reader.read(4096)
                if not data:
                    if self.logger is not None:
                        self.logger.info('client %s disconnected', client_ip)
                    break

                if self.handler is not None:
                    yield from self.handler.process(data)
        except asyncio.CancelledError:
            if self.logger is not None:
                self.logger.info('disconnecting client %s', client_ip)
            

    def __enter__(self):
        """Ought to be called with no asyncio event loop running"""

        self._set_up_handler()

        # start asyncio.Server
        future_server = asyncio.start_server(self._accept_client, self.ip, self.port, loop=self._loop)
        # wait until server socket is set up
        self._server = self._loop.run_until_complete(future_server)
        if self.logger is not None:
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
                    if self.logger is not None:
                        self.logger.error("could not disconnect client %s", self._client_ip(client_writer))

        self._server.close()
        self._loop.run_until_complete(self._server.wait_closed())
        self._server = None
        if self.logger is not None:
            self.logger.info('server stopped')

        return False
