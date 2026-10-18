import random,unittest,copy
from particle_bake import plan,birth_ranges
from test_particle_initial_only import definition

class OrderedLifetimeTests(unittest.TestCase):
    def test_last_write_wins_but_earlier_random_sample_consumed(self):
        d=definition(2)
        d['modules']['initializers'].insert(1,{'function':'Lifetime Random','parameters':{'lifetime_max':7}})
        d['modules']['initializers'][2]['parameters']={'lifetime_max':.4}
        original=copy.deepcopy(d);config=plan(d)
        rng=random.Random(5);expected=random.Random(5)
        expected.uniform(0,7);last=expected.uniform(0,.4)
        life,radius=birth_ranges(config,rng)
        self.assertEqual(life,last);self.assertEqual(radius,1)
        self.assertEqual(rng.random(),expected.random())
        self.assertEqual(config['lifetime_range'],[0,.4]);self.assertEqual(d,original)
    def test_invalid_earlier_write_is_not_discarded(self):
        d=definition(2)
        d['modules']['initializers'].insert(1,{'function':'Lifetime Random','parameters':{'lifetime_min':-1,'lifetime_max':7}})
        with self.assertRaisesRegex(ValueError,'Invalid ordered'):plan(d)
