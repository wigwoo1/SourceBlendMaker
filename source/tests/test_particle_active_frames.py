import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sim import Birth,Segment,active_frame_samples,simulation_at,simulation_clock_samples


class ActiveParticleFrameTests(unittest.TestCase):
    def assert_schedule_matches_reference(self,segments,frames,seconds,births,lifetimes):
        expected={}
        for index,(frame,time) in enumerate(zip(frames,seconds)):
            clock=simulation_at(segments,time)
            alive=[(birth,max(0.,clock-birth.simulation_time)) for birth in births
                   if birth.index in lifetimes and birth.time<=time
                   and clock-birth.simulation_time<lifetimes[birth.index]-1e-10
                   and lifetimes[birth.index]>0]
            if alive:expected[index]=(frame,time,alive)
        actual={index:(frame,time,alive) for index,frame,time,alive
                in active_frame_samples(births,segments,frames,seconds,lifetimes)}
        self.assertEqual(actual,expected)

    def test_matches_living_during_speed_ramps_and_pauses(self):
        segments=[Segment(0,2,True,True,1.,2.),
                  Segment(2,4,False,False,2.,2.),
                  Segment(4,8,True,True,.5,1.5)]
        frames=list(range(17));seconds=[i*.5 for i in frames]
        births=[Birth(0,0.,0.),Birth(1,.5,.625),Birth(2,1.5,2.125),
                Birth(3,4.,3.),Birth(4,6.,4.5),Birth(5,9.,6.)]
        lifetimes={0:1.5,1:2.75,2:.5,3:1.,4:2.5,5:3.}
        self.assert_schedule_matches_reference(segments,frames,seconds,births,lifetimes)
        self.assertEqual(simulation_clock_samples(segments,seconds),
                         [simulation_at(segments,time) for time in seconds])

    def test_clock_sample_events_match_across_key_boundaries(self):
        segments=[Segment(0,1,True,True,0.,2.),Segment(1,2,False,True,2.,1.),
                  Segment(2,3,True,False,1.,1.),Segment(3,4,True,True,1.,.5)]
        times=[-1.,0.,.25,1.,1.5,2.,2.5,3.,3.5,4.,5.]
        self.assertEqual(simulation_clock_samples(segments,times),
                         [simulation_at(segments,time) for time in times])

    def test_skips_frames_without_living_particles_and_unaccepted_births(self):
        segments=[Segment(0,20)]
        frames=list(range(21));seconds=[float(i) for i in frames]
        births=[Birth(0,2.,2.),Birth(1,15.,15.),Birth(2,30.,30.)]
        lifetimes={0:2.,1:1.,2:4.,3:0.}
        samples=list(active_frame_samples(births,segments,frames,seconds,lifetimes))
        self.assertEqual([sample[0] for sample in samples],[2,3,15])
        self.assert_schedule_matches_reference(segments,frames,seconds,births,lifetimes)

    def test_randomized_event_schedule_is_equivalent(self):
        rng=random.Random(2481)
        segments=[Segment(0,3,True,True,.5,1.5),
                  Segment(3,5,True,False,1.5,1.5),
                  Segment(5,12,True,True,1.,.25)]
        frames=list(range(49));seconds=[i*.25 for i in frames]
        births=[];clock=0.
        for index in range(70):
            time=rng.random()*12
            births.append(Birth(index,time,simulation_at(segments,time)))
        births.sort(key=lambda birth:(birth.time,birth.index))
        lifetimes={birth.index:rng.choice((.05,.25,.75,1.5,3.,8.)) for birth in births}
        self.assert_schedule_matches_reference(segments,frames,seconds,births,lifetimes)


if __name__=='__main__':unittest.main()
