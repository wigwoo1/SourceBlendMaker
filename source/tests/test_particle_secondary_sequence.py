import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_secondary_sequence import FIELD, from_unit, initialize, sample


class Samples:
    def __init__(self, *values):self.values=iter(values);self.count=0
    def random(self):self.count+=1;return next(self.values)


class SecondarySequenceTests(unittest.TestCase):
    def module(self, **parameters):
        return {'function':'Sequence Two Random','parameters':parameters}

    def test_uses_secondary_field_without_replacing_primary_sequence(self):
        before={9:2.,13:0.,4:50.}
        after=initialize([self.module(sequence_min=4,sequence_max=9)],before,Samples(.5))
        self.assertEqual(FIELD,13);self.assertEqual(after,{9:2.,13:7.,4:50.})
        self.assertEqual(before,{9:2.,13:0.,4:50.})

    def test_installed_reversed_bounds_are_not_sorted(self):
        params={'sequence_min':5,'sequence_max':0}
        self.assertEqual([from_unit(params,u) for u in (0.,.249,.25,.5,.75,.999)],
                         [5.,5.,4.,3.,2.,2.])

    def test_equal_bounds_still_consume_random_sample(self):
        rng=Samples(.3)
        self.assertEqual(sample({'sequence_min':6,'sequence_max':6},rng),6.)
        self.assertEqual(rng.count,1)

    def test_later_writes_win_disabled_writes_consume_nothing(self):
        modules=[self.module(sequence_min=4,sequence_max=9),
                 self.module(sequence_min=60,sequence_max=61,**{'operator enabled':False}),
                 self.module(sequence_min=1,sequence_max=2)]
        rng=Samples(.5,0.)
        self.assertEqual(initialize(modules,{9:3},rng),{9:3,13:1.})
        self.assertEqual(rng.count,2)

    def test_reproduces_sse_rounding_at_upper_edge(self):
        # A double input below one rounds to 1.0f in SSE. The installed code
        # does not clamp the result back into the configured range.
        self.assertEqual(from_unit({'sequence_min':4,'sequence_max':9},1-1e-9),10.)

    def test_invalid_parameters_are_explicit(self):
        for value in (-1,64,2.1,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):from_unit({'sequence_min':value},.1)
        for unit in (-.1,1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):from_unit({},unit)

    def test_omitted_bounds_use_installed_metadata_defaults(self):
        self.assertEqual(from_unit({},.9),0.)
