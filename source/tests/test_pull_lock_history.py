import unittest
from particle_pull_lock_history import evaluate

class PullLockHistoryTests(unittest.TestCase):
    operators=[{'function':'Movement Basic','parameters':{}},
               {'function':'Movement Lock to Control Point','parameters':{}}]
    def test_translation_does_not_create_velocity_and_rewind_is_repeatable(self):
        lock=lambda p,a,b,l:(2*(b-a),0,0)
        result=evaluate(self.operators,(0,0,0),(0,0,0),1,3,lock)
        self.assertAlmostEqual(result[0][0],2,places=5)
        self.assertAlmostEqual(result[0][0],result[1][0],places=5)
        evaluate(self.operators,(0,0,0),(0,0,0),2,3,lock)
        self.assertEqual(result,evaluate(self.operators,(0,0,0),(0,0,0),1,3,lock))
    def test_force_observes_previous_lock_displacement(self):
        seen=[]
        def force(age,position):
            seen.append(position[0]);return (-position[0],0,0)
        locked=evaluate(self.operators,(0,0,0),(0,0,0),1,3,
            lambda p,a,b,l:(b-a,0,0),force)
        plain=evaluate(self.operators,(0,0,0),(0,0,0),1,3,
            lambda p,a,b,l:(0,0,0),lambda t,p:(-p[0],0,0))
        self.assertGreater(max(seen),0)
        self.assertLess(locked[0][0],plain[0][0]+1)

    def test_faded_lock_keeps_acquired_displacement(self):
        from particle_pull_lock_history import bind_translation_delta
        delta=bind_translation_delta({},lambda age:(age,0,0),fade=(.25,.5))
        position,_=evaluate(self.operators,(0,0,0),(0,0,0),3,4,delta)
        self.assertAlmostEqual(position[0],1.5,places=4)

    def test_bake_bridge_retains_per_birth_fade_after_detachment_and_rewind(self):
        from particle_pull_lock_history import baked_position
        lock={'start_fadeout_min':.2,'start_fadeout_max':.3,'end_fadeout_min':.4,'end_fadeout_max':.6}
        definition={'modules':{'operators':[self.operators[0],{'function':'Movement Lock to Control Point','parameters':lock}],'forces':[]}}
        state={'offset':(0,0,0),'velocity':(0,0,0),'creation_simulation_time':0.,
               'force_seed':7,'vector_oscillations':{},'translation_lock_fade':(.25,.5)}
        query=lambda cp,clock:(clock,0,0)
        for age in (3.,4.,3.):
            self.assertAlmostEqual(baked_position(definition,state,age,4.,1.,(0,0,0),query)[0],1.5,places=4)
        self.assertAlmostEqual(baked_position(definition,state,.25,4.,1.,(0,0,0),query)[0],.25,places=5)
        self.assertEqual(state['translation_lock_fade'],(.25,.5))
    def test_rotation_distance_and_shared_timing_require_more_work(self):
        from particle_pull_lock_history import bind_translation_delta
        for parameters in ({'lock rotation':True},{'distance fade range':1},
                           {'operator start fadein':1},
                           {'operator strength random scale min':.5}):
            with self.assertRaises(ValueError):
                bind_translation_delta(parameters,lambda age:(0,0,0))

    def test_external_acceleration_survives_translation_lock(self):
        base=evaluate(self.operators,(0,0,0),(0,0,0),1,3,
            lambda p,a,b,l:(0,0,0),acceleration=lambda age:(3,0,0))
        moving=evaluate(self.operators,(0,0,0),(0,0,0),1,3,
            lambda p,a,b,l:(b-a,0,0),acceleration=lambda age:(3,0,0))
        self.assertAlmostEqual(moving[0][0]-base[0][0],1,places=4)
        self.assertGreater(base[0][0],1)

    def test_cached_ticks_match_reference_and_fractional_rewinds(self):
        from particle_pull_lock_history import History
        lock=lambda p,a,b,l:(2*(b-a),0,0)
        force=lambda age,position:(-position[0],1,0)
        cached=History(self.operators,(1,0,0),(.2,0,0),4,lock,force)
        for age in (.1,.105,.2,.19,.5,1,.001,1.005):
            reference=evaluate(self.operators,(1,0,0),(.2,0,0),age,4,lock,force)
            self.assertEqual(cached.query(age),reference)
        self.assertLessEqual(len(cached.samples),8)

    def test_division_authored_tick_boundaries_match_cached_reference(self):
        from particle_pull_lock_history import History
        lock=lambda p,a,b,l:(b-a,0,0);force=lambda t,p:(-p[0],0,0)
        cached=History(self.operators,(0,0,0),(0,0,0),3,lock,force)
        for index in range(1,121):
            age=index/120
            self.assertEqual(cached.query(age),evaluate(self.operators,(0,0,0),(0,0,0),age,3,lock,force))

    def test_bake_bridge_scales_world_and_source_units_consistently(self):
        from particle_pull_lock_history import baked_position
        definition={'modules':{'operators':self.operators,'forces':[
            {'function':'Pull towards control point','parameters':{'amount of force':3,'falloff power':0}}]}}
        def state(scale):return {'offset':(0,0,0),'velocity':(.1*scale,0,0),
            'creation_simulation_time':0,'force_seed':7,'vector_oscillations':{}}
        source=state(1);scaled=state(.0254)
        for age in (.1,.3,.2,.5):
            a=baked_position(definition,source,age,2,1,(20,0,0),lambda cp,t:(2*t,0,0))
            b=baked_position(definition,scaled,age,2,.0254,(20*.0254,0,0),lambda cp,t:(2*t*.0254,0,0))
            for x,y in zip(a,b):self.assertAlmostEqual(x*.0254,y,places=7)
        self.assertIsNotNone(scaled.get('_pull_lock_history'))
