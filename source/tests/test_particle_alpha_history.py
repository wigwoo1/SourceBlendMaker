import unittest
from particle_alpha_history import alpha
from test_particle_initial_only import definition
from test_particle_scalar_oscillation import parameters

class AlphaHistoryTests(unittest.TestCase):
    def setup_definition(self):
        d=definition(1);p=parameters();p['oscillation field']=7
        d['modules']['operators']=[{'function':'Oscillate Scalar','parameters':p}]
        return d
    def test_alpha_clamps_every_step(self):
        d=self.setup_definition()
        self.assertEqual(alpha(d,{'alpha':.9},.2,1,step=.1),1)
        p=d['modules']['operators'][0]['parameters'];p['oscillation rate min']=p['oscillation rate max']=-2
        self.assertEqual(alpha(d,{'alpha':.1},.2,1,step=.1),0)
    def test_remap_before_and_after_oscillation(self):
        d=self.setup_definition();osc=d['modules']['operators'][0]
        remap={'function':'Remap Scalar','parameters':{'input field':7,'output field':7,'input minimum':0,'input maximum':1,'output minimum':.2,'output maximum':.2}}
        d['modules']['operators']=[remap,osc]
        state={'alpha':.5,'creation_simulation_time':0}
        self.assertAlmostEqual(alpha(d,state,.1,1,step=.1),.4,places=6)
        d['modules']['operators']=[osc,remap]
        self.assertAlmostEqual(alpha(d,state,.1,1,step=.1),.2,places=6)
    def test_unsampled_random_alpha_rejected(self):
        d=self.setup_definition();d['modules']['operators'][0]['parameters']['oscillation rate max']=3
        with self.assertRaises(ValueError):alpha(d,{'alpha':.5},.2,1)
    def test_disabled_operator_keeps_sample_index(self):
        d=self.setup_definition();osc=d['modules']['operators'][0]
        sampled=dict(osc['parameters']);sampled['oscillation rate min']=sampled['oscillation rate max']=1
        d['modules']['operators'].insert(0,{'function':'Oscillate Scalar','parameters':{'operator enabled':False}})
        self.assertAlmostEqual(alpha(d,{'alpha':.1,'scalar_oscillations':{1:sampled}},.2,1),.3,places=6)

    def test_simple_fade_preserves_lower_current_alpha(self):
        d=definition(1)
        d['modules']['operators']=[
            {'function':'Remap Scalar','parameters':{'input field':7,'output field':7,'input minimum':0,'input maximum':1,'output minimum':.05,'output maximum':.05}},
            {'function':'Alpha Fade Out Simple','parameters':{}}]
        self.assertEqual(alpha(d,{'alpha':.8,'creation_simulation_time':0},.9375,1),.05)

    def test_simple_fade_in_stops_writing_after_interval(self):
        d=definition(1)
        d['modules']['operators']=[
            {'function':'Remap Scalar','parameters':{'input field':7,'output field':7,'input minimum':0,'input maximum':1,'output minimum':.4,'output maximum':.4}},
            {'function':'Alpha Fade In Simple','parameters':{}}]
        self.assertEqual(alpha(d,{'alpha':.8,'creation_simulation_time':0},.0625,1),.125)
        self.assertEqual(alpha(d,{'alpha':.8,'creation_simulation_time':0},.5,1),.4)
