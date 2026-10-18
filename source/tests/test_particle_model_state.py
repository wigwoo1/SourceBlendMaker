import unittest
from particle_model_state import State

class Random:
    def random(self):return .5
class Binding:
    boxes=[{}]
    def __init__(self):self.target=(0.,0.,0.);self.calls=0
    def point(self,index,relative,depsgraph):self.calls+=1;return self.target
class StateTests(unittest.TestCase):
    def test_cached_target_matches_binding_target_without_requery(self):
        binding=Binding();state=State(binding,{},Random(),None)
        calls=binding.calls
        self.assertEqual(state.lerp(.5,None,{},target=(10.,0.,0.)),(5.,0.,0.))
        self.assertEqual(binding.calls,calls)
        with self.assertRaises(ValueError):state.lerp(.75,None,{},target=(float('nan'),0.,0.))
    def test_duplicate_time_does_not_apply_movement_twice(self):
        binding=Binding();state=State(binding,{},Random(),None)
        binding.target=(10.,0.,0.)
        self.assertEqual(state.lerp(.5,None,{}),(5.,0.,0.))
        calls=binding.calls
        self.assertEqual(state.lerp(.5,None,{}),(5.,0.,0.))
        self.assertEqual(binding.calls,calls)
        self.assertEqual(state.lerp(.75,None,{}),(8.75,0.,0.))
    def test_changed_settings_backward_and_nonfinite_time_rejected(self):
        state=State(Binding(),{},Random(),None);state.lerp(.5,None,{})
        for age,parameters in ((.4,{}),(float('nan'),{}),(.5,{'lifetime lerp end':2})):
            with self.assertRaises(ValueError):state.lerp(age,None,parameters)
