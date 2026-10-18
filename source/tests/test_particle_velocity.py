import math,random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_velocity import sample,validate,settings

def parameters():return {'random_speed_min':2,'random_speed_max':4,'speed_in_local_coordinate_system_min':[1,2,3],'speed_in_local_coordinate_system_max':[1,2,3],'control_point_number':2}

class VelocityTests(unittest.TestCase):
    def test_world_speed_magnitude_and_local_vector(self):
        rng=random.Random(17)
        for _ in range(100):
            world,local=sample(parameters(),rng)
            self.assertTrue(2-1e-10<=math.sqrt(sum(v*v for v in world))<=4+1e-10)
            self.assertEqual(local,(1,2,3))
        self.assertEqual(validate(parameters()),2)

    def test_reversed_local_ranges_stay_in_bounds(self):
        p=parameters();p['speed_in_local_coordinate_system_min']=[10,10,0];p['speed_in_local_coordinate_system_max']=[-10,-10,0]
        for _ in range(20):
            _,local=sample(p,random.Random(_))
            self.assertTrue(-10<=local[0]<=10 and -10<=local[1]<=10 and local[2]==0)

    def test_installed_omitted_defaults_preserve_authored_local_velocity(self):
        self.assertEqual(validate({}),0)
        self.assertEqual(sample({},random.Random(1)),((0.,0.,0.),(0.,0.,0.)))
        p={'speed_in_local_coordinate_system_min':[0,0,650],'speed_in_local_coordinate_system_max':[0,0,650]}
        self.assertEqual(sample(p,random.Random(2)),((0.,0.,0.),(0.,0.,650.)))
        self.assertNotIn('random_speed_min',p)
        self.assertEqual(settings({'random_speed_min':4})['random_speed_min'],4)

    def test_invalid_and_nonfinite_settings(self):
        for key,value in (('random_speed_min',float('nan')),('control_point_number',.5),('speed_in_local_coordinate_system_min',[0,0]),('operator end fadeout',1)):
            p=parameters();p[key]=value
            with self.assertRaises(ValueError):validate(p)
