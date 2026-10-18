import unittest,math
from particle_pull_integrator import simulate
from particle_twist_axis import settings,acceleration

class SpatialForceTests(unittest.TestCase):
    def test_spatial_acceleration_reaches_midpoint_integration(self):
        points=[]
        def force(position,time):
            points.append(tuple(position))
            return (2,0,0)
        position,velocity=simulate((0,0,0),(0,0,0),2,lambda t:(0,0,0),0,2,spatial_force=force)
        self.assertAlmostEqual(position[0],4,places=10)
        self.assertAlmostEqual(velocity[0],4,places=10)
        self.assertGreater(max(p[0] for p in points),3)
    def test_twist_changes_motion_without_axial_acceleration(self):
        config=settings({'amount of force':2})
        position,velocity=simulate((1,0,3),(0,0,0),.1,lambda t:(0,0,0),0,2,
                                  spatial_force=lambda p,t:acceleration(config,p,(0,0,0)))
        self.assertLess(position[1],0)
        self.assertAlmostEqual(position[2],3)
        self.assertAlmostEqual(velocity[2],0)
