import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src'))
del os
#del sys

def log(*text):
    print('\n', text, file=sys.stderr)

import unittest
import asyncio
from sensationdriver.actors import PrioritizedIntensity
from sensationdriver.actors import VibrationMotor

class TestPrioritizedIntensity(unittest.TestCase):

    def setUp(self):
        self.intensity = PrioritizedIntensity()

    def test_set(self):
        self.intensity.set(20)
        self.assertEqual(self.intensity.eval(), 20)

    def test_update(self):
        self.intensity.set(20)
        self.intensity.set(40)
        self.assertEqual(self.intensity.eval(), 40)

    def test_priority(self):
        self.intensity.set(20, 100)
        self.intensity.set(10, 101)
        self.assertEqual(self.intensity.eval(), 10)

    def test_fallback(self):
        self.intensity.set(20, 100)
        self.intensity.set(10, 200)
        self.intensity.set(0, 200)
        self.assertEqual(self.intensity.eval(), 20)

    def test_clear(self):
        self.intensity.set(20, 100)
        self.intensity.reset()
        self.assertEqual(self.intensity.eval(), 0)

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper

class TestVibrationMotor(unittest.TestCase):

    class MockDriver(object):
        def __init__(self, loop):
            self.loop = loop
            self.calls = []
            self.start_time = None
            self.intensity = 0

        def setPWM(self, outlet, start, intensity):
            time = self.loop.time()
            if not self.start_time:
                self.start_time = time
            self.intensity = intensity / 4096
            self.calls.append(((time - self.start_time), self.intensity))

    def setUp(self):
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(None)
        self.loop = asyncio.get_event_loop()

        self.driver = TestVibrationMotor.MockDriver(self.loop)
        self.motor = VibrationMotor(self.driver, 0, loop=self.loop)


    @async_test
    def test_direct_set(self):
        self.motor.intensity = 1

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 1)

    @async_test
    def test_minimal_change_ingored(self):
        self.motor.intensity = 0.5
        yield from asyncio.sleep(0.1)
        self.motor.intensity = 0.5001

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 1)
        self.assertEqual(self.motor.intensity, 0.5001)

    @async_test
    def test_delayed_set(self):
        self.motor.intensity = 0.1

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)

    @async_test
    def test_delayed_update(self):
        self.motor.intensity = 0.1
        yield from asyncio.sleep(0.1)
        self.motor.intensity = 0.2

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor._MOTOR_MIN_INTENSITY_WARMUP, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.2), delta=0.01)

    @async_test
    def test_instant_min(self):
        delay = self.motor._MOTOR_MIN_INTENSITY_WARMUP + 0.1
        self.motor.intensity = 1
        yield from asyncio.sleep(delay)
        self.motor.intensity = 0.1

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], delay, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_delayed_min(self):
        delay = self.motor._MOTOR_MIN_INTENSITY_WARMUP - 0.1
        self.motor.intensity = 1
        yield from asyncio.sleep(delay)
        self.motor.intensity = 0.1

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor._MOTOR_MIN_INTENSITY_WARMUP, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_instant_update(self):
        self.motor.intensity = 0.1
        yield from asyncio.sleep(0.1)
        self.motor.intensity = 1

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertEqual(secondCall[1], 1)
        self.assertAlmostEqual(secondCall[0], 0.1, delta=0.01)

    @async_test
    def test_instant_off(self):
        self.motor.intensity = 0.1
        yield from asyncio.sleep(0.1)
        self.motor.intensity = 0

        if self.motor._update_task:
            yield from self.motor._update_task

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertEqual(secondCall[1], 0)
        self.assertAlmostEqual(secondCall[0], 0.1, delta=0.01)



if __name__ == '__main__':
    unittest.main()
