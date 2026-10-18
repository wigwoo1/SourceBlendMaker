import unittest
from particle_force_history import ForceHistory
from particle_forces import displacement
from particle_collision_history import KillHistory

class ForceCacheCollisionTests(unittest.TestCase):
    def test_cached_motion_preserves_first_impact_and_rewind_visibility(self):
        modules=[{'function':'random force','parameters':{'min force':[3,0,0],'max force':[9,0,0]}}]
        def trace(start,end,radius):
            boundary=2-radius
            if start[0]>=boundary:return {'fraction':0.}
            if end[0]<boundary:return None
            return {'fraction':(boundary-start[0])/(end[0]-start[0])}
        for drag in (0,.00001,.2,2):
            cached=ForceHistory(modules,42,drag)
            reference=KillHistory(lambda age:displacement(modules,42,age,drag),lambda age:.1,trace)
            optimized=KillHistory(cached.query,lambda age:.1,trace)
            for age in (.003,.02,.1,.5,1,2,4,.1,1,4):
                self.assertEqual(reference.alive(age),optimized.alive(age))
            self.assertIsNotNone(reference.death_age)
            self.assertAlmostEqual(reference.death_age,optimized.death_age,places=10)
