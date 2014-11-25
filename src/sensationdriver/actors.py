import asyncio
import logging
import time

from sortedcontainers import SortedDict

from . import platform

if platform.is_raspberry():
    from adafruit import pca9685
    from adafruit import wirebus
else:
    from .dummy import pca9685
    from .dummy import wirebus

def parse_config(config, logger=None):
    # { 
    #     "drivers": [<Driver>],
    #     "regions": {
    #         "LEFT_HAND": [<Actor>]
    #     }
    # }

    def driver_for_address(drivers, address, i2c_bus_number):
        if address not in drivers:
            if not wirebus.I2C.isDeviceAnswering(address, i2c_bus_number):
                return None

            driver = pca9685.Driver(address, i2c_bus_number, debug=__debug__, logger=logger)
            drivers[address] = driver
        return drivers[address]

    vibration_config = config['vibration']
    global_actor_mapping_curve_degree = vibration_config.get('actor_mapping_curve_degree', None)
    global_actor_min_intensity = vibration_config.get('actor_min_intensity', None)
    global_actor_min_intensity_warmup = vibration_config.get('actor_min_intensity_warmup', None)
    global_actor_min_instant_intensity = vibration_config.get('actor_min_instant_intensity', None)

    drivers = {}    # driver_address -> driver
    regions = {}    # region_name -> actor_index -> actor
    for region_config in vibration_config['regions']:
        dirver_address = region_config['driver_address']
        if type(dirver_address) is str:
            dirver_address = int(dirver_address, 16) if dirver_address.startswith('0x') else int(dirver_address)
            
        driver = driver_for_address(drivers, dirver_address, region_config['i2c_bus_number'])

        if driver is None:
            logger.error("No driver found for at address 0x%02X on I2C bus %d for region %s - ignoring region", dirver_address, region_config['i2c_bus_number'], region_config['name'])
            continue

        if region_config['name'] not in regions:
            regions[region_config['name']] = {}

        region_actor_mapping_curve_degree = region_config.get('actor_mapping_curve_degree', global_actor_mapping_curve_degree)
        region_actor_min_intensity = region_config.get('actor_min_intensity', global_actor_min_intensity)
        region_actor_min_intensity_warmup = region_config.get('actor_min_intensity_warmup', global_actor_min_intensity_warmup)
        region_actor_min_instant_intensity = region_config.get('actor_min_instant_intensity', global_actor_min_instant_intensity)

        region_actors = regions[region_config['name']]
        for actor_config in region_config['actors']:
            if actor_config['index'] in region_actors:
                logger.error("Multiple actors configured with index %d in region %s - ignoring subsequent definitions", actor_config['index'], region_config['name'])
                continue
            else:
                vibration_motor = VibrationMotor(driver=driver, outlet=actor_config['outlet'], index_in_region=actor_config['index'], position=actor_config['position'], logger=logger)

                mapping_curve_degree = actor_config.get('mapping_curve_degree', region_actor_mapping_curve_degree)
                min_intensity = actor_config.get('min_intensity', region_actor_min_intensity)
                min_intensity_warmup = actor_config.get('min_intensity_warmup', region_actor_min_intensity_warmup)                
                min_instant_intensity = actor_config.get('min_instant_intensity', region_actor_min_instant_intensity)
                if mapping_curve_degree is not None:
                    vibration_motor.mapping_curve_degree = mapping_curve_degree
                if min_intensity is not None:
                    vibration_motor.min_intensity = min_intensity
                if min_intensity_warmup is not None:
                    vibration_motor.min_intensity_warmup = min_intensity_warmup
                if min_instant_intensity is not None:
                    vibration_motor.min_instant_intensity = min_instant_intensity

                region_actors[actor_config['index']] = vibration_motor

    for region_name in regions:
        regions[region_name] = list(regions[region_name].values())
    return { "drivers": list(drivers.values()), "regions": regions }


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

    def __init__(self, driver, outlet, index_in_region, position=None, logger=None):
        self.driver = driver
        self.outlet = outlet
        self.index_in_region = index_in_region
        self.position = position
        self.logger = logger if logger is not None else logging.getLogger('root')
        self.profiler = None

        self.mapping_curve_degree = 1.5       # degree of the function used to map intensity values from [0, 1] to the supported motor range. Use '2' for square, '3' for cubic and so on. No matter which degree, it is ensured an intensity of 0 is always off and an intensity of 1 always equals full motor intensity. Only supports positive values.
        self.min_intensity = 0.3              # minimum intensity at which the motor will keep running (maybe after being startet at a higher intensity)
        self.min_instant_intensity = 0.5      # minimum intensity that can be applied to the motor directly
        self.min_intensity_warmup = 0.2       # how long does the motor need to be run at _MOTOR_MIN_INSTANT_INTENSITY before it's okay to switch down to _MOTOR_MIN_INTENSITY

        self._intensity = PrioritizedIntensity()
        self._target_intensity = self._intensity.eval()
        self.__current_intensity = 0
        self._running_since = None

    def _profile(self, action, *args):
        if self.profiler is not None: 
            self.profiler.log(action, *args)

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
        
        self._profile("set_pwm", self.index_in_region, self.__current_intensity)

        self.driver.setPWM(self.outlet, 0, self.__current_intensity)
        if value < self._SENSITIVITY:
            self._running_since = None
        elif self._running_since is None:
            self._running_since = time.time()

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
            self._profile("set_intensity", self.index_in_region, intensity, priority, self._target_intensity, 'direct')

            self._current_intensity = self._target_intensity
        else:
            if self._current_intensity < self.min_intensity:
                self._current_intensity = self.min_instant_intensity
            delay = self.min_intensity_warmup - self._running_time()

            self._profile("set_intensity", self.index_in_region, intensity, priority, self._target_intensity, 'delayed', delay)

            yield from asyncio.sleep(delay)
            self._current_intensity = self._target_intensity
