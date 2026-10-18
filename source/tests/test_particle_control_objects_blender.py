"""Blender integration tests for standalone SFM particle control transforms."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import bpy
except ImportError:
    bpy = None


@unittest.skipIf(bpy is None, "Run this transform test with Blender's Python")
class ParticleControlObjectTests(unittest.TestCase):
    def setUp(self):
        from particle_control_objects import import_missing
        self.import_missing = import_missing
        self.scene = bpy.context.scene
        self.created_ids = []

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.get("sfm_particle_control_point"):
                bpy.data.objects.remove(obj, do_unlink=True)
        for collection in list(bpy.data.collections):
            if collection.name == "SFM Particle Control Points" and collection.users == 0:
                bpy.data.collections.remove(collection)

    @staticmethod
    def transform(identifier, name, position):
        return SimpleNamespace(
            id=identifier,
            name=name,
            get=lambda key, default=None: position if key == "position" else default,
        )

    def test_creates_animated_object_for_standalone_transform(self):
        cp = self.transform("standalone-cp2", "controlPoint2", (255.0, 255.0, 255.0))
        system = SimpleNamespace(name="laser_sight_beam_dot", get=lambda key, default=None: [cp] if key == "controlPoints" else default)
        pending = [(system, {}, None)]
        calls = []

        def animate(obj, shot, transform, frames, seconds):
            calls.append((obj, transform, frames, seconds))
            obj.location = transform.get("position")

        result = self.import_missing(pending, self.scene, None, [1, 2], [0.0, 1.0], animate)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["ids"], ["standalone-cp2"])
        self.assertEqual(len(calls), 1)
        obj = next(o for o in self.scene.objects if o.get("sfm_transform_id") == "standalone-cp2")
        self.assertTrue(obj.get("sfm_particle_control_point"))
        self.assertTrue(obj.hide_render)
        self.assertEqual(tuple(obj.location), (255.0, 255.0, 255.0))

    def test_reuses_scene_transform_and_deduplicates_repeated_controls(self):
        existing = bpy.data.objects.new("existing CP0", None)
        self.scene.collection.objects.link(existing)
        existing["sfm_transform_id"] = "existing-cp0"
        cp = self.transform("existing-cp0", "controlPoint0", (1.0, 2.0, 3.0))
        system = SimpleNamespace(name="system", get=lambda key, default=None: [cp] if key == "controlPoints" else default)
        called = []
        result = self.import_missing([(system, {}, None), (system, {}, None)], self.scene, None, [1], [0.0], lambda *args: called.append(args))
        self.assertEqual(result["created"], 0)
        self.assertEqual(called, [])
        self.assertEqual(sum(o.get("sfm_transform_id") == "existing-cp0" for o in self.scene.objects), 1)
        bpy.data.objects.remove(existing, do_unlink=True)


if __name__ == "__main__":
    # Blender's command-line flags remain in sys.argv when it runs a script.
    sys.argv[:] = sys.argv[:1]
    unittest.main()
