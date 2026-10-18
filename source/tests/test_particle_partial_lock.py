import unittest,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_partial_lock import displacement,exponent_sample,sampled_fades,history_displacement,validate

class MotionTests(unittest.TestCase):
    def test_prepared_inverse_matches_fade_motion_on_ramps_and_pauses(self):
        from particle_sim import Segment,Birth,simulation_at
        from particle_clock_prepared import PreparedInverse
        segments=[Segment(0,1,True,True,1.,2.),Segment(1,2,True,False),Segment(2,4,True,True,2.,.5)]
        inverse=PreparedInverse(segments)
        for birth_time in (0.,.5,1.5,2.5):
            birth=Birth(0,birth_time,simulation_at(segments,birth_time))
            for time in (2.75,3.5,4.):
                position=lambda t:(t*t,t*.3,0.)
                expected=history_displacement(segments,birth,time,2.,(.2,.8),position)
                actual=history_displacement(segments,birth,time,2.,(.2,.8),position,prepared_inverse=inverse)
                for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=8)
    def test_history_clock_maps_to_moving_control(self):
        from particle_sim import Segment,Birth
        segments=[Segment(0,4)]
        result=history_displacement(segments,Birth(0,0,0),4,2,(.5,1),lambda t:(10*t,0,0))
        self.assertAlmostEqual(result[0],15.,places=10)
    def test_experimental_scope_guards(self):
        self.assertEqual(validate({'start_fadeout_min':.5,'start_fadeout_max':.7}),(0,512.))
        for p in ({'lock rotation':True},{'distance fade range':1},{'control_point_number':64},{'instant jump threshold':-1}):
            with self.assertRaises(ValueError):validate(p)
    def test_installed_quarter_step_exponents(self):
        self.assertEqual(exponent_sample(.16,.5),.4)
        self.assertEqual(exponent_sample(.25,1.24),.25)
        self.assertAlmostEqual(exponent_sample(.25,1.25),.25**1.25)
        self.assertEqual(exponent_sample(.25,.1),1.)
    def test_independent_fade_samples(self):
        p={'start_fadeout_min':.5,'start_fadeout_max':.7,'end_fadeout_min':.8,'end_fadeout_max':1}
        self.assertEqual(sampled_fades(p,0,1),(.5,1.))
        self.assertEqual(sampled_fades(p,1,0),(.7,.8))
        for bad in (float('nan'),-1,2):
            with self.assertRaises(ValueError):sampled_fades(p,bad,.5)
    def test_detachment_preserves_received_motion(self):
        history=[(0,(0,0,0)),(1,(10,0,0)),(2,(20,0,0)),(3,(30,0,0))]
        # Full following for first second, half-average following for next.
        self.assertEqual(displacement(history,2,.5,1),(15.,0.,0.))
        self.assertEqual(displacement(history[:3],2,.5,1),(15.,0.,0.))
    def test_sample_density_invariance_for_linear_control(self):
        coarse=[(0,(0,0,0)),(4,(40,80,-40))]
        dense=[(i/10,(i,2*i,-i)) for i in range(41)]
        for a,b in zip(displacement(coarse,4,.5,1),displacement(dense,4,.5,1)):
            self.assertAlmostEqual(a,b,places=12)
    def test_full_lock_and_immediate_release(self):
        h=[(0,(3,4,5)),(1,(7,2,9))]
        self.assertEqual(displacement(h,2,1,1),(4.,-2.,4.))
        self.assertEqual(displacement(h,2,0,0),(0.,0.,0.))
    def test_control_reversal_does_not_undo_detached_motion(self):
        self.assertEqual(displacement([(0,(0,0,0)),(2,(20,0,0)),(4,(0,0,0))],2,.5,1),(15.,0.,0.))
    def test_invalid_and_conflicting_history(self):
        for h in ([(1,(0,0,0)),(0,(1,0,0))],[(0,(0,0,0)),(0,(1,0,0))],[(0,(float('nan'),0,0))]):
            with self.assertRaises(ValueError):displacement(h,2,.5,1)
    def test_jump_threshold_bypasses_age_fade(self):
        self.assertEqual(displacement([(0,(0,0,0)),(.5,(600,0,0)),(1,(610,0,0))],2,0,0),(600.,0.,0.))
        self.assertEqual(displacement([(0,(0,0,0)),(1,(512,0,0))],2,1,1),(512.,0.,0.))

