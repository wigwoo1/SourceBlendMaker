import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_spin import angle,settings

class SpinTests(unittest.TestCase):
    def test_constant_spin(self):
        self.assertAlmostEqual(math.degrees(angle({'spin_rate_degrees':-20},3)),-60)
    def test_stops_without_angle_jump(self):
        p={'spin_rate_degrees':10,'spin_stop_time':2}
        self.assertAlmostEqual(math.degrees(angle(p,1)),7.5)
        self.assertAlmostEqual(math.degrees(angle(p,2)),10)
        self.assertAlmostEqual(math.degrees(angle(p,5)),10)
    def test_minimum_rate_continues(self):
        p={'spin_rate_degrees':-10,'spin_stop_time':2,'spin_rate_min':-2}
        self.assertAlmostEqual(math.degrees(angle(p,2)),-12)
        self.assertAlmostEqual(math.degrees(angle(p,4)),-16)
    def test_invalid_parameters(self):
        for p in ({'spin_stop_time':-1},{'spin_rate_degrees':float('nan')},{'spin_rate_min':float('inf')}):
            with self.assertRaises(ValueError):settings(p)
    def test_collection_fade_depends_on_birth_time(self):
        p={'spin_rate_degrees':10,'operator start fadeout':5,'operator end fadeout':7}
        self.assertAlmostEqual(math.degrees(angle(p,10)),60)
        self.assertAlmostEqual(math.degrees(angle(p,3,6)),2.5)
        self.assertAlmostEqual(math.degrees(angle(p,3,8)),0)
    def test_slowdown_times_fade(self):
        p={'spin_rate_degrees':10,'spin_stop_time':2,'operator end fadein':2}
        self.assertAlmostEqual(math.degrees(angle(p,2)),10/3)
    def test_unsupported_fade_rejected(self):
        with self.assertRaises(ValueError):angle({'operator fade oscillate':1},2)
