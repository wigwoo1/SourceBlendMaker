import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from particle_initial import prepend, validate_count, creation_time
from particle_sim import Birth, Segment, continuous_births, living


class InitialParticleTests(unittest.TestCase):
    def test_initial_particles_are_independent_of_emission_gate(self):
        segments = [Segment(5., 6., emitting=False)]
        births = prepend(continuous_births(segments, 10), 3, 5.)
        self.assertEqual([(b.index, b.time, age) for b, age in living(births, segments, 5.5, 1.)],
                         [(0, 5., .5), (1, 5., .5), (2, 5., .5)])
        self.assertEqual(living(births, segments, 6., 1.), [])

    def test_paused_simulation_keeps_initial_particles_alive(self):
        segments = [Segment(0., 4., emitting=False, simulating=False)]
        self.assertEqual(len(living(prepend([], 2, 0.), segments, 3., .1)), 2)

    def test_emitter_births_keep_clocks_and_unique_indices(self):
        result = prepend([Birth(0, .25, .25), Birth(1, .5, .5)], 2, 0.)
        self.assertEqual(result, [Birth(0, 0., 0.), Birth(1, 0., 0.), Birth(2, .25, .25), Birth(3, .5, .5)])
        self.assertEqual(prepend(result[2:], 0, 0.), [Birth(0, .25, .25), Birth(1, .5, .5)])

    def test_invalid_count_or_clock(self):
        for count in (-1, .5, float('nan'), float('inf'), 100001):
            with self.assertRaises(ValueError): validate_count(count)
        with self.assertRaises(ValueError): prepend([], 1, float('nan'))
        with self.assertRaises(ValueError): prepend([Birth(0, -1., 0.)], 1, 0.)

    def test_delayed_creation_uses_parent_simulation_clock(self):
        segments = [Segment(5., 6., speed_start=2., speed_end=2.),
                    Segment(6., 9., simulating=False), Segment(9., 11.)]
        self.assertAlmostEqual(creation_time(segments, 1.), 5.5)
        self.assertAlmostEqual(creation_time(segments, 2.), 6.)
        self.assertAlmostEqual(creation_time(segments, 3.), 10.)
        self.assertIsNone(creation_time(segments, 5.))
        self.assertEqual(creation_time(segments, 0.), 5.)

    def test_speed_ramp_and_unreached_delays(self):
        self.assertAlmostEqual(creation_time([Segment(0., 2., speed_start=0., speed_end=2.)], .5), 1.)
        self.assertIsNone(creation_time([], 0.))
        self.assertIsNone(creation_time([Segment(0., 2., simulating=False)], 1.))
        for delay in (-1., float('nan'), float('inf')):
            with self.assertRaises(ValueError): creation_time([Segment(0., 1.)], delay)
