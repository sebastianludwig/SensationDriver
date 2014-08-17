import asyncio
import logging
import time

from sortedcontainers import SortedDict


class PrioritizedIntensity(object):
    _MIN_VALUE = 0.005

    def __init__(self):
        self._values = SortedDict()

    def set(self, value, priority=100):
        value = float(value)
        if value < self._MIN_VALUE and priority in self._values:
            del self._values[priority]
        else:
            self._values[priority] = value

    def eval(self):
        if not self._values:
            return 0.0
        return self._values.values()[len(self._values) - 1]

    def top_priority(self):
        if not self._values:
            return 0
        return self._values.keys()[len(self._values) - 1]

    def reset(self):
        self._values.clear()


class VibrationMotor(object):
    _SENSITIVITY = 0.005                    # ignore any changes below the this value and treat values below as "motor off"

    def __init__(self, driver, outlet, position=None, logger=None):
        self.driver = driver
        self.outlet = outlet
        self.position = position
        self.logger = logger if logger is not None else logging.getLogger('root')

        self.mapping_curve_degree = 1.5       # degree of the function used to map intensity values from [0, 1] to the supported motor range. Use '2' for square, '3' for cubic and so on. No matter which degree, it is ensured an intensity of 0 is always off and an intensity of 1 always equals full motor intensity. Only supports positive values.
        self.min_intensity = 0.3              # minimum intensity at which the motor will keep running (maybe after being startet at a higher intensity)
        self.min_instant_intensity = 0.5      # minimum intensity that can be applied to the motor directly
        self.min_intensity_warmup = 0.2       # how long does the motor need to be run at _MOTOR_MIN_INSTANT_INTENSITY before it's okay to switch down to _MOTOR_MIN_INTENSITY

        self._intensity = PrioritizedIntensity()
        self._target_intensity = self._intensity.eval()
        self.__current_intensity = 0
        self._running_since = None

    def _map_intensity(self, intensity):
        return self.min_intensity + (1 - self.min_intensity) * intensity ** self.mapping_curve_degree

    def _running_time(self):
        if self._running_since is None:
            return 0
        else:
            return time.time() - self._running_since

    def _can_set_directly(self, intensity):
        if intensity < self._SENSITIVITY:    # turn off
            return True
        if intensity >= self.min_instant_intensity:  # intense enough to start instantly
            return True
        if self._running_time() > self.min_intensity_warmup: # running long enough
            return True
        return False

    @property
    def _current_intensity(self):
        return self.__current_intensity

    @_current_intensity.setter
    def _current_intensity(self, value):
        if abs(value - self.__current_intensity) < self._SENSITIVITY:
            return
        self.logger.debug("setting %s to %.3f", self.position, value)
        self.__current_intensity = value
        # TODO move the 4095 into the driver - it's a detail which doesn't belong here
        self.driver.setPWM(self.outlet, 0, int(self.__current_intensity * 4095))
        self._running_since = time.time() if value >= self._SENSITIVITY else None

    def intensity(self):
        return self._intensity.eval()

    @asyncio.coroutine
    def set_intensity(self, intensity, priority=100):
        intensity = float(intensity)
        if intensity < 0 or intensity > 1: raise ValueError('intensity not in interval [0, 1]: %s' % intensity)
        self._intensity.set(intensity, priority)

        if self._intensity.eval() < self._SENSITIVITY:
            self._target_intensity = 0
        else:
            self._target_intensity = self._map_intensity(self._intensity.eval())


        if self._can_set_directly(self._target_intensity):
            self._current_intensity = self._target_intensity
        else:
            if self._current_intensity < self.min_intensity:
                self._current_intensity = self.min_instant_intensity
            delay = self.min_intensity_warmup - self._running_time()
            yield from asyncio.sleep(delay)
            self._current_intensity = self._target_intensity
