"""Check measured CPU trail layout, including asymmetric signed constraints."""
import math,unittest
from particle_trail_geometry import corners


class TrailGeometryTests(unittest.TestCase):
    def test_current_to_tail_order_half_width_and_sign(self):
        positive=corners((0,0,0),(-4,0,0),2,(0,0,10))
        self.assertEqual(positive,((0,1,0),(0,-1,0),(-4,-1,0),(-4,1,0)))
        negative=corners((0,0,0),(-4,0,0),-2,(0,0,10))
        self.assertEqual(negative,tuple(positive[i] for i in (1,0,3,2)))

    def test_constraint_is_signed_and_defaults_to_enabled(self):
        for width,expected in ((8,4),(-8,8)):
            q=corners((0,0,0),(-4,0,0),width,(0,0,10))
            self.assertAlmostEqual(math.dist(q[0],q[1]),expected)
        q=corners((0,0,0),(-4,0,0),8,(0,0,10),False)
        self.assertAlmostEqual(math.dist(q[0],q[1]),8)

    def test_off_axis_side_uses_eye_not_camera_plane_normal(self):
        q=corners((3,4,5),(0,0,8),2,(0,0,10))
        self.assertEqual(q,((3.8,3.4,5),(2.2,4.6,5),(2.2,4.6,13),(3.8,3.4,13)))

    def test_zero_and_parallel_views_have_no_visible_quad(self):
        for delta,width,eye in (((0,0,0),2,(0,0,10)),((-4,0,0),0,(0,0,10)),((0,0,3),2,(0,0,10))):
            self.assertEqual(corners((0,0,0),delta,width,eye),())

    def test_invalid_geometry_does_not_enter_mesh(self):
        for width in (math.nan,math.inf):
            with self.assertRaises(ValueError):corners((0,0,0),(-4,0,0),width,(0,0,10))
