import unittest
from particle_radius_remap import radius
from particle_bake import appearance

def module(name,p):return {'function':name,'parameters':p}
def overwrite(source=8):return module('Remap Scalar',{'input field':source,'output field':3,'input minimum':0,'input maximum':.5,'output minimum':16,'output maximum':5})

class RadiusRemapTests(unittest.TestCase):
    def test_creation_time_not_age_and_authored_order(self):
        scale=module('Radius Scale',{'start_time':0,'end_time':1,'radius_start_scale':2,'radius_end_scale':2})
        self.assertEqual(radius([scale,overwrite()],.1,1,100,.25),10.5)
        self.assertEqual(radius([scale,overwrite()],.8,1,100,.25),10.5)
        self.assertEqual(radius([overwrite(),scale],.8,1,100,.25),200)
    def test_persistent_current_radius_history(self):
        p=module('Remap Scalar',{'input field':3,'output field':3,'input minimum':0,'input maximum':100,'output minimum':0,'output maximum':50})
        self.assertEqual(radius([p],.2,1,80,0,step=.1),10)
    def test_appearance_requires_creation_time(self):
        d={'modules':{'operators':[overwrite()]}}
        with self.assertRaisesRegex(ValueError,'creation'):appearance(d,.2,1,100)
        self.assertEqual(appearance(d,.2,1,100,creation_time=.25),(10.5,1))
    def test_invalid_result_rejected(self):
        p=overwrite();p['parameters']['output minimum']=-2
        with self.assertRaises(ValueError):radius([p],0,1,1,0)
    def test_full_radius_oscillator_may_cross_zero(self):
        p={'oscillation field':3,'proportional 0/1':True,'start/end proportional':True,
           'oscillation multiplier':2,'oscillation start phase':.5,
           'oscillation rate min':-100,'oscillation rate max':-100,
           'oscillation frequency min':0,'oscillation frequency max':0,
           'start time min':0,'start time max':0,'end time min':1,'end time max':1}
        definition={'modules':{'operators':[module('Oscillate Scalar',p)]}}
        value,_=appearance(definition,.2,1,5,creation_time=0)
        self.assertLess(value,0)
        self.assertTrue(__import__('math').isfinite(value))
    def test_plan_rejects_invalid_field_ids(self):
        from test_particle_initial_only import definition
        from particle_bake import plan
        for value in (True,3.5,float('nan'),'3'):
            d=definition(1);p=overwrite();p['parameters']['input field']=value
            d['modules']['operators']=[p]
            with self.assertRaises(ValueError):plan(d)
