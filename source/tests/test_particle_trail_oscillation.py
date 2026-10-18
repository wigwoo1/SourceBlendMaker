import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_oscillation import trail_duration


class TrailOscillationTests(unittest.TestCase):
    def test_trail_oscillation_does_not_change_opacity_or_radius(self):
        from particle_bake import appearance
        p={'oscillation field':10,'oscillation rate':-10,'oscillation frequency':0,'oscillation start phase':math.pi/4}
        d={'modules':{'operators':[{'function':'Oscillate Scalar Simple','parameters':p}]}}
        self.assertEqual(appearance(d,.5,1,3),(3,1))

    def test_trail_duration_matches_independent_integration(self):
        p={'oscillation field':10,'oscillation rate':.5,'oscillation frequency':9}
        d={'modules':{'operators':[{'function':'Oscillate Scalar Simple','parameters':p}]}}
        count=20000;age=.27;step=age/count
        expected=.1+sum(.5*math.sin(1+18*(i+.5)*step)*step for i in range(count))
        self.assertAlmostEqual(trail_duration(d,.1,age),expected,places=8)
        self.assertEqual(trail_duration(d,.1,0),.1)
        self.assertAlmostEqual(trail_duration(d,.1,math.tau/18),.1)

    def test_negative_duration_clamped_and_disabled_ignored(self):
        p={'oscillation field':10,'oscillation rate':-10,'oscillation frequency':0,'oscillation start phase':math.pi/4}
        d={'modules':{'operators':[{'function':'Oscillate Scalar Simple','parameters':p}]}}
        self.assertEqual(trail_duration(d,.1,1),0)
        p['operator enabled']=False
        self.assertEqual(trail_duration(d,.1,1),.1)
