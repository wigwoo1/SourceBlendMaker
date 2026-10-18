import unittest
from particle_secondary_alpha import History,rendered_alpha

class SecondaryAlphaTests(unittest.TestCase):
    def params(self,**changes):
        return {'oscillation field':16,'oscillation rate':-4,
                'oscillation frequency':1,'oscillation multiplier':0,
                'oscillation start phase':.5,**changes}
    def test_initial_and_linear_constant_wave(self):
        history=History([self.params()],0,step=.125)
        self.assertEqual(history.query(0),1)
        self.assertEqual(history.query(.125),.5)
        self.assertEqual(history.query(.25),0)
    def test_product(self):
        self.assertEqual(rendered_alpha(.5,.25),.125)
    def test_partial_does_not_mutate_tick_history(self):
        history=History([self.params()],0,step=.125)
        self.assertEqual(history.query(.0625),.75)
        self.assertEqual(history.query(.125),.5)
        self.assertEqual(history.query(.0625),.75)
    def test_collection_birth_time_changes_phase(self):
        p=self.params(**{'oscillation multiplier':1,'oscillation start phase':0})
        self.assertNotEqual(History([p],0,.125).query(.125),History([p],1,.125).query(.125))
    def test_ordered_clamping(self):
        negative=self.params(**{'oscillation rate':-16})
        positive=self.params(**{'oscillation rate':4})
        self.assertEqual(History([negative,positive],0,.125).query(.125),.5)
        self.assertEqual(History([positive,negative],0,.125).query(.125),0)
    def test_timed_strength_rejected(self):
        with self.assertRaises(ValueError):History([self.params(**{'operator end fadein':1})],0)

if __name__=='__main__':unittest.main()
