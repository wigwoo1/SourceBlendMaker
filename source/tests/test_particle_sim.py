import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sim import Segment,continuous_births,living,emission_window,simulation_at,delayed_segments

class ParticleClockTests(unittest.TestCase):
    def test_child_delay_starts_fresh_clock(self):
        delayed=delayed_segments([Segment(0,4)],2)
        self.assertEqual(simulation_at(delayed,1),0)
        self.assertAlmostEqual(simulation_at(delayed,3),1)
        self.assertEqual([round(b.time,6) for b in continuous_births(delayed,2)],[2.5,3,3.5,4])

    def test_child_delay_respects_parent_pause(self):
        delayed=delayed_segments([Segment(0,1),Segment(1,5,simulating=False),Segment(5,8)],1.5)
        self.assertEqual(simulation_at(delayed,5),0)
        self.assertAlmostEqual(continuous_births(delayed,2)[0].time,6)

    def test_rate_and_lifetime(self):
        segments=[Segment(0,2)]
        births=continuous_births(segments,10)
        self.assertEqual(len(births),20)
        self.assertAlmostEqual(births[0].time,.1)
        self.assertEqual(len(living(births,segments,1,.2)),2)

    def test_gate_carries_fraction(self):
        segments=[Segment(0,.15),Segment(.15,.5,emitting=False),Segment(.5,.65)]
        births=continuous_births(segments,10)
        self.assertEqual(len(births),3)
        self.assertAlmostEqual(births[1].time,.55)

    def test_pause_freezes_lifetime(self):
        segments=[Segment(0,.2),Segment(.2,2,simulating=False),Segment(2,2.2)]
        births=continuous_births(segments,10)
        self.assertEqual(len(living(births,segments,1,.15)),2)
        self.assertEqual(len(births),4)
        self.assertAlmostEqual(births[2].time,2.1)

    def test_speed_ramp_subdivision_invariance(self):
        whole=continuous_births([Segment(0,2,speed_start=0,speed_end=2)],10)
        split=continuous_births([Segment(0,1,speed_start=0,speed_end=1),Segment(1,2,speed_start=1,speed_end=2)],10)
        self.assertEqual(len(whole),20)
        for a,b in zip(whole,split):self.assertAlmostEqual(a.time,b.time)
        self.assertAlmostEqual(whole[0].time,(.2)**.5)

    def test_rejects_invalid_and_excessive_bakes(self):
        with self.assertRaises(ValueError):continuous_births([Segment(0,1,speed_start=-1)],1)
        with self.assertRaises(ValueError):continuous_births([Segment(0,1)],100,max_particles=10)

    def test_delayed_finite_emitter_stops_births_but_not_aging(self):
        original=[Segment(0,10)]
        gated=emission_window(original,2,1)
        births=continuous_births(gated,4)
        self.assertEqual([round(b.time,6) for b in births],[2.25,2.5,2.75,3.0])
        self.assertAlmostEqual(simulation_at(gated,8),8)
        self.assertEqual(living(births,gated,8,1),[])

    def test_window_uses_frozen_simulation_time(self):
        original=[Segment(0,1),Segment(1,5,simulating=False),Segment(5,8)]
        gated=emission_window(original,1.5,.5)
        self.assertEqual([round(b.time,6) for b in continuous_births(gated,4)],[5.75,6.0])

    def test_window_preserves_ramp_and_gate_phase(self):
        original=[Segment(0,2,speed_start=0,speed_end=2)]
        gated=emission_window(original,.5,1)
        births=continuous_births(gated,2)
        self.assertEqual(len(births),2)
        self.assertAlmostEqual(births[0].simulation_time,1)
        self.assertAlmostEqual(births[0].time,math.sqrt(2))
        self.assertAlmostEqual(simulation_at(gated,2),2)

if __name__=='__main__':unittest.main()
