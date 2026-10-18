import math
import unittest
from particle_epitrochoid import offset
from particle_epitrochoid import validate

class EpitrochoidTests(unittest.TestCase):
    def test_converter_validation(self):
        self.assertEqual(validate({'control point number':3}),3)
        for p in ({'operator time scale seed':1},
                  {'operator strength scale seed':1},
                  {'use particle count instead of creation time':True}):
            with self.assertRaises(ValueError):validate(p)

    def test_zero_seeds_leave_authored_scale_ranges_inactive(self):
        self.assertEqual(validate({'operator time scale min':.1,
                                   'operator time scale max':.4,
                                   'operator strength random scale min':-7.45e-8,
                                   'operator strength random scale max':.3}),0)
        for p in ({'operator end fadein':1},{'operator strength scale control point':0},
                  {'operator end cap state':0},{'operator time offset seed':1},
                  {'operator time scale min':float('nan')}):
            with self.assertRaises(ValueError):validate(p)

    def test_planner_preserves_authored_control_point(self):
        from test_particle_initial_only import definition
        from particle_bake import plan
        d=definition(2)
        d['modules']['initializers'][0]={'function':'Position Along Epitrochoid',
                                     'parameters':{'control point number':3}}
        self.assertEqual(plan(d)['control_point'],3)
        self.assertEqual(d['modules']['initializers'][0]['parameters'],{'control point number':3})
    def test_installed_plus_offset_and_disabled_dimension(self):
        self.assertEqual(offset(0,0,{}),(68.,0.,0.))
        self.assertEqual(offset(0,0,{'first dimension':-1}),(0.,0.,0.))

    def test_birth_time_and_count_phase(self):
        p={'particle density':1.,'point offset':0.,'radius 1':2.,'radius 2':3.}
        a=offset(math.pi/2,0,p)
        self.assertAlmostEqual(a[0],0);self.assertAlmostEqual(a[1],5)
        b=offset(100,0,dict(p,**{'use particle count instead of creation time':True}))
        self.assertEqual(b,(5.,0.,0.))

    def test_reject_unverified_and_invalid_inputs(self):
        for p in ({'first dimension':3},{'radius 1':float('nan')},
                  {'scale from conrol point (radius 1/radius 2/offset)':0}):
            with self.assertRaises(ValueError):offset(0,0,p)
