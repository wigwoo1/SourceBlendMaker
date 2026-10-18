import unittest
from particle_hitbox_lerp import weight,apply

class LerpTests(unittest.TestCase):
    def test_authored_interval_and_endpoint_skip(self):
        self.assertEqual(weight(.5,0,1,1),.5)
        self.assertEqual(weight(.5,0,1,.5),.25)
        self.assertEqual(weight(0,0,1,1),0)
        self.assertEqual(weight(1,0,1,1),0)
        self.assertEqual(weight(2,0,1,1),0)
    def test_current_and_previous_blend_independently(self):
        current,previous=apply((0,0,0),(2,0,0),(10,4,6),age=.5)
        self.assertEqual(current,(5,2,3));self.assertEqual(previous,(6,2,3))
    def test_invalid_inputs_rejected(self):
        for values in ((0,0,0,1),(-1,0,1,1),(.5,1,1,1),(float('nan'),0,1,1)):
            with self.assertRaises(ValueError):weight(*values)
