import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_bake import appearance,birth_ranges,birth_fades
import random

class AppearanceTests(unittest.TestCase):
    def test_mixed_radius_order_and_no_double_oscillation(self):
        import math
        scale={'function':'Radius Scale','parameters':{'radius_start_scale':2,'radius_end_scale':2}}
        oscillation={'function':'Oscillate Scalar Simple','parameters':{'oscillation field':3,'oscillation rate':10,'oscillation frequency':0,'oscillation multiplier':1,'oscillation start phase':math.pi/2}}
        from particle_radius_scale import mixed_radius
        for modules in ([scale,oscillation],[oscillation,scale]):
            definition={'modules':{'operators':modules}}
            self.assertEqual(appearance(definition,.5,1,10)[0],mixed_radius(modules,.5,1,10))
    def test_radius_bias_midpoint(self):
        for bias in (0.,.1,.5,.75,.95,1.):
            definition={'modules':{'operators':[{'function':'Radius Scale','parameters':{'radius_start_scale':0,'radius_end_scale':1,'scale_bias':bias}}]}}
            self.assertAlmostEqual(appearance(definition,.5,1,2)[0],2*(.5 if bias==0 else bias))
    def test_repeated_radius_envelopes(self):
        definition={'modules':{'operators':[{'function':'Radius Scale','parameters':{'radius_start_scale':0,'radius_end_scale':1,'end_time':.25}},{'function':'Radius Scale','parameters':{'radius_start_scale':1,'radius_end_scale':0,'start_time':.25,'end_time':1}}]}}
        self.assertEqual(appearance(definition,0,1,2)[0],0)
        self.assertEqual(appearance(definition,.25,1,2)[0],2)
        self.assertAlmostEqual(appearance(definition,.625,1,2)[0],1)
        # End is exclusive: hold the final active simulation sample.
        self.assertAlmostEqual(appearance(definition,1,1,2)[0],2/90)
    def test_birth_ranges_are_repeatable_and_bounded(self):
        config={'lifetime_range':[1,3],'radius_range':[2,7]}
        first=random.Random(42);second=random.Random(42)
        samples=[birth_ranges(config,first) for _ in range(100)]
        self.assertEqual(samples,[birth_ranges(config,second) for _ in range(100)])
        self.assertTrue(all(1<=life<=3 and 2<=radius<=7 for life,radius in samples))
        self.assertGreater(len(set(samples)),1)
        config={'lifetime_range':[2,2],'radius_range':[4,4]}
        state=first.getstate();self.assertEqual(birth_ranges(config,first),(2,4));self.assertEqual(first.getstate(),state)
    def test_fade_units(self):
        definition={'modules':{'operators':[{'function':'Alpha Fade In Random','parameters':{'fade in time min':.5,'fade in time max':.5,'proportional 0/1':False}}]}}
        self.assertEqual(appearance(definition,.25,10,2),(2,.5))
        definition['modules']['operators'][0]['parameters']['proportional 0/1']=True
        self.assertEqual(appearance(definition,.25,10,2),(2,.05))
        self.assertEqual(appearance(definition,5,10,2),(2,1))

    def test_nonpositive_and_random_durations(self):
        parameters={'fade in time min':0,'fade in time max':0,'proportional 0/1':False}
        definition={'modules':{'operators':[{'function':'Alpha Fade In Random','parameters':parameters}]}}
        self.assertEqual(appearance(definition,0,10,2),(2,1))
        parameters.update({'fade in time min':.1,'fade in time max':.5})
        with self.assertRaisesRegex(ValueError,'Random alpha'):appearance(definition,1,10,2)

    def test_sampled_fade_duration_changes_opacity(self):
        definition={'modules':{'operators':[{'function':'Alpha Fade In Random','parameters':{'fade in time min':.25,'fade in time max':1.,'proportional 0/1':False}}]}}
        self.assertEqual(appearance(definition,.25,10,2,{0:.5}),(2,.5))
        self.assertEqual(appearance(definition,.25,10,2,{0:1.}),(2,.25))
        samples=[birth_fades(definition,random.Random(seed))[0] for seed in range(30)]
        self.assertTrue(all(.25<=value<=1. for value in samples))
        self.assertGreater(len(set(samples)),1)

    def test_constant_fades_preserve_random_stream(self):
        definition={'modules':{'operators':[{'function':'Alpha Fade In Random','parameters':{'fade in time min':.5,'fade in time max':.5}}]}}
        rng=random.Random(42);state=rng.getstate()
        self.assertEqual(birth_fades(definition,rng),{0:.5});self.assertEqual(rng.getstate(),state)

    def test_invalid_fade_range(self):
        definition={'modules':{'operators':[{'function':'Alpha Fade In Random','parameters':{'fade in time min':1.,'fade in time max':-.5}}]}}
        with self.assertRaises(ValueError):birth_fades(definition,random.Random(42))
