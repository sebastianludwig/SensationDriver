from utils import *

from sensationdriver.pipeline import Element
from sensationdriver.pipeline import Dispatcher
from sensationdriver.pipeline import TerminateProcessing

class MemoryElement(Element):
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
    def _process(self, number):
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
        first = MemoryElement()
        second = MemoryElement()
        third = MemoryElement()
        fourth = MemoryElement()

        chain = first >> second >> third >> fourth
        yield from chain.set_up()

        for element in chain:
            self.assertEqual(element.set_up_called_counter, 1)

    @async_test
    def test_tear_down_propagates(self):
        first = MemoryElement()
        second = MemoryElement()
        third = MemoryElement()
        fourth = MemoryElement()

        chain = first >> second >> third >> fourth
        yield from chain.tear_down()

        for element in chain:
            self.assertEqual(element.tear_down_called_counter, 1)

    @async_test
    def test_process_propagates(self):
        first = MemoryElement()
        second = MemoryElement()
        third = MemoryElement()
        fourth = MemoryElement()

        chain = first >> second >> third >> fourth
        self.run_async(chain.process(42))

        yield from self.wait_for_async()

        for element in chain:
            self.assertEqual(element.process_called_counter, 1)
        self.assertEqual(fourth.processed_number, 45)

    def test_multiplexing(self):
        first = MemoryElement()
        a1 = MemoryElement()
        a2 = MemoryElement()
        b1 = MemoryElement()
        b2 = MemoryElement()

        chain = first >> [a1 >> a2,
                          b1 >> b2]

        self.run_async(chain.process(1))

        yield from self.wait_for_async()

        i = 0
        for element in chain:
            self.assertEqual(element.process_called_counter, 1)
            i += 1
        self.assertEqual(i, 5)
        self.assertEqual(a2.processed_number, 2)
        self.assertEqual(b2.processed_number, 2)

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
            self.run_async(chain.process(1))

            yield from self.wait_for_async()

    @async_test
    def test_terminate_prcessing(self):
        class TerminalElement(MemoryElement):
            @asyncio.coroutine
            def _process(self, number):
                yield from super()._process(number)
                raise TerminateProcessing
                return number

        first = MemoryElement()
        second = TerminalElement()
        third = MemoryElement()

        chain = first >> second >> third
        self.run_async(chain.process(42))

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
        first = MemoryElement()
        second = Dispatcher(self.two_times.calc)
        third = MemoryElement()

        chain = first >> second >> third

        self.run_async(chain.process(2))

        yield from self.wait_for_async()

        self.assertEqual(self.two_times.input_number, 3)
        self.assertEqual(third.processed_number, 6)

