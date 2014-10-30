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

def parse_actor_config(config, logger=None):
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


class Vibration(pipeline.Element):
    def __init__(self, config_path, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)

        with open(config_path) as f:
            config = parse_actor_config(yaml.load(f), logger=logger)

        self.drivers = config['drivers']
        for driver in self.drivers:
            # TODO use ALLCALL address to set PWM frequency
            driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz) # TODO test different frequencies


        self.actors = {}
        for region_name, actors in config['regions'].items():
            try:
                region_index = sensationprotocol.Vibration.Region.Value(region_name)

                region_actors = {}
                for actor in actors:
                    region_actors[actor.index_in_region] = actor
                
                self.actors[region_index] = region_actors
            except ValueError:
                self.logger.error("Region with unknown name '%s' configured - ignoring region", region_name)
                continue

    def _set_up(self):
        for driver in self.drivers:
            driver.setAllPWM(0, 0)
        # TODO reset all actors

    def _tear_down(self):
        if not __debug__:
            for driver in self.drivers:
                driver.setAllPWM(0, 0)

    @asyncio.coroutine
    def _process(self, vibration):
        actor = self._actor(vibration.target_region, vibration.actor_index)
        if actor:
            yield from actor.set_intensity(vibration.intensity, vibration.priority)
        else:
            self.logger.warning("No actor configured with index %d in region %s", vibration.actor_index, sensationprotocol.Vibration.Region.Name(vibration.target_region))

        return vibration

    def _actor(self, region, index):
        if region in self.actors and index in self.actors[region]:
            return self.actors[region][index]
        else:
            return None

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
            tracks.append(Track(target_region=track.target_region, actor_index=track.actor_index, priority=pattern.priority, keyframes=track.keyframes))

        self.logger.info("playing %d tracks", len(tracks))
        delta_time = 0
        while tracks:
            for track in tracks:
                track.advance(delta_time)

                message = track.create_message()

                yield from self.inlet.process(message)

            tracks = [t for t in tracks if not t.is_finished]
            start = self._loop.time()
            yield from asyncio.sleep(1/self.samling_frequency)
            delta_time = self._loop.time() - start

        self.logger.info("finished playing pattern %s", pattern.identifier)

        return message
