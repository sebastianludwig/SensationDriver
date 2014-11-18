from utils import *

from sensationdriver.handler import Vibration
from sensationdriver import protocol

class TestVibration(AsyncTestCase):
    class MockDriver:
        def setPWMFreq(self, frequency):
            pass

    class MockActor:
        def __init__(self, index_in_region):
            self.index_in_region = index_in_region
            self.intensity = 0

        @asyncio.coroutine
        def set_intensity(self, intensity, priority=100):
            self.intensity = intensity

    def setUp(self):
        super().setUp()

        self.driver = self.MockDriver()
        self.actor_three = self.MockActor(3)
        self.actor_four = self.MockActor(4)

        self.actor_config = {
            "drivers": [self.driver],
            "regions": {
                "LEFT_HAND": [self.actor_three, self.actor_four]
            }
        }

    def vibration_message(self, actor, intensity, priority=100):
        vibration = protocol.Vibration()
        vibration.target_region = protocol.Vibration.Region.Value("LEFT_HAND")
        vibration.actor_index = actor
        vibration.intensity = intensity
        vibration.priority = priority
        return vibration

    @async_test
    def test_sets_value_on_actor(self):     
        vibration_handler = Vibration(self.actor_config)

        yield from vibration_handler.process((42, self.vibration_message(3, 1)))

        self.assertAlmostEqual(self.actor_three.intensity, 1)

    @async_test
    def test_lower_index_message_is_ignored(self):
        vibration_handler = Vibration(self.actor_config)

        yield from vibration_handler.process((42, self.vibration_message(3, 1)))
        yield from vibration_handler.process((41, self.vibration_message(3, 0.5)))

        self.assertAlmostEqual(self.actor_three.intensity, 1)

    @async_test
    def test_higher_index_message_is_processed(self):
        vibration_handler = Vibration(self.actor_config)

        yield from vibration_handler.process((42, self.vibration_message(3, 1)))
        yield from vibration_handler.process((43, self.vibration_message(3, 0.5)))

        self.assertAlmostEqual(self.actor_three.intensity, 0.5)

    @async_test
    def test_lower_index_message_for_different_actor_is_processed(self):
        vibration_handler = Vibration(self.actor_config)

        yield from vibration_handler.process((42, self.vibration_message(3, 1)))
        yield from vibration_handler.process((41, self.vibration_message(4, 0.5)))

        self.assertAlmostEqual(self.actor_three.intensity, 1)
        self.assertAlmostEqual(self.actor_four.intensity, 0.5)

    @async_test
    def test_lower_index_message_with_different_priority_is_processed(self):
        vibration_handler = Vibration(self.actor_config)

        yield from vibration_handler.process((40, self.vibration_message(3, 0.8, 80)))
        yield from vibration_handler.process((42, self.vibration_message(3, 1)))
        yield from vibration_handler.process((41, self.vibration_message(3, 0.5, 80)))

        self.assertAlmostEqual(self.actor_three.intensity, 0.5)


if __name__ == '__main__':
    unittest.main()
