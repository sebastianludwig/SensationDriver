import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src'))
del os

import unittest
import asyncio

def log(*text):
    print('\n', *text, file=sys.stderr)

class Logger(object):
    def debug(self, *args):
        log("Debug: ", *args)

    def info(self, *args):
        log("Info: ", *args)

    def warning(self, *args):
        log("Warning: ", *args)

    def error(self, *args):
        log("Error: ", *args)


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class AsyncTestCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self._tasks = []

    def run_async(self, coro):
        task = asyncio.Task(coro)
        self._tasks.append(task)

    @asyncio.coroutine
    def wait_for_async(self):
        yield from asyncio.gather(*self._tasks)
