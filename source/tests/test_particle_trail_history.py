import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from particle_sim import Birth, Segment
from particle_trail_history import previous_time


class TrailHistoryTests(unittest.TestCase):
    def test_lookback_uses_simulation_clock_with_pause(self):
        segments = [Segment(0, 1), Segment(1, 2, simulating=False), Segment(2, 3)]
        birth = Birth(0, 0, 0)
        self.assertAlmostEqual(previous_time(segments, birth, 2.5, 1.5, 1), .5)
        self.assertEqual(previous_time(segments, birth, 2.5, 1.5, 2), 0)

    def test_ramp_and_zero_lookback(self):
        segments = [Segment(0, 2, speed_start=0, speed_end=2)]
        birth = Birth(0, 0, 0)
        self.assertAlmostEqual(previous_time(segments, birth, 2, 2, 1.5), 1)
        self.assertEqual(previous_time(segments, birth, 2, 2, 0), 2)
