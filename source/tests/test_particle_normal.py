import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_normal import align,offset,locked
from particle_ring import angle_matrix

class NormalTests(unittest.TestCase):
    def test_lock_newborn_fraction_is_not_normalized(self):
        identity=angle_matrix(0,0,0);turned=angle_matrix(0,90,0)
        result=locked((1,0,0),identity,turned,.005,.01)
        self.assertAlmostEqual(result[0],.5);self.assertAlmostEqual(result[1],.5)
        self.assertAlmostEqual(math.hypot(*result),math.sqrt(.5))
        self.assertEqual(locked((1,0,0),identity,turned,0,.01),(1,0,0))
    def test_lock_relative_rotation_and_age_saturation(self):
        previous=angle_matrix(0,45,0);current=angle_matrix(0,135,0)
        result=locked((1,0,0),previous,current,1,.01)
        self.assertAlmostEqual(result[0],0);self.assertAlmostEqual(result[1],1)
        result=locked((1,2,3),previous,previous,1,.01)
        for actual,expected in zip(result,(1,2,3)):self.assertAlmostEqual(actual,expected)
        with self.assertRaises(ValueError):locked((1,0,0),previous,current,1,0)
    def test_authored_ring_offset_identity(self):
        normal=offset(align((1,0,0)),(0,0,1),{'offset in local space 0/1':True,'normalize output 0/1':True},angle_matrix(0,0,0))
        self.assertAlmostEqual(normal[0],1/math.sqrt(2));self.assertAlmostEqual(normal[2],1/math.sqrt(2))
        self.assertAlmostEqual(math.hypot(*normal),1)
    def test_local_rotation_and_world_offset(self):
        p={'offset in local space 0/1':True}
        result=offset((0,0,0),(1,0,0),p,angle_matrix(0,90,0))
        self.assertAlmostEqual(result[0],0);self.assertAlmostEqual(result[1],1)
        self.assertEqual(offset((1,0,0),(0,0,1),{}),(1,0,1))
    def test_zero_and_invalid_vectors(self):
        self.assertEqual(offset((1,0,0),(-1,0,0),{'normalize output 0/1':True}),(0,0,0))
        with self.assertRaises(ValueError):align((float('nan'),0,0))
        with self.assertRaises(ValueError):offset((1,0,0),(0,0,1),{'offset in local space 0/1':True})
