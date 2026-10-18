import math
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ik import solve,length,sub,dot

class IKTests(unittest.TestCase):
    def check_lengths(self,result,root):
        self.assertAlmostEqual(length(sub(result['knee'],root)),result['upper_length'],places=7)
        self.assertAlmostEqual(length(sub(result['end'],result['knee'])),result['lower_length'],places=7)

    def test_reachable_target_and_pole_side(self):
        for side in (-1,1):
            result=solve((0,0,0),(1,0,0),(2,0,0),(1,0,0),(0,side,0))
            self.check_lengths(result,(0,0,0));self.assertFalse(result['clamped'])
            self.assertAlmostEqual(result['knee'][0],.5)
            self.assertAlmostEqual(result['knee'][1],side*math.sqrt(.75))
            self.assertEqual(result['end'],(1.,0.,0.))

    def test_unreachable_and_source_limits(self):
        for limits,expected in [(False,2),(True,1.9996)]:
            result=solve((0,0,0),(1,0,0),(2,0,0),(10,0,0),(0,1,0),limits)
            self.check_lengths(result,(0,0,0));self.assertTrue(result['clamped'])
            self.assertAlmostEqual(result['end'][0],expected)
        result=solve((0,0,0),(2,0,0),(3,0,0),(.1,0,0),(0,1,0),True)
        self.check_lengths(result,(0,0,0));self.assertAlmostEqual(result['end'][0],1.15)

    def test_singular_pole_and_target(self):
        for target in [(0,0,0),(1,0,0)]:
            result=solve((0,0,0),(1,0,0),(2,0,0),target,(3,0,0))
            self.check_lengths(result,(0,0,0))
            self.assertTrue(all(math.isfinite(x) for x in result['knee']))

    def test_degenerate_input_rejected(self):
        with self.assertRaises(ValueError):solve((0,0,0),(0,0,0),(1,0,0),(1,0,0),(0,1,0))
        with self.assertRaises(ValueError):solve((0,0,0),(1,0,0),(2,0,0),(math.nan,0,0),(0,1,0))
