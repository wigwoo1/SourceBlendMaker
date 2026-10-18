import unittest
from particle_plane_force_motion import simulate

class PlaneMotionTests(unittest.TestCase):
    def test_constant_force_matches_analytic_motion(self):
        p={'Force at Min distance':(0,0,2),'Force at Max distance':(0,0,2)}
        point,speed=simulate((0,0,0),(1,0,0),2,[p],lambda cp,t:(0,0,0))
        for a,b in zip(point,(2,0,4)):self.assertAlmostEqual(a,b,places=10)
        self.assertAlmostEqual(speed[2],4,places=10)
    def test_animated_control_sampled_in_birth_clock(self):
        calls=[]
        def target(cp,t):calls.append((cp,t));return (0,0,t)
        p={'Control point number':2,'Force at Max distance':(0,0,1)}
        simulate((0,0,10),(0,0,0),.02,[p],target,birth_clock=3)
        self.assertTrue(calls);self.assertTrue(all(cp==2 and 3<=t<=3.02 for cp,t in calls))
