import unittest
from particle_parent_sample import position, birth_fraction, selection, buffer_position


class ParentSampleTests(unittest.TestCase):
    def test_fractional_parent_blends_both_buffers_before_birth_time(self):
        current=((10,0,0),(30,0,0));previous=((2,0,0),(14,0,0))
        # Spatial midpoint is current20, previous8. Birth halfway is14.
        self.assertEqual(buffer_position(current,previous,.5,.5,1),
                         ((14.,0.,0.),(8.,0.,0.)))

    def test_last_parent_and_single_parent_are_sampled_without_neighbor(self):
        self.assertEqual(buffer_position(((10,0,0),),((2,0,0),),0,.5,1),
                         ((6.,0.,0.),(2.,0.,0.)))
        self.assertEqual(buffer_position(((0,0,0),(10,0,0)),((0,0,0),(2,0,0)),1,.5)[0],
                         (6.,0.,0.))

    def test_parent_buffer_mismatch_and_missing_parent_are_rejected(self):
        with self.assertRaises(ValueError):buffer_position((),(),0,.5)
        with self.assertRaises(ValueError):buffer_position(((0,0,0),),(),0,.5)
        with self.assertRaises(ValueError):buffer_position(((0,0,0),),((0,0,0),),1,.5)

    def test_sequential_overflow_resets_instead_of_modulo(self):
        self.assertEqual(selection(3,7,2),(0.,2.))
        self.assertEqual(selection(3,2,2),(2.,4.))

    def test_random_fractional_increment_uses_last_index_range(self):
        self.assertEqual(selection(4,0,.5,.5),(1.5,2.))
        self.assertEqual(selection(5,0,.5,.5),(2.,2.5))
        self.assertEqual(selection(5,0,.5,.75),(3.,3.5))

    def test_integer_increment_random_selection_is_discrete(self):
        self.assertEqual(selection(5,0,1,.5),(2.,3.))
        self.assertEqual(selection(5,0,1,.99),(4.,5.))

    def test_empty_parent_and_unverified_negative_state_rejected(self):
        for args in ((0,0,1),(3,-1,1),(3,0,-1)):
            with self.assertRaises(ValueError):selection(*args)

    def test_creation_time_uses_rounded_tick_interval(self):
        self.assertEqual(birth_fraction(.75,1.,.5),.5)
        self.assertEqual(birth_fraction(0,1.,.5),0.)
        self.assertEqual(birth_fraction(2,1.,.5),1.)

    def test_zero_and_rounded_away_steps_use_time_boundary(self):
        self.assertEqual(birth_fraction(.9,1.,0),0.)
        self.assertEqual(birth_fraction(1.,1.,0),1.)
        self.assertEqual(birth_fraction(1e8,1e8,.001),1.)

    def test_mid_tick_birth_inherits_partial_displacement(self):
        # Parent moves 8 units this tick; birth halfway inherits only 4.
        self.assertEqual(position((10,20,30),(2,12,22),.5,1),
                         ((6.,16.,26.),(2.,12.,22.)))

    def test_zero_scale_preserves_stationary_child_previous(self):
        self.assertEqual(position((10,20,30),(2,12,22),.5),
                         ((6.,16.,26.),(6.,16.,26.)))

    def test_negative_scale_reverses_inherited_motion(self):
        self.assertEqual(position((10,0,0),(2,0,0),.5,-1),
                         ((6.,0.,0.),(10.,0.,0.)))

    def test_birth_fraction_is_clamped(self):
        self.assertEqual(position((10,0,0),(2,0,0),-1,1)[0],(2.,0.,0.))
        self.assertEqual(position((10,0,0),(2,0,0),2,1)[0],(10.,0.,0.))

    def test_invalid_buffers_are_rejected(self):
        for current in ((1,2),(float('nan'),0,0)):
            with self.assertRaises(ValueError):position(current,(0,0,0),.5)
