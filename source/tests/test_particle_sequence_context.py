import unittest
from particle_sequence import SequenceSelection

class Constant:
    def __init__(self):self.calls=0
    def random(self):self.calls+=1;return 0.

class SequenceTests(unittest.TestCase):
    def test_fractional_and_nonfinite_bounds_are_not_truncated(self):
        for value in (.5,float('nan'),float('inf'),True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):SequenceSelection(dict(sequence_min=value),Constant())
    def test_integral_float_bounds_are_supported(self):
        self.assertEqual(SequenceSelection(dict(sequence_min=2.,sequence_max=2.),Constant()).next(),2)
    def test_linear_keeps_cycle_across_births(self):
        rng=Constant();context=SequenceSelection(dict(sequence_min=2,sequence_max=4,linear=True),rng)
        self.assertEqual([context.next() for _ in range(7)],[2,3,4,2,3,4,2]);self.assertEqual(rng.calls,0)
    def test_shuffle_reshuffles_existing_permutation(self):
        rng=Constant();context=SequenceSelection(dict(sequence_min=2,sequence_max=4,shuffle=True),rng)
        self.assertEqual([context.next() for _ in range(6)],[3,4,2,4,2,3]);self.assertEqual(rng.calls,4)
    def test_default_single_sequence_consumes_draw(self):
        rng=Constant();context=SequenceSelection({},rng)
        self.assertEqual(context.next(),0);self.assertEqual(rng.calls,1)
    def test_reversed_random_range_keeps_source_signed_span_and_consumption(self):
        class Units:
            def __init__(self):self.units=iter((0.,.25,.5,.75));self.calls=0
            def random(self):self.calls+=1;return next(self.units)
        rng=Units();context=SequenceSelection({'sequence_min':3},rng)
        self.assertEqual([context.next() for _ in range(4)],[3,3,2,2])
        self.assertEqual(rng.calls,4)
    def test_zero_signed_span_still_consumes_random_draw(self):
        rng=Constant();context=SequenceSelection({'sequence_min':3,'sequence_max':2},rng)
        self.assertEqual(context.next(),3);self.assertEqual(rng.calls,1)
    def test_primary_random_uses_float32_before_integer_truncation(self):
        import math
        class Boundary:
            def random(self):return math.nextafter(.5,0.)
        self.assertEqual(SequenceSelection({'sequence_max':1},Boundary()).next(),1)
    def test_reversed_context_modes_are_not_guessed(self):
        for key in ('shuffle','linear'):
            with self.assertRaisesRegex(ValueError,'Reversed shuffle/linear'):
                SequenceSelection({'sequence_min':3,key:True},Constant())

    def test_ordered_initializer_uses_context_for_each_module_index(self):
        from particle_initializer_sampler import bind
        class Fixed:
            def __init__(self,value):self.value=value
            def next(self):return self.value
        sampler=bind(Constant(),lambda *args: ({},None),{},
                     {1:Fixed(2),7:Fixed(5)})
        first=sampler(1,{'function':'Sequence Random','parameters':{}},{9:0},(0,0,0))
        second=sampler(7,{'function':'Sequence Random','parameters':{}},first[0],(0,0,0))
        self.assertEqual(first[0],{9:2})
        self.assertEqual(second[0],{9:5})

if __name__=='__main__':unittest.main()
