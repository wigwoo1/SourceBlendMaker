import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from moving_maintained import birth_clock,global_birth_time
from particle_sim import Segment

class MovingMaintainedClockTests(unittest.TestCase):
    def test_birth_position_clock_remains_fixed_between_replacements(self):
        gates=[(0,5)]
        self.assertEqual(birth_clock(.5,1,gates),0)
        self.assertEqual(birth_clock(1.5,1,gates),1)
        self.assertEqual(birth_clock(2,1,gates),2)

    def test_disabled_emission_does_not_replenish(self):
        self.assertEqual(birth_clock(3,1,[(0,.5)]),0)
        self.assertIsNone(birth_clock(0,1,[(1,2)]))

    def test_birth_time_respects_simulation_pause(self):
        segments=[Segment(0,1),Segment(1,3,simulating=False),Segment(3,5)]
        self.assertAlmostEqual(global_birth_time(segments,1.5),3.5)
        with self.assertRaises(ValueError):global_birth_time(segments,10)

    def test_creation_time_is_exact_at_first_frame(self):
        self.assertEqual(global_birth_time([Segment(5,6)],0),5)
        self.assertEqual(global_birth_time([Segment(0,2,simulating=False),Segment(2,4)],0),2)

if __name__=='__main__':unittest.main()
