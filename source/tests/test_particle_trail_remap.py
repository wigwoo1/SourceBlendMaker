import unittest
from particle_radius_remap import scalar_state

def module(name,p):return {'function':name,'parameters':p}
def remapping(source=3):return module('Remap Scalar',{'input field':source,'output field':10,'input minimum':0,'input maximum':250,'output minimum':.2,'output maximum':.1})

class TrailRemapTests(unittest.TestCase):
    def test_trail_reads_ordered_radius_scale(self):
        scale=module('Radius Scale',{'start_time':0,'end_time':1,'radius_start_scale':2,'radius_end_scale':2})
        radius,trail=scalar_state([scale,remapping()],0,1,125,0,initial_trail=1)
        self.assertEqual(radius,250);self.assertAlmostEqual(trail,.1)
        self.assertAlmostEqual(scalar_state([remapping(),scale],0,1,125,0,initial_trail=1)[1],.15)
    def test_trail_persists_between_ticks(self):
        p=remapping(10);p['parameters'].update({'input maximum':1,'output minimum':0,'output maximum':.5})
        self.assertEqual(scalar_state([p],.2,1,1,0,step=.1,initial_trail=.8)[1],.1)
    def test_negative_trail_is_rejected(self):
        p=remapping();p['parameters']['output minimum']=-1
        with self.assertRaises(ValueError):scalar_state([p],0,1,0,0,initial_trail=1)
    def test_plan_requires_trail_renderer(self):
        from test_particle_initial_only import definition
        from particle_bake import plan
        d=definition(1);d['modules']['operators']=[remapping()]
        with self.assertRaises(ValueError):plan(d)
        d['modules']['renderers'][0]['function']='render_sprite_trail'
        plan(d)
