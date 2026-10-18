import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_dual_sequence_blend import combine


class DualSequenceBlendTests(unittest.TestCase):
    def test_mode_one_uses_secondary_color_even_when_its_alpha_is_zero(self):
        self.assertEqual(combine((0,0,1,1),(1,0,0,0),1),(1,0,0,1))

    def test_mode_two_retains_primary_opacity(self):
        self.assertEqual(combine((0,0,1,.2),(1,0,0,1),2),(1,0,0,.2))
        self.assertEqual(combine((0,0,1,.2),(1,0,0,0),2),(0,0,1,.2))

    def test_mode_zero_is_symmetric_including_alpha(self):
        a,b=(.1,.2,.3,.4),(.7,.8,.9,.8)
        self.assertEqual(combine(a,b,0),combine(b,a,0))
        self.assertAlmostEqual(combine(a,b,0)[3],.6)

    def test_invalid_samples_and_modes_are_explicit(self):
        for mode in (-1,3,True,'1'):
            with self.assertRaises(ValueError):combine((0,0,0,1),(1,1,1,1),mode)
        for bad in ((0,0,1),(0,0,float('nan'),1),(1,1,1,-.1),(1,1,1,1.1)):
            with self.assertRaises(ValueError):combine(bad,(1,1,1,1),0)
