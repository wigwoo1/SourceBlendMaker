import unittest
from particle_vector_oscillation import resolve_zero_rate

class VectorOscillationTests(unittest.TestCase):
    def definition(self,p):return {'modules':{'operators':[{'function':'Oscillate Vector','parameters':p}]}}
    def test_zero_defaults_preserve_original(self):
        source=self.definition({})
        result,used=resolve_zero_rate(source)
        self.assertTrue(used)
        self.assertEqual(result['modules']['operators'],[])
        self.assertEqual(len(source['modules']['operators']),1)
    def test_invalid_ranges_and_fields_rejected(self):
        for p in ({'oscillation rate min':[0,1,0]},{'oscillation field':4},{'oscillation frequency max':[1,float('nan'),1]}):
            with self.assertRaises(ValueError):resolve_zero_rate(self.definition(p))
    def test_nonzero_is_retained_for_history(self):
        source=self.definition({'oscillation rate max':[1,0,0]})
        result,removed=resolve_zero_rate(source)
        self.assertFalse(removed)
        self.assertIs(result,source)
    def test_mixed_noop_removal_preserves_nonzero_and_disabled(self):
        modules=[{'function':'Oscillate Vector','parameters':p} for p in
                 ({},{'oscillation rate max':[1,0,0]},{'operator enabled':False})]
        source={'modules':{'operators':modules}}
        result,removed=resolve_zero_rate(source)
        self.assertTrue(removed)
        self.assertEqual(result['modules']['operators'],modules[1:])
