import random,unittest
from types import SimpleNamespace
from particle_deaths import Deaths
from particle_parent_collection import Collection
from particle_birth_capacity import DeathAwareBirthCapacity

class ParticleDeathTests(unittest.TestCase):
    def test_first_death_wins_and_queries_can_rewind(self):
        deaths=Deaths();deaths.record(1,0.,2.);deaths.record(1,0.,3.)
        self.assertEqual(deaths.time(1),2.)
        self.assertFalse(deaths.alive(1,2.));self.assertTrue(deaths.alive(1,1.))
        deaths.record(1,0.,.5)
        self.assertFalse(deaths.alive(1,.5));self.assertTrue(deaths.alive(1,.25))

    def test_parent_death_does_not_shorten_authored_sampler_lifetime(self):
        deaths=Deaths();calls=[];birth=SimpleNamespace(index=1,simulation_time=0.)
        def sample(b,age,life):calls.append(life);return ((age,0,0),None,None,None)
        collection=Collection(1,[birth],{1:10.},{1:(0,0,0)},sample,1.,deaths=deaths)
        deaths.record(1,0.,.5)
        self.assertEqual(collection.snapshot(.5,.1).particle_ids,())
        self.assertEqual(collection.snapshot(.25,.1).particle_ids,(1,))
        self.assertEqual(calls,[10.,10.]);self.assertEqual(collection.lifetimes[1],10.)
        self.assertEqual(collection.snapshot(1.,.1).particle_ids,())

    def test_later_death_event_releases_existing_capacity_at_boundary(self):
        deaths=Deaths();capacity=DeathAwareBirthCapacity(1,deaths)
        self.assertTrue(capacity.has_capacity(0.));capacity.add(0.,10.,1)
        deaths.record(1,0.,.5)
        self.assertFalse(capacity.has_capacity(.49));self.assertTrue(capacity.has_capacity(.5))
        capacity.add(.5,20.,2)
        self.assertFalse(capacity.has_capacity(10.)) # stale natural expiry cannot free a second slot

    def test_precomputed_death_and_birth_time_death(self):
        deaths=Deaths();deaths.record(1,0.,0.);capacity=DeathAwareBirthCapacity(1,deaths)
        capacity.has_capacity(0.);capacity.add(0.,5.,1)
        self.assertTrue(capacity.has_capacity(0.))

    def test_random_births_and_early_deaths_match_direct_reference(self):
        rng=random.Random(15015);deaths=Deaths();capacity=DeathAwareBirthCapacity(9,deaths)
        active=[];clock=0.
        for identity in range(500):
            clock+=rng.choice((0.,.01,.1));life=rng.choice((.02,.2,1.,3.));death=clock+rng.random()*life
            # Supply simulator decisions before the next admission query.
            deaths.record(identity,clock,death)
            active=[(born,life,killed) for born,life,killed in active if clock-born<life and clock<killed]
            expected=len(active)<9
            self.assertEqual(capacity.has_capacity(clock),expected)
            if expected:capacity.add(clock,life,identity);active.append((clock,life,death))

    def test_natural_expiry_preserves_subtraction_rounding(self):
        capacity=DeathAwareBirthCapacity(1,Deaths());capacity.has_capacity(.5);capacity.add(.5,.2,1)
        self.assertFalse(capacity.has_capacity(.7));self.assertTrue(capacity.has_capacity(.7000000000000001))

    def test_invalid_history_and_reused_identity_rejected(self):
        deaths=Deaths()
        for identity,born,death in [(True,0,1),(1,1,0),(1,0,float('nan'))]:
            with self.assertRaises(ValueError):deaths.record(identity,born,death)
        deaths.record(1,0,1)
        with self.assertRaises(ValueError):deaths.record(1,2,3)
        with self.assertRaises(ValueError):deaths.alive(1,float('inf'))
        capacity=DeathAwareBirthCapacity(1,deaths);capacity.has_capacity(0.);capacity.add(0.,2.,1)
        capacity.has_capacity(1.)
        with self.assertRaises(ValueError):capacity.add(1.,2.,1)
        with self.assertRaises(ValueError):capacity.has_capacity(.9)

if __name__=='__main__':unittest.main()
