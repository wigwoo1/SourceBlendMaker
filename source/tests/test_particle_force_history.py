import unittest
from particle_force_history import ForceHistory
from particle_forces import displacement
from test_particle_forces import force

class ForceHistoryTests(unittest.TestCase):
    def test_small_positive_drag_preserves_reference_exactly(self):
        modules=force([-100,-100,-50],[100,100,100])
        for drag in (1.1e-8,1e-7,1e-6,1e-5,.0001,.001,.00999):
            history=ForceHistory(modules,42,drag)
            for age in (.003,.1,.7,1,5,15,14.99,.1,15.1):
                self.assertEqual(history.query(age),displacement(modules,42,age,drag))
    def test_matches_existing_force_model_and_rewind(self):
        modules=force([-5,-3,-2],[7,4,3])
        for drag in (0,.2,2):
            history=ForceHistory(modules,42,drag)
            for age in (0,.003,.02,.1,.2,.3,1,4,4.003,3.99,.1,4.1):
                expected=displacement(modules,42,age,drag)
                for a,b in zip(history.query(age),expected):self.assertAlmostEqual(a,b,places=10)
            self.assertLessEqual(max(len(h['samples']) for h in history.histories),8)
    def test_module_index_and_disabled_force_keep_seed_stream(self):
        modules=force([1,2,3],[4,5,6])*2
        modules=[{'function':'ignored','parameters':{}},*modules]
        history=ForceHistory(modules,13)
        for a,b in zip(history.query(.731),displacement(modules,13,.731)):self.assertAlmostEqual(a,b,places=12)
