import unittest
from particle_scalar_oscillation import delta,settings,wave,sample

def parameters():
    return {'oscillation field':4,'proportional 0/1':True,'start/end proportional':True,
            'oscillation multiplier':2,'oscillation start phase':.5,
            'oscillation rate min':2,'oscillation rate max':2,
            'oscillation frequency min':0,'oscillation frequency max':0,
            'start time min':0,'start time max':0,'end time min':1,'end time max':1}

class FullScalarOscillationTests(unittest.TestCase):
    def test_constant_peak_integrates_roll(self):
        self.assertAlmostEqual(delta(parameters(),.25,1),.5,places=6)
    def test_absolute_clock_bypasses_phase(self):
        p=parameters();p['proportional 0/1']=False
        self.assertEqual(delta(p,.25,1),0)
    def test_unsampled_ranges_and_invalid_parameters_rejected(self):
        p=parameters();p['oscillation rate max']=3
        with self.assertRaises(ValueError):settings(p)
        p=parameters();p['oscillation rate min']=None
        with self.assertRaises(ValueError):settings(p)
    def test_portal2_omitted_minimum_rate_uses_verified_metadata_default(self):
        import random
        p={'oscillation rate max':400.,'oscillation frequency min':0.,'oscillation frequency max':500.}
        resolved=settings(p,allow_random=True)
        self.assertEqual((resolved['oscillation rate min'],resolved['oscillation rate max']),(0.,400.))
        self.assertEqual(resolved['oscillation field'],7)
        self.assertEqual(sample(p,random.Random(7)),sample(resolved,random.Random(7)))
        self.assertNotIn('oscillation rate min',p)
    def test_omitted_rate_and_frequency_pairs_have_valid_zero_motion(self):
        resolved=settings({})
        self.assertEqual((resolved['oscillation frequency min'],resolved['oscillation frequency max']),(1.,1.))
        self.assertEqual(delta({},.4,1.),0.)
    def test_authored_invalid_range_is_not_replaced_by_defaults(self):
        with self.assertRaisesRegex(ValueError,'Invalid oscillation parameter range'):
            settings({'oscillation rate max':-1.},allow_random=True)
    def test_source_omitted_defaults_are_restored_without_mutating_input(self):
        import random
        p=parameters()
        for key in ('oscillation field','proportional 0/1','start/end proportional','oscillation multiplier',
                    'oscillation start phase','start time min','start time max',
                    'end time min','end time max'):
            del p[key]
        resolved=settings(p)
        self.assertEqual(resolved['oscillation field'],7)
        self.assertEqual(resolved['proportional 0/1'],True)
        self.assertEqual(resolved['start/end proportional'],True)
        self.assertEqual(resolved['oscillation multiplier'],2.0)
        self.assertEqual(resolved['oscillation start phase'],.5)
        self.assertEqual((resolved['start time min'],resolved['start time max']),(0.,0.))
        self.assertEqual((resolved['end time min'],resolved['end time max']),(1.,1.))
        self.assertNotIn('oscillation multiplier',p)
        self.assertAlmostEqual(delta(p,.25,1),delta(parameters(),.25,1),places=6)
        sampled=sample(p,random.Random(4))
        self.assertEqual(sampled['oscillation multiplier'],2.0)
        self.assertEqual(sampled['start time min'],0.0)
    def test_window_stops_accumulation(self):
        p=parameters();p['end time min']=p['end time max']=.2
        self.assertEqual(delta(p,.3,1),delta(p,.4,1))
    def test_fractional_or_boolean_fields_rejected(self):
        for field in (True,4.5,'4'):
            p=parameters();p['oscillation field']=field
            with self.assertRaises(ValueError):settings(p)
    def test_random_parameters_sample_once_and_are_reproducible(self):
        import random
        p=parameters();p['oscillation rate min']=-2
        a=sample(p,random.Random(3));b=sample(p,random.Random(3))
        self.assertEqual(a,b)
        self.assertEqual(a['oscillation rate min'],a['oscillation rate max'])
        self.assertTrue(-2<=a['oscillation rate min']<=2)
        self.assertEqual(delta(a,.2,1),delta(b,.2,1))
        self.assertEqual(p['oscillation rate min'],-2)
    def test_radius_scale_and_oscillation_preserve_order(self):
        from particle_radius_remap import scalar_state
        p=parameters();p['oscillation field']=3
        osc={'function':'Oscillate Scalar','parameters':p}
        scale={'function':'Radius Scale','parameters':{'start_time':0,'end_time':1,'radius_start_scale':2,'radius_end_scale':2}}
        self.assertAlmostEqual(scalar_state([scale,osc],.1,1,5,0,step=.1)[0],10.2,places=5)
        self.assertEqual(scalar_state([osc,scale],.1,1,5,0,step=.1)[0],10)
    def test_radius_uses_persistent_birth_sample(self):
        from particle_bake import appearance
        from test_particle_initial_only import definition
        d=definition(1);p=parameters();p['oscillation field']=3;p['oscillation rate max']=4
        d['modules']['operators']=[{'function':'Oscillate Scalar','parameters':p}]
        chosen=dict(p);chosen['oscillation rate min']=chosen['oscillation rate max']=3
        value,_=appearance(d,.2,1,5,creation_time=0,oscillation_samples={0:chosen})
        self.assertAlmostEqual(value,5.6,places=5)
        self.assertEqual(p['oscillation rate max'],4)
