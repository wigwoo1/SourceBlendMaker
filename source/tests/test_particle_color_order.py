import unittest
from particle_color_order import evaluate
def module(name,p=None):return {'function':name,'parameters':p or {}}
class ColorOrderTests(unittest.TestCase):
    def test_lighting_reads_current_faded_color(self):
        modules=[module('Color Fade',{'color_fade':[0,0,0],'ease_in_and_out':False}),module('Color Light from Control Point')]
        self.assertEqual(evaluate(modules,(1,1,1),.5,lambda x:x[:3],lambda rgb:[x*.5 for x in rgb]),(.25,)*3)
    def test_later_fade_reads_birth_color(self):
        modules=[module('Color Light from Control Point'),module('Color Fade',{'color_fade':[0,0,0],'ease_in_and_out':False})]
        self.assertEqual(evaluate(modules,(1,1,1),.5,lambda x:x[:3],lambda rgb:[x*.5 for x in rgb]),(.5,)*3)
    def test_equal_time_fade_does_not_overwrite_lighting(self):
        modules=[module('Color Light from Control Point'),module('Color Fade',{'fade_start_time':.5,'fade_end_time':.5})]
        self.assertEqual(evaluate(modules,(1,1,1),.5,lambda x:x[:3],lambda rgb:[x*.5 for x in rgb]),(.5,)*3)
