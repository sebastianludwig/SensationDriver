import asyncio

# TODO actually drive motor - add reference to driver? at least an 'index' variable
class VibrationMotor(object):
    _MAPPING_CURVE_DEGREE = 1.5             # degree of the function used to map intensity values from [0, 1] to the supported motor range. Use '2' for square, '3' for cubic and so on. No matter which degree, it is ensured an intensity of 0 is always off and an intensity of 1 always equals full motor intensity.
    _SENSITIVITY = 0.005                    # ignore any changes below the this value and treat values below as "motor off"
    _MOTOR_MIN_INTENSITY = 0.3              # minimum intensity at which the motor will keep running (maybe after being startet at a higher intensity)
    _MOTOR_MIN_INSTANT_INTENSITY = 0.5      # minimum intensity that can be applied to the motor directly
    _MOTOR_MIN_INTENSITY_WARMUP = 0.2       # how long does the motor need to be run at _MOTOR_MIN_INSTANT_INTENSITY before it's okay to switch down to _MOTOR_MIN_INTENSITY

    def __init__(self, loop=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self._intensity = 0
        self._target_intensity = 0
        self.__current_intensity = 0
        self._update_task = None

    def _map_intensity(self, intensity):
        return self._MOTOR_MIN_INTENSITY + (1 - self._MOTOR_MIN_INTENSITY) * intensity ** self._MAPPING_CURVE_DEGREE

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, intensity):
        intensity = float(intensity)
        if intensity < 0 or intensity > 1: raise ValueError('intensity not in interval [0, 1]: %s' % intensity)
        self._intensity = intensity

        if self._intensity < self._SENSITIVITY:
            self._target_intensity = 0
        else:
            self._target_intensity = self._map_intensity(self._intensity)

        intensity_needs_update = abs(self._current_intensity - self._target_intensity) > self._SENSITIVITY

        if intensity_needs_update:
            if not self._update_task or self._update_task.done():
                self._update_task = asyncio.Task(self._update_intensity())

    @property
    def _current_intensity(self):
        return self.__current_intensity

    @_current_intensity.setter
    def _current_intensity(self, value):
        self.logger.debug("setting %.3f" % value)
        self.__current_intensity = value

    @asyncio.coroutine
    def _update_intensity(self):
        can_set_target_intensity_directly = (self._target_intensity < self._SENSITIVITY or       # should turn off
            self._target_intensity >= self._MOTOR_MIN_INSTANT_INTENSITY or                      # intense enough to start instantly
            self._current_intensity >= self._MOTOR_MIN_INTENSITY)                                # already moving

        if can_set_target_intensity_directly:
            self._current_intensity = self._target_intensity
        else:
            self._current_intensity = self._MOTOR_MIN_INSTANT_INTENSITY
            yield from asyncio.sleep(self._MOTOR_MIN_INTENSITY_WARMUP)
            self._current_intensity = self._target_intensity
