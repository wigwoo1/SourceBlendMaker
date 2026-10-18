import unittest
from particle_scalar_remap import remap,ordered_alpha

class ScalarRemapTests(unittest.TestCase):
    def test_emp_creation_time(self):
        p={'input minimum':0,'input maximum':2,'output minimum':.5,'output maximum':0,'output field':7}
        self.assertEqual([remap(p,t,.9) for t in (-1,0,1,2,3)],[.5,.5,.25,0,0])

    def test_strength_and_clamped_alpha_bounds(self):
        p={'output minimum':-2,'output maximum':4,'output field':7}
        self.assertEqual(remap(p,.25,.8,.5),.525)
        p['output field']=3
        self.assertEqual(remap(p,.25,.8,1),-.5)

    def test_equal_and_reversed_input_bounds(self):
        p={'input minimum':2,'input maximum':2,'output minimum':10,'output maximum':20}
        self.assertEqual(remap(p,1,0),10)
        self.assertEqual(remap(p,2,0),20)
        p['input minimum']=4
        self.assertEqual(remap(p,3,0),15)

    def test_invalid_values(self):
        for p in ({'input minimum':float('nan')},{'output field':.5},{'output field':32}):
            with self.assertRaises(ValueError):remap(p,0,0)

    def test_authored_alpha_order(self):
        fade={'function':'Alpha Fade Out Simple','parameters':{'proportional fade out time':1}}
        overwrite={'function':'Remap Scalar','parameters':{'input field':8,'output field':7,'input minimum':0,'input maximum':2,'output minimum':.5,'output maximum':0}}
        state={'alpha':.8,'creation_simulation_time':0}
        definition={'modules':{'operators':[fade,overwrite]}}
        self.assertEqual(ordered_alpha(definition,state,.75,1),.5)
        definition['modules']['operators'].reverse()
        self.assertEqual(ordered_alpha(definition,state,.75,1),.125)
        state['creation_simulation_time']=1
        # The simple Source fade caps against initial alpha, rather than
        # multiplying the remapped current alpha for a second time.
        self.assertEqual(ordered_alpha(definition,state,.75,1),.125)

    def test_chained_current_alpha_and_plan_limits(self):
        import copy
        from test_particle_initial_only import definition
        from particle_bake import plan
        p={'input field':7,'output field':7,'input minimum':0,'input maximum':1,'output minimum':0,'output maximum':.5}
        d=definition(1)
        d['modules']['operators']=[{'function':'Remap Scalar','parameters':copy.deepcopy(p)} for _ in range(2)]
        plan(d)
        self.assertEqual(ordered_alpha(d,{'alpha':.8,'creation_simulation_time':0},.3,1),.2)
        for key,value in (('input field',3),('output field',3),('input minimum',float('nan')),('operator end fadein',1)):
            invalid=copy.deepcopy(d);invalid['modules']['operators'][0]['parameters'][key]=value
            with self.assertRaises(ValueError):plan(invalid)
        invalid=copy.deepcopy(d);del invalid['modules']['operators'][0]['parameters']['input minimum']
        with self.assertRaisesRegex(ValueError,'explicit'):plan(invalid)

    def test_creation_time_to_rotation_speed_is_supported(self):
        from test_particle_initial_only import definition
        from particle_bake import plan
        d=definition(1)
        d['modules']['operators']=[
            {'function':'Rotation Basic','parameters':{}},
            {'function':'Remap Scalar','parameters':{
                'input field':8,'output field':5,'input minimum':0,'input maximum':1,
                'output minimum':-1,'output maximum':1,
            }},
        ]
        plan(d)
        self.assertEqual(ordered_alpha(d,{'alpha':.8,'creation_simulation_time':.75},.2,1),.8)
        unsupported=definition(1)
        unsupported['modules']['operators']=[{'function':'Remap Scalar','parameters':{
            'input field':7,'output field':5,'input minimum':0,'input maximum':1,
            'output minimum':-1,'output maximum':1,
        }}]
        with self.assertRaisesRegex(ValueError,'Unsupported scalar remap field'):
            plan(unsupported)

if __name__=='__main__':unittest.main()
