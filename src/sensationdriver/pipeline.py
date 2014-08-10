import logging
import asyncio


class TerminateProcessing(Exception):
    pass

class Element(object):
    def __init__(self, downstream=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self.downstream = downstream

    def __rshift__(self, rhs):
        last = self
        while last.downstream:
            last = last.downstream
        last.downstream = rhs
        return self

    def __iter__(self):
        yield self
        for successor in self._successors():
            for element in successor:
                yield element

    def _successors(self):
        if isinstance(self.downstream, list):
            for sub_stream in self.downstream:
                yield sub_stream
        elif self.downstream:
            yield self.downstream

    def _set_up(self):
        """Subclasses my decorate this as a coroutine"""
        pass

    @asyncio.coroutine
    def set_up(self):
        if asyncio.iscoroutinefunction(self._set_up):
            yield from self._set_up()
        else:
            self._set_up()

        for successor in self._successors():
            yield from successor.set_up()

    def _tear_down(self):
        """Subclasses my decorate this as a coroutine"""
        pass

    @asyncio.coroutine
    def tear_down(self):
        for successor in self._successors():
            yield from successor.tear_down()

        if asyncio.iscoroutinefunction(self._tear_down):
            yield from self._tear_down()
        else:
            self._tear_down()

    @asyncio.coroutine
    def _process(self, data):
        return data

    @asyncio.coroutine
    def process(self, data):
        try:
            result = yield from self._process(data)

            assert result is not None, "pipeline element '{0}' processing result must not be None".format(self.__class__.__name__)

            for successor in self._successors():
                yield from successor.process(result)
        except TerminateProcessing:
            pass


class Dispatcher(Element):
    def __init__(self, target, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.target = target

    @asyncio.coroutine
    def _process(self, data):
        result = self.target(data)
        if asyncio.iscoroutine(result):
            yield from result
        return result

