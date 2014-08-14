from utils import *

from sensationdriver.patterns import BezierPath
from sensationdriver.patterns import Track


class Point(object):
    def __init__(self, time, value):
        self.time = time
        self.value = value


class Keyframe(object):
    def __init__(self, control_point, out_tangent_end=None, in_tangent_start=None):
        self.control_point = control_point
        self.out_tangent_end = out_tangent_end
        self.in_tangent_start = in_tangent_start


class TestBezierPath(unittest.TestCase):
    def setUp(self):
        self.logger = TestLogger()

    def test_bezier_calculation(self):
        start = Point(0, 0)
        end = Point(1.8, 2)

        start_out_tangent_end = Point(0.6, 0)
        end_in_tangent_start = Point(1.2, -1.279795)

        expected_values = [
            (0.0, 0.0),
            (0.055555, -0.01084869),
            (0.111111, -0.03938968),
            (0.166666, -0.0796154),
            (0.222222, -0.1255182),
            (0.277777, -0.1710906),
            (0.333333, -0.2103248),
            (0.388888, -0.2372134),
            (0.444444, -0.2457487),
            (0.5, -0.2299231),
            (0.555555, -0.1837291),
            (0.611111, -0.101159),
            (0.666666, 0.02379485),
            (0.722222, 0.1971399),
            (0.777777, 0.4248839),
            (0.833333, 0.7130347),
            (0.888888, 1.067599),
            (0.944444, 1.494586),
            (1.0, 2)]

        for t, expected_value in expected_values:
            value = BezierPath.calculate_bezier_value(t, start, start_out_tangent_end, end_in_tangent_start, end)
            self.assertAlmostEqual(value, expected_value, delta=0.00001)

    def test_timeline(self):
        start = Point(0, 0)
        end = Point(1.8, 2)

        start_out_tangent_end = Point(0.6, 0)
        end_in_tangent_start = Point(1.2, -1.279795)

        keyframes = [Keyframe(start, out_tangent_end=start_out_tangent_end), Keyframe(end, in_tangent_start=end_in_tangent_start)]

        path = BezierPath(keyframes=keyframes)

        expected_values = [
            0.0,
            -0.01084869,
            -0.03938968,
            -0.0796154,
            -0.1255182,
            -0.1710906,
            -0.2103248,
            -0.2372134,
            -0.2457487,
            -0.2299231,
            -0.1837291,
            -0.101159,
            0.02379485,
            0.1971399,
            0.4248839,
            0.7130347,
            1.067599,
            1.494586]

        # preparation
        timeline = path.timeline()
        next(timeline)
        i = 0
        value = timeline.send(0)
        while True:
            self.assertAlmostEqual(value, expected_values[i], delta=0.00001)
            try:
                value = timeline.send(0.1)
                i += 1
            except StopIteration:
                break

    def test_multiple_keyframes(self):
        # 0 - 0.3
        #   0.1325325 - 0.3
        #   0.2650649 - 1.161977
        # 0.3975974 - 1.333954
        #   0.8650649 - 1.940549
        #   1.332533 - -0.5553294
        # 1.8 - 2
        p0 = Point(0, 0.3)
        c1 = Point(0.1325325, 0.3)
        c2 = Point(0.2650649, 1.161977)
        p3 = Point(0.3975974, 1.333954)
        c4 = Point(0.8650649, 1.940549)
        c5 = Point(1.332533, -0.5553294)
        p6 = Point(1.8, 2)

        keyframes = [Keyframe(p0, out_tangent_end=c1),
                    Keyframe(p3, in_tangent_start=c2, out_tangent_end=c4),
                    Keyframe(p6, in_tangent_start=c5)]

        path = BezierPath(keyframes=keyframes)

        expected_values = [
            0.3,
            0.438888,
            0.7567842,
            1.105537,
            1.337044,
            1.420382,
            1.427235,
            1.37534,
            1.282435,
            1.166256,
            1.044542,
            0.9350283,
            0.8554535,
            0.8235546,
            0.8570688,
            0.9737334,
            1.191285,
            1.527464]

        # preparation
        timeline = path.timeline()
        next(timeline)
        i = 0
        value = timeline.send(0)
        while True:
            self.assertAlmostEqual(value, expected_values[i], delta=0.00001)
            try:
                value = timeline.send(0.1)
                i += 1
            except StopIteration:
                break


class TestTrack(unittest.TestCase):
    def setUp(self):
        # 0 - 0.3
        #   0.1325325 - 0.3
        #   0.2650649 - 1.161977
        # 0.3975974 - 1.333954
        #   0.8650649 - 1.940549
        #   1.332533 - -0.5553294
        # 1.8 - 2
        p0 = Point(0, 0.3)
        c1 = Point(0.1325325, 0.3)
        c2 = Point(0.2650649, 1.161977)
        p3 = Point(0.3975974, 1.333954)
        c4 = Point(0.8650649, 1.940549)
        c5 = Point(1.332533, -0.5553294)
        p6 = Point(1.8, 2)

        keyframes = [Keyframe(p0, out_tangent_end=c1),
                    Keyframe(p3, in_tangent_start=c2, out_tangent_end=c4),
                    Keyframe(p6, in_tangent_start=c5)]

        self.track = Track(target_region='region', actor_index='actor_index', keyframes=keyframes, priority=4)

    def test_is_finished(self):
        self.assertFalse(self.track.is_finished)
        self.track.advance(0.5)
        self.assertFalse(self.track.is_finished)
        self.track.advance(1.3001)
        self.assertTrue(self.track.is_finished)

    def test_returns_last_value(self):
        value = 0
        while not self.track.is_finished:
            value = self.track.advance(0.3)

    def test_returns_last_value_immediatly(self):
        value = self.track.advance(4)
        self.assertAlmostEqual(value, 2, delta=0.00001)

    def test_initial_value(self):
        self.assertAlmostEqual(self.track.value, 0.3, delta=0.000001)

    def test_advance(self):
        value = self.track.advance(0.4)
        self.assertAlmostEqual(value, 1.337044, delta=0.000001)
        value = self.track.advance(0.4)
        self.assertAlmostEqual(value, 1.282435, delta=0.000001)
        value = self.track.advance(0.4)
        self.assertAlmostEqual(value, 0.8554535, delta=0.000001)

