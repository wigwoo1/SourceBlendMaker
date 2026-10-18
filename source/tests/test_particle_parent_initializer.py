import unittest
from particle_parent_initializer import Initializer,motion
from particle_parent_buffer import Snapshot


class ParentInitializerTests(unittest.TestCase):
    def test_unsupported_shared_timing_is_rejected_before_sampling(self):
        for parameters in ({'operator start fadein':.5},
                           {'operator time scale max':2},
                           {'operator strength scale control point':0},
                           {'operator time offset min':float('nan')}):
            with self.subTest(parameters=parameters):
                with self.assertRaisesRegex(ValueError,'shared strength/time'):
                    Initializer(parameters)

    def test_inherited_displacement_becomes_world_units_per_simulation_second(self):
        origin,velocity=motion((10,0,0),(9,0,0),1/120,.0254)
        self.assertAlmostEqual(origin[0],.254)
        self.assertAlmostEqual(velocity[0],3.048)

    def test_zero_tick_allows_only_stationary_inherited_buffers(self):
        self.assertEqual(motion((1,0,0),(1,0,0),0,1),((1.,0.,0.),(0.,0.,0.)))
        with self.assertRaises(ValueError):motion((1,0,0),(0,0,0),0,1)

    def snapshot(self):
        return Snapshot.capture(0,1,(3,7),((10,0,0),(30,0,0)),((2,0,0),(14,0,0)))

    def test_sequential_births_follow_parent_cursor_and_inherit_motion(self):
        initializer=Initializer({'Inherited Velocity Scale':1})
        self.assertEqual(initializer.initialize(self.snapshot(),.75,.5),((6.,0.,0.),(2.,0.,0.)))
        self.assertEqual(initializer.initialize(self.snapshot(),.75,.5),((22.,0.,0.),(14.,0.,0.)))
        self.assertEqual(initializer.initialize(self.snapshot(),.75,.5)[0],(6.,0.,0.))

    def test_random_fractional_selection_blends_parent_birth_positions(self):
        initializer=Initializer({'Random Parent Particle Distribution':True,'Particle Increment Amount':.5,'Inherited Velocity Scale':1})
        self.assertEqual(initializer.initialize(self.snapshot(),.75,.5,.5),((14.,0.,0.),(8.,0.,0.)))

    def test_empty_parent_kills_birth_without_advancing_cursor(self):
        initializer=Initializer({})
        self.assertIsNone(initializer.initialize(Snapshot.capture(0,1,(),(),()),1,.1))
        self.assertEqual(initializer.cursor,0)
        with self.assertRaises(ValueError):initializer.initialize(None,1,.1)

    def test_initializer_instances_do_not_share_cursor(self):
        a,b=Initializer({}),Initializer({})
        a.initialize(self.snapshot(),1,.1)
        self.assertEqual(b.cursor,0)
