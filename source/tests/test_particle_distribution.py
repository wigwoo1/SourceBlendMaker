import sys,unittest,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_distribution import random_float_exp,birth_ranges,alpha_bounds

class DistributionTests(unittest.TestCase):
    def test_alpha_initializer_defaults_override_definition_alpha(self):
        self.assertEqual(alpha_bounds({'Alpha Random':{}},32),(255,255))
        self.assertEqual(alpha_bounds({'Alpha Random':{'alpha_min':64}},32),(64,255))
        self.assertEqual(alpha_bounds({'Alpha Random':{'alpha_max':128}},32),(255,128))
    def test_absent_alpha_initializer_uses_definition_alpha(self):
        self.assertEqual(alpha_bounds({},32),(32,32))
    def test_descending_radius_preserves_authored_endpoint_order(self):
        class Rng:
            def uniform(self,a,b):return a+(b-a)*.25
        self.assertEqual(birth_ranges({'lifetime_range':[3,3],'radius_range':[25,20]},Rng()),(3,23.75))
    def test_birth_lifetime_and_radius_have_independent_exponents(self):
        class Rng:
            def random(self):return .25
        config={'lifetime_range':[1,5],'radius_range':[2,10],'lifetime_exponent':2,'radius_exponent':.5}
        self.assertEqual(birth_ranges(config,Rng()),(1.25,6))
    def test_constant_birth_ranges_preserve_random_stream(self):
        rng=random.Random(92);reference=random.Random(92)
        self.assertEqual(birth_ranges({'lifetime_range':[2,2],'radius_range':[3,3]},rng),(2,3))
        self.assertEqual(rng.random(),reference.random())
    def test_valve_exponent_formula(self):
        class Rng:
            def random(self):return .25
        self.assertEqual(random_float_exp(Rng(),20,40,2),21.25)
        self.assertAlmostEqual(random_float_exp(Rng(),20,40,.5),30)
    def test_uniform_stream_is_preserved(self):
        a=random.Random(41);b=random.Random(41)
        self.assertEqual(random_float_exp(a,10,30),b.uniform(10,30))
        self.assertEqual(a.random(),b.random())
    def test_invalid_exponents_are_rejected(self):
        for exponent in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):random_float_exp(random.Random(),0,1,exponent)
