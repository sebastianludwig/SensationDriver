import logging
import yaml

from . import platform
from . import pipeline
from .protocol import sensationprotocol_pb2 as sensationprotocol
from .actors import VibrationMotor

if platform.is_raspberry():
    from adafruit import pca9685
    from adafruit import wirebus
else:
    from .dummy import pca9685
    from .dummy import wirebus

# TODO
# pass priority to actor

class Vibration(pipeline.Element):
    def __init__(self, config_path, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)
        pca9685.Driver.softwareReset()

        self.drivers = {}
        self.actors = {}

        self._init_actors(config_path)

    def _init_actors(self, config_path):
        with open(config_path) as f:
            config = yaml.load(f)

        for region in config['vibration']['regions']:
            if region['driver_address'] not in self.drivers:
                if not wirebus.I2C.isDeviceAnswering(region['driver_address']):
                    self.logger.error("No driver found for at address 0x%02X for region %s - ignoring region", region['driver_address'], region['name'])
                    continue
                driver = pca9685.Driver(region['driver_address'], debug=__debug__, logger=self.logger)
                # TODO use ALLCALL address to set PWM frequency
                driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz) # TODO test different frequencies
                self.drivers[region['driver_address']] = driver
            driver = self.drivers[region['driver_address']]

            try:
                region_index = sensationprotocol.Vibration.Region.Value(region['name'])
            except ValueError:
                self.logger.error("Region with unknown name '%s' configured - ignoring region", region['name'])
                continue

            if region_index not in self.actors:
                self.actors[region_index] = {}

            region_actors = self.actors[region_index]

            for actor in region['actors']:
                if actor['index'] in region_actors:
                    self.logger.error("Multiple actors configured with index %d in region %s - ignoring subsequent definitions", actor['index'], region['name'])
                    continue
                else:
                    vibration_motor = VibrationMotor(driver=driver, outlet=actor['outlet'], position=actor['position'], logger=self.logger)
                    region_actors[actor['index']] = vibration_motor

    def _set_up(self):
        for driver in self.drivers.values():
            driver.setAllPWM(0, 0)

    def _tear_down(self):
        if not __debug__:
            for driver in self.drivers.values():
                driver.setAllPWM(0, 0)

    def _process(self, sensation):
        if sensation.region in self.actors and sensation.actor_index in self.actors[sensation.region]:
            self.actors[sensation.region][sensation.actor_index].set_intensity(sensation.intensity)
        else:
            self.logger.debug("No actor configured with index %d in region %s", sensation.actor_index, sensationprotocol.Vibration.Region.Name(sensation.region))

        return sensation
