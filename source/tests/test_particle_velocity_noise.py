import itertools,math,unittest
from particle_velocity_noise import sample,settings
from particle_noise import f32


def flat(value):
    return [list(range(256)) for _ in range(3)]+[[value]*256]


class VelocityNoiseTests(unittest.TestCase):
    def test_installed_defaults_and_independent_component_flags(self):
        self.assertEqual(settings({})['Spatial Noise Coordinate Scale'],f32(.01))
        self.assertEqual(sample({},(0,0,0),0,flat(.75)),(.75,)*3)
        for absolute,invert in itertools.product((0,1),repeat=2):
            p={'Absolute Value':[absolute]*3,'Invert Abs Value':[invert]*3}
            n=-.5
            if absolute:n=abs(n)
            if invert:n=1-n
            expected=n if absolute else n*.5+.5
            self.assertEqual(sample(p,(0,0,0),0,flat(.25)),(expected,)*3)

    def test_invert_does_not_force_absolute_or_clamp_authored_range(self):
        p={'Invert Abs Value':[1,0,0],'output minimum':[2,10,3],'output maximum':[10,-2,3]}
        self.assertEqual(sample(p,(0,0,0),0,flat(0)),(14,10,3))

    def test_local_rotation_and_timestep_do_not_apply_translation(self):
        p={'Apply Velocity in Local Space (0/1)':True,'output minimum':[2,4,6],'output maximum':[2,4,6]}
        matrix=((0,-1,0),(1,0,0),(0,0,1))
        self.assertEqual(sample(p,(200,300,400),1,flat(.5),matrix,.5),(-2,1,3))
        with self.assertRaisesRegex(ValueError,'birth control-point rotation'):sample(p,(0,0,0),0,flat(.5))

    def test_time_position_and_channels_are_correlated_and_repeatable(self):
        p={'Spatial Noise Coordinate Scale':.2}
        a=sample(p,(1.25,3.75,12),.5)
        self.assertEqual(a,sample(p,(1.25,3.75,12),.5))
        self.assertNotEqual(a,sample(p,(2.25,3.75,12),.5))
        self.assertNotEqual(a,sample(p,(1.25,3.75,12),1.5))
        self.assertGreater(len(set(a)),1)

    def test_invalid_coordinates_ranges_flags_and_control_points_fail(self):
        for p in ({'Control Point Number':-1},{'Control Point Number':64},
                  {'Control Point Number':.5},{'output maximum':[1,2]},
                  {'Absolute Value':[0,math.nan,0]},{'Time Noise Coordinate Scale':math.inf},
                  {'Spatial Coordinate Offset':[0,0,1e100]}):
            with self.subTest(p=p),self.assertRaises(ValueError):settings(p)
        for pos,time in (((0,0,math.nan),0),((0,0,0),1e100)):
            with self.assertRaises(ValueError):sample({},pos,time)
        with self.assertRaises(ValueError):sample({},(0,0,0),0,time_step=-1)


if __name__=='__main__':unittest.main()
