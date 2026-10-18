import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_birth_capacity import ActiveBirthCapacity


class ActiveBirthCapacityTests(unittest.TestCase):
    def assert_matches_reference(self,events,maximum):
        active=[];expected=[]
        for index,(time,lifetime) in enumerate(events):
            active=[(born,life) for born,life in active if time-born<life]
            accepted=len(active)<maximum
            expected.append(accepted)
            if accepted:active.append((time,lifetime))

        capacity=ActiveBirthCapacity(maximum);actual=[]
        for index,(time,lifetime) in enumerate(events):
            accepted=capacity.has_capacity(time)
            actual.append(accepted)
            if accepted:capacity.add(time,lifetime,index)
        self.assertEqual(actual,expected)

    def test_expiry_and_simultaneous_births_match_reference(self):
        events=[(0.,.5),(0.,.25),(.25,.5),(.5,.2),(.5,.5),(.7,.25),(1.,.5)]
        self.assert_matches_reference(events,2)

    def test_randomized_sorted_births_match_reference(self):
        rng=random.Random(4501)
        events=[];time=0.
        for _ in range(1500):
            time+=rng.choice((0.,0.,.001,.01,.1))
            events.append((time,rng.choice((.001,.01,.25,.5,1.,3.))))
        self.assert_matches_reference(events,37)

    def test_expiry_at_exact_lifetime_frees_capacity(self):
        capacity=ActiveBirthCapacity(1)
        self.assertTrue(capacity.has_capacity(2.))
        capacity.add(2.,.5,0)
        self.assertFalse(capacity.has_capacity(2.499))
        self.assertTrue(capacity.has_capacity(2.5))

    def test_rejects_invalid_capacity_and_out_of_order_births(self):
        for maximum in (-1,True,1.5):
            with self.subTest(maximum=maximum),self.assertRaises(ValueError):ActiveBirthCapacity(maximum)
        capacity=ActiveBirthCapacity(2)
        capacity.has_capacity(1.)
        with self.assertRaises(ValueError):capacity.has_capacity(.9)


if __name__=='__main__':unittest.main()
