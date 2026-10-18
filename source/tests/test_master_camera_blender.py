"""Native camera cuts, source timing and saved-file checks (no SFM assets)."""
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import bpy
except ImportError:
    bpy = None


@unittest.skipIf(bpy is None, 'Run with Blender Python')
class MasterCameraTests(unittest.TestCase):
    def setUp(self):
        from blender_worker import Curves
        from master_camera import create_cameras
        self.Curves = Curves
        self.create = create_cameras
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.master = bpy.context.scene
        self.master.name = 'Master fixture'
        self.master.sequence_editor_create()

    def shot(self, name, master_start, source_start=1, duration=6):
        scene = bpy.data.scenes.new(name)
        scene.frame_start = source_start
        scene.frame_end = source_start + duration - 1
        parent = bpy.data.objects.new(name + ' parent', None)
        camera = bpy.data.objects.new(name + ' camera', bpy.data.cameras.new(name + ' data'))
        scene.collection.objects.link(parent); scene.collection.objects.link(camera)
        camera.parent = parent
        camera.location = (1, 2, 3)
        scene.camera = camera
        frames = [source_start, source_start + duration - 1]
        self.Curves(parent, name + ' parent motion').add('rotation_euler', frames, [(0, 0, 0), (0, 0, 1)])
        self.Curves(camera, name + ' motion').add('location', frames, [(1, 2, 3), (3, 4, 7)])
        self.Curves(camera.data, name + ' lens').add('lens', frames, [25, 80])
        strip = self.master.sequence_editor.strips.new_scene(name, scene, 1, master_start)
        strip.frame_final_duration = duration
        self.master.timeline_markers.new(name, frame=master_start)
        return scene, camera, strip

    def check_camera(self, scene, original, master_frame, source_frame):
        bpy.context.window.scene = scene
        scene.frame_set(math.floor(source_frame), subframe=source_frame % 1)
        original = original.evaluated_get(bpy.context.evaluated_depsgraph_get())
        expected = original.matrix_world.copy()
        lens = original.data.lens
        bpy.context.window.scene = self.master
        self.master.frame_set(math.floor(master_frame), subframe=master_frame % 1)
        proxy = self.master.camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
        self.assertTrue(self.master.camera.get('sfm_master_camera_proxy'))
        for a, b in zip(expected, proxy.matrix_world):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=5)
        self.assertAlmostEqual(lens, proxy.data.lens, places=4)

    def test_native_cuts_parent_motion_lens_and_save_reopen(self):
        first = self.shot('shot4', 1, 5)
        second = self.shot('shot3', 7, 10)
        source_actions = [s[1].animation_data.action for s in (first, second)]
        report = self.create(self.master, self.Curves)
        self.assertEqual([r['shot'] for r in report['cameras']], ['shot4', 'shot3'])
        self.assertTrue(all(r['method'] == 'shared_actions_retimed_with_native_nla' for r in report['cameras']))
        for index, source in enumerate((first, second)):
            proxy = bpy.data.objects[report['cameras'][index]['master_camera']]
            self.assertIs(source[1].animation_data.action, source_actions[index])
            self.assertEqual(proxy.animation_data.nla_tracks[0].strips[0].action, source_actions[index])
        for frame in (1, 2.5, 6, 7, 9.25, 12):
            source = first if frame < 7 else second
            self.check_camera(source[0], source[1], frame, source[0].frame_start + frame - source[2].frame_start)
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'master.blend')
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            self.master = bpy.data.scenes['Master fixture']
            for frame, shot, source_frame in ((6, 'shot4', 10), (7, 'shot3', 10), (9.5, 'shot3', 12.5)):
                scene = bpy.data.scenes[shot]
                self.check_camera(scene, scene.camera, frame, source_frame)

    def test_trimmed_scene_and_explicit_strip_camera(self):
        scene, camera, strip = self.shot('shot7', 13)
        alternate = bpy.data.objects.new('Override camera', bpy.data.cameras.new('Override data'))
        scene.collection.objects.link(alternate)
        alternate.location = (9, 8, 7); alternate.data.lens = 37
        strip.scene_camera = alternate
        strip.frame_offset_start = 2
        report = self.create(self.master, self.Curves)
        self.assertEqual(report['cameras'][0]['source_start'], 3)
        self.assertEqual(report['cameras'][0]['master_start'], 15)
        self.check_camera(scene, alternate, 16, 4)
        self.assertEqual(scene.camera, camera)

    def test_constraints_and_focus_target_are_baked(self):
        scene, camera, strip = self.shot('constrained', 10)
        target = bpy.data.objects.new('Constraint target', None)
        focus = bpy.data.objects.new('Focus target', None)
        scene.collection.objects.link(target); scene.collection.objects.link(focus)
        target.location = (0, 0, 0); focus.location = (0, 0, -12)
        camera.parent = None
        constraint = camera.constraints.new('COPY_TRANSFORMS'); constraint.target = target
        self.Curves(target, 'Constraint motion').add('location', [1, 6], [(0, 0, 0), (5, 0, 0)])
        camera.data.dof.use_dof = True; camera.data.dof.focus_object = focus
        report = self.create(self.master, self.Curves)
        self.assertEqual(report['cameras'][0]['method'], 'evaluated_camera_baked_at_each_output_frame')
        for frame in (10, 12, 15):
            self.check_camera(scene, camera, frame, frame - 9)
            self.assertAlmostEqual(self.master.camera.data.dof.focus_distance, 12, places=5)
        self.assertIsNone(self.master.camera.data.dof.focus_object)
        self.assertEqual(camera.data.dof.focus_object, focus)

    def test_missing_camera_is_reported_without_inventing_one(self):
        scene = bpy.data.scenes.new('Missing')
        scene.frame_end = 4
        self.master.sequence_editor.strips.new_scene('Missing', scene, 1, 1)
        report = self.create(self.master, self.Curves)
        self.assertEqual(report['cameras'], [])
        self.assertEqual(report['missing_shot_cameras'], ['Missing'])
        self.assertIsNone(self.master.camera)

    def test_timing_matches_actual_sequencer_render(self):
        import numpy as np
        scene = bpy.data.scenes.new('Rendered shot')
        scene.frame_start = 5; scene.frame_end = 10
        camera = bpy.data.objects.new('Render source camera', bpy.data.cameras.new('Render source data'))
        scene.collection.objects.link(camera); scene.camera = camera
        camera.data.type = 'ORTHO'; camera.data.ortho_scale = 10
        self.Curves(camera, 'Render source motion').add('location', [5, 10], [(0, 0, 5), (5, 0, 5)])
        mesh = bpy.data.meshes.new('Target quad')
        mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)], [], [(0,1,2,3)])
        target = bpy.data.objects.new('Render target', mesh); scene.collection.objects.link(target)
        material = bpy.data.materials.new('White emission'); material.use_nodes = True
        nodes = material.node_tree.nodes; nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial'); emission = nodes.new('ShaderNodeEmission')
        material.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
        mesh.materials.append(material)
        for s in (scene, self.master):
            s.render.engine = 'CYCLES'; s.cycles.samples = 1; s.cycles.use_denoising = False
            s.render.resolution_x = s.render.resolution_y = 64; s.render.resolution_percentage = 100
            s.render.image_settings.file_format = 'PNG'
        strip = self.master.sequence_editor.strips.new_scene('Rendered shot', scene, 1, 20)
        strip.animation_offset_start = 1
        strip.frame_offset_start = 2
        report = self.create(self.master, self.Curves)
        self.assertEqual(report['cameras'][0]['source_start'], 8)
        # Blender shifts frame_start by one when animation_offset_start is set;
        # the two-frame left trim therefore makes frame 23 the first image.
        self.assertEqual(report['cameras'][0]['master_start'], 23)
        self.check_camera(scene, camera, 23, 8)
        with tempfile.TemporaryDirectory() as directory:
            masks = []
            for s, frame, name in ((scene,8,'source'), (self.master,23,'master')):
                bpy.context.window.scene = s; s.frame_set(frame)
                s.render.filepath = str(Path(directory) / (name + '.png'))
                bpy.ops.render.render(scene=s.name, write_still=True)
                image = bpy.data.images.load(s.render.filepath, check_existing=False)
                pixels = np.array(image.pixels[:]).reshape(-1,4)
                masks.append(pixels[:,:3].max(axis=1) > .1)
            self.assertGreater(int(masks[0].sum()), 100)
            self.assertTrue(np.array_equal(*masks), 'Scene-strip render uses a different source frame')


if __name__ == '__main__':
    unittest.main(argv=[__file__])
