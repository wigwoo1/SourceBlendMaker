"""Transform-follow integration test. Run with Blender --background --python."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None


@unittest.skipIf(bpy is None, "Run this transform test with Blender's Python")
class ControlPointPositionTransformTests(unittest.TestCase):
    def test_local_offset_follows_animated_origin_transform(self):
        from particle_cp_positions import overlay

        root = bpy.data.objects.new("CP positions test origin", None)
        bpy.context.scene.collection.objects.link(root)
        root["sfm_transform_id"] = "cp0"
        driver = bpy.data.objects.new("CP positions test animated driver", None)
        bpy.context.scene.collection.objects.link(driver)
        target = bpy.data.objects.new("CP positions test target", None)
        bpy.context.scene.collection.objects.link(target)
        target["sfm_transform_id"] = "cp1"
        root.rotation_euler[2] = 1.5707963267948966
        constraint = root.constraints.new("COPY_LOCATION")
        constraint.target = driver
        driver.location = (1.0, 2.0, 3.0)
        driver.keyframe_insert(data_path="location", frame=1)
        driver.location = (5.0, 0.0, 0.0)
        driver.keyframe_insert(data_path="location", frame=3)
        bpy.context.view_layer.update()

        definition = {
            "name": "local-offset-fixture",
            "modules": {"operators": [{
                "function": "Set Control Point Positions",
                "parameters": {
                    "First Control Point Number": 1,
                    "First Control Point Parent": 0,
                    "First Control Point Location": [0.0, 128.0, 0.0],
                },
            }]},
        }
        descriptor = {"control_points": [{"id": "cp0"}, {"id": "cp1"}]}
        controls, config = overlay(definition, descriptor,
                                   {"cp0": root, "cp1": target}, 0.0254,
                                   bpy.context.scene)
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        first = controls["cp1"].matrix_world.translation.copy()
        self.assertAlmostEqual(first.x, 1.0 - 128.0 * 0.0254, places=5)
        self.assertAlmostEqual(first.y, 2.0, places=5)
        self.assertAlmostEqual(first.z, 3.0, places=5)
        self.assertEqual(len(config["points"]), 1)

        bpy.context.scene.frame_set(3)
        bpy.context.view_layer.update()
        moved = controls["cp1"].matrix_world.translation
        self.assertAlmostEqual(moved.x, 5.0 - 128.0 * 0.0254, places=5)
        self.assertAlmostEqual(moved.y, 0.0, places=5)
        self.assertAlmostEqual(moved.z, 0.0, places=5)

        bpy.data.objects.remove(root, do_unlink=True)
        bpy.data.objects.remove(driver, do_unlink=True)
        bpy.data.objects.remove(target, do_unlink=True)

    def test_operator_creates_control_points_missing_from_session(self):
        from particle_cp_positions import overlay

        root = bpy.data.objects.new("CP positions generated origin", None)
        bpy.context.scene.collection.objects.link(root)
        root["sfm_transform_id"] = "generated-cp0"
        root.location = (2.0, 3.0, 4.0)
        bpy.context.view_layer.update()
        definition = {
            "name": "generated-control-points",
            "modules": {"operators": [{
                "function": "Set Control Point Positions",
                "parameters": {
                    "First Control Point Number": 1,
                    "First Control Point Parent": 0,
                    "First Control Point Location": [0.0, 128.0, 0.0],
                    "Second Control Point Number": 2,
                    "Second Control Point Parent": 0,
                    "Second Control Point Location": [0.0, -128.0, 0.0],
                },
            }]},
        }
        descriptor = {"control_points": [{"id": "generated-cp0"}]}
        controls, config = overlay(definition, descriptor, {"generated-cp0": root},
                                   0.0254, bpy.context.scene)
        self.assertEqual([point["name"] for point in descriptor["control_points"][1:]],
                         ["controlPoint1", "controlPoint2"])
        positive = controls[descriptor["control_points"][1]["id"]].matrix_world.translation
        negative = controls[descriptor["control_points"][2]["id"]].matrix_world.translation
        self.assertAlmostEqual(positive.x, 2.0, places=5)
        self.assertAlmostEqual(positive.y, 3.0 + 128.0 * 0.0254, places=5)
        self.assertAlmostEqual(positive.z, 4.0, places=5)
        self.assertAlmostEqual(negative.x, 2.0, places=5)
        self.assertAlmostEqual(negative.y, 3.0 - 128.0 * 0.0254, places=5)
        self.assertAlmostEqual(negative.z, 4.0, places=5)
        self.assertEqual(len(config["points"]), 2)
        bpy.data.objects.remove(root, do_unlink=True)


if __name__ == "__main__":
    unittest.main()
