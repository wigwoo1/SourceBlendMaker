import unittest
from particle_bone_lock import apply,weight

class BoneLockTests(unittest.TestCase):
    def test_default_zero_end_keeps_model_delta(self):
        self.assertEqual(weight(20,.125),1.)
        self.assertEqual(apply((4,0,0),(3,0,0),(0,0,0),(2,0,0),age=20,step=.125),((6,0,0),(5,0,0)))
    def test_newborn_fraction_and_fade_strength(self):
        self.assertEqual(weight(.0625,.125),.5)
        self.assertEqual(weight(.5,.125,0,1,.5),.25)
        self.assertEqual(weight(.25,.125,.5,1,0),1.)
        self.assertEqual(weight(1,.125,0,1),0.)
    def test_bypass_keeps_delta_past_fade_and_ignores_strength(self):
        self.assertEqual(weight(2,.125,0,1,0,bypass=True),1.)
    def test_rigid_snaps_both_buffers_but_respects_endpoint_skip(self):
        args=((4,0,0),(3,0,0),(0,0,0),(2,7,9))
        self.assertEqual(apply(*args,age=.5,step=.125,rigid=True),((2,7,9),(2,7,9)))
        self.assertEqual(apply(*args,age=1,step=.125,end=1,rigid=True),args[:2])
    def test_delta_preserves_existing_velocity(self):
        current,previous=apply((10,5,0),(8,4,0),(0,0,0),(3,2,1),age=.5,step=.125)
        self.assertEqual(tuple(a-b for a,b in zip(current,previous)),(2,1,0))
    def test_invalid_clock_rejected(self):
        for age,step in ((-1,.1),(0,0),(0,float('nan'))):
            with self.assertRaises(ValueError):weight(age,step)
