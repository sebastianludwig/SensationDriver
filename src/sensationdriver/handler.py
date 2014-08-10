import logging
import yaml
import asyncio

from . import platform
from . import pipeline
from .protocol import sensationprotocol_pb2 as sensationprotocol
from .actors import VibrationMotor
from .patterns import Track

if platform.is_raspberry():
    from adafruit import pca9685
    from adafruit import wirebus
else:
    from .dummy import pca9685
    from .dummy import wirebus


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
        # TODO reset all actors

    def _tear_down(self):
        if not __debug__:
            for driver in self.drivers.values():
                driver.setAllPWM(0, 0)

    @asyncio.coroutine
    def _process(self, vibration):
        if vibration.target_region in self.actors and vibration.actor_index in self.actors[vibration.target_region]:
            actor = self.actors[vibration.target_region][vibration.actor_index]
            yield from actor.set_intensity(vibration.intensity, vibration.priority)
        else:
            self.logger.debug("No actor configured with index %d in region %s", vibration.actor_index, sensationprotocol.Vibration.Region.Name(vibration.target_region))

        return vibration

class Patterns(object):
    def __init__(self, inlet, loop=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self.inlet = inlet
        self.patterns = {}      # identifier -> [Tracks]
        self.samling_frequency = 10

    def load(self, pattern):
        self.logger.info("loaded pattern %s", pattern.identifier)
        self.patterns[pattern.identifier] = pattern.tracks
        return pattern

    @asyncio.coroutine
    def play(self, pattern):
        self.logger.info("play pattern %s", pattern.identifier)
        if not pattern.identifier in self.patterns:
            self.logger.warning("Unknown pattern to play: %s", pattern.identifier)
            return pattern

        tracks = []
        for track in self.patterns[pattern.identifier]:
            tracks.append(Track(track.region, track.actor_index, track.keyframes))

        delta_time = 0
        while tracks:
            for track in tracks:
                value = track.advance(delta_time)

                self.logger.info("would create message for %d: %.2f", track.actor_index, track.value)

            tracks = [t for t in tracks if not t.is_finished]
            start = self._loop.time()
            yield from asyncio.sleep(1/self.samling_frequency)
            delta_time = self._loop.time() - start


        return message
