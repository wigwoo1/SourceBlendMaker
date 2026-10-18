import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_refraction import displacement,sampling_uv,compositor_pixels,tint_factor

class RefractionTests(unittest.TestCase):
    def test_dx9_blur_clamp(self):
        from particle_refraction import dx9_blur_amount
        for authored,effective in ((-4,0),(0,0),(1,1),(2,1),(99,1)):
            self.assertEqual(dx9_blur_amount(authored),effective)
        for authored in (1.5,True,'1'):
            with self.assertRaises(ValueError):dx9_blur_amount(authored)
    def test_blur_kernel(self):
        from particle_refraction import blur_samples
        self.assertEqual(blur_samples(0),((0.,0.,1.),))
        self.assertEqual(blur_samples(1)[0],(-1/1024,-1/1024,4/9))
        for amount,count in ((1,4),(2,25)):
            samples=blur_samples(amount)
            self.assertEqual(len(samples),count)
            self.assertAlmostEqual(sum(w for x,y,w in samples),1)
            self.assertAlmostEqual(sum(x*w for x,y,w in samples),0)
            self.assertAlmostEqual(sum(y*w for x,y,w in samples),0)
        for amount in (-1,3,True,1.5):
            with self.assertRaises(ValueError):blur_samples(amount)
    def test_tint_texture_and_vertex_modulation(self):
        self.assertEqual(tint_factor((1,1,1),texture=(.5,.25,.5),vertex=(1,.5,1)),(1,.25,1))
    def test_tint_coverage(self):
        self.assertEqual(tint_factor((.2,.5,1),.5),(.6,.75,1))
        self.assertEqual(tint_factor((0,0,0),0),(1,1,1))
    def test_non_square_image_pixel_conversion(self):
        self.assertEqual(compositor_pixels((.1,-.2),100,50),(-10,10))
    def test_invalid_image_size(self):
        for size in ((0,10),(10.5,10),(-1,10)):
            with self.assertRaises(ValueError):compositor_pixels((0,0),*size)
    def test_negative_strength_reverses_sampling(self):
        self.assertEqual(displacement((.5,-.25),1,-.2),(-.1,.05))
    def test_alpha_masks_displacement(self):
        self.assertEqual(displacement((1,1),0,.2),(0,0))
        self.assertEqual(displacement((1,1),1,.2,0,True),(0,0))
        self.assertEqual(displacement((1,1),.5,.2,.5,True),(.05,.05))
    def test_vertex_alpha_only_modulates_when_enabled(self):
        self.assertEqual(displacement((1,0),1,.2,0),(.2,0))
    def test_screen_uv_is_not_clamped(self):
        self.assertEqual(sampling_uv((.95,.5),(1,0),1,.2),(1.15,.5))
    def test_invalid_parameters(self):
        for args in (((1,),1,.2),((1,0),2,.2),((1,0),1,float('nan'))):
            with self.assertRaises(ValueError):displacement(*args)
