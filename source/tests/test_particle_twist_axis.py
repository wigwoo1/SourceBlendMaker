import math,unittest
from particle_twist_axis import settings,acceleration

class TwistAxisTests(unittest.TestCase):
    def test_direction_and_distance_independence(self):
        config=settings({'amount of force':4,'twist axis':[0,0,2]})
        self.assertEqual(acceleration(config,(1,0,0),(0,0,0)),(0.,-4.,0.))
        self.assertEqual(acceleration(config,(100,0,0),(0,0,0)),(0.,-4.,0.))
        self.assertEqual(acceleration(config,(2,1,0),(1,1,0)),(0.,-4.,0.))
    def test_installed_reduction_and_axis_guard(self):
        config=settings({'amount of force':1})
        self.assertAlmostEqual(acceleration(config,(1,0,1),(0,0,0))[1],-1/math.sqrt(2))
        self.assertEqual(acceleration(config,(0,0,1),(0,0,0)),(0.,0.,0.))
        self.assertEqual(acceleration(config,(0,0,0),(0,0,0)),(0.,0.,0.))
    def test_invalid_settings(self):
        for p in ({'twist axis':[0,0,0]},{'control point':.5},
                  {'object local space axis 0/1':True},{'amount of force':float('nan')}):
            with self.assertRaises(ValueError):settings(p)
