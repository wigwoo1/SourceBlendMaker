import unittest
from particle_plane_force import acceleration

class PlaneForceTests(unittest.TestCase):
    def test_signed_distance_clamp_and_control_origin(self):
        p={'Force at Min distance':(0,0,-2),'Force at Max distance':(0,0,2),'Max Distance from plane':10}
        self.assertEqual(acceleration((0,0,7),(0,0,2),p),(0,0,0))
        self.assertEqual(acceleration((0,0,-10),(0,0,0),p),(0,0,-2))
        self.assertEqual(acceleration((0,0,20),(0,0,0),p),(0,0,2))
    def test_quantized_exponent_and_unnormalized_normal(self):
        p={'Force at Max distance':(1,0,0),'Exponent':1.24,'Plane Normal':(0,0,2)}
        self.assertEqual(acceleration((0,0,.25),(0,0,0),p),(.5,0,0))
    def test_equal_distance_and_invalid_parameters(self):
        self.assertEqual(acceleration((0,0,1),(0,0,0),{'Max Distance from plane':0}), (0,0,0))
        with self.assertRaises(ValueError):acceleration((0,0,1),(0,0,0),{'Exponent':-1})
