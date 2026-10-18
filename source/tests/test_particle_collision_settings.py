import unittest
from particle_collision_settings import settings

class CollisionSettingsTests(unittest.TestCase):
    def test_shared_fades_and_seeded_timing_rejected(self):
        for change in ({'operator start fadeout':1},{'operator time scale seed':4},
                       {'operator strength scale control point':2}):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'shared timing'):
                settings({'kill particle on collision':True,**change})
    def test_authored_snow_kill_trace_configuration(self):
        p=settings({'kill particle on collision':True,'collision group':'DEBRIS','trace accuracy tolerance':256})
        self.assertEqual(p['collision group'],'DEBRIS')
        self.assertEqual(p['radius scale'],1)
        self.assertEqual(p['trace accuracy tolerance'],256)
    def test_unsupported_responses_and_filters_rejected(self):
        for change in ({'kill particle on collision':False},{'collision mode':3},{'collision group':'PLAYER'},{'Confirm Collision':True}):
            with self.assertRaises(ValueError):settings({'kill particle on collision':True,**change})
    def test_invalid_radius_and_offset_rejected(self):
        for change in ({'radius scale':-1},{'control point offset for fast collisions':[0,float('nan'),0]}):
            with self.assertRaises(ValueError):settings({'kill particle on collision':True,**change})
