import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_forces import displacement


def force(low,high):
    return [{'function':'random force','parameters':{'min force':low,'max force':high}}]


class RandomForceTests(unittest.TestCase):
    def test_constant_force_matches_closed_form_with_drag(self):
        modules=force([2,-3,4],[2,-3,4]);age=.237
        for drag in (0,.2,2):
            factor=.5*age*age if drag==0 else age/drag-(1-math.exp(-drag*age))/(drag*drag)
            for value,acceleration in zip(displacement(modules,17,age,drag),(2,-3,4)):
                self.assertAlmostEqual(value,acceleration*factor,places=12)

    def test_repeatable_and_seed_dependent(self):
        modules=force([-5,-5,-5],[5,5,5])
        self.assertEqual(displacement(modules,3,.4),displacement(modules,3,.4))
        self.assertNotEqual(displacement(modules,3,.4),displacement(modules,4,.4))
        self.assertEqual(displacement(modules,3,0),[0,0,0])

    def test_disabled_force_and_reversed_bounds(self):
        modules=force([3,3,3],[-3,-3,-3])
        self.assertTrue(all(math.isfinite(v) for v in displacement(modules,4,.1)))
        modules[0]['parameters']['operator enabled']=False
        self.assertEqual(displacement(modules,4,.1),[0,0,0])
