import unittest,math
from particle_twist import settings,acceleration,trajectory

class TwistTests(unittest.TestCase):
    def test_known_ballistic_motion_without_twist(self):
        position,velocity=trajectory({},(1,2,3),(4,5,6),1,lambda t:(0,0,0),gravity=(0,0,-10))
        for actual,expected in zip(position,(5,7,4)):self.assertAlmostEqual(actual,expected)
        for actual,expected in zip(velocity,(4,5,-4)):self.assertAlmostEqual(actual,expected)

    def test_short_time_tangent_and_translated_trajectory(self):
        p={'amount of force':4};origin=lambda t:(0,0,0)
        position,velocity=trajectory(p,(1,0,0),(0,0,0),.001,origin,step=1/10000)
        self.assertAlmostEqual(position[1],-2e-6,places=10)
        self.assertAlmostEqual(velocity[1],-.004,places=9)
        shifted,shift_velocity=trajectory(p,(8,3,2),(0,0,0),.001,lambda t:(7,3,2),step=1/10000)
        for actual,expected,offset in zip(shifted,position,(7,3,2)):self.assertAlmostEqual(actual-offset,expected)
        for actual,expected in zip(shift_velocity,velocity):self.assertAlmostEqual(actual,expected)
    def test_tangent_direction_and_translation(self):
        p={'amount of force':4}
        self.assertEqual(acceleration(p,(1,0,0),(0,0,0)),(0.,-4.,0.))
        self.assertEqual(acceleration(p,(8,3,2),(7,3,2)),(0.,-4.,0.))
        p['amount of force']=-4
        self.assertEqual(acceleration(p,(1,0,0),(0,0,0)),(0.,4.,0.))

    def test_no_radial_or_axis_acceleration(self):
        p={'amount of force':2,'twist axis':(1,2,3)}
        force=acceleration(p,(4,-2,1),(0,0,0))
        self.assertAlmostEqual(sum(a*b for a,b in zip(force,(4,-2,1))),0)
        self.assertAlmostEqual(sum(a*b for a,b in zip(force,(1,2,3))),0)
        self.assertTrue(all(math.isfinite(v) for v in force))
        self.assertEqual(acceleration(p,(0,0,0),(0,0,0)),(0.,0.,0.))

    def test_defaults_and_unverified_inputs(self):
        self.assertEqual(settings({})['control_point'],0)
        for p in ({'twist axis':(0,0,0)},{'amount of force':float('nan')},{'control point':.5},{'control point':64}):
            with self.assertRaises(ValueError):settings(p)
        with self.assertRaisesRegex(ValueError,'not yet verified'):
            acceleration({'object local space axis 0/1':True},(1,0,0),(0,0,0))
