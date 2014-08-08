import time

from utils import *

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

    def test_tolerance_towards_zero(self):
        self.intensity.set(20, 100)
        self.intensity.set(10, 200)
        self.intensity.set(PrioritizedIntensity._MIN_VALUE - 0.0001, 200)
        self.assertEqual(self.intensity.eval(), 20)

    def test_resetting_twice(self):
        self.intensity.set(20)
        self.intensity.set(0)
        self.intensity.set(0)
        self.assertEqual(self.intensity.eval(), 0)

    def test_clear(self):
        self.intensity.set(20, 100)
        self.intensity.reset()
        self.assertEqual(self.intensity.eval(), 0)

    def test_top_priority(self):
        self.assertEqual(self.intensity.top_priority(), 0)
        self.intensity.set(1, 10)
        self.assertEqual(self.intensity.top_priority(), 10)
        self.intensity.set(2, 9)
        self.assertEqual(self.intensity.top_priority(), 10)
        self.intensity.set(2, 11)
        self.assertEqual(self.intensity.top_priority(), 11)


class TestVibrationMotor(AsyncTestCase):

    class MockDriver(object):
        def __init__(self):
            self.calls = []
            self.start_time = None
            self.intensity = 0

        def setPWM(self, outlet, start, intensity):
            current_time = time.time()
            if not self.start_time:
                self.start_time = current_time
            self.intensity = intensity / 4096
            self.calls.append(((current_time - self.start_time), self.intensity))

    def setUp(self):
        super().setUp()

        self.driver = TestVibrationMotor.MockDriver()
        self.motor = VibrationMotor(self.driver, 0)

    @async_test
    def test_direct_set(self):
        update = asyncio.Task(self.motor.set_intensity(1))

        yield from update

        self.assertEqual(len(self.driver.calls), 1)

    @async_test
    def test_minimal_change_ingored(self):
        self.run_async(self.motor.set_intensity(0.5))
        yield from asyncio.sleep(0.1)
        self.run_async(self.motor.set_intensity(0.5001))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 1)
        self.assertEqual(self.motor.intensity(), 0.5001)

    @async_test
    def test_delayed_set(self):
        self.run_async(self.motor.set_intensity(0.1))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)

    @async_test
    def test_delayed_update(self):
        self.run_async(self.motor.set_intensity(0.1))
        yield from asyncio.sleep(0.1)
        self.run_async(self.motor.set_intensity(0.2))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor._MOTOR_MIN_INTENSITY_WARMUP, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.2), delta=0.01)

    @async_test
    def test_instant_min(self):
        delay = self.motor._MOTOR_MIN_INTENSITY_WARMUP + 0.1
        self.run_async(self.motor.set_intensity(1))
        yield from asyncio.sleep(delay)
        self.run_async(self.motor.set_intensity(0.1))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], delay, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_delayed_min(self):
        delay = self.motor._MOTOR_MIN_INTENSITY_WARMUP - 0.1
        self.run_async(self.motor.set_intensity(1))
        yield from asyncio.sleep(delay)
        self.run_async(self.motor.set_intensity(0.1))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor._MOTOR_MIN_INTENSITY_WARMUP, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_instant_update(self):
        self.run_async(self.motor.set_intensity(0.1))
        yield from asyncio.sleep(0.1)
        self.run_async(self.motor.set_intensity(1))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertEqual(secondCall[1], 1)
        self.assertAlmostEqual(secondCall[0], 0.1, delta=0.01)

    @async_test
    def test_instant_off(self):
        self.run_async(self.motor.set_intensity(0.1))
        yield from asyncio.sleep(0.1)
        self.run_async(self.motor.set_intensity(0))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertEqual(secondCall[1], 0)
        self.assertAlmostEqual(secondCall[0], 0.1, delta=0.01)

    @async_test
    def test_no_update_for_lower_priority(self):
        self.run_async(self.motor.set_intensity(0.5, 100))
        yield from asyncio.sleep(0.5)
        self.run_async(self.motor.set_intensity(0.8, 50))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 1)
        self.assertEqual(self.motor.intensity(), 0.5)

    @async_test
    def test_update_for_higher_priority(self):
        self.run_async(self.motor.set_intensity(0.5, 100))
        yield from asyncio.sleep(0.5)
        self.run_async(self.motor.set_intensity(0.8, 150))

        yield from self.wait_for_async()

        self.assertEqual(len(self.driver.calls), 2)
        self.assertEqual(self.motor.intensity(), 0.8)

