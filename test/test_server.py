from utils import *

from sensationdriver.server import Server


class TestServer(unittest.TestCase):
    class MemoryHandler(object):
        def __init__(self):
            self.set_up_called_counter = 0
            self.tear_down_called_counter = 0

        @asyncio.coroutine
        def set_up(self):
            self.set_up_called_counter += 1

        @asyncio.coroutine
        def tear_down(self):
            self.tear_down_called_counter += 1

    def test_handler_set_up_called_on_assignment(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        self.assertEqual(handler.set_up_called_counter, 1)

    def test_handler_tear_down_called_on_reassigment(self):
        server = Server()
        handler1 = self.MemoryHandler()
        handler2 = self.MemoryHandler()
        server.handler = handler1
        server.handler = handler2
        self.assertEqual(handler1.tear_down_called_counter, 1)

    def test_handler_tear_down_called_on_stop(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        server.start()
        server.stop()
        self.assertEqual(handler.tear_down_called_counter, 1)

    def test_handler_set_up_called_on_restart(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        server.start()
        server.stop()
        server.start()
        self.assertEqual(handler.set_up_called_counter, 2)
        server.stop()

    def test_handler_set_up_not_called_twice_on_start(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        server.start()
        self.assertEqual(handler.set_up_called_counter, 1)
        server.stop()
