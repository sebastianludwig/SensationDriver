import yaml
import asyncio

from . import pipeline
from . import protocol
from .actor import VibrationMotor
from .pattern import Track


class Vibration(pipeline.Element):
    def __init__(self, actor_config, downstream=None, logger=None):
        super().__init__(downstream=downstream, logger=logger)

        self._actor_config = actor_config

    def process_actor_config(self):
        self.drivers = self._actor_config['drivers']
        for driver in self.drivers:
            # TODO use ALLCALL address to set PWM frequency
            driver.setPWMFreq(1200)                        # Set frequency to a little above 1133 Hz, to get near linear motor control


        self.actors = {}
        for region_name, actors in self._actor_config['regions'].items():
            try:
                region_index = protocol.Vibration.Region.Value(region_name)

                region_actors = {}
                for actor in actors:
                    region_actors[actor.index_in_region] = actor
                
                self.actors[region_index] = region_actors
            except ValueError:
                if self.logger is not None:
                    self.logger.error("Region with unknown name '%s' configured - ignoring region", region_name)
                continue

    def _set_up(self):
        self.process_actor_config()

        for driver in self.drivers:
            driver.setAllPWM(0, 0)
        # TODO reset all actor objects to match the driver value

        if self.profiler is not None:
            for region_index, region_actors in self.actors.items():
                for index, actor in region_actors.items():
                    actor.profiler = self.profiler

    def _tear_down(self):
        for driver in self.drivers:
            driver.setAllPWM(0, 0)

    @asyncio.coroutine
    def _process_single(self, vibration):
        self._profile("process", vibration)

        region = vibration.target_region
        actor_index = vibration.actor_index

        if region not in self.actors or actor_index not in self.actors[region]:
            if self.logger is not None:
                self.logger.warning("No actor configured with index %d in region %s", actor_index, protocol.Vibration.Region.Name(region))
            return vibration

        actor = self.actors[vibration.target_region][vibration.actor_index]
        
        yield from actor.set_intensity(vibration.intensity, vibration.priority)

        return vibration


class Pattern(object):
    def __init__(self, inlet, loop=None, logger=None):
        self.logger = logger
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self.inlet = inlet
        self.patterns = {}      # identifier -> [Tracks]
        self.samling_frequency = 10

    def load(self, pattern):
        if self.logger is not None:
            self.logger.info("loaded pattern %s", pattern.identifier)
        self.patterns[pattern.identifier] = pattern.tracks
        return pattern

    def play(self, pattern):
        if self.logger is not None:
            self.logger.info("play pattern %s", pattern.identifier)
        if not pattern.identifier in self.patterns:
            if self.logger is not None:
                self.logger.warning("Unknown pattern to play: %s", pattern.identifier)
            return pattern

        tracks = []
        for track in self.patterns[pattern.identifier]:
            tracks.append(Track(target_region=track.target_region, actor_index=track.actor_index, priority=pattern.priority, keyframes=track.keyframes))

        return asyncio.Task(self._sample_tracks(tracks), loop=self._loop)

    @asyncio.coroutine    
    def _sample_tracks(self, tracks):
        if self.logger is not None:
            self.logger.info("playing %d tracks", len(tracks))
        delta_time = 0
        loop = self._loop
        while tracks:
            messages = []
            for track in tracks:
                track.advance(delta_time)

                messages.append(track.create_message())

            yield from self.inlet.process(messages)

            tracks = [t for t in tracks if not t.is_finished]
            sleep_start = loop.time()
            yield from self._sleep_for_sampling_interval()      # TODO: improve this: measure the time needed to reduce sleeping time
            delta_time = loop.time() - sleep_start

        if self.logger is not None:
            self.logger.info("finished playing pattern %s", pattern.identifier)

    @asyncio.coroutine
    def _sleep_for_sampling_interval(self):
        yield from asyncio.sleep(1 / self.samling_frequency)
