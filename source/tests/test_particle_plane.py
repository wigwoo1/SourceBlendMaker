import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_plane import settings,world_plane,project
from particle_ring import angle_matrix

class PlaneTests(unittest.TestCase):
    def test_radius_clearance_and_already_above_plane(self):
        point,normal=world_plane({},angle_matrix(0,0,0),(0,0,2),1)
        self.assertEqual(project((3,4,1),.5,point,normal),(3,4,2.5))
        self.assertEqual(project((3,4,4),.5,point,normal),(3,4,4))
    def test_control_rotation_and_global_flags(self):
        point,normal=world_plane({'plane point':(1,0,0),'plane normal':(0,0,2)},angle_matrix(90,0,0),(3,4,5),2)
        self.assertAlmostEqual(point[2],3)
        self.assertAlmostEqual(normal[0],1)
        point,normal=world_plane({'global origin':True,'global normal':True,'plane point':(1,0,0)},angle_matrix(90,0,0),(3,4,5),2)
        self.assertEqual(point,(2,0,0));self.assertEqual(normal,(0,0,1))
    def test_invalid_planes_rejected(self):
        for p in ({'plane normal':(0,0,0)},{'plane point':(float('nan'),0,0)},{'control point number':64},{'operator fade oscillate':1}):
            with self.assertRaises(ValueError):settings(p)
