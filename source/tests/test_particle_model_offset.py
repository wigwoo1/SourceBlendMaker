import unittest
from particle_model_offset import apply
class ModelOffsetTests(unittest.TestCase):
    def test_shifts_both_and_preserves_velocity_difference(self):
        position,previous=apply((1,2,3),(.5,1,2),(8,-4,2))
        self.assertEqual(position,(9,-2,5))
        self.assertEqual(previous,(8.5,-3,4))
        self.assertEqual(tuple(a-b for a,b in zip(position,previous)),(.5,1,1))
    def test_zero_offset_identity(self):
        self.assertEqual(apply((1,2,3),(1,2,3),(0,0,0)),((1,2,3),(1,2,3)))
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):apply((1,2,3),(1,2,3),(float('nan'),0,0))
