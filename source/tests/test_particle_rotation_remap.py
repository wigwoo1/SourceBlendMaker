import math
import unittest

from particle_rotation_remap import remap_speed, late_write_angle_correction


class RotationRemapTests(unittest.TestCase):
    def test_creation_time_remaps_to_rotation_speed(self):
        parameters = {
            'input field': 8, 'output field': 5,
            'input minimum': 0, 'input maximum': 1,
            'output minimum': -1, 'output maximum': 1,
        }
        self.assertEqual(remap_speed(parameters, 0.75, 0), 0.5)

    def test_ordered_late_write_applies_after_one_tick(self):
        correction = late_write_angle_correction(0, 1, 1, True)
        self.assertAlmostEqual(correction, math.radians(1) * (1 - 1/120))
        self.assertEqual(late_write_angle_correction(0, 1, 1, False), 0)

    def test_unsupported_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Only creation-time'):
            remap_speed({'input field': 7, 'output field': 5}, 0, 0)
        with self.assertRaises(ValueError):
            late_write_angle_correction(0, 1, -1, True)


if __name__ == '__main__':
    unittest.main()
