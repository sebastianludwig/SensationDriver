import logging
import asyncio
import traceback
import collections
import time


class TerminateProcessing(Exception):
    pass


class Element(object):
    def __init__(self, downstream=None, logger=None):
        self.logger = logger
        self.downstream = downstream
        self.profiler = None

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

    def _profile(self, action, *args):
        if self.profiler is not None:
            self.profiler.log(action, *args)

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
    def _process_single(self, data):
        return data

    @asyncio.coroutine
    def _process(self, data):
        result = []
        for element in data:
            try:
                mapped = yield from self._process_single(element)

                assert mapped is not None, "pipeline element '{0}' single element processing result must not be None".format(self.__class__.__name__)

                result.append(mapped)
            except TerminateProcessing:
                pass
        return result

    @asyncio.coroutine
    def process(self, data):
        try:
            result = yield from self._process(data)

            assert result is not None, "pipeline element '{0}' processing result must not be None".format(self.__class__.__name__)
            assert isinstance(result, collections.Iterable), "pipeline element '{0}' processing must return an iterable".format(self.__class__.__name__)

            for successor in self._successors():
                yield from successor.process(result)
        except TerminateProcessing:
            pass


class Counter(Element):
    def __init__(self, limit, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.limit = limit
        self.counter = 0
        self.start = None

    @asyncio.coroutine
    def _process_single(self, message):
        if self.start is None:
            self.start = time.time()

        self.counter += 1

        if self.counter == self.limit:
            duration = (time.time() - self.start) * 1000
            if self.logger:
                self.logger.info("received %d messages in %.0f ms" % (self.counter, duration))
            self.counter = 0
            self.start = None

        return message


class Logger(Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.level = logging.INFO

    @asyncio.coroutine
    def _process_single(self, message):
        if self.logger is not None:
            self.logger.log(self.level, 'received:\n--\n%s--', message)

        return message


class Dispatcher(Element):
    def __init__(self, target, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.target = target
        self.coroutine_target = asyncio.iscoroutinefunction(target)

    @asyncio.coroutine
    def _process_single(self, data):
        result = self.target(data)
        if self.coroutine_target:
            result = yield from result
        return result


class Numerator(Element):
    def __init__(self, downstream=None, logger=None):
        self._index = -1

    @asyncio.coroutine
    def _process_single(self, element):
        self._index += 1        
        return (self._index, element)


class Serializer(Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.super_process = super().process

    @asyncio.coroutine
    def _process(self, elements):
        super_process = self.super_process
        for element in elements:
            yield from super_process(message)
        raise TerminateProcessing()


class Parallelizer(Element):
    def __init__(self, loop=None, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self._workers = set()   # asyncio.Task, each running process() of a successor
        self._tearing_down = False

    @asyncio.coroutine
    def _tear_down(self):
        self._tearing_down = True

        # wait for worker to finish
        if not self._workers:
            return

        for task in self._workers:
            task.cancel()

        done, pending = yield from asyncio.wait(self._workers, loop=self._loop, timeout=2)

        if pending and self.logger is not None:
            self.logger.error("could not cancel processing of %d messages", len(pending))

        self._tearing_down = False


    @asyncio.coroutine
    def _process_single(self, data):
        def worker_finished(task):
            # HINT maybe use helper.create_exception_reporting_task
            if not (self._tearing_down and task.cancelled()) and task.exception():
                ex = task.exception()
                output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
                if self.logger is not None:
                    self.logger.critical(''.join(output))

            self._workers.remove(task)

        for successor in self._successors():
            # start async task to process message
            # TODO use self._loop.create_task once Python 3.4.2 is released
            worker = asyncio.Task(successor.process(data), loop=self._loop)
            worker.add_done_callback(worker_finished)
            self._workers.add(worker)
        
        return data

    @asyncio.coroutine
    def _process(self, data):
        yield from super()._process(data)
        raise TerminateProcessing()
