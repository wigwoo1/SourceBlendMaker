import math,unittest
from particle_orientation import validate,world_corners,upright_corners,upright_normal,world_plane_yaw,sample_world_plane_yaw

class OrientationTests(unittest.TestCase):
    def test_authored_plane_and_quarter_turn(self):
        self.assertEqual(world_corners((3,4,5),2,0),((5,6,5),(5,2,5),(1,2,5),(1,6,5)))
        actual=world_corners((0,0,0),1,math.pi/2)
        expected=((1,-1,0),(-1,-1,0),(-1,1,0),(1,1,0))
        for a,b in zip(actual,expected):
            for x,y in zip(a,b):self.assertAlmostEqual(x,y)
    def test_rotation_preserves_square_and_plane(self):
        for angle in (.123,1.7,-2.3):
            points=world_corners((0,0,7),3,angle)
            for i,p in enumerate(points):
                self.assertEqual(p[2],7)
                self.assertAlmostEqual(p[0]**2+p[1]**2,18)
                q=points[(i+1)%4]
                self.assertAlmostEqual(sum((a-b)**2 for a,b in zip(p,q)),36)
    def test_unverified_modes_rejected(self):
        self.assertEqual(validate({'orientation_type':2,'orientation control point':-1},'render_animated_sprites'),2)
        self.assertEqual(validate({'orientation_type':2,'orientation control point':0},'render_animated_sprites'),2)
        self.assertEqual(validate({'orientation_type':1},'render_animated_sprites'),1)
        for renderer,function in (({'orientation_type':3},'render_animated_sprites'),({'orientation_type':1,'orientation control point':0},'render_animated_sprites'),({'orientation_type':1},'render_rope'),({'orientation_type':2,'orientation control point':64},'render_animated_sprites'),({'orientation_type':2,'orientation control point':.5},'render_animated_sprites'),({'orientation_type':2},'render_rope')):
            with self.assertRaises(ValueError):validate(renderer,function)
    def test_upright_geometry_and_normal(self):
        self.assertEqual(upright_corners((0,0,0),2,0,(1,0,3)),((0,-2,-2),(0,-2,2),(0,2,2),(0,2,-2)))
        self.assertEqual(upright_normal((2,0,5)),(1,0,0))
        for angle in (.7,-1.2):
            points=upright_corners((3,4,5),2,angle,(2,3,4))
            for a,b in zip(points,points[1:]+points[:1]):self.assertAlmostEqual(math.dist(a,b),4)
    def test_upright_degenerate_and_invalid_inputs(self):
        for camera in ((0,0,1),(float('nan'),1,0),(1,2)):
            with self.assertRaises(ValueError):upright_corners((0,0,0),2,0,camera)
        with self.assertRaises(ValueError):upright_corners((0,0,0),-1,0,(1,0,0))
    def test_world_plane_yaw_defaults_and_ordered_range(self):
        self.assertEqual(world_plane_yaw({'function':'Rotation Yaw Random','parameters':{}},2,'render_animated_sprites'),{'yaw_initial':0.,'yaw_offset_min':0.,'yaw_offset_max':360.,'yaw_random_exponent':1.})
        self.assertEqual(world_plane_yaw({'parameters':{}},1,'render_animated_sprites')['yaw_initial'],0.)
        self.assertEqual(world_plane_yaw({'parameters':{}},2,'render_animated_sprites',0)['yaw_initial'],0.)
        with self.assertRaises(ValueError):world_plane_yaw({'parameters':{}},0,'render_animated_sprites')
        self.assertEqual(world_plane_yaw({'parameters':{}},0,'render_animated_sprites',spritecard=True)['yaw_initial'],0.)
        with self.assertRaises(ValueError):world_plane_yaw({'parameters':{'operator start fadein':.1}},2,'render_animated_sprites')
        with self.assertRaises(ValueError):world_plane_yaw({'parameters':{'yaw_random_exponent':0}},2,'render_animated_sprites')
        import random
        p={'yaw_initial':15.,'yaw_offset_min':-45.,'yaw_offset_max':45.,'yaw_random_exponent':1.}
        value=sample_world_plane_yaw(p,random.Random(31))
        self.assertGreaterEqual(value,math.radians(-30));self.assertLessEqual(value,math.radians(60))
