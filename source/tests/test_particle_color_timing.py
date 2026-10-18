import unittest
from particle_color_timing import active,History,settings
class ColorTimingTests(unittest.TestCase):
    def test_installed_cache_and_omitted_end(self):
        self.assertTrue(active({'operator end fadein':.01},0))
        self.assertTrue(active({'operator start fadeout':.9},2))
    def test_positive_strength_does_not_blend_color(self):
        h=History((0,0,0),(1,1,1),1,{'operator end fadein':1,'operator start fadeout':2,'ease_in_and_out':False},0,step=.125)
        self.assertEqual(h.query(.125),(.125,)*3)
    def test_inactive_color_freezes_and_reverse_queries_repeat(self):
        h=History((0,0,0),(1,1,1),1,{'operator start fadeout':.25,'operator end fadeout':.5,'ease_in_and_out':False},0,step=.125)
        self.assertEqual(h.query(.75),(.375,)*3)
        self.assertEqual(h.query(.25),(.25,)*3)
        self.assertEqual(h.query(.75),(.375,)*3)
    def test_collection_clock_includes_birth_time(self):
        h=History((.2,.3,.4),(1,1,1),1,{'operator start fadeout':.25,'operator end fadeout':.5},1,step=.125)
        self.assertEqual(h.query(.75),(.2,.3,.4))
    def test_partial_queries_do_not_advance_tick_history(self):
        h=History((0,0,0),(1,1,1),1,{'operator start fadeout':.25,'operator end fadeout':.5,'ease_in_and_out':False},0,step=.125)
        self.assertEqual(h.query(.4),(.4,)*3)
        self.assertEqual(h.query(.75),(.375,)*3)
    def test_external_strength_rejected(self):
        for p in ({'operator time offset max':1},{'operator fade oscillate':1},{'operator strength scale control point':0}):
            with self.assertRaises(ValueError):settings(p)
