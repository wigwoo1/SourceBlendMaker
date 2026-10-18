import math,unittest
from particle_distribution import rotation_angle

class Draws:
    def __init__(self,values):self.values=iter(values);self.count=0
    def random(self):self.count+=1;return next(self.values)
    def uniform(self,low,high):return low+(high-low)*self.random()

class RotationDefaults(unittest.TestCase):
    def test_present_omitted_settings_rotate_and_flip(self):
        rng=Draws([.25,.1])
        self.assertAlmostEqual(rotation_angle({'Rotation Random':{}},rng),-math.pi/2)
        self.assertEqual(rng.count,2)
    def test_absent_initializer_keeps_zero_and_does_not_sample(self):
        rng=Draws([])
        self.assertEqual(rotation_angle({},rng),0);self.assertEqual(rng.count,0)
    def test_authored_flip_disabled_and_initial_rotation(self):
        rng=Draws([.5])
        params=dict(rotation_initial=90,rotation_offset_max=180,randomly_flip_direction=False)
        self.assertAlmostEqual(rotation_angle({'Rotation Random':params},rng),math.pi)
        self.assertEqual(rng.count,1)
    def test_authored_exponent_affects_angle(self):
        rng=Draws([.5,.9])
        self.assertAlmostEqual(rotation_angle({'Rotation Random':{'rotation_random_exponent':2}},rng),math.pi/2)
    def test_fixed_bounds_still_consume_sign_draw(self):
        rng=Draws([.8,.1])
        params=dict(rotation_offset_min=90,rotation_offset_max=90)
        self.assertAlmostEqual(rotation_angle({'Rotation Random':params},rng),-math.pi/2)
        self.assertEqual(rng.count,2)

if __name__=='__main__':unittest.main()
