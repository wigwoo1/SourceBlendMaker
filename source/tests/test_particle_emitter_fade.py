import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_emitter_fade import continuous,settings
from particle_sim import Segment

class EmitterFadeTests(unittest.TestCase):
    def test_fade_in_integrates_emission_instead_of_scaling_existing_particles(self):
        p={'operator end fadein':1}
        result=continuous([Segment(0,1)],4,p)
        self.assertEqual(len(result),2)
        self.assertAlmostEqual(result[0].time,math.sqrt(.5))
        self.assertAlmostEqual(result[1].time,1)

    def test_fade_out_and_segment_subdivision(self):
        p={'operator end fadeout':1}
        whole=continuous([Segment(0,2)],4,p)
        split=continuous([Segment(0,.25),Segment(.25,.75),Segment(.75,2)],4,p)
        self.assertEqual(len(whole),2);self.assertEqual(len(split),2)
        self.assertAlmostEqual(whole[0].time,1-math.sqrt(.5))
        for a,b in zip(whole,split):self.assertAlmostEqual(a.time,b.time,places=7)

    def test_clock_speed_and_pause(self):
        p={'operator end fadein':1}
        result=continuous([Segment(0,.25,speed_start=2,speed_end=2),
                           Segment(.25,1.25,simulating=False),
                           Segment(1.25,1.5,speed_start=2,speed_end=2)],4,p)
        self.assertEqual(len(result),2)
        self.assertAlmostEqual(result[0].time,1.25+(math.sqrt(.5)-.5)/2)
        self.assertAlmostEqual(result[1].time,1.5)

    def test_zero_end_disables_an_orphaned_emitter_fade_start(self):
        p={'operator start fadein':.17,'operator end fadein':0,
           'operator start fadeout':.2,'operator end fadeout':0}
        self.assertEqual(settings(p),(0.,0.,0.,0.))
        self.assertEqual(continuous([Segment(0,1)],4,p),
                         continuous([Segment(0,1)],4,{}))

    def test_unsupported_or_invalid_fades(self):
        for p in ({'operator end fadein':float('nan')},{'operator end fadeout':-1},
                  {'operator start fadein':2,'operator end fadein':1},
                  {'operator end fadein':2,'operator start fadeout':1,'operator end fadeout':3},
                  {'operator fade oscillate':1}):
            with self.assertRaises(ValueError):settings(p)
