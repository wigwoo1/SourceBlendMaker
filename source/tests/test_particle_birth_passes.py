import random,unittest
from unittest.mock import patch
from particle_birth_passes import execution_order
from particle_initializer_history import initialize
from particle_initializer_sampler import bind


def module(name,**p):return {'function':name,'parameters':p}


class BirthPassTests(unittest.TestCase):
    def test_stable_primary_then_override_order_and_original_indices(self):
        modules=[module('Velocity Noise'),module('Position Modify Offset Random'),
                 module('Color Random'),module('Position Within Sphere Random'),
                 module('Lifetime Random'),module('Remap Noise to Scalar'),
                 module('Sequence Random'),module('Velocity Random')]
        self.assertEqual(execution_order(modules),[2,3,4,5,6,0,1,7])

    def test_first_primary_writer_wins_without_consuming_later_rng(self):
        modules=[module('Lifetime Random',lifetime_min=2,lifetime_max=4),
                 module('Lifetime Random',lifetime_min=20,lifetime_max=40)]
        rng,reference=random.Random(12),random.Random(12)
        expected=reference.uniform(2,4)
        fields,_,history=initialize(modules,{1:1},(0,0,0),bind(rng,None,{}),order=execution_order(modules))
        self.assertEqual(fields[1],expected)
        self.assertEqual([s['index'] for s in history],[0])
        self.assertEqual(rng.random(),reference.random())

    def test_disabled_primary_does_not_reserve_attribute_or_change_indices(self):
        modules=[module('Radius Random',**{'operator enabled':False}),module('Radius Random'),
                 module('Remap Noise to Scalar'),module('Remap Initial Scalar')]
        self.assertEqual(execution_order(modules),[1,3])

    def test_radius_noise_runs_before_early_authored_radius_scaled_offset(self):
        modules=[module('Position Modify Offset Random'),module('Remap Noise to Scalar'),
                 module('Radius Random')]
        seen=[]
        def sample(index,module,fields,position):
            seen.append((index,fields[3]))
            return {},(position[0]+fields[3],0,0)
        with patch('particle_noise_scalar.sample',return_value=7):
            fields,position,history=initialize(modules,{3:1,8:0},(0,0,0),sample,[],order=execution_order(modules))
        self.assertEqual(fields[3],7);self.assertEqual(position,(7,0,0))
        self.assertEqual(seen,[(0,7)]);self.assertEqual([s['index'] for s in history],[1,0])

    def test_sequence_context_uses_original_index_after_reordering(self):
        class Context:
            def next(self):return 23
        modules=[module('Velocity Noise'),module('Sequence Random')]
        fields,_,history=initialize(modules,{9:0},(0,0,0),bind(random.Random(1),lambda *a:({},None),{},
            {1:Context()}),order=execution_order(modules))
        self.assertEqual(fields[9],23);self.assertEqual([s['index'] for s in history],[1,0])

    def test_incomplete_multi_attribute_callbacks_and_custom_fields_are_explicit(self):
        for name in ('Position From Control Points','Position Along Path Sequential'):
            with self.assertRaisesRegex(ValueError,'multi-attribute'):execution_order([module(name)])
        with self.assertRaisesRegex(ValueError,'color/alpha'):execution_order([module('Alpha Random',**{'output field':16})])
        with self.assertRaisesRegex(ValueError,'shared timing/strength'):
            execution_order([module('Velocity Noise',**{'operator start fadein':1})])
        with self.assertRaisesRegex(ValueError,'unverified initializer pass'):execution_order([module('Unknown')])

    def test_history_rejects_invalid_execution_indices(self):
        modules=[module('Lifetime Random')]
        for order in ([0,0],[-1],[1],[True]):
            with self.assertRaises(ValueError):initialize(modules,{1:1},(0,0,0),None,order=order)


if __name__=='__main__':unittest.main()
