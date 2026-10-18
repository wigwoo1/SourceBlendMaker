import unittest
from particle_collision_history import KillHistory
from particle_brush_trace import sweep

class CollisionHistoryTests(unittest.TestCase):
    def trace(self,start,end,radius):
        return sweep(start,end,[{'normal':(0,0,1),'distance':0}],radius)
    def test_stays_dead_when_trajectory_later_leaves_surface(self):
        history=KillHistory(lambda t:(0,0,1-4*t if t<=.5 else -1+4*(t-.5)),lambda t:0,self.trace)
        self.assertTrue(history.alive(.1));self.assertFalse(history.alive(1))
        self.assertAlmostEqual(history.death_age,.25)
        self.assertTrue(history.alive(.1));self.assertFalse(history.alive(.8))
    def test_initial_solid_and_radius_contact(self):
        inside=KillHistory(lambda t:(0,0,-1),lambda t:0,self.trace)
        self.assertFalse(inside.alive(0))
        expanded=KillHistory(lambda t:(0,0,1-t),lambda t:.2,self.trace)
        self.assertFalse(expanded.alive(1));self.assertAlmostEqual(expanded.death_age,.8)
    def test_query_order_does_not_change_trace_subdivisions(self):
        a=KillHistory(lambda t:(0,0,1-4*t*t),lambda t:0,self.trace)
        b=KillHistory(lambda t:(0,0,1-4*t*t),lambda t:0,self.trace)
        for t in (.003,.127,.251,.333):a.alive(t)
        a.alive(1);b.alive(1)
        self.assertEqual(a.death_age,b.death_age)
