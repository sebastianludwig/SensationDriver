import asyncio
import traceback
import logging

from sortedcontainers import SortedDict


class PrioritizedIntensity(object):
    _MIN_VALUE = 0.005

    def __init__(self):
        self._values = SortedDict()

    def set(self, value, priority=100):
        value = float(value)
        if value < self._MIN_VALUE:
            del self._values[priority]
        else:
            self._values[priority] = value

    def eval(self):
        if not self._values:
            return 0.0
        return self._values.values()[len(self._values) - 1]

    def reset(self):
        self._values.clear()


class VibrationMotor(object):
    _MAPPING_CURVE_DEGREE = 1.5             # degree of the function used to map intensity values from [0, 1] to the supported motor range. Use '2' for square, '3' for cubic and so on. No matter which degree, it is ensured an intensity of 0 is always off and an intensity of 1 always equals full motor intensity.
    _SENSITIVITY = 0.005                    # ignore any changes below the this value and treat values below as "motor off"
    _MOTOR_MIN_INTENSITY = 0.3              # minimum intensity at which the motor will keep running (maybe after being startet at a higher intensity)
    _MOTOR_MIN_INSTANT_INTENSITY = 0.5      # minimum intensity that can be applied to the motor directly
    _MOTOR_MIN_INTENSITY_WARMUP = 0.2       # how long does the motor need to be run at _MOTOR_MIN_INSTANT_INTENSITY before it's okay to switch down to _MOTOR_MIN_INTENSITY

    def __init__(self, driver, outlet, position=None, loop=None, logger=None):
        self.driver = driver
        self.outlet = outlet
        self.position = position
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self._intensity = 0
        self._target_intensity = 0
        self.__current_intensity = 0
        self._running_since = None

    def _map_intensity(self, intensity):
        return self._MOTOR_MIN_INTENSITY + (1 - self._MOTOR_MIN_INTENSITY) * intensity ** self._MAPPING_CURVE_DEGREE

    def _running_time(self):
        if self._running_since is None:
            return 0
        else:
            return self._loop.time() - self._running_since

    def _can_set_directly(self, intensity):
        if intensity < self._SENSITIVITY:    # turn off
            return True
        if intensity >= self._MOTOR_MIN_INSTANT_INTENSITY:  # intense enough to start instantly
            return True
        if self._current_intensity >= self._MOTOR_MIN_INTENSITY and self._running_time() > self._MOTOR_MIN_INTENSITY_WARMUP:
            return True

    @property
    def _current_intensity(self):
        return self.__current_intensity

    @_current_intensity.setter
    def _current_intensity(self, value):
        if abs(value - self.__current_intensity) < self._SENSITIVITY:
            return
        self.logger.info("setting %s to %.3f", self.position, value)
        self.__current_intensity = value
        self.driver.setPWM(self.outlet, 0, int(self.__current_intensity * 4096))
        self._running_since = self._loop.time() if value >= self._SENSITIVITY else None

    def intensity(self):
        return self._intensity

    def set_intensity(self, intensity):
        intensity = float(intensity)
        if intensity < 0 or intensity > 1: raise ValueError('intensity not in interval [0, 1]: %s' % intensity)
        self._intensity = intensity

        if self._intensity < self._SENSITIVITY:
            self._target_intensity = 0          # TODO this (and only this) needs to become a PrioritizedIntensity
        else:
            self._target_intensity = self._map_intensity(self._intensity)

        def update_complete(task):
            if task.exception():
                ex = task.exception()
                output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
                self.logger.critical(''.join(output))

        update_task = asyncio.Task(self._update_intensity(), loop=self._loop)
        update_task.add_done_callback(update_complete)
        return update_task

        # TODO check out how it looks if it's a coroutine (-> process needs to become one, so does _process...)
        # ...then everything would need to be threadsafe...actually it already needs to be threadsave, because we support multiple clients
        # which is not too bad, because hardly anything has state (only this actor so far?)
        # and it's concurrency only at well defined points... so I could just lock this complete setter? No, bad idea (because of the wait..)
        # TODO pass loop here to not rely on a global event loop..?


    @asyncio.coroutine
    def _update_intensity(self):
        intensity_needs_update = abs(self._current_intensity - self._target_intensity) > self._SENSITIVITY

        if not intensity_needs_update:
            return

        if self._can_set_directly(self._target_intensity):
            self._current_intensity = self._target_intensity
        else:
            if self._current_intensity < self._MOTOR_MIN_INTENSITY:
                self._current_intensity = self._MOTOR_MIN_INSTANT_INTENSITY
            delay = self._MOTOR_MIN_INTENSITY_WARMUP - self._running_time()
            yield from asyncio.sleep(delay, loop=self._loop)
            self._current_intensity = self._target_intensity
