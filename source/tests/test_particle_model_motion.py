import unittest
from particle_model_motion import advance,History

def module(name,**parameters):return dict(function=name,parameters=parameters)

class OrderedModelMotionTests(unittest.TestCase):
    def test_spawn_offset_and_bone_delta_preserve_velocity_on_scrub(self):
        from particle_model_offset import apply
        initial,_=apply((0,0,0),(0,0,0),(4,-2,1))
        history=History([module('Movement Basic'),module('Movement Lock to Bone')],
            initial,(8,0,0),lambda operator,old,new:((old*16,0,0),(new*16,0,0)),step=.125,maximum_age=1.)
        self.assertEqual(history.query(1.),((28,-2,1),(27,-2,1)))
        snapshots=list(history.snapshots.snapshots)
        self.assertEqual(history.query(.5625)[0],(17.5,-2,1))
        self.assertEqual(history.query(1.)[0],(28,-2,1))
        self.assertEqual(history.snapshots.snapshots,snapshots)
    def test_spawn_offset_is_interpolated_toward_hitbox(self):
        history=History([module('Movement Basic'),module('Movement Lerp to Hitbox')],
            (4,0,0),(8,0,0),lambda operator,old,new:((3,0,0),(3,0,0)),step=.125,maximum_age=1.)
        self.assertEqual(history.query(.125),((4.75,0,0),(3.875,0,0)))
    def test_initial_velocity_survives_first_hitbox_lerp_tick(self):
        history=History([module('Movement Basic'),module('Movement Lerp to Hitbox')],
                        (0,0,0),(8,0,0),lambda operator,old,new:((3,0,0),(3,0,0)),
                        step=.125,maximum_age=1.)
        # One metre of velocity displacement, then a 1/8 lerp toward x=3.
        self.assertEqual(history.query(.125),((1.25,0,0),(.375,0,0)))
        saved=list(history.snapshots.snapshots)
        self.assertEqual(history.query(.0625)[0],(.625,0,0))
        self.assertEqual(history.query(.125)[0],(1.25,0,0))
        self.assertEqual(history.snapshots.snapshots,saved)
    def test_lerp_order_preserves_gravity_then_interpolates_both_buffers(self):
        move=module('Movement Basic',gravity=(0,0,64))
        lerp=module('Movement Lerp to Hitbox')
        def run(operators):
            return advance(operators,(0,0,0),(-1,0,0),age=.5,step=.125,previous_step=.125,
                           target_pair=lambda operator:((0,0,0),(3,0,0)))
        self.assertEqual(run([move,lerp]),((2,0,.5),(1.5,0,0)))
        self.assertEqual(run([lerp,move]),((2,0,1),(1.5,0,0)))
    def test_history_backward_queries_do_not_repeat_model_displacement(self):
        history=History([module('Movement Basic'),module('Movement Lock to Bone')],
                        (0,0,0),(8,0,0),lambda operator,old,new:((old*16,0,0),(new*16,0,0)),
                        step=.125,maximum_age=1.)
        current,previous=history.query(1.)
        self.assertEqual(current,(24,0,0));self.assertEqual(previous,(23,0,0))
        snapshots=list(history.snapshots.snapshots)
        self.assertEqual(history.query(.5)[0],(12,0,0))
        self.assertEqual(history.query(.5625)[0],(13.5,0,0))
        self.assertEqual(history.query(1.)[0],current)
        self.assertEqual(history.snapshots.snapshots,snapshots)
    def test_history_stops_at_lifespan_limit(self):
        history=History([module('Movement Lock to Bone',**{'rigid lock':True})],
                        (0,0,0),(0,0,0),lambda operator,old,new:((0,0,0),(new,0,0)),step=.125,maximum_age=.3)
        self.assertAlmostEqual(history.query(.3)[0][0],.3,places=6)
        with self.assertRaises(ValueError):history.query(.31)
    def run_step(self,operators,position=(0,0,0),previous=(-1,0,0),target=((0,0,0),(3,0,0))):
        return advance(operators,position,previous,age=1,step=.125,previous_step=.125,
                       target_pair=lambda operator:target)
    def test_rigid_order_changes_gravity_displacement(self):
        move=module('Movement Basic',gravity=(0,0,64))
        lock=module('Movement Lock to Bone',**{'rigid lock':True})
        self.assertEqual(self.run_step([move,lock]),((3,0,0),(3,0,0)))
        self.assertEqual(self.run_step([lock,move]),((3,0,1),(3,0,0)))
    def test_follow_delta_preserves_velocity_for_next_movement(self):
        lock=module('Movement Lock to Bone')
        current,previous=self.run_step([module('Movement Basic'),lock])
        self.assertEqual((current,previous),((4,0,0),(3,0,0)))
        result=self.run_step([module('Movement Basic')],current,previous)
        self.assertEqual(result,((5,0,0),(4,0,0)))
    def test_disabled_lock_does_not_query_model(self):
        result=advance([module('Movement Lock to Bone',**{'operator enabled':False})],
                       (2,0,0),(1,0,0),age=1,step=.125,previous_step=.125,
                       target_pair=lambda operator:self.fail('Disabled lock queried target'))
        self.assertEqual(result,((2,0,0),(1,0,0)))
    def test_multiple_locks_use_their_own_targets(self):
        first=module('Movement Lock to Bone',control_point_number=0)
        second=module('Movement Lock to Bone',control_point_number=1)
        result=advance([first,second],(0,0,0),(-1,0,0),age=1,step=.125,previous_step=.125,
                       target_pair=lambda operator:((0,0,0),(operator['parameters']['control_point_number']+1,0,0)))
        self.assertEqual(result,((3,0,0),(2,0,0)))
