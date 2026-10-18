import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import math
import random
import unittest
from pathlib import Path
from particle_vector_history import DEFAULTS, History, evaluate, increment, sample, settings

def operator(name, parameters): return {'function': name, 'parameters': parameters}

class OrderedVectorTests(unittest.TestCase):
    def test_defaults_match_static_installed_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parent/'fixtures/vector_parameter_binding_validation.json').read_text())
        for p in receipt['parameters']:
            actual = DEFAULTS[p['name']]
            if isinstance(actual, tuple): expected = tuple(float(v) for v in p['default'].split())
            elif isinstance(actual, bool): expected = bool(int(p['default']))
            else: expected = float(p['default'])
            self.assertEqual(actual, expected, p['name'])

    def oscillator(self, offset=False, field=0):
        return settings({'oscillation rate min': (1., 0., 0.), 'oscillation rate max': (1., 0., 0.),
                         'oscillation frequency min': (0.,)*3, 'oscillation frequency max': (0.,)*3,
                         'offset instead of accelerate position': offset, 'oscillation field': field})

    def test_acceleration_mode_accumulates_velocity_and_preserves_order(self):
        step = 1/128; n = 16; move = operator('Movement Basic', {})
        osc = operator('Oscillate Vector', self.oscillator())
        for ops, expected in (([osc, move], step*n*(n+3)/2), ([move, osc], step*n*(n+1)/2)):
            result = evaluate(ops, (0.,)*3, (0.,)*3, (.5,)*3, n*step, 10., step=step)
            self.assertEqual(result[0], (expected, 0., 0.))
            self.assertGreater(result[0][0] - result[1][0], step)

    def test_offset_mode_does_not_inject_velocity(self):
        step = 1/128; n = 16; move = operator('Movement Basic', {})
        osc = operator('Oscillate Vector', self.oscillator(offset=True))
        for ops in ([osc, move], [move, osc]):
            position, previous, _ = evaluate(ops, (0.,)*3, (0.,)*3, (.5,)*3, n*step, 10., step=step)
            self.assertEqual(position, (n*step, 0., 0.))
            self.assertEqual(position, previous)

    def test_partial_step_keeps_constant_velocity(self):
        position, _, _ = evaluate([operator('Movement Basic', {})], (0.,)*3, (1., -2., 3.),
                                  (.5,)*3, .013, 1.)
        for actual, expected in zip(position, (.013, -.026, .039)):
            self.assertAlmostEqual(actual, expected, places=7)

    def test_rgb_clamps_each_tick_and_fade_order_matters(self):
        p = self.oscillator(field=6)
        p['oscillation rate min'] = p['oscillation rate max'] = (128., -128., 0.)
        osc = operator('Oscillate Vector', p)
        fade = operator('Color Fade', {'color_fade': (0, 0, 0, 255), 'fade_start_time': 0., 'fade_end_time': .001})
        arguments = ((0.,)*3, (0.,)*3, (.5,)*3, 1/128, 1.)
        self.assertEqual(evaluate([fade, osc], *arguments, step=1/128)[2], (1., 0., 0.))
        self.assertEqual(evaluate([osc, fade], *arguments, step=1/128)[2], (0., 0., 0.))

    def test_window_end_exclusive_and_absolute_clock_ignores_phase(self):
        p = self.oscillator()
        p.update({'start/end proportional': False, 'start time min': .2, 'start time max': .2,
                  'end time min': .5, 'end time max': .5})
        self.assertEqual(increment(p, .1, 10., .1), (0.,)*3)
        self.assertGreater(increment(p, .2, 10., .1)[0], 0.)
        self.assertEqual(increment(p, .5, 10., .1), (0.,)*3)
        p['proportional 0/1'] = False
        self.assertEqual(increment(p, .2, 10., .1), (0.,)*3)

    def test_random_ranges_are_sampled_once_and_persist(self):
        p = self.oscillator()
        p['oscillation rate max'] = (2., 1., 1.)
        sampled = sample(p, random.Random(19))
        self.assertEqual(sampled['oscillation rate min'], sampled['oscillation rate max'])
        from particle_scalar_oscillation import f32
        expected = tuple(f32(value * .01) for value in sampled['oscillation rate min'])
        for age in (.1, .2, .3): self.assertEqual(increment(sampled, age, 1., .01), expected)
        with self.assertRaises(ValueError): increment(p, .1, 1., .01)

    def test_spatial_force_reads_position_in_authored_order(self):
        step=1/128
        osc=operator('Oscillate Vector',self.oscillator(offset=True))
        move=operator('Movement Basic',{})
        from particle_vector_history import advance
        observed=[]
        def force(time,position):
            observed.append((time,position))
            return (-position[0],0.,0.)
        before=advance([osc,move],(1.,0.,0.),(1.,0.,0.),(.5,)*3,(.5,)*3,
                       step,10.,step,step,spatial_acceleration=force)
        self.assertEqual(observed[-1],(step,(1.+step,0.,0.)))
        after=advance([move,osc],(1.,0.,0.),(1.,0.,0.),(.5,)*3,(.5,)*3,
                      step,10.,step,step,spatial_acceleration=force)
        self.assertEqual(observed[-1],(step,(1.,0.,0.)))
        self.assertNotEqual(before[0],after[0])

    def test_spatial_twist_cache_preserves_partial_queries_and_rewinds(self):
        from particle_twist_axis import acceleration as twist, settings as twist_settings
        config=twist_settings({'amount of force':4.})
        force=lambda time,position:twist(config,position,(time*.2,0.,0.))
        ops=[operator('Oscillate Vector',self.oscillator()),operator('Movement Basic',{'drag':.2})]
        args=(ops,(2.,1.,0.),(.3,0.,0.),(.5,)*3)
        cached=History(*args,3.,spatial_acceleration=force)
        for age in (0.,.01,.017,.5,.503,.49,.001,.7):
            self.assertEqual(cached.query(age),evaluate(*args,age,3.,spatial_acceleration=force))
            self.assertLessEqual(len(cached.samples),8)

    def test_cache_matches_reference_with_partial_ticks_and_rewinds(self):
        rng=random.Random(81)
        ages=[0.,.001,.009,.003,.017] + sorted(rng.uniform(0.,2.) for _ in range(80)) + [.02,.01,1.91,2.001]
        for drag in (0.,.001,.2,.95):
            for offset in (False,True):
                operators=[operator('Movement Basic',{'drag':drag,'gravity':(0.,0.,-9.)}),
                           operator('Oscillate Vector',self.oscillator(offset=offset)),
                           operator('Oscillate Vector',self.oscillator(field=6))]
                position,velocity,color=(3.,-2.,1.),(.3,2.,-1.),(.1,.3,.5)
                acceleration=lambda time:(math.floor(time*60)%3-1.,.1,0.)
                cached=History(operators,position,velocity,color,3.,acceleration=acceleration)
                for age in ages:
                    self.assertEqual(cached.query(age),evaluate(operators,position,velocity,color,age,3.,acceleration=acceleration), (drag,offset,age))
                    self.assertLessEqual(len(cached.samples),8)

if __name__ == '__main__': unittest.main()
