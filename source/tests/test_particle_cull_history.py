import unittest
from types import SimpleNamespace
from particle_cull_history import History
from particle_birth_capacity import DeathAwareBirthCapacity
from particle_parent_collection import Collection

class CullHistoryTests(unittest.TestCase):
    def birth(self,index=1,time=0.):return SimpleNamespace(index=index,simulation_time=time)
    def history(self,position=None,control=None):
        return History(position or (lambda b,a,l:(0,0,1-a*4)),control or (lambda b,a:(0,0,0)),step=.125)

    def test_capacity_and_parent_share_actual_death_without_shortening_lifetime(self):
        h=self.history();b=self.birth();h.add(b,10.)
        capacity=DeathAwareBirthCapacity(1,h);capacity.has_capacity(0.);capacity.add(0.,10.,1)
        seen=[]
        def sample(b,a,l):seen.append(l);return ((0,0,1-a*4),None,None,None)
        parent=Collection(0,[b],{1:10.},{1:(0,0,0)},sample,1.,deaths=h)
        self.assertEqual(parent.snapshot(.25,.125).particle_ids,(1,))
        self.assertEqual(seen,[10.,10.])
        h.advance(.375)
        self.assertTrue(capacity.has_capacity(.375));self.assertEqual(parent.snapshot(.375,.125).particle_ids,())
        self.assertEqual(parent.snapshot(.125,.125).particle_ids,(1,))
        self.assertEqual(parent.snapshot(1.,.125).particle_ids,())
        self.assertEqual(parent.lifetimes[1],10.)

    def test_short_excursion_is_not_lost_between_render_frames(self):
        h=self.history(lambda b,a,l:(0,0,-1 if .125<=a<=.25 else 1));h.add(self.birth(),3.)
        self.assertFalse(h.alive(1,1.));self.assertEqual(h.time(1),.125)

    def test_query_subdivision_and_rewind_do_not_change_death(self):
        a=self.history();b=self.history();a.add(self.birth(),2.);b.add(self.birth(),2.)
        a.advance(1.)
        for t in (.03,.14,.25,.4,1.,.05):b.advance(t)
        self.assertEqual(a.time(1),b.time(1));self.assertEqual(a.time(1),.375)

    def test_birth_clock_and_control_motion_are_used(self):
        h=self.history(lambda b,a,l:(0,0,1),lambda b,a:(0,0,a*4));h.add(self.birth(time=2.),2.)
        self.assertTrue(h.alive(1,2.25));self.assertFalse(h.alive(1,2.375));self.assertEqual(h.time(1),2.375)

    def test_no_future_sample_and_natural_lifetime_bounds(self):
        ages=[]
        h=self.history(lambda b,a,l:ages.append(a) or (0,0,1));h.add(self.birth(),.25)
        h.advance(.03);self.assertEqual(ages,[0.])
        h.advance(10.);self.assertEqual(ages,[0.,.125])

    def test_below_plane_at_birth_and_invalid_configuration(self):
        h=self.history(lambda b,a,l:(0,0,-1));h.add(self.birth(),1.)
        self.assertFalse(h.alive(1,0.));self.assertEqual(h.time(1),0.)
        with self.assertRaises(ValueError):h.add(self.birth(),1.)
        with self.assertRaises(ValueError):History(None,None,step=0.)
        with self.assertRaises(ValueError):h.advance(float('nan'))

    def test_registering_another_birth_invalidates_global_query_cache(self):
        h=self.history();h.add(self.birth(),10.);h.advance(2.)
        h.add(self.birth(index=2,time=1.),10.);h.advance(1.)
        self.assertFalse(h.alive(2,1.5))
        self.assertEqual(h.time(2),1.375)

if __name__=='__main__':unittest.main()
