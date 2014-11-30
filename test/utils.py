import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src'))
del os

import unittest
import asyncio

def log(*text):
    print('\n', *text, file=sys.stderr)

class TestLogger(object):
    def __init__(self, console=True, capture=False):
        self._print = console
        self._capture = capture
        self.log = []

    def _log(self, prefix, args):
        message = "{0}: {1}".format(prefix, ' '.join(map(str, args)))
        if self._print:
            log(message)
        if self._capture:
            self.log.append(message)

    def debug(self, *args):
        self._log('Debug', args)

    def info(self, *args):
        self._log('Info', args)

    def warning(self, *args):
        self._log('Warning', args)

    def error(self, *args):
        self._log('Error', args)

    def critical(self, *args):
        self._log('Critical', args)


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
        return task

    @asyncio.coroutine
    def wait_for_async(self):
        yield from asyncio.gather(*self._tasks)
