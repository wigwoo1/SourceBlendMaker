import unittest
from particle_cp_vector_color import color, initialize, settings
from particle_bake import plan
from test_particle_initial_only import definition


class ControlPointColorTests(unittest.TestCase):
    def parameters(self, **extra):
        return {'output field':6,'input minimum':[0,0,0],'input maximum':[1,1,1],
                'output minimum':[0,0,0],'output maximum':[1,1,1],**extra}

    def test_components_are_linear_rgb_and_not_color_bytes(self):
        self.assertEqual(color(self.parameters(),(.25,.5,.75),(1,1,1),0),(.25,.5,.75))

    def test_remaps_input_byte_data_then_clamps_rgb_output(self):
        p=self.parameters(**{'input maximum':[255]*3,'output maximum':[255]*3})
        self.assertEqual(color(p,(-2,128,512),(1,1,1),0),(0.,1.,1.))

    def test_equal_input_bounds_use_step(self):
        p=self.parameters(**{'input minimum':[1]*3,'input maximum':[1]*3})
        self.assertEqual(color(p,(.9,1,1.1),(1,1,1),0),(0.,1.,1.))

    def test_descending_input_range(self):
        p=self.parameters(**{'input minimum':[1]*3,'input maximum':[0]*3})
        self.assertEqual(color(p,(0,.25,1),(1,1,1),0),(1.,.75,0.))

    def test_initial_rgb_multiplier(self):
        p=self.parameters(**{'output is scalar of initial random range':True})
        self.assertEqual(color(p,(.5,.5,.5),(.25,.5,1),0),(.125,.25,.5))

    def test_creation_gate_is_half_open_and_either_wildcard_disables_it(self):
        p=self.parameters(**{'emitter lifetime start time (seconds)':2,'emitter lifetime end time (seconds)':3})
        self.assertEqual(color(p,(1,0,0),(.5,.5,.5),2),(1.,0.,0.))
        self.assertEqual(color(p,(1,0,0),(.5,.5,.5),3),(.5,.5,.5))
        for key in ('emitter lifetime start time (seconds)','emitter lifetime end time (seconds)'):
            self.assertEqual(color(dict(p,**{key:-1}),(1,0,0),(.5,.5,.5),100),(1.,0.,0.))

    def test_ordered_second_pass_overwrite_then_multiply(self):
        modules=[{'function':'Remap Control Point to Vector','parameters':self.parameters()},
                 {'function':'Remap Control Point to Vector','parameters':self.parameters(**{'output is scalar of initial random range':True})}]
        self.assertEqual(initialize(modules,(1,1,1),0,lambda cp:(.5,.5,.5)),(.25,.25,.25))

    def test_missing_control_point_query_is_reported(self):
        with self.assertRaisesRegex(ValueError,'imported control-point query'):
            initialize([{'function':'Remap Control Point to Vector','parameters':self.parameters()}],(1,1,1),0,None)

    def test_installed_zero_bounds_defaults(self):
        self.assertEqual(color({'output field':6},(1,2,3),(.5,.5,.5),0),(0.,0.,0.))

    def test_unsupported_transform_and_field_are_rejected_by_planner(self):
        for p in ({'output field':0},{'output field':6,'local space CP':1}):
            effect=definition(2)
            effect['modules']['initializers'].append({'function':'Remap Control Point to Vector','parameters':p})
            with self.subTest(p=p),self.assertRaises(ValueError):plan(effect)

    def test_nonfinite_components_are_rejected(self):
        with self.assertRaises(ValueError):color(self.parameters(),(float('nan'),0,0),(1,1,1),0)
