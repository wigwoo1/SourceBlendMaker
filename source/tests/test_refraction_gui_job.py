import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import App,blender_open_args
from batch_queue import plan_jobs
class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
class RefractionGuiTests(unittest.TestCase):
    def test_master_timeline_setting_controls_blender_open_command(self):
        self.assertEqual(blender_open_args('blender.exe','scene.blend'),['blender.exe','scene.blend'])
        args=blender_open_args('blender.exe','scene.blend',True)
        self.assertEqual(args[:2],['blender.exe','scene.blend'])
        self.assertEqual(args[2],'--python-expr')
        self.assertIn("bpy.data.workspaces.get('SFM Timeline')",args[3])

    def test_setting_reaches_single_and_batch_jobs(self):
        for enabled in (False,True):
            state=SimpleNamespace(fields={'session':Value('a.dmx'),'output':Value('a.blend')},extra=[],light_gain=Value('10'),particle_light_gain=Value('1'),particle_frame_step=Value(4),animation_keyframe_fps=Value('30'),flex_unlocker=Value(False),experimental_refraction=Value(enabled),experimental_delayed_decay=Value(enabled),experimental_pull=Value(enabled),experimental_spline=Value(enabled),experimental_partial_lock=Value(enabled))
            state.experimental_tint=Value(enabled)
            state.experimental_parent=Value(enabled)
            state.experimental_pull_lock=Value(enabled)
            state.experimental_noise=Value(enabled)
            state.open_master_timeline=Value(enabled)
            job=App.job(state);self.assertEqual(job['particle_frame_step'],4);self.assertIs(job['experimental_refraction'],enabled)
            self.assertEqual(job['animation_keyframe_fps'],'30')
            self.assertIs(job['open_master_timeline'],enabled)
            self.assertIs(job['experimental_tint'],enabled)
            self.assertIs(job['experimental_parent'],enabled)
            self.assertIs(job['experimental_pull_lock'],enabled)
            self.assertIs(job['experimental_noise'],enabled)
            jobs=plan_jobs(['a.dmx','b.dmx'],job,'unused-test-output')
            self.assertTrue(all(j['experimental_refraction'] is enabled for j in jobs))
            self.assertTrue(all(j['experimental_tint'] is enabled for j in jobs))
            self.assertTrue(all(j['experimental_parent'] is enabled for j in jobs))
            self.assertTrue(all(j['experimental_pull_lock'] is enabled for j in jobs))
            self.assertTrue(all(j['experimental_noise'] is enabled for j in jobs))
            self.assertTrue(all(j['particle_frame_step']==4 for j in jobs))
            self.assertTrue(all(j['open_master_timeline'] is enabled for j in jobs))
            self.assertIs(job['experimental_delayed_decay'],enabled)
            self.assertTrue(all(j['experimental_delayed_decay'] is enabled for j in jobs))
            self.assertIs(job['experimental_spline'],enabled)
            self.assertIs(job['experimental_partial_lock'],enabled)
            self.assertTrue(all(j['experimental_partial_lock'] is enabled for j in jobs))
            self.assertTrue(all(j['experimental_spline'] is enabled for j in jobs))
            self.assertIs(job['experimental_pull'],enabled)
            self.assertTrue(all(j['experimental_pull'] is enabled for j in jobs))
