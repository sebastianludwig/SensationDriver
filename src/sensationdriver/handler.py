import logging
import yaml
import asyncio

from . import pipeline
from . import protocol
from .actors import VibrationMotor
from .pattern import Track


class Vibration(pipeline.Element):
    def __init__(self, actor_config, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)

        self._actor_config = actor_config

    def process_actor_config(self):
        self.drivers = self._actor_config['drivers']
        for driver in self.drivers:
            # TODO use ALLCALL address to set PWM frequency
            driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz) # TODO test different frequencies


        self.actors = {}
        self.processed_message_indices = {}
        for region_name, actors in self._actor_config['regions'].items():
            try:
                region_index = protocol.Vibration.Region.Value(region_name)

                region_actors = {}
                region_actor_indices = {}
                for actor in actors:
                    region_actors[actor.index_in_region] = actor
                    region_actor_indices[actor.index_in_region] = {}
                
                self.actors[region_index] = region_actors
                self.processed_message_indices[region_index] = region_actor_indices
            except ValueError:
                self.logger.error("Region with unknown name '%s' configured - ignoring region", region_name)
                continue

    def _set_up(self):
        self.process_actor_config()

        for driver in self.drivers:
            driver.setAllPWM(0, 0)
        # TODO reset all actors

        if self.profiler is not None:
            for region_index, region_actors in self.actors.items():
                for index, actor in region_actors.items():
                    actor.profiler = self.profiler

    def _tear_down(self):
        if not __debug__:
            for driver in self.drivers:
                driver.setAllPWM(0, 0)

    @asyncio.coroutine
    def _process(self, indexed_vibration):
        message_index = indexed_vibration[0]
        vibration = indexed_vibration[1]

        self._profile("process", vibration)

        if not self._should_process_message(message_index, vibration):
            return indexed_vibration
        self._save_processed_message_index(message_index, vibration)

        actor = self.actors[vibration.target_region][vibration.actor_index]
        
        yield from actor.set_intensity(vibration.intensity, vibration.priority)

        return indexed_vibration

    def _should_process_message(self, message_index, vibration):
        region = vibration.target_region
        actor_index = vibration.actor_index

        if region not in self.actors or actor_index not in self.actors[region]:
            self.logger.warning("No actor configured with index %d in region %s", actor_index, protocol.Vibration.Region.Name(region))
            return False

        priority = vibration.priority
        if priority in self.processed_message_indices[region][actor_index]:
            return message_index > self.processed_message_indices[region][actor_index][priority]
        else:
            return True

    def _save_processed_message_index(self, message_index, vibration):
        region = vibration.target_region
        actor_index = vibration.actor_index
        priority = vibration.priority

        self.processed_message_indices[region][actor_index][priority] = message_index


class Pattern(object):
    def __init__(self, inlet, loop=None, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self.inlet = inlet
        self.patterns = {}      # identifier -> [Tracks]
        self.samling_frequency = 10

    def load(self, indexed_pattern):
        pattern = indexed_pattern[1]
        self.logger.info("loaded pattern %s", pattern.identifier)
        self.patterns[pattern.identifier] = pattern.tracks
        return indexed_pattern

    @asyncio.coroutine
    def play(self, indexed_pattern):
        pattern = indexed_pattern[1]
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
            sleep_start = self._loop.time()
            yield from self._sleep_for_sampling_interval()
            delta_time = self._loop.time() - sleep_start

        self.logger.info("finished playing pattern %s", pattern.identifier)

        return indexed_pattern

    @asyncio.coroutine
    def _sleep_for_sampling_interval(self):
        yield from asyncio.sleep(1 / self.samling_frequency)
