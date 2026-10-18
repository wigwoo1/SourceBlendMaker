import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_maintain_count import batch_times,target_count,schedule

class MaintainCountTests(unittest.TestCase):
    def test_replacement_and_capacity(self):
        from particle_sim import Segment
        births=schedule([Segment(0,1)],{'count to maintain':3},2,lambda birth:.5,step=.25)
        # Refills distribute creation over the preceding tick. The staggered
        # replacement particles therefore expire on different later ticks.
        self.assertEqual(len(births),7)
        self.assertEqual([b.simulation_time for b in births],[0,0,.25,.375,.5,.75,.875])
    def test_pause_and_emission_gate(self):
        from particle_sim import Segment
        births=schedule([Segment(0,.5),Segment(.5,1,simulating=False),Segment(1,1.5,emitting=False)],{'count to maintain':1},1,lambda birth:.25,step=.25)
        self.assertTrue(births)
        self.assertTrue(all(b.time<.5 for b in births))
    def test_replacement_lifetime_validation(self):
        from particle_sim import Segment
        with self.assertRaises(ValueError):schedule([Segment(0,1)],{},100,lambda birth:0)
    def test_target_defaults_scaling_and_truncation(self):
        self.assertEqual(target_count({}),100)
        self.assertEqual(target_count({'count to maintain':600}),600)
        p={'count to maintain':10,'maintain count scale control point':1,'maintain count scale control point field':1}
        self.assertEqual(target_count(p,[1,.29,3]),2)
        self.assertEqual(target_count(p,[1,-2,3]),0)
        with self.assertRaises(ValueError):target_count(p)
        with self.assertRaises(ValueError):target_count({'control point with snapshot data':0})
    def test_fill_and_capacity(self):
        self.assertEqual(batch_times(2,6,100,1,2,0),[1,1.25,1.5,1.75])
        self.assertEqual(batch_times(2,6,4,1,2,0),[1,1.5])
        self.assertEqual(batch_times(6,6,100,1,2,0),[])
        self.assertEqual(batch_times(8,6,100,1,2,0),[])
    def test_start_boundary_and_zero_tick(self):
        self.assertEqual(batch_times(0,2,100,1,2,3),[])
        self.assertEqual(batch_times(0,2,100,1,2,1.5),[1.5,1.75])
        self.assertEqual(batch_times(0,2,100,2,2,2),[2,2])
    def test_invalid_inputs(self):
        for args in ((-1,2,100,0,1,0),(0,2.5,100,0,1,0),(0,2,100,2,1,0),(0,2,100,0,float('nan'),0)):
            with self.assertRaises(ValueError):batch_times(*args)
