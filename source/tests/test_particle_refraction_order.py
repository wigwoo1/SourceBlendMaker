import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_refraction_order import back_to_front

class OrderTests(unittest.TestCase):
    def test_view_depth_not_radial_distance(self):
        self.assertEqual(back_to_front([(100,0,-1),(0,0,-5)],(0,0,0),(0,0,-1)),[1,0])
    def test_equal_depth_is_stable(self):
        self.assertEqual(back_to_front([(1,0,-2),(-1,0,-2)],(0,0,0),(0,0,-1)),[0,1])
    def test_camera_rotation_and_translation(self):
        self.assertEqual(back_to_front([(12,0,0),(15,0,0),(9,0,0)],(10,0,0),(2,0,0)),[1,0,2])
    def test_invalid_coordinates(self):
        for camera,forward in (((0,0),(0,0,1)),((0,0,0),(0,0,0)),((0,0,0),(0,float('nan'),1))):
            with self.assertRaises(ValueError):back_to_front([(0,0,0)],camera,forward)
