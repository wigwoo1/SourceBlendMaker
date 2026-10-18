import unittest
from particle_color_fade import color,settings

class ColorFadeTests(unittest.TestCase):
    def test_installed_easing_default_and_explicit_linear(self):
        self.assertEqual(color((0,0,0),(1,1,1),.25,{}),(.15625,)*3)
        self.assertEqual(color((0,0,0),(1,1,1),.25,{'ease_in_and_out':False}),(.25,)*3)
    def test_equal_endpoints_leave_initial_color(self):
        self.assertEqual(color((.1,.2,.3),(1,1,1),.8,{'fade_start_time':.5,'fade_end_time':.5}),(.1,.2,.3))
    def test_unknown_output_and_nonfinite_time_rejected(self):
        for p in ({'output field':21},{'fade_end_time':float('nan')}):
            with self.assertRaises(ValueError):settings(p)
