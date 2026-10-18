import math
import random
import unittest
from particle_spritecard_geometry import corners, settings
from particle_yaw import PI32, flip, sample


def module(name, **parameters):
    return {'function': name, 'parameters': parameters}


class SpriteCardGeometryTests(unittest.TestCase):
    def test_billboard_zero_yaw_retains_existing_corner_and_uv_order(self):
        for theta in (0., .7, -1.2):
            c, s = math.cos(theta), math.sin(theta)
            expected = ((-c+s,-s-c,0),(c+s,s-c,0),(c-s,s+c,0),(-c-s,c-s,0))
            for actual, reference in zip(corners((0,0,0),1,theta,0,0,(0,0,10)), expected):
                for a, b in zip(actual, reference): self.assertAlmostEqual(a,b)

    def test_camera_facing_yaw_tilts_plane_instead_of_becoming_roll(self):
        points = corners((0,0,0),2,0,math.pi/2,0,(0,0,10))
        self.assertAlmostEqual(points[0][0],0)
        self.assertAlmostEqual(points[0][1],-2)
        self.assertAlmostEqual(points[0][2],2)
        self.assertTrue(all(abs(p[0])<1e-8 for p in points))

    def test_upright_yaw_rotates_about_world_z_and_uses_relative_view(self):
        a = corners((0,0,0),2,0,math.pi/2,1,(0,-10,2))
        for actual, expected in zip(a[0],(0,2,-2)): self.assertAlmostEqual(actual,expected)
        b = corners((9,7,3),2,0,math.pi/2,1,(9,-3,5))
        for p,q in zip(a,b):
            for v,w,t in zip(p,q,(9,7,3)):self.assertAlmostEqual(v,w-t)

    def test_ground_orientation_ignores_yaw_and_preserves_square(self):
        for roll in (0., .4, 1.3):
            a = corners((2,3,4),3,roll,0,2,(0,0,10))
            self.assertEqual(a,corners((2,3,4),3,roll,2.1,2,(0,0,10)))
            for p,q in zip(a,a[1:]+a[:1]):
                self.assertEqual(p[2],4);self.assertAlmostEqual(math.dist(p,q),6)

    def test_material_orientation_selection_and_explicit_gaps(self):
        mat = {'sfm_particle_shader':'SpriteCard'}
        self.assertEqual(settings(mat,'render_animated_sprites')['orientation'],0)
        self.assertIsNone(settings(mat,'render_sprite_trail'))
        self.assertIsNone(settings({'sfm_particle_shader':'UnlitGeneric'},'render_animated_sprites'))
        self.assertEqual(settings({**mat,'sfm_particle_material_orientation':-1},'render_animated_sprites')['orientation'],0)
        for extra in ({'sfm_particle_material_orientation':3},
                      {'sfm_particle_material_orientation':2,'sfm_particle_material_orientation_matrix':'rotate 90'},
                      {'sfm_particle_material_orientation':float('nan')},
                      {'sfm_particle_material_spline_type':1}):
            with self.assertRaises(ValueError):settings({**mat,**extra},'render_animated_sprites')

    def test_invalid_geometry_inputs_fail_explicitly(self):
        for mode,eye in ((3,(1,2,3)),(1,(0,0,10))):
            with self.assertRaises(ValueError):corners((0,0,0),1,0,0,mode,eye)
        with self.assertRaises(ValueError):corners((float('nan'),0,0),1,0,0,0,(0,0,10))


class YawBirthTests(unittest.TestCase):
    def yaw(self, degrees):
        return module('Rotation Yaw Random',yaw_initial=degrees,yaw_offset_min=0,yaw_offset_max=0)

    def test_random_yaw_and_flip_obey_authored_order(self):
        flip_module = module('Rotation Yaw Flip Random',**{'Flip Percentage':1})
        before,_ = sample([self.yaw(25),flip_module],random.Random(4))
        after,_ = sample([flip_module,self.yaw(25)],random.Random(4))
        self.assertAlmostEqual(before,flip(math.radians(25)))
        self.assertAlmostEqual(after,math.radians(25))
        self.assertGreater(before,math.pi);self.assertLess(after,math.pi)

    def test_flip_uses_float_pi_remainder_instead_of_adding_pi_unconditionally(self):
        self.assertAlmostEqual(flip(0),PI32)
        self.assertAlmostEqual(flip(4),math.fmod(4,PI32)+math.pi,places=6)
        self.assertLess(flip(4),5)
        self.assertAlmostEqual(flip(-.2),math.pi-.2,places=6)

    def test_disabled_writes_do_not_replace_yaw(self):
        disabled=self.yaw(170);disabled['parameters']['operator enabled']=False
        angle,_ = sample([self.yaw(20),disabled],random.Random(4))
        self.assertAlmostEqual(angle,math.radians(20))
