import time

from utils import *

from sensationdriver.pipeline import Element
from sensationdriver.pipeline import Dispatcher
from sensationdriver.pipeline import Parallelizer
from sensationdriver.pipeline import TerminateProcessing

class IncrementElement(Element):
    def __init__(self, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        self.process_called_counter = 0
        self.set_up_called_counter = 0
        self.tear_down_called_counter = 0
        self.processed_number = None

    def _set_up(self):
        self.set_up_called_counter += 1

    def _tear_down(self):
        self.tear_down_called_counter += 1

    @asyncio.coroutine
    def _process_single(self, number):
        self.process_called_counter += 1
        self.processed_number = number
        return number + 1


class TestElement(AsyncTestCase):
    def test_chaining(self):
        first = Element()
        self.assertIsNone(first.downstream)
        second = Element()
        first >> second
        self.assertEqual(first.downstream, second)

    def test_chaining_returns_first_element(self):
        first = Element()
        chain = first >> Element() >> Element()
        self.assertEqual(chain, first)

    def test_iteration(self):
        first = Element()
        second = Element()
        third = Element()
        fourth = Element()

        chain = first >> second >> third >> fourth
        elements = [first, second, third, fourth]

        i = 0
        for element in chain:
            self.assertEqual(element, elements[i])
            i += 1
        self.assertEqual(i, 4)

    @async_test
    def test_set_up_propagates(self):
        first = IncrementElement()
        second = IncrementElement()
        third = IncrementElement()
        fourth = IncrementElement()

        chain = first >> second >> third >> fourth
        yield from chain.set_up()

        for element in chain:
            self.assertEqual(element.set_up_called_counter, 1)

    @async_test
    def test_tear_down_propagates(self):
        first = IncrementElement()
        second = IncrementElement()
        third = IncrementElement()
        fourth = IncrementElement()

        chain = first >> second >> third >> fourth
        yield from chain.tear_down()

        for element in chain:
            self.assertEqual(element.tear_down_called_counter, 1)

    @async_test
    def test_process_propagates(self):
        first = IncrementElement()
        second = IncrementElement()
        third = IncrementElement()
        fourth = IncrementElement()

        chain = first >> second >> third >> fourth
        self.run_async(chain.process([42]))

        yield from self.wait_for_async()

        for element in chain:
            self.assertEqual(element.process_called_counter, 1)
        self.assertEqual(fourth.processed_number, 45)

    @async_test
    def test_multiplexing(self):
        first = IncrementElement()
        a1 = IncrementElement()
        a2 = IncrementElement()
        b1 = IncrementElement()
        b2 = IncrementElement()

        chain = first >> [a1 >> a2,
                          b1 >> b2]

        self.run_async(chain.process([1]))

        yield from self.wait_for_async()

        i = 0
        for element in chain:
            self.assertEqual(element.process_called_counter, 1)
            i += 1
        self.assertEqual(i, 5)
        self.assertEqual(a2.processed_number, 3)
        self.assertEqual(b2.processed_number, 3)

    @async_test
    def test_process_call_process_single_for_every_element(self):
        element = IncrementElement()

        self.run_async(element.process([1, 2, 3, 4]))

        yield from self.wait_for_async()

        self.assertEqual(element.process_called_counter, 4)

    @async_test
    def test_process_returns_results_of_process_single(self):
        class MemoryElement(Element):
            def __init__(self, downstream=None, logger=None):
                super().__init__(downstream=downstream, logger=logger)
                self.process_argument = None

            @asyncio.coroutine
            def _process(self, data):
                self.process_argument = data
                return data

        memory_element = MemoryElement()
        chain = IncrementElement() >> memory_element

        self.run_async(chain.process([1, 2, 3, 4]))

        yield from self.wait_for_async()

        self.assertEqual(len(memory_element.process_argument), 4)
        self.assertEqual(memory_element.process_argument[0], 2)
        self.assertEqual(memory_element.process_argument[3], 5)

    @async_test
    def test_process_must_not_return_none(self):
        class NoneElement(Element):
            @asyncio.coroutine
            def _process(self, number):
                return None

        first = Element()
        second = NoneElement()
        third = Element()

        chain = first >> second >> third

        with self.assertRaises(AssertionError):
            self.run_async(chain.process([1]))

            yield from self.wait_for_async()

    @async_test
    def test_process_single_must_not_return_none(self):
        class NoneElement(Element):
            @asyncio.coroutine
            def _process_single(self, number):
                return None

        first = Element()
        second = NoneElement()
        third = Element()

        chain = first >> second >> third

        with self.assertRaises(AssertionError):
            self.run_async(chain.process([1]))

            yield from self.wait_for_async()

    @async_test
    def test_process_must_return_iterable(self):
        class NotIterable(Element):
            @asyncio.coroutine
            def _process(self, number):
                return 9

        first = Element()
        second = NotIterable()
        third = Element()

        chain = first >> second >> third

        with self.assertRaises(AssertionError):
            self.run_async(chain.process([1]))

            yield from self.wait_for_async()

    @async_test
    def test_process_terminate_prcessing(self):
        class TerminalElement(IncrementElement):
            @asyncio.coroutine
            def _process(self, number):
                yield from super()._process(number)
                raise TerminateProcessing
                return number

        first = IncrementElement()
        second = TerminalElement()
        third = IncrementElement()

        chain = first >> second >> third
        self.run_async(chain.process([42]))

        yield from self.wait_for_async()

        self.assertEqual(first.process_called_counter, 1)
        self.assertEqual(second.process_called_counter, 1)
        self.assertEqual(third.process_called_counter, 0)

    @async_test
    def test_process_single_terminate_prcessing(self):
        class TerminalElement(IncrementElement):
            @asyncio.coroutine
            def _process_single(self, number):
                yield from super()._process_single(number)
                raise TerminateProcessing
                return number

        first = IncrementElement()
        second = TerminalElement()
        third = IncrementElement()

        chain = first >> second >> third
        self.run_async(chain.process([42]))

        yield from self.wait_for_async()

        self.assertEqual(first.process_called_counter, 1)
        self.assertEqual(second.process_called_counter, 1)
        self.assertEqual(third.process_called_counter, 0)


class TestDispatcher(AsyncTestCase):
    class TwoTimes:
        def __init__(self):
            self.input_number = None

        def calc(self, number):
            self.input_number = number
            return 2 * number


    def setUp(self):
        super().setUp()
        self.two_times = self.TwoTimes()

    @async_test
    def test_dispatching(self):
        first = IncrementElement()
        second = Dispatcher(self.two_times.calc)
        third = IncrementElement()

        chain = first >> second >> third

        self.run_async(chain.process([2]))

        yield from self.wait_for_async()

        self.assertEqual(self.two_times.input_number, 3)
        self.assertEqual(third.processed_number, 6)


class TestParallelizer(AsyncTestCase):
    class WaitingRecorder(Element):
        def __init__(self, delay, downstream=None, logger=None):
            super().__init__(downstream=downstream, logger=logger)
            self.delay = delay
            self.execution_times = []

        @asyncio.coroutine
        def _process(self, data):
            yield from asyncio.sleep(self.delay)
            self.execution_times.append(time.time())
            return data


    @async_test
    def test_serial_parallelization(self):
        recorder = self.WaitingRecorder(1)

        parallelizer = Parallelizer()
        chain = parallelizer >> recorder

        yield from chain.process([1])
        yield from chain.process([2])

        yield from asyncio.wait(parallelizer._workers, loop=self.loop, timeout=2)

        self.assertAlmostEqual(recorder.execution_times[0], recorder.execution_times[1], delta=0.001)

    @async_test
    def test_multiplexing_parallelization(self):
        recorder1 = self.WaitingRecorder(1)
        recorder2 = self.WaitingRecorder(1)

        parallelizer = Parallelizer()
        chain = parallelizer >> [recorder1, recorder2]

        yield from chain.process([4])

        yield from asyncio.wait(parallelizer._workers, loop=self.loop, timeout=2)

        self.assertAlmostEqual(recorder1.execution_times[0], recorder2.execution_times[0], delta=0.001)

    @async_test
    def test_tear_down_cancels_tasks(self):     # HINT this test doesn't really test for cancellation - only that tear_down() exits fast.. maybe also assert _workers is empty?
        recorder = self.WaitingRecorder(5)

        parallelizer = Parallelizer()
        chain = parallelizer >> recorder

        yield from chain.process([1])
        start = time.time()
        yield from chain.tear_down()
        duration = time.time() - start

        self.assertLess(duration, 0.1)
        self.assertFalse(recorder.execution_times)

    @async_test
    def test_exceptions_are_logged(self):
        class TestException(Exception):
            pass

        class ExceptionElement(Element):
            @asyncio.coroutine
            def _process(self, data):
                raise TestException()

        logger = TestLogger(console=False, capture=True)
        parallelizer = Parallelizer(logger=logger)
        chain = parallelizer >> ExceptionElement()

        yield from chain.process([1])

        yield from asyncio.wait(parallelizer._workers, loop=self.loop, timeout=2)

        self.assertTrue(any("raise TestException()" in line for line in logger.log))


if __name__ == '__main__':
    unittest.main()
