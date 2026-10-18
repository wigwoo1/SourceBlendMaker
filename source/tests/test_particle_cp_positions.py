import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from particle_bake import plan
from particle_cp_positions import settings
from test_particle_initial_only import definition


def params(**updates):
    return {
        "First Control Point Number": 1,
        "First Control Point Parent": 0,
        "First Control Point Location": [0.0, 0.0, 500.0],
        "Second Control Point Number": 2,
        "Second Control Point Parent": 0,
        "Second Control Point Location": [0.0, 128.0, 0.0],
        "Set positions in world space": False,
        "Control Point to offset positions from": 0,
        "operator start fadein": 0.0,
        "operator end fadein": 0.0,
        "operator start fadeout": 0.0,
        "operator end fadeout": 0.0,
        "operator fade oscillate": 0.0,
        **updates,
    }


class ControlPointPositionTests(unittest.TestCase):
    def test_normalizes_multiple_local_origin_offsets(self):
        result = settings(params())
        self.assertEqual(result["points"], [
            {"target": 1, "parent": 0, "location": (0.0, 0.0, 500.0)},
            {"target": 2, "parent": 0, "location": (0.0, 128.0, 0.0)},
        ])

    def test_planner_accepts_supported_control_point_operator(self):
        effect = definition(2)
        effect["modules"]["operators"].append({
            "function": "Set Control Point Positions", "parameters": params()})
        self.assertEqual(plan(effect)["renderer"], "render_animated_sprites")

    def test_planner_rejects_unverified_world_space_and_parent_modes(self):
        for updates, message in (
            ({"Set positions in world space": True}, "world space"),
            ({"Control Point to offset positions from": 2}, "nonzero offset"),
            ({"First Control Point Parent": 3}, "nonzero parent"),
            ({"operator start fadein": 0.25}, "fades"),
        ):
            with self.subTest(updates=updates):
                effect = definition(2)
                effect["modules"]["operators"].append({
                    "function": "Set Control Point Positions", "parameters": params(**updates)})
                with self.assertRaisesRegex(ValueError, message):
                    plan(effect)

    def test_conflicting_duplicate_target_and_unknown_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "configures control point 1 more than once"):
            settings(params(**{
                "Second Control Point Number": 1,
                "Second Control Point Location": [1.0, 0.0, 0.0],
            }))
        with self.assertRaisesRegex(ValueError, "Unverified.*mystery"):
            settings(params(mystery=1))

    def test_source_default_metadata_fields_are_accepted_but_nondefaults_rejected(self):
        defaults = {
            "operator time offset seed": 0,
            "operator time offset min": 0.0,
            "operator time offset max": 0.0,
            "operator time scale seed": 0,
            "operator time scale min": 1.0,
            "operator time scale max": 1.0,
            "operator time strength random scale max": 1.0,
            "operator strength scale seed": 0,
            "operator strength random scale min": 1.0,
            "operator strength random scale max": 1.0,
            "operator strength scale control point": -1,
            "operator end cap state": -1,
            "operator help and notes": "",
            "Inherit CP Orientation": False,
            "Only set position once": False,
        }
        self.assertEqual(settings(params(**defaults))["points"][0]["target"], 1)
        for field, value in (("operator time scale min", 0.5),
                             ("operator strength random scale max", 2.0),
                             ("operator strength scale control point", 2),
                             ("Inherit CP Orientation", True),
                             ("Only set position once", True)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "non-default unverified"):
                settings(params(**{field: value}))

    def test_bad_indices_and_nonfinite_locations_rejected(self):
        for updates in (
            {"First Control Point Number": 1.5},
            {"First Control Point Number": 64},
            {"First Control Point Location": [0.0, float("nan"), 0.0]},
            {"First Control Point Location": [0.0, 1.0]},
        ):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                settings(params(**updates))


if __name__ == "__main__":
    unittest.main()
