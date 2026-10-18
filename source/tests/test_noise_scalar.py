import math
import unittest
from particle_noise_scalar import sample


class NoiseScalarTests(unittest.TestCase):
    def setUp(self):
        self.tables = [list(range(256)) for _ in range(3)] + [[.75] * 256]

    def test_signed_and_absolute_ranges(self):
        self.assertEqual(sample({'output minimum': 10, 'output maximum': 30}, (0, 0, 0), 0, self.tables), 25)
        self.assertEqual(sample({'output minimum': 10, 'output maximum': 30, 'absolute value': True}, (0, 0, 0), 0, self.tables), 20)

    def test_inverted_negative_noise(self):
        self.tables[3] = [.25] * 256
        p = {'absolute value': True, 'invert absolute value': True}
        self.assertEqual(sample(p, (10, 20, 30), 2, self.tables), .5)

    def test_alpha_clamp_and_angle_conversion(self):
        self.assertEqual(sample({'output field': 7, 'output minimum': 2, 'output maximum': 4}, (0, 0, 0), 0, self.tables), 1)
        self.assertAlmostEqual(sample({'output field': 4, 'output maximum': 180}, (0, 0, 0), 0, self.tables), math.pi * .75, places=6)

    def test_reject_unknown_context_and_nonfinite(self):
        for p in ({'world time noise coordinate scale': 1}, {'output field': 99}, {'output maximum': float('nan')}):
            with self.assertRaises(ValueError):
                sample(p, (0, 0, 0), 0, self.tables)

    def test_ordered_remap_reads_noise_result(self):
        from particle_sprite_state import remap_scalars
        noise = {'function': 'Remap Noise to Scalar', 'parameters': {'output minimum': 10, 'output maximum': 30}}
        remap = {'function': 'Remap Initial Scalar', 'parameters': {'input field': 3, 'input minimum': 10, 'input maximum': 30, 'output field': 7}}
        fields = {3: 1, 7: 1, 8: 0}
        self.assertEqual(remap_scalars(fields, [noise, remap], (0, 0, 0), self.tables)[7], .75)
        self.assertEqual(remap_scalars(fields, [remap, noise], (0, 0, 0), self.tables)[7], 0)

    def test_offset_uses_only_preceding_noise(self):
        from particle_sprite_state import offset_radius
        noise = {'function': 'Remap Noise to Scalar', 'parameters': {'output maximum': 4}}
        offset = {'function': 'Position Modify Offset Random', 'parameters': {}}
        fields = {3: 1, 8: 0}
        self.assertEqual(offset_radius(fields, [noise, offset], noise_position=(0, 0, 0), noise_tables=self.tables), 3)
        self.assertEqual(offset_radius(fields, [offset, noise], noise_position=(0, 0, 0), noise_tables=self.tables), 1)

    def test_birth_context_is_required(self):
        from particle_sprite_state import remap_scalars
        module = {'function': 'Remap Noise to Scalar', 'parameters': {}}
        with self.assertRaises(ValueError):
            remap_scalars({3: 1, 8: 0}, [module])
        module['parameters']['operator enabled'] = False
        self.assertEqual(remap_scalars({3: 1, 8: 0}, [module])[3], 1)

    def test_secondary_opacity_noise_survives_history_rewind(self):
        from particle_sprite_state import remap_scalars
        from particle_secondary_alpha import History
        module = {'function': 'Remap Noise to Scalar', 'parameters': {'output field': 16}}
        fields = remap_scalars({16: 1, 8: 0}, [module], (0, 0, 0), self.tables)
        history = History([{'oscillation field': 16, 'oscillation rate': -.2}], 0, initial=fields[16])
        reference = History([{'oscillation field': 16, 'oscillation rate': -.2}], 0, initial=fields[16])
        history.query(1)
        self.assertEqual(history.query(.1), reference.query(.1))
        self.assertEqual(history.query(0), fields[16])
        with self.assertRaises(ValueError):
            History([], 0, initial=float('nan'))


if __name__ == '__main__':
    unittest.main()
