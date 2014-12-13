import yaml
import time

from utils import *

from sensationdriver import actor
from sensationdriver.actor import PrioritizedIntensity
from sensationdriver.actor import VibrationMotor


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
            self.intensity = intensity
            self.calls.append(((current_time - self.start_time), self.intensity))

    def setUp(self):
        super().setUp()

        self.driver = TestVibrationMotor.MockDriver()
        self.motor = VibrationMotor(self.driver, 0, 0)
        self.motor.mapping_curve_degree = 1.5
        self.motor.motor_min_intensity = 0.3
        self.motor.motor_min_instant_intensity = 0.5
        self.motor.motor_min_intensity_warmup = 0.2


    @async_test
    def test_direct_set(self):
        update = asyncio.Task(self.motor.set_intensity(1))

        yield from update

        self.assertEqual(len(self.driver.calls), 1)
        self.assertEqual(self.driver.calls[0][1], 1)

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
        # given a value which requires warmup is set
        self.run_async(self.motor.set_intensity(0.1))

        # when we set another value which requires warmup during warmup
        yield from asyncio.sleep(0.1)
        self.run_async(self.motor.set_intensity(0.2))

        yield from self.wait_for_async()

        # then we expect the second value to be set after warmup
        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor.motor_min_intensity_warmup, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.2), delta=0.01)

    @async_test
    def test_warmup_time_accumulates(self):
        # given the motor is set twice to a value needing warmup
        self.motor.min_intensity_warmup = 1
        self.run_async(self.motor.set_intensity(0.1))
        yield from asyncio.sleep(0.7)
        self.run_async(self.motor.set_intensity(0.15))
        yield from asyncio.sleep(0.5)

        # when we set it to another value needing warmup
        self.run_async(self.motor.set_intensity(0.2))

        yield from self.wait_for_async()

        # then the third value should be set instantly, because the total warmup is already complete
        self.assertEqual(len(self.driver.calls), 3)
        thirdCall = self.driver.calls[2]
        self.assertAlmostEqual(thirdCall[0], 1.2, delta=0.01)

    @async_test
    def test_instant_min(self):
        # given the motor runs long enough fast enough
        delay = self.motor.motor_min_intensity_warmup + 0.1
        self.run_async(self.motor.set_intensity(1))
        yield from asyncio.sleep(delay)

        # when we set the minimum intensity
        self.run_async(self.motor.set_intensity(0.1))

        yield from self.wait_for_async()

        # then we expect an instant setting of the minimum value
        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], delay, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_delayed_min(self):
        # given the motor runs a little less than the necessary warmup time on full intensity
        delay = self.motor.motor_min_intensity_warmup - 0.1
        self.run_async(self.motor.set_intensity(1))
        yield from asyncio.sleep(delay)

        # when we set the minimum intensity
        self.run_async(self.motor.set_intensity(0.1))

        yield from self.wait_for_async()

        # then then the minimum intensity is only set after the full warmup time
        self.assertEqual(len(self.driver.calls), 2)
        secondCall = self.driver.calls[1]
        self.assertAlmostEqual(secondCall[0], self.motor.motor_min_intensity_warmup, delta=0.01)
        self.assertAlmostEqual(secondCall[1], self.motor._map_intensity(0.1), delta=0.01)

    @async_test
    def test_instant_update(self):
        # given the motor runs a little bit on warmup intensity (to later set minimum intensity)
        self.run_async(self.motor.set_intensity(0.1))
        yield from asyncio.sleep(0.1)

        # when we set full itensity
        self.run_async(self.motor.set_intensity(1))

        yield from self.wait_for_async()

        # the motor is set to full itensity immediatly
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


class TestActorConfigParsing(unittest.TestCase):
    def test_simple_parsing(self):
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        },
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                },
                                {
                                    "name": "RIGHT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x41",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        },
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config)
        self.assertEqual(len(result['drivers']), 2)
        self.assertEqual(len(result['regions']), 2)
        self.assertEqual(len(result['regions']['LEFT_HAND']), 2)
        self.assertEqual(len(result['regions']['RIGHT_HAND']), 2)

    def test_driver_reusage(self):
        # two regions, same driver
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                },
                                {
                                    "name": "LEFT_FOREARM",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config)
        self.assertEqual(len(result['drivers']), 1)
        self.assertEqual(len(result['regions']), 2)
        self.assertEqual(result['regions']['LEFT_HAND'][0].driver, result['regions']['LEFT_FOREARM'][0].driver)

    def test_region_merging(self):
        # one region, split into two definitions (different drivers)
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                },
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x41",
                                    "actors": [
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config)
        self.assertEqual(len(result['drivers']), 2)
        self.assertEqual(len(result['regions']), 1)
        self.assertEqual(len(result['regions']['LEFT_HAND']), 2)
        self.assertNotEqual(result['regions']['LEFT_HAND'][0].driver, result['regions']['LEFT_HAND'][1].driver)

    def test_global_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config, logger=TestLogger())

        a = result['regions']['LEFT_HAND'][0]
        self.assertEqual(a.mapping_curve_degree, 42)
        self.assertEqual(a.min_intensity, 43)
        self.assertEqual(a.min_intensity_warmup, 44)
        self.assertEqual(a.min_instant_intensity, 45)

    def test_region_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    
                                    "actor_mapping_curve_degree": 52,
                                    "actor_min_intensity": 53,
                                    "actor_min_intensity_warmup": 54,
                                    "actor_min_instant_intensity": 55,

                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config, logger=TestLogger())

        a = result['regions']['LEFT_HAND'][0]
        self.assertEqual(a.mapping_curve_degree, 52)
        self.assertEqual(a.min_intensity, 53)
        self.assertEqual(a.min_intensity_warmup, 54)
        self.assertEqual(a.min_instant_intensity, 55)

    def test_local_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    
                                    "actor_mapping_curve_degree": 52,
                                    "actor_min_intensity": 53,
                                    "actor_min_intensity_warmup": 54,
                                    "actor_min_instant_intensity": 55,

                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0,

                                            "mapping_curve_degree": 62,
                                            "min_intensity": 63,
                                            "min_intensity_warmup": 64,
                                            "min_instant_intensity": 65,
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = actor.parse_config(config, logger=TestLogger())

        a = result['regions']['LEFT_HAND'][0]
        self.assertEqual(a.mapping_curve_degree, 62)
        self.assertEqual(a.min_intensity, 63)
        self.assertEqual(a.min_intensity_warmup, 64)
        self.assertEqual(a.min_instant_intensity, 65)


if __name__ == '__main__':
    unittest.main()
