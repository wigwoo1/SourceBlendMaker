import unittest
from particle_bake import parameters

class ParameterDiagnosticsTests(unittest.TestCase):
    def test_missing_and_repeated_are_distinguished(self):
        d={'modules':{'initializers':[]}}
        with self.assertRaisesRegex(ValueError,'Missing required Lifetime Random'):
            parameters(d,'initializers','Lifetime Random')
        d['modules']['initializers']=[{'function':'Lifetime Random','parameters':{'lifetime_max':7}},
                                     {'function':'Lifetime Random','parameters':{'lifetime_max':.4}}]
        with self.assertRaisesRegex(ValueError,'Repeated Lifetime Random.*2 instances'):
            parameters(d,'initializers','Lifetime Random')
