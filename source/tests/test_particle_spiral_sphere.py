import unittest,math
from particle_spiral_sphere import offset

class SpiralSphereTests(unittest.TestCase):
    def test_first_point_and_sphere_radius(self):
        p={'density':40,'initial radius':40}
        self.assertAlmostEqual(offset(0,p)[2],39)
        for i in range(40):self.assertAlmostEqual(sum(x*x for x in offset(i,p)),1600)
    def test_installed_greater_than_reset_boundary(self):
        p={'density':40,'initial radius':40}
        self.assertAlmostEqual(offset(40,p)[2],-41)
        self.assertEqual(offset(41,p),offset(0,p))
    def test_default_and_validation(self):
        self.assertEqual(offset(0,{}),(0.,0.,0.))
        for p in ({'density':.5},{'density':-1},{'initial radius':float('nan')},
                  {'Use Particle Count as Density Scale':True},
                  {'Override CP (X/Y/Z *= Radius/Density/Speed)':0}):
            with self.assertRaises(ValueError):offset(0,p)
        with self.assertRaises(ValueError):offset(-1,{})
