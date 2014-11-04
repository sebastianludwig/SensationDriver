import math

from . import protocol

# HINT this class may be specialized as VibrationTrack one day
class Track(object):
    def __init__(self, target_region, actor_index, priority, keyframes):
        self.target_region = target_region
        self.actor_index = actor_index
        self.priority = priority

        self.bezier_path = BezierPath(keyframes)
        self.timeline = self.bezier_path.timeline()
        next(self.timeline)

        self.value = 0
        self._finished = False
        self.advance(0)

    @property
    def is_finished(self):
        return self._finished

    def advance(self, seconds):
        def scale_value(value):
            return (value - self.bezier_path.min_value) / (self.bezier_path.max_value - self.bezier_path.min_value)

        if self._finished:
            return None

        try:
            self.value = scale_value(self.timeline.send(seconds))
        except StopIteration as result:
            self.value = scale_value(result.value)
            self._finished = True

        return self.value

    def create_message(self):
        vibration = protocol.Vibration()
        vibration.target_region = self.target_region
        vibration.actor_index = self.actor_index
        vibration.intensity = self.value
        vibration.priority = self.priority

        message = protocol.Message()
        message.type = protocol.Message.VIBRATION
        message.vibration.CopyFrom(vibration)

        return message


class BezierPath(object):
    def __init__(self, keyframes):
        self._keyframes = keyframes
        self.__bounds = None
        self._min_value = None
        self._max_value = None

    @property
    def _bounds(self):
        if self.__bounds is None:
            bounds = []
            for i in range(1, len(self._keyframes)):
                start = self._keyframes[i - 1]
                end = self._keyframes[i]
                bounds.append(BezierPath._calculate_bounds(start.control_point, start.out_tangent_end, end.in_tangent_start, end.control_point))
            self.__bounds = { 'left': min(b['left'] for b in bounds),
                             'top': max(b['top'] for b in bounds),
                             'right': max(b['right'] for b in bounds),
                             'bottom': min(b['bottom'] for b in bounds) }

        return self.__bounds

    @property
    def min_value(self):
        return self._bounds['bottom']

    @property
    def max_value(self):
        return self._bounds['top']


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

    # Based on: http://stackoverflow.com/questions/2587751/an-algorithm-to-find-bounding-box-of-closed-bezier-curves
    # Source: http://blog.hackers-cafe.net/2009/06/how-to-calculate-bezier-curves-bounding.html
    # Original version: NISHIO Hirokazu
    # Modifications: Timo
    # Python port: Sebastian
    def _calculate_bounds(p0, p1, p2, p3):
        tvalues = []

        for i in range(0,2):
            if i == 0:
                b = 6 * p0.time - 12 * p1.time + 6 * p2.time
                a = -3 * p0.time + 9 * p1.time - 9 * p2.time + 3 * p3.time
                c = 3 * p1.time - 3 * p0.time
            else:
                b = 6 * p0.value - 12 * p1.value + 6 * p2.value
                a = -3 * p0.value + 9 * p1.value - 9 * p2.value + 3 * p3.value
                c = 3 * p1.value - 3 * p0.value

            if abs(a) < 1e-12:
                if (abs(b) < 1e-12):
                    continue

                t = -c / b

                if 0 < t and t < 1:
                    tvalues.append(t)
                continue

            b2ac = b * b - 4 * c * a
            if b2ac < 0:
                continue
            sqrtb2ac = math.sqrt(b2ac)

            t1 = (-b + sqrtb2ac) / (2 * a)
            if 0 < t1 and t1 < 1:
                tvalues.append(t1)

            t2 = (-b - sqrtb2ac) / (2 * a)
            if 0 < t2 and t2 < 1:
                tvalues.append(t2)

        extremeties = []
        for j in range(len(tvalues) - 1, -1, -1):
            t = tvalues[j]
            mt = 1 - t
            x = (mt * mt * mt * p0.time) + (3 * mt * mt * t * p1.time) + (3 * mt * t * t * p2.time) + (t * t * t * p3.time)
            y = (mt * mt * mt * p0.value) + (3 * mt * mt * t * p1.value) + (3 * mt * t * t * p2.value) + (t * t * t * p3.value)

            extremeties.append((x, y))

        extremeties.append((p0.time, p0.value))
        extremeties.append((p3.time, p3.value))

        return { 'left': min(point[0] for point in extremeties),
                 'top': max(point[1] for point in extremeties),
                 'right': max(point[0] for point in extremeties),
                 'bottom': min(point[1] for point in extremeties) }
