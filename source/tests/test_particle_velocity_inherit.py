import unittest
from particle_velocity_inherit import previous_position_delta as delta

class VelocityInheritanceArithmeticTests(unittest.TestCase):
    def sample(self, current=(1., 2., 3.), previous=(0., 0., 0.), **changes):
        args=dict(interval_48=.5, interval_4c=.25, clock_54=1.,
                  owner_3bc=0., owner_3c8=0., velocity_scale=2.)
        args.update(changes)
        return delta(current, previous, **args)

    def test_previous_position_write_has_opposite_sign_and_interval_ratio(self):
        self.assertEqual(self.sample(), (-1., -2., -3.))

    def test_negative_scale_reverses_inheritance(self):
        self.assertEqual(self.sample(velocity_scale=-2.), (1., 2., 3.))

    def test_zero_or_negative_interval_writes_nothing(self):
        for dt in (0., -.5):
            self.assertEqual(self.sample(interval_48=dt), (0., 0., 0.))

    def test_movement_cutoff_is_strict_and_uses_all_axes(self):
        self.assertEqual(self.sample((120., 160., 0.)), (0., 0., 0.))
        self.assertEqual(self.sample((198., 0., 0.)), (-198., 0., 0.))

    def test_timing_gate_boundary_and_both_owner_branches(self):
        self.assertEqual(self.sample(clock_54=.5), (0., 0., 0.))
        self.assertEqual(self.sample(clock_54=.25, owner_3bc=1.), (-1., -2., -3.))
        self.assertEqual(self.sample(clock_54=.25, owner_3c8=.5), (-1., -2., -3.))

    def test_stationary_control_does_not_add_velocity(self):
        self.assertEqual(self.sample((1., 2., 3.), (1., 2., 3.)), (0., 0., 0.))

    def test_missing_or_nonfinite_history_is_rejected(self):
        with self.assertRaises(ValueError):self.sample((0., 1.))
        with self.assertRaises(ValueError):self.sample(velocity_scale=float('nan'))

if __name__ == '__main__':unittest.main()
