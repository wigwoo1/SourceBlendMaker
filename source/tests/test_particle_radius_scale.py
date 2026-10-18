import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_radius_scale import sample,ordered_sample,history,sampled_radius,mixed_radius

class RadiusScaleTests(unittest.TestCase):
    def test_signed_spline_width_preserves_scale_and_requires_opt_in(self):
        modules=[{'function':'Radius Scale','parameters':{'radius_start_scale':1,'radius_end_scale':0}}]
        with self.assertRaises(ValueError):sampled_radius(modules,.5,1,-220)
        self.assertEqual(sampled_radius(modules,.5,1,-220,allow_signed_radius=True),-110)
        self.assertEqual(sampled_radius([],0,1,-220,allow_signed_radius=True),-220)
    def test_mixed_operator_order(self):
        import math
        scale={'function':'Radius Scale','parameters':{'radius_start_scale':2,'radius_end_scale':2}}
        oscillation={'function':'Oscillate Scalar Simple','parameters':{'oscillation field':3,'oscillation rate':10,'oscillation frequency':0,'oscillation multiplier':1,'oscillation start phase':math.pi/2}}
        self.assertAlmostEqual(mixed_radius([scale,oscillation],.5,1,10,.1),21)
        self.assertAlmostEqual(mixed_radius([oscillation,scale],.5,1,10,.1),20)
    def test_mixed_zero_rate_matches_scale_history(self):
        modules=[{'function':'Radius Scale','parameters':{'start_time':.1,'end_time':.4,'radius_start_scale':1,'radius_end_scale':3}},
                 {'function':'Oscillate Scalar Simple','parameters':{'oscillation field':3,'oscillation rate':0}}]
        for age in (0,.1,.25,.4,.8):self.assertAlmostEqual(mixed_radius(modules,age,1,10),sampled_radius(modules,age,1,10))
    def test_fast_history_matches_explicit_replay(self):
        import random,math
        rng=random.Random(7)
        for case in range(100):
            modules=[{'function':'Radius Scale','parameters':{'start_time':rng.random(), 'end_time':rng.random(), 'radius_start_scale':rng.random()*3, 'radius_end_scale':rng.random()*5, 'scale_bias':rng.uniform(.1,.9)}} for _ in range(3)]
            age=rng.uniform(0,2);life=rng.uniform(.1,2);step=1/120
            fractions=[tick*step/life for tick in range(math.floor(age/step)+1)]+[age/life]
            self.assertAlmostEqual(sampled_radius(modules,age,life,10,step),history(modules,fractions,10)[-1])
    def test_fast_history_strict_endpoint(self):
        modules=[{'function':'Radius Scale','parameters':{'start_time':0,'end_time':.5,'radius_start_scale':1,'radius_end_scale':2}}]
        self.assertAlmostEqual(sampled_radius(modules,.5,1,10,.1),18)
    def test_history_preserves_last_active_value(self):
        modules=[{'function':'Radius Scale','parameters':{'start_time':.2,'end_time':.5,'radius_start_scale':2,'radius_end_scale':4}}]
        self.assertEqual(history(modules,[0,.2,.35,.5,.9],10),[10,20,30,30,30])
    def test_history_rejects_backwards_time(self):
        with self.assertRaises(ValueError):history([], [.5,.25],10)
    def test_active_write_reads_initial_radius(self):
        self.assertEqual(sample({'radius_start_scale':2,'radius_end_scale':4},.5,10,999),30)
    def test_interval_preserves_current_value(self):
        p={'start_time':.2,'end_time':.8,'radius_start_scale':2,'radius_end_scale':4}
        for time in (0,.1,.8,1):self.assertEqual(sample(p,time,10,777),777)
        self.assertEqual(sample(p,.2,10,777),20)
    def test_repeated_active_scales_overwrite(self):
        modules=[{'function':'Radius Scale','parameters':{'radius_start_scale':2,'radius_end_scale':2}},
                 {'function':'Radius Scale','parameters':{'radius_start_scale':3,'radius_end_scale':3}}]
        self.assertEqual(ordered_sample(modules,.5,10,10),30)
    def test_invalid_interval_skips_and_nonfinite_rejects(self):
        self.assertEqual(sample({'start_time':1,'end_time':0},.5,10,7),7)
        with self.assertRaises(ValueError):sample({},float('nan'),10,7)
