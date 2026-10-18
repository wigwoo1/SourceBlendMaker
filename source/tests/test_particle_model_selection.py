import unittest
from particle_model_selection import select

class Draws:
    def __init__(self):self.values=iter((.5,.25,.5,.75));self.calls=0
    def random(self):self.calls+=1;return next(self.values)
class SelectionTests(unittest.TestCase):
    def test_scaled_coordinates_follow_source_endpoints(self):
        for scale,expected in ((.5,(.5,.5,.5)),(.75,(.375,.5,.625)),(2.,(-.25,.5,1.25)),(0.,(.75,.5,.25))):
            rng=Draws();self.assertEqual(select({'model hitbox scale':scale},78,rng)['relative'],expected)
            self.assertEqual(rng.calls,4)
    def test_index_and_persistent_coordinates(self):
        rng=Draws();self.assertEqual(select({},78,rng),dict(index=39,relative=(.25,.5,.75)))
        self.assertEqual(rng.calls,4)
    def test_desired_index_clamps_and_consumes_selection_draw(self):
        rng=Draws();self.assertEqual(select({'desired hitbox':999},78,rng)['index'],77)
        self.assertEqual(rng.calls,4)
    def test_unverified_settings_rejected(self):
        for p in ({'model hitbox scale':-.5},{'model hitbox scale':float('nan')},{'model hitbox scale':1e39},{'force to be inside model':.5},{'direction bias':(0,float('nan'),0)},{'desired hitbox':.5}):
            with self.assertRaises(ValueError):select(p,78,Draws())
    def test_sfm_ignored_bias_and_surface_flag_preserve_draws(self):
        rng=Draws();actual=select({'direction bias':(100,-50,20),'force to be inside model':2},78,rng)
        self.assertEqual(actual,select({},78,Draws()));self.assertEqual(rng.calls,4)
