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

    def test_handler_torn_down_after_server_usage(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        with server:
            pass
        self.assertEqual(handler.tear_down_called_counter, 1)

    def test_handler_set_up_called_on_restart(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        with server:
            pass

        with server:
            self.assertEqual(handler.set_up_called_counter, 2)


    def test_handler_set_up_not_called_twice_on_start(self):
        server = Server()
        handler = self.MemoryHandler()
        server.handler = handler
        with server:
            self.assertEqual(handler.set_up_called_counter, 1)


if __name__ == '__main__':
    unittest.main()
