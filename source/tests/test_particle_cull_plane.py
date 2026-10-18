import unittest
from particle_cull_plane import plane,negative_side

class CullPlaneGeometryTests(unittest.TestCase):
    def test_default_plane_kills_negative_z(self):
        p=plane((0,0,0))
        self.assertTrue(negative_side((0,0,-1),p))
        self.assertFalse(negative_side((0,0,1),p))
        self.assertFalse(negative_side((0,0,0),p))

    def test_positive_offset_moves_plane_opposite_normal(self):
        p=plane((0,0,0),offset=8)
        self.assertEqual(p[0],(0.,0.,-8.))
        self.assertTrue(negative_side((0,0,-9),p))
        self.assertFalse(negative_side((0,0,-7),p))

    def test_offset_uses_normalized_world_normal(self):
        a=plane((1,2,3),(0,0,2),4)
        b=plane((1,2,3),(0,0,1),4)
        self.assertEqual(a,b)
        self.assertEqual(a[0],(1.,2.,-1.))

    def test_control_point_translation_is_applied(self):
        p=plane((10,20,30),offset=8)
        self.assertTrue(negative_side((10,20,21),p))
        self.assertFalse(negative_side((10,20,23),p))

    def test_reversed_normal_reverses_killed_side(self):
        p=plane((0,0,0),(0,0,-1))
        self.assertTrue(negative_side((0,0,1),p))
        self.assertFalse(negative_side((0,0,-1),p))

    def test_no_prior_crossing_is_required(self):
        self.assertTrue(negative_side((0,0,-100),plane((0,0,0))))

    def test_degenerate_or_nonfinite_input_is_rejected(self):
        for normal in ((0,0,0),(0,0,float('nan'))):
            with self.assertRaises(ValueError):plane((0,0,0),normal)
        with self.assertRaises(ValueError):negative_side((0,0,float('inf')),plane((0,0,0)))

if __name__=='__main__':unittest.main()
