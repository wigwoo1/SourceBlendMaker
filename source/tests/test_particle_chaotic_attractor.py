import unittest,math
from particle_chaotic_attractor import step,velocity,validate

class ChaoticAttractorTests(unittest.TestCase):
    def test_planner_control_point_and_authored_settings_preserved(self):
        from test_particle_initial_only import definition
        from particle_bake import plan
        d=definition(2)
        parameters={'Relative Control point number':3,'operator time scale min':.1,
                    'operator time scale max':.5,'Speed Min':2,'Speed Max':15,'Scale':10}
        d['modules']['initializers'][0]={'function':'Position From Chaotic Attractor','parameters':parameters.copy()}
        self.assertEqual(plan(d)['control_point'],3)
        self.assertEqual(d['modules']['initializers'][0]['parameters'],parameters)
        with self.assertRaises(ValueError):validate({'operator time scale seed':1})
    def test_zero_context_first_recurrence(self):
        self.assertEqual(step((0,0,0),{}),(0.,-1.,0.))
        second=step((0,-1,0),{})
        self.assertAlmostEqual(second[0],math.sin(.9629629))
        self.assertAlmostEqual(second[1],-math.cos(1.5))
        self.assertEqual(second[2],0)
    def test_previous_position_speed_sign_and_integer_bounds(self):
        self.assertEqual(velocity((0,0,0),(0,-1,0),{'Speed Min':2,'Speed Max':15},0),(0.,2.,0.))
        self.assertEqual(velocity((0,0,0),(0,-1,0),{'Speed Min':2,'Speed Max':15},.999),(0.,15.,0.))
        self.assertEqual(velocity((0,0,0),(0,-2,0),{'Speed Min':2,'Speed Max':2,'Uniform speed':True},0),(0.,4.,0.))
    def test_invalid_input(self):
        with self.assertRaises(ValueError):step((0,0,0),{'Pickover A Parameter':float('nan')})
        with self.assertRaises(ValueError):velocity((0,0,0),(0,1,0),{'Speed Min':3,'Speed Max':2},.5)
