import random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_emitters import births
from particle_sim import Segment,living

def module(function,**p):return {'function':function,'parameters':p}

class EmitterTests(unittest.TestCase):
    def test_scaled_burst_samples_once_before_cap_spill(self):
        emitter=module('emit_instantaneously',num_to_emit=8,**{'emission count scale control point':1,'maximum emission per frame':2})
        samples=[]
        def sample(cp,field,time):samples.append((cp,field,time));return .5
        result=births([emitter],[Segment(0,1)],0,[0,.1,.2],burst_scale_sample=sample)
        self.assertEqual([b.time for b in result],[0,0,.1,.1])
        self.assertEqual(samples,[(1,0,0)])
    def test_scaled_burst_delayed_emission_samples_current_control(self):
        emitter=module('emit_instantaneously',num_to_emit=8,emission_start_time=.1,**{'emission count scale control point':0})
        samples=[]
        result=births([emitter],[Segment(0,.5,emitting=False),Segment(.5,1)],0,
                     burst_scale_sample=lambda cp,field,time:samples.append(time) or .25)
        self.assertEqual(len(result),2)
        self.assertEqual(samples,[.5])
    def test_default_burst_cap_uses_definition_capacity(self):
        emitter=module('emit_instantaneously',num_to_emit=250)
        result=births([emitter],[Segment(0,1)],0,[0,.1],maximum_particles=300)
        self.assertEqual(len(result),250)
        self.assertTrue(all(b.time==0 for b in result))

    def test_negative_default_cap_and_5000_ceiling(self):
        emitter=module('emit_instantaneously',num_to_emit=6000,**{'maximum emission per frame':-1})
        result=births([emitter],[Segment(0,1)],0,[0,.1],maximum_particles=10000)
        self.assertEqual(len(result),6000)
        self.assertEqual(sum(b.time==0 for b in result),5000)
        self.assertEqual(sum(b.time==.1 for b in result),1000)

    def test_definition_capacity_limits_default_burst_step(self):
        emitter=module('emit_instantaneously',num_to_emit=5)
        result=births([emitter],[Segment(0,1)],0,[0,.1,.2],maximum_particles=2)
        self.assertEqual([b.time for b in result],[0,0,.1,.1,.2])

    def test_random_burst_start_respects_simulation_pause(self):
        emitter=module('emit_instantaneously',num_to_emit=2,emission_start_time=.2,**{'emission_start_time max':.8})
        start=.2+.6*random.Random(0).random()
        result=births([emitter],[Segment(0,.1),Segment(.1,.6,simulating=False),Segment(.6,2)],0)
        self.assertEqual(len(result),2)
        for birth in result:
            self.assertAlmostEqual(birth.simulation_time,start)
            self.assertAlmostEqual(birth.time,start+.5)

    def test_snapshot_burst_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError,'Snapshot-scaled'):
            births([module('emit_instantaneously',**{'control point with snapshot data':0})],[Segment(0,1)],0)

    def test_reversed_burst_count_bounds_are_normalized(self):
        for seed in range(20):
            reversed_bounds=module('emit_instantaneously',num_to_emit=2,num_to_emit_minimum=8)
            ordinary=module('emit_instantaneously',num_to_emit=8,num_to_emit_minimum=2)
            result=births([reversed_bounds],[Segment(0,1)],seed)
            self.assertEqual(result,births([ordinary],[Segment(0,1)],seed))
            self.assertTrue(2<=len(result)<=8)

    def test_installed_default_burst_count_is_100(self):
        implicit=births([module('emit_instantaneously')],[Segment(0,1)],0)
        explicit=births([module('emit_instantaneously',num_to_emit=100)],[Segment(0,1)],0)
        self.assertEqual(implicit,explicit)
        self.assertEqual(len(implicit),100)

    def test_installed_default_rate_uses_100_per_second(self):
        implicit=births([module('emit_continuously')],[Segment(0,1)],0)
        explicit=births([module('emit_continuously',emission_rate=100)],[Segment(0,1)],0)
        self.assertEqual(implicit,explicit)
        self.assertEqual(len(implicit),100)
    def test_source_negative_one_duration_means_unbounded_emission(self):
        implicit=births([module('emit_continuously',emission_rate=2)],[Segment(0,1)],0)
        sentinel=births([module('emit_continuously',emission_rate=2,emission_duration=-1)],[Segment(0,1)],0)
        self.assertEqual(sentinel,implicit)
    def test_maintained_emission_requires_lifetime_scheduler(self):
        with self.assertRaisesRegex(ValueError,'lifetime-aware'):
            births([module('emit to maintain count')],[Segment(0,1)],0)
        with self.assertRaisesRegex(ValueError,'snapshot'):
            births([module('emit to maintain count',**{'control point with snapshot data':0})],[Segment(0,1)],0)
    def test_random_bursts_accept_the_converter_string_seed(self):
        m=[module('emit_instantaneously',num_to_emit=8,num_to_emit_minimum=2),
           module('emit_instantaneously',num_to_emit=9,num_to_emit_minimum=3)]
        seed='saved-session particle instance'
        expected=random.Random(seed).randint(2,8)+random.Random(seed+':emitter:1').randint(3,9)
        result=births(m,[Segment(0,1)],seed)
        self.assertEqual(len(result),expected)
        self.assertEqual(result,births(m,[Segment(0,1)],seed))
        self.assertTrue(all(b.time==0 for b in result))

    def test_merge_burst_and_independent_continuous_clocks(self):
        m=[module('emit_continuously',emission_rate=2),
           module('emit_instantaneously',num_to_emit=2,emission_start_time=.25),
           module('emit_continuously',emission_rate=4)]
        result=births(m,[Segment(0,1)],12)
        self.assertEqual([b.index for b in result],list(range(8)))
        for b,t in zip(result,[.25,.25,.25,.5,.5,.75,1,1]):
            self.assertAlmostEqual(b.time,t)
            self.assertAlmostEqual(b.simulation_time,t)

    def test_shared_gate_and_pause(self):
        m=[module('emit_continuously',emission_rate=2)]*2
        result=births(m,[Segment(0,.5),Segment(.5,1,simulating=False),Segment(1,1.5)],0)
        self.assertEqual([b.time for b in result],[.5,.5,1.5,1.5])
        self.assertEqual(len(living(result,[Segment(0,1)],.75,1)),2)

    def test_strength_timing_is_not_silently_ignored(self):
        m=module('emit_continuously',emission_rate=2)
        m['parameters']['operator fade oscillate']=.5
        with self.assertRaisesRegex(ValueError,'Oscillating emitter strength'):births([m],[Segment(0,1)],0)

    def test_capped_burst_spreads_and_respects_pause(self):
        emitter=module('emit_instantaneously',num_to_emit=5,**{'maximum emission per frame':2})
        result=births([emitter],[Segment(0,.1),Segment(.1,.2,simulating=False),Segment(.2,1)],0,[0,.1,.2,.3])
        self.assertEqual([b.time for b in result],[0,0,.2,.2,.3])
        self.assertEqual([b.index for b in result],list(range(5)))
        self.assertAlmostEqual(result[-1].simulation_time,.2)

    def test_capped_burst_truncates_at_shot_end(self):
        emitter=module('emit_instantaneously',num_to_emit=10,**{'maximum emission per frame':2})
        result=births([emitter],[Segment(0,.1)],0,[0,.05,.1])
        self.assertEqual(len(result),4)
