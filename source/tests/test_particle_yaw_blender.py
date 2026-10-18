"""Native SpriteCard yaw/material planning, birth state and saved geometry."""
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
bpy=fixture.bpy


@unittest.skipIf(bpy is None,"Run using Blender's Python")
class SpriteCardYawBakeTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=fixture.ChildControlPointBakeTests();self.base.setUp()

    def definition(self, yaw=45, roll=30, mode=1):
        d=fixture.definition('yaw fixture',0,None,fixture.module('emit_instantaneously',num_to_emit=1),[0,0,0])
        d['children']=[]
        d['modules']['renderers'][0]['parameters'].update(orientation_type=mode)
        d['modules']['initializers'].extend([
            fixture.module('Rotation Random',rotation_initial=roll,rotation_offset_min=0,rotation_offset_max=0,randomly_flip_direction=False),
            fixture.module('Rotation Yaw Random',yaw_initial=yaw,yaw_offset_min=0,yaw_offset_max=0)])
        return d

    def bake(self, definition, shader='SpriteCard', material_mode=0):
        from particle_bake import bake
        material=self.base.material
        material['sfm_particle_shader']=shader
        material['sfm_particle_material_orientation']=material_mode
        return bake(fixture.System(),{'definitions':[definition],'control_points':[{'id':'cp0'}],'random_seed':1},
                    fixture.Shot(),self.base.scene,[1,6],[0.,.5],10.,{'fixture.vmt':material},fixture.Curves,scale=1.)

    def mesh_points(self):
        obj=next(o for o in self.base.scene.objects if o.get('sfm_baked_frame')==1)
        return [tuple(v.co) for v in obj.data.vertices]

    def test_material_overrides_pcf_and_yaw_does_not_become_roll(self):
        d=self.definition(yaw=90,roll=0,mode=1)
        # These CPU settings are ignored by Source when the VMT is SpriteCard.
        d['modules']['renderers'][0]['parameters']['orientation control point']=63
        records=self.bake(d)
        self.assertTrue(all(not r.get('reason') for r in records),records)
        self.assertEqual(records[0]['spritecard_geometry']['orientation'],0)
        self.assertTrue(records[0]['yaw_attribute']['separate_from_roll'])
        points=self.mesh_points()
        self.assertTrue(all(abs(p[0])<1e-6 for p in points),points)
        self.assertGreater(max(p[2] for p in points)-min(p[2] for p in points),.19)

    def test_legacy_and_ordered_births_store_independent_yaw(self):
        from mathutils import Matrix
        from particle_sprite_state import sample as legacy
        from particle_ordered_birth import sample as ordered
        d=self.definition()
        a=legacy(d,random.Random(2),1.,Matrix.Identity(3))
        b,_=ordered(d,random.Random(2),1.,0.,0,lambda cp:((0,0,0),Matrix.Identity(3)),(0,0,0))
        for state in (a,b):
            self.assertAlmostEqual(state['angle'],math.radians(30))
            self.assertAlmostEqual(state['yaw'],math.radians(45))

    def test_ordered_flip_after_random_changes_yaw_without_double_uv_mirroring(self):
        from mathutils import Matrix
        from particle_ordered_birth import sample
        from particle_yaw import flip
        d=self.definition(yaw=25,roll=30)
        d['modules']['initializers'].append(fixture.module('Rotation Yaw Flip Random',**{'Flip Percentage':1}))
        state,_=sample(d,random.Random(2),1.,0.,0,lambda cp:((0,0,0),Matrix.Identity(3)),(0,0,0))
        self.assertAlmostEqual(state['yaw'],flip(math.radians(25)))
        self.assertAlmostEqual(state['angle'],math.radians(30))
        records=self.bake(d)
        self.assertTrue(all(not r.get('reason') for r in records),records)
        obj=next(o for o in self.base.scene.objects if o.get('sfm_baked_frame')==1)
        self.assertEqual(tuple(obj.data.uv_layers[0].data[0].uv),(0.,0.))

    def test_non_spritecard_world_plane_yaw_is_not_applied_as_roll(self):
        records=self.bake(self.definition(yaw=75,roll=0,mode=2),shader='UnlitGeneric')
        self.assertTrue(all(not r.get('reason') for r in records),records)
        points=self.mesh_points()
        self.assertAlmostEqual(points[0][0],.1,places=6)
        self.assertAlmostEqual(points[0][1],.1,places=6)
        self.assertTrue(all(abs(p[2])<1e-6 for p in points))

    def test_native_save_reopen_preserves_yaw_vertices(self):
        records=self.bake(self.definition(yaw=40,roll=20))
        self.assertTrue(all(not r.get('reason') for r in records),records)
        expected=self.mesh_points();name=self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'yaw.blend')
            bpy.ops.wm.save_as_mainfile(filepath=path);bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene=bpy.data.scenes[name]
            self.assertEqual(expected,self.mesh_points())

    def test_untraced_cpu_billboard_keeps_existing_uv_flip(self):
        d=self.definition(mode=0)
        d['modules']['initializers']=[m for m in d['modules']['initializers'] if m['function']!='Rotation Yaw Random']
        d['modules']['initializers'].append(fixture.module('Rotation Yaw Flip Random',**{'Flip Percentage':1}))
        records=self.bake(d,shader='UnlitGeneric')
        self.assertTrue(all(not r.get('reason') for r in records),records)
        obj=next(o for o in self.base.scene.objects if o.get('sfm_baked_frame')==1)
        self.assertEqual(tuple(obj.data.uv_layers[0].data[0].uv),(1.,0.))


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
