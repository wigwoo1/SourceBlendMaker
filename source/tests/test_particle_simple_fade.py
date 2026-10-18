import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_bake import appearance,simple_fade,simple_fade_value

class SimpleFadeTests(unittest.TestCase):
    def test_fades_use_particle_lifetime_fraction(self):
        definition={'modules':{'operators':[{'function':'Alpha Fade In Simple','parameters':{'proportional fade in time':.25}}, {'function':'Alpha Fade Out Simple','parameters':{'proportional fade out time':.5}}]}}
        self.assertEqual(appearance(definition,0,4,2),(2,0))
        self.assertEqual(appearance(definition,.5,4,2),(2,.5))
        self.assertEqual(appearance(definition,2,4,2),(2,1))
        self.assertEqual(appearance(definition,3,4,2),(2,.5))
        self.assertEqual(appearance(definition,4,4,2),(2,0))

    def test_zero_duration_and_disabled_operator(self):
        self.assertEqual(simple_fade('Alpha Fade In Simple',{'proportional fade in time':0},0),1)
        self.assertEqual(simple_fade('Alpha Fade Out Simple',{'proportional fade out time':0},.5),1)
        self.assertEqual(simple_fade('Alpha Fade Out Simple',{'proportional fade out time':0},1),0)
        definition={'modules':{'operators':[{'function':'Alpha Fade In Simple','parameters':{'operator enabled':False}}]}}
        self.assertEqual(appearance(definition,0,4,2),(2,1))

    def test_installed_defaults_and_smooth_curve(self):
        self.assertEqual(simple_fade('Alpha Fade In Simple',{},.0625),.15625)
        self.assertEqual(simple_fade('Alpha Fade Out Simple',{},.9375),.15625)
        self.assertEqual(simple_fade('Alpha Fade In Simple',{},.1875),.84375)
        self.assertEqual(simple_fade('Alpha Fade Out Simple',{},.8125),.84375)

    def test_invalid_parameters(self):
        for duration in (-1,1.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):simple_fade('Alpha Fade Out Simple',{'proportional fade out time':duration},.5)
        for field in (3,10,True):
            with self.assertRaisesRegex(ValueError,'field'):simple_fade('Alpha Fade In Simple',{'aplha field':field},.5)

    def test_initial_alpha_and_current_alpha_are_distinct(self):
        self.assertEqual(simple_fade_value('Alpha Fade Out Simple',{},.9375,.9,.8),.125)
        self.assertEqual(simple_fade_value('Alpha Fade Out Simple',{},.9375,.05,.8),.05)
        self.assertEqual(simple_fade_value('Alpha Fade In Simple',{},.0625,.9,.8),.125)
        self.assertEqual(simple_fade_value('Alpha Fade In Simple',{},.25,.4,.8),.4)
