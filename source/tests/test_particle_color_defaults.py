import unittest
from particle_distribution import color_bytes

class RandomValue:
    def __init__(self,value):self.value=value;self.calls=0
    def random(self):self.calls+=1;return self.value

class ColorDefaults(unittest.TestCase):
    def test_all_channels_share_blend_factor(self):
        rng=RandomValue(.25)
        color=color_bytes({'Color Random':{'color1':[255,0,0,255],'color2':[0,255,255,255]}},[0]*4,rng)
        self.assertEqual(color,[191.25,63.75,63.75]);self.assertEqual(rng.calls,1)
    def test_present_defaults_white_over_definition_color(self):
        rng=RandomValue(.4)
        self.assertEqual(color_bytes({'Color Random':{}},[10,20,30,255],rng),[255]*3)
        self.assertEqual(rng.calls,1)
    def test_absent_preserves_definition_without_draw(self):
        rng=RandomValue(.4)
        self.assertEqual(color_bytes({},[10,20,30,255],rng),[10,20,30]);self.assertEqual(rng.calls,0)
    def test_tinted_path_requires_separate_support(self):
        rng=RandomValue(.4)
        with self.assertRaises(ValueError):color_bytes({'Color Random':{'tint_perc':1}},[255]*4,rng)
        self.assertEqual(rng.calls,0)

if __name__=='__main__':unittest.main()
