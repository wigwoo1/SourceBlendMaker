import math,random,unittest
from particle_tint_color import blend,color,settings,validate

class TintColorTests(unittest.TestCase):
    def test_provider_preflight_rejects_invalid_cp_and_threshold(self):
        for params in ({'tint_perc':math.nan},{'tint_perc':2},{'tint control point':64},
                       {'tint control point':1.5},{'tint update movement threshold':-1},
                       {'tint clamp min':[255,0,0],'tint clamp max':[0,255,255]}):
            with self.assertRaises(ValueError):validate(params)
    def test_planner_requires_explicit_tint_permission(self):
        from particle_bake import plan
        def module(name,**params):return {'function':name,'parameters':params}
        d={'name':'Tint gate fixture','parameters':{},'modules':{
            'renderers':[module('render_animated_sprites')],
            'emitters':[module('emit_instantaneously',**{'num_to_emit':1})],
            'initializers':[module('Lifetime Random',lifetime_min=1,lifetime_max=1),
                            module('Position From Control Points'),module('Color Random',tint_perc=.5)],
            'operators':[module('Lifespan Decay')],'forces':[],'constraints':[]}}
        with self.assertRaisesRegex(ValueError,'Control-point particle tint'):plan(d)
        plan(d,allow_tint=True)
    def test_decoded_modes_and_fractions(self):
        base=(.2,.5,.8);light=(.8,.25,.5)
        targets=((.8,.25,.5),(.68,.25,.8),(.2,.25,.5),(.8,.5,.8),(.16,.125,.4))
        for mode,target in enumerate(targets):
            for fraction in (0,.5,1):
                actual=blend(base,base,.3,light,fraction,mode)
                for a,b,c in zip(actual,base,target):self.assertAlmostEqual(a,b+(c-b)*fraction)
    def test_clamp_before_amplification_and_linear_conversion(self):
        params={'tint_perc':1,'tint clamp min':[128,0,0],'tint clamp max':[255,64,255],'light amplification amount':2}
        result=color(params,[255]*4,random.Random(1),lambda p:(0,255,255,0))
        self.assertEqual(result[0],1)
        self.assertAlmostEqual(result[1],((128/255+.055)/1.055)**2.4,places=6)
        self.assertEqual(result[2],1)
    def test_shared_random_fraction(self):
        result=blend((0,0,0),(1,.5,.25),.4,(1,1,1),0,0)
        self.assertEqual(result,(.4,.2,.1))
    def test_invalid_settings_and_light_bytes(self):
        for mode in (True,-1,5,1.5,math.nan,math.inf):
            with self.assertRaises(ValueError):settings({'tint blend mode':mode})
        for amplification in (-1,math.inf,math.nan):
            with self.assertRaises(ValueError):settings({'light amplification amount':amplification})
        for packed in ((0,0,0),(0,0,0,256),(0.,0,0,0)):
            with self.assertRaises(ValueError):color({'tint_perc':1},[255]*4,random.Random(0),lambda p:packed)
