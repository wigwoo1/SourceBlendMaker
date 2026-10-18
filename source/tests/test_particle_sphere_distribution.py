import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from particle_sphere_distribution import choose, settings


class SphereDistributionTests(unittest.TestCase):
    def test_uniformly_selects_inclusive_supplied_control_point_range(self):
        config = settings({
            "control_point_number": 1,
            "randomly distribute to highest supplied Control Point": True,
            "randomly distribution growth time": 0.0,
            "scale cp (distance/speed/local speed)": -1,
        }, 3)
        values = [choose(random.Random(seed), config) for seed in range(32)]
        self.assertTrue(all(1 <= value <= 3 for value in values))
        self.assertEqual(set(values), {1, 2, 3})

    def test_disabled_distribution_needs_no_extra_control_points(self):
        self.assertIsNone(settings({"control_point_number": 1}, 1))

    def test_model_growth_and_cp_scaling_remain_rejected(self):
        base = {"control_point_number": 1,
                "randomly distribute to highest supplied Control Point": True}
        for updates, message in (
            ({"create in model": 1}, "model placement"),
            ({"randomly distribution growth time": 0.2}, "growth time"),
            ({"scale cp (distance/speed/local speed)": 2}, "scaled sphere"),
        ):
            with self.subTest(updates=updates), self.assertRaisesRegex(ValueError, message):
                settings({**base, **updates}, 3)

    def test_start_must_not_exceed_highest_available_cp(self):
        with self.assertRaisesRegex(ValueError, "precedes"):
            settings({"control_point_number": 4,
                      "randomly distribute to highest supplied Control Point": True}, 3)


if __name__ == "__main__":
    unittest.main()
