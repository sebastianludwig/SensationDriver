import struct

from utils import *

from sensationdriver import protocol
from sensationdriver.message import DeprecatedFilter
from sensationdriver.message import Splitter


class TestSplitter(AsyncTestCase):
    def pack_message(self, data):
        return struct.pack('!i', len(data)) + data

    @async_test
    def test_splits_data(self):
        data = self.pack_message(b'message 1') + self.pack_message(b'message 2')

        splitter = Splitter()
        messages = yield from splitter._process(data)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], b'message 1')
        self.assertEqual(messages[1], b'message 2')

    @async_test
    def test_keeps_remaining_chunks_for_next_chunk(self):
        data = self.pack_message(b'message 1') + self.pack_message(b'message 2')

        splitter = Splitter()
        first_batch = yield from splitter._process(data[:15])
        second_batch = yield from splitter._process(data[15:])

        self.assertEqual(len(first_batch), 1)
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(first_batch[0], b'message 1')
        self.assertEqual(second_batch[0], b'message 2')


class TestDeprecatedFilter(AsyncTestCase):
    def wrapped_vibration_message(self, actor, intensity, priority=100, region="LEFT_HAND"):
        vibration = protocol.Vibration()
        vibration.target_region = protocol.Vibration.Region.Value(region)
        vibration.actor_index = actor
        vibration.intensity = intensity
        vibration.priority = priority

        return vibration

    def setUp(self):
        super().setUp()

    @async_test
    def test_passes_on_single_message(self):
        filter = DeprecatedFilter()

        messages = [self.wrapped_vibration_message(1, 0.5)]

        result = yield from filter._process(messages)

        self.assertEqual(len(result), 1)

    @async_test
    def test_filters_old(self):
        filter = DeprecatedFilter()

        first = self.wrapped_vibration_message(1, 0.5)
        second = self.wrapped_vibration_message(1, 0.5)

        result = yield from filter._process([first, second])

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(list(result)[0], second)
    
    @async_test
    def test_separates_between_actors(self):
        filter = DeprecatedFilter()

        messages = [self.wrapped_vibration_message(1, 0.5), self.wrapped_vibration_message(2, 0.5)]

        result = yield from filter._process(messages)

        self.assertEqual(len(result), 2)


    @async_test
    def test_separates_between_regions(self):
        filter = DeprecatedFilter()

        messages = [self.wrapped_vibration_message(1, 0.5, region='LEFT_HAND'), 
                self.wrapped_vibration_message(1, 0.5, region='RIGHT_HAND')]

        result = yield from filter._process(messages)

        self.assertEqual(len(result), 2)


    @async_test
    def test_lets_priorities_pass(self):
        filter = DeprecatedFilter()

        messages = [self.wrapped_vibration_message(1, 0.5, 100), self.wrapped_vibration_message(1, 0.5, 80)]

        result = yield from filter._process(messages)

        self.assertEqual(len(result), 2)

