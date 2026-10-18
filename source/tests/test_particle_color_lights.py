import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_color_lights import settings,color,attenuation_coefficients

class ColorLightsTests(unittest.TestCase):
    def test_half_distance_normalization_and_equal_distance_fallback(self):
        for d50,d0 in ((100,200),(50,59),(60,60),(30,1)):
            a,b,c=attenuation_coefficients(d50,d0)
            self.assertAlmostEqual(1/(c+d50*(b+d50*a)),.5)
            self.assertTrue(all(math.isfinite(v) for v in (a,b,c)))
    def test_world_control_offset_and_component_clamps(self):
        config=settings({'Light 1 Color':(255,0,0,255),'Light 1 Control Point Offset':(10,0,0),'Initial Color Bias':.5})
        rgb=color(config,(110,0,0),(.2,.4,.6),{0:(0,0,0)})
        self.assertAlmostEqual(rgb[0],.6);self.assertEqual(rgb[1:],(.2,.3))
        config=settings({'Light 1 Color':(255,0,0,255),'Clamp Maximum Light Value to Initial Color':True})
        self.assertEqual(color(config,(0,0,0),(.2,.4,.6),{0:(0,0,0)}),(.2,0,0))
    def test_installed_fourth_light_descriptor_alias(self):
        config=settings({'Light 3 Color':(1,2,3,255),'Light 4 Color':(255,0,0,255),'Light 4 Control Point':2})
        self.assertEqual(config['lights'][2]['color'],config['lights'][3]['color'])
        self.assertEqual(config['lights'][3]['cp'],2)
    def test_unverified_and_invalid_lighting_rejected(self):
        for p in ({'Light 1 Dynamic Light':True},{'Light 1 Type 0=Point 1=Spot':1},{'Compute Normals From Control Points':True},{'Light 1 50% Distance':0},{'Light 1 Color':(float('nan'),0,0,255)}):
            with self.assertRaises(ValueError):settings(p)
