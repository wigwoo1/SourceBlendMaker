import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_trail_velocity import displacement


class TrailVelocityTests(unittest.TestCase):
    def test_observed_motion_takes_precedence(self):
        self.assertEqual(displacement((2,0,0),(0,5,0),.2),((2.,0.,0.),False))

    def test_static_history_uses_velocity_and_lookback(self):
        self.assertEqual(displacement((0,0,0),(0,0,-10),.25),((0.,0.,-2.5),True))

    def test_zero_velocity_keeps_static_history(self):
        self.assertEqual(displacement((0,0,0),(0,0,0),.25),((0.,0.,0.),False))

    def test_zero_lookback_does_not_create_motion(self):
        self.assertEqual(displacement((0,0,0),(0,0,10),0),((0.,0.,0.),False))

    def test_invalid_vector_or_duration_is_rejected(self):
        for args in (((1,2),(0,0,0),.1),((0,0,0),(0,0,float('nan')),.1),((0,0,0),(1,0,0),-1)):
            with self.subTest(args=args),self.assertRaises(ValueError):displacement(*args)


if __name__=='__main__':unittest.main()
