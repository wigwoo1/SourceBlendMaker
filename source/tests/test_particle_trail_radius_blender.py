"""Native signed animated trail-width, texture-corner and save/reopen checks."""
import sys,unittest,tempfile,math
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
from test_particle_trail_full_alpha import definition
from particle_bake import plan


class TrailRadiusPlanningTests(unittest.TestCase):
    def test_unlit_material_enables_cpu_radius_only(self):
        config=plan(definition(3),material={'sfm_particle_shader':'UnlitGeneric'})
        self.assertTrue(config['cpu_trail_geometry'])
        for shader in ('SpriteCard','Refract',''):
            with self.assertRaisesRegex(ValueError,'requires an UnlitGeneric'):
                plan(definition(3),material={'sfm_particle_shader':shader})
        with self.assertRaisesRegex(ValueError,'requires sprite geometry'):
            plan(definition(4),material={'sfm_particle_shader':'UnlitGeneric'})


@unittest.skipIf(fixture.bpy is None,"Run using Blender's Python")
class TrailRadiusBakeTests(unittest.TestCase):
    def setUp(self):
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=fixture.ChildControlPointBakeTests();self.base.setUp()
        self.base.material['sfm_particle_shader']='UnlitGeneric'

    def bake(self,oscillator=True):
        from particle_bake import bake
        d=definition(3)
        # Constant -1 width/second: .1 initial -> .05, -.15, -.4.
        d['modules']['renderers'][0]['parameters']['constrain radius to length']=False
        if not oscillator:d['modules']['operators'].pop()
        return bake(fixture.System(),{'definitions':[d],'control_points':[{'id':'cp0'}],'random_seed':1},
                    fixture.Shot(),self.base.scene,[2,4,7],[.05,.25,.5],12.,
                    {'fixture.vmt':self.base.material},fixture.Curves,scale=1.)

    def snapshot(self):
        return [(o['sfm_baked_frame'],[tuple(v.co) for v in o.data.vertices],
                 [tuple(v.uv) for v in o.data.uv_layers.active.data],
                 [tuple(v.color) for v in o.data.color_attributes['sfm_particle_color'].data])
                for o in sorted((o for o in self.base.scene.objects if o.get('sfm_baked_frame') is not None),key=lambda o:o['sfm_baked_frame'])]

    def test_signed_animated_width_and_uvs_preserve_motion_and_alpha(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        self.assertIn('signed half-width',records[0]['trail_geometry'])
        animated=self.snapshot();self.assertEqual(len(animated),3)
        for row,width in zip(animated,(.05,-.15,-.4)):
            points=row[1]
            self.assertAlmostEqual(math.dist(points[0],points[1]),abs(width),places=6)
            self.assertEqual(points[0][1]>points[1][1],width>0)
            self.assertEqual(row[2],[(0,0),(1,0),(1,1),(0,1)])
        for obj in list(self.base.scene.objects):
            if obj.get('sfm_baked_frame') is not None:fixture.bpy.data.objects.remove(obj,do_unlink=True)
        records=self.bake(False);self.assertFalse(records[0].get('reason'),records)
        for a,b in zip(animated,self.snapshot()):
            for pair in ((0,1),(2,3)):
                for axis in range(3):self.assertAlmostEqual(sum(a[1][i][axis] for i in pair),sum(b[1][i][axis] for i in pair),places=6)
            self.assertEqual(a[2:],b[2:])

    def test_signed_geometry_survives_save_reopen(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        expected=self.snapshot();name=self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'trail-radius.blend')
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path);fixture.bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene=fixture.bpy.data.scenes[name];self.assertEqual(self.snapshot(),expected)

    def test_gpu_radius_material_is_reported_and_not_baked(self):
        self.base.material['sfm_particle_shader']='SpriteCard'
        records=self.bake()
        self.assertIn('requires an UnlitGeneric',records[0].get('reason',''))
        self.assertEqual(self.snapshot(),[])


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
