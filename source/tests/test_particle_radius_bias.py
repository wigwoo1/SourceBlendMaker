import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_radius_bias import interpolate

class RadiusBiasTests(unittest.TestCase):
    def test_rational_off_midpoint(self):
        self.assertAlmostEqual(interpolate(.25,.1),1/28)
        self.assertAlmostEqual(interpolate(.75,.9),27/28)
    def test_ease_ignores_bias(self):
        for bias in (0,.1,.5,.9,1):self.assertAlmostEqual(interpolate(.25,bias,True),.15625)
    def test_zero_default_and_endpoints(self):
        self.assertEqual(interpolate(.25,0),.25)
        for bias in (0,.1,.5,1):
            self.assertEqual(interpolate(0,bias),0)
            self.assertEqual(interpolate(1,bias),1)
    def test_invalid_bias(self):
        for bias in (-1,2,float('nan')):
            with self.assertRaises(ValueError):interpolate(.5,bias)
