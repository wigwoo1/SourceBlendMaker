import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_decay_experimental import living,activation
from particle_sim import Birth,Segment

class DelayedDecayTests(unittest.TestCase):
    timing={'operator start fadein':3,'operator end fadein':3}

    def test_default_decay_matches_existing_lifetime_clock(self):
        from particle_sim import living as ordinary_living
        segments=[Segment(0,1),Segment(1,2,simulating=False),Segment(2,5,speed_start=.5,speed_end=2)]
        births=[Birth(0,0,0),Birth(1,.5,.5)]
        for time in (0,.5,1,1.5,2,2.5,3,4):
            self.assertEqual(living(births,segments,time,{0:1,1:1},{}),ordinary_living(births,segments,time,1))

    def test_early_particle_survives_lifetime_but_late_birth_keeps_its_lifetime(self):
        births=[Birth(0,0,0),Birth(1,2.5,2.5)]
        segments=[Segment(0,5)];lives={0:1,1:1}
        self.assertEqual([(b.index,a) for b,a in living(births,segments,2,lives,self.timing)],[(0,2)])
        self.assertEqual([(b.index,a) for b,a in living(births,segments,3,lives,self.timing)],[(1,.5)])
        self.assertEqual(living(births,segments,3.5,lives,self.timing),[])

    def test_pause_speed_and_rewind_are_deterministic(self):
        segments=[Segment(0,1),Segment(1,4,simulating=False),Segment(4,6,speed_start=2,speed_end=2)]
        births=[Birth(0,0,0)];lives={0:1}
        expected=living(births,segments,4.5,lives,self.timing)
        self.assertEqual(expected,[(births[0],2)])
        self.assertEqual(living(births,segments,5,lives,self.timing),[])
        self.assertEqual(living(births,segments,4.5,lives,self.timing),expected)

    def test_ramps_and_invalid_clocks_stay_unsupported(self):
        for p in ({'operator end fadein':3},{'operator end fadeout':4},
                  {'operator fade oscillate':1},{'operator start fadein':float('nan')}):
            with self.assertRaises(ValueError):activation(p)
        with self.assertRaises(ValueError):
            living([Birth(0,0,0)],[Segment(0,1,speed_start=-1)],.5,{0:1},self.timing)
