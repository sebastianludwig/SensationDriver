from .protocol import sensationprotocol_pb2 as sensationprotocol

# HINT this class may be specialized as VibrationTrack one day
class Track(object):
    def __init__(self, target_region, actor_index, priority, keyframes):
        self.target_region = target_region
        self.actor_index = actor_index
        self.priority = priority

        bezier_path = BezierPath(keyframes)
        self.timeline = bezier_path.timeline()
        next(self.timeline)

        self.value = 0
        self._finished = False
        self.advance(0)

    @property
    def is_finished(self):
        return self._finished

    def advance(self, seconds):
        if self._finished:
            return None

        try:
            self.value = self.timeline.send(seconds)
        except StopIteration as result:
            self.value = result.value
            self._finished = True

        return self.value

    def create_message(self):
        vibration = sensationprotocol.Vibration()
        vibration.target_region = self.target_region
        vibration.actor_index = self.actor_index
        vibration.intensity = self.value
        vibration.priority = self.priority

        message = sensationprotocol.Message()
        message.type = sensationprotocol.Message.VIBRATION
        message.vibration.CopyFrom(vibration)

        return message


class BezierPath(object):
    # TODO get min and max values http://stackoverflow.com/questions/2587751/an-algorithm-to-find-bounding-box-of-closed-bezier-curves

    def __init__(self, keyframes):
        self._keyframes = keyframes

    # returns a generator
    # call send(timespan) on the generator to advance the sampling by timespan seconds
    # and receive value at the new time. StopIteration is raised, once the time advanced
    # past the path's total time.
    #
    # usage:
    #   timeline = path.timeline()
    #   next(timeline)
    #   value = timeline.send(0)
    def timeline(self):
        time = 0
        current_end = 1
        start = self._keyframes[0]
        end = self._keyframes[current_end]

        while time <= self._keyframes[-1].control_point.time:
            # advance keyframe pair
            while time > end.control_point.time:
                current_end += 1
                start = end
                end = self._keyframes[current_end]

            t = (time - start.control_point.time) / (end.control_point.time - start.control_point.time)
            # yield returns the right side and receives
            time += yield BezierPath.calculate_bezier_value(t, start.control_point, start.out_tangent_end, end.in_tangent_start, end.control_point)
        return self._keyframes[-1].control_point.value

    #
    #  1 ___ 2
    #  |/   \|
    #  0     3
    # t varies from 0..1
    def calculate_bezier_value(t, p0, p1, p2, p3):
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        # p = uuu * p0
        p = p0.value * uuu

        # p += 3 * uu * t * p1
        p += 3 * uu * t * p1.value

        # p += 3 * u * tt * p2
        p += 3 * u * tt * p2.value

        # p += ttt * p3
        p += p3.value * ttt

        return p

