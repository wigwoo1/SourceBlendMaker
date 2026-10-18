import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_ring import even_angle,identity_sample,angle_matrix,rotate,transformed_sample,settings

class RingTests(unittest.TestCase):
    def test_random_ring_counter_phase(self):
        p={'initial radius':40,'min initial speed':10,'max initial speed':10}
        point,velocity=transformed_sample(1,p,1,10,angle_matrix(0,0,0),(3,4,5),random_fraction=.25)
        self.assertAlmostEqual(point[0],-37)
        self.assertAlmostEqual(point[1],4)
        self.assertAlmostEqual(point[2],5)
        self.assertAlmostEqual(velocity[0],-10)
    def test_random_ring_radius_and_transform(self):
        for index in range(50):
            point,velocity=transformed_sample(index,{'initial radius':40,'XY velocity only':False},1,6,angle_matrix(45,30,20),(0,0,0),random_fraction=index/50)
            self.assertAlmostEqual(math.hypot(*point),40)
            self.assertAlmostEqual(math.hypot(*velocity),6)
    def test_random_ring_rejects_unimplemented_or_nonfinite(self):
        for p,f in (({'thickness':1},.5),({'Override CP 2 (X/Y/Z *= Pitch/Yaw/Roll)':0},.5),({},float('nan')),({},None),({},1.1)):
            with self.assertRaises(ValueError):transformed_sample(0,p,1,0,angle_matrix(0,0,0),(0,0,0),random_fraction=f)
    def test_installed_defaults_preserve_authored_values(self):
        authored={'even distribution':True,'initial radius':30,'max initial speed':600}
        result=settings(authored)
        self.assertEqual(result['even distribution count'],-1)
        self.assertEqual(result['control point number'],0)
        self.assertTrue(result['XY velocity only'])
        self.assertEqual(result['initial radius'],30)
        self.assertNotIn('thickness',authored)
        for p in ({'control point number':64},{'initial radius':float('nan')},{'min initial speed':2,'max initial speed':1}):
            with self.assertRaises(ValueError):settings(p)
    def test_source_angle_axes(self):
        cases=((0,90,0,(0,1,0)),(90,0,0,(0,0,-1)),(0,0,90,(1,0,0)))
        for pitch,yaw,roll,expected in cases:
            actual=rotate(angle_matrix(pitch,yaw,roll),(1,0,0))
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b)
    def test_transformed_ring_and_xy_velocity(self):
        p={'even distribution':True,'even distribution count':4,'initial radius':2,'roll':90}
        position,velocity=transformed_sample(0,p,4,10,angle_matrix(0,0,0),(3,4,5))
        self.assertAlmostEqual(position[2],7)
        self.assertEqual(velocity[2],0)
        p['XY velocity only']=False
        position,velocity=transformed_sample(0,p,4,10,angle_matrix(0,0,0),(3,4,5))
        self.assertAlmostEqual(velocity[2],10)
    def test_counter_phase_and_batch_fallback(self):
        self.assertAlmostEqual(even_angle(0,4,8),math.pi/2)
        self.assertAlmostEqual(even_angle(3,4,8),math.tau)
        self.assertAlmostEqual(even_angle(0,-1,8),math.pi/4)
    def test_identity_radius_and_radial_velocity(self):
        for index in range(75):
            point,velocity=identity_sample(index,{'even distribution':True,'even distribution count':75,'initial radius':30},100,600)
            self.assertAlmostEqual(math.hypot(*point),30)
            self.assertAlmostEqual(math.hypot(*velocity),600)
            self.assertAlmostEqual(point[0]*velocity[1]-point[1]*velocity[0],0,places=8)
    def test_unverified_features_rejected(self):
        for params in ({},{'even distribution':True,'thickness':1},{'even distribution':True,'pitch':45}):
            with self.assertRaises(ValueError):identity_sample(0,params,75,600)
