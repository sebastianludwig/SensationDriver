import logging
import yaml
import asyncio

from . import pipeline
from .protocol import sensationprotocol_pb2 as sensationprotocol
from .actors import VibrationMotor
from .patterns import Track




class Vibration(pipeline.Element):
    def __init__(self, actor_config, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)

        self.drivers = actor_config['drivers']
        for driver in self.drivers:
            # TODO use ALLCALL address to set PWM frequency
            driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz) # TODO test different frequencies


        self.actors = {}
        for region_name, actors in actor_config['regions'].items():
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
