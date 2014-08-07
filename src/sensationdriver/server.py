import asyncio
import logging
import traceback


class Server(object):
    def __init__(self, loop=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self.handler = None
        self._server = None     # asyncio.Server
        self._clients = {}      # asyncio.Task -> (asyncio.StreamReader, asyncio.StreamWriter)
        self._workers = set()   # asyncio.Task, each running handler.process()

    def _accept_client(self, client_reader, client_writer):
        if not self._clients and self.handler is not None:               # first client connects
            self.handler.set_up()

        def client_disconnected(task):
            if task.exception():
                ex = task.exception()
                output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
                self.logger.critical(''.join(output))

            del self._clients[task]
            if not self._clients and self.handler is not None:           # last client disconnected
                self.handler.tear_down()

        # schedule a new Task to handle this specific client connection
        # TODO use self._loop.create_task once Python 3.4.2 is available on OS X via brew
        task = asyncio.Task(self._handle_client(client_reader, client_writer), loop=self._loop)
        task.add_done_callback(client_disconnected)

        self._clients[task] = (client_reader, client_writer)

    def client_ip(self, client_writer):
        return client_writer.get_extra_info('peername')[0]

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer):
        def worker_finished(task):
            if task.exception():
                ex = task.exception()
                output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
                self.logger.critical(''.join(output))

            self._workers.remove(task)

        client_ip = self.client_ip(client_writer)
        self.logger.info("connection from {0}".format(client_ip))
        try:
            while True:
                data = yield from client_reader.readexactly(4)
                message_size = int.from_bytes(data, byteorder='big')

                message = yield from client_reader.readexactly(message_size)

                if self.handler is not None:
                    # start async task to process message
                    # TODO use create_task (see above)
                    worker = asyncio.Task(self.handler.process(message), loop=self._loop)
                    worker.add_done_callback(worker_finished)
                    self._workers.add(worker)
        except asyncio.CancelledError:
            self.logger.info('disconnecting client %s', client_ip)
        except asyncio.IncompleteReadError:
            self.logger.info('client %s disconnected', client_ip)

    def start(self, ip='', port=10000):
        # start asyncio.Server
        future_server = asyncio.start_server(self._accept_client, ip, port, loop=self._loop)
        # wait until server socket is set up
        self._server = self._loop.run_until_complete(future_server)
        self.logger.info('server started, listening on %s:%s', ip, port)

    def stop(self):
        if self._server is None:
            return

        # wait for worker to finish
        if self._workers:
            for task in self._workers:
                task.cancel()

            done, pending = self._loop.run_until_complete(asyncio.wait(self._workers, loop=self._loop, timeout=2))

            if pending:
                self.logger.error("could not cancel processing of %d messages", len(pending))


        # wait for clients to be disconnected
        if self._clients:
            for task in self._clients:
                task.cancel()

            done, pending = self._loop.run_until_complete(asyncio.wait(self._clients.keys(), loop=self._loop, timeout=2))

            if pending:
                for task in pending:
                    client_writer = self._clients[task][1]
                    self.logger.error("could not disconnect client %s", self.client_ip(client_writer))

        self._server.close()
        self._loop.run_until_complete(self._server.wait_closed())
        self._server = None
        self.logger.info('server stopped')
