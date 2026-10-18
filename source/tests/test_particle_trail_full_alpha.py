"""Full opacity oscillators must reach the existing shared trail alpha baker."""
import sys,unittest,tempfile
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
from test_particle_scalar_oscillation import parameters
from particle_bake import plan


def definition(field=7):
    d=fixture.definition('trail alpha fixture',0,None,fixture.module('emit_instantaneously',num_to_emit=1),[2,0,0])
    d['children']=[]
    d['modules']['renderers']=[fixture.module('render_sprite_trail')]
    p=parameters();p['oscillation field']=field
    p['oscillation rate min']=p['oscillation rate max']=-1.
    d['modules']['operators'].append(fixture.module('Oscillate Scalar',**p))
    return d


class TrailAlphaPlanningTests(unittest.TestCase):
    def test_full_alpha_and_omitted_default_field_are_accepted(self):
        for omitted in (False,True):
            d=definition()
            if omitted:del d['modules']['operators'][-1]['parameters']['oscillation field']
            self.assertEqual(plan(d)['renderer'],'render_sprite_trail')

    def test_roll_trails_still_require_separate_geometry_verification(self):
        with self.assertRaisesRegex(ValueError,'requires sprite geometry'):plan(definition(4))

    def test_rope_is_not_silently_added_to_the_new_scope(self):
        d=definition();d['modules']['renderers'][0]['function']='render_rope'
        with self.assertRaises(ValueError):plan(d,experimental_ring=True)


@unittest.skipIf(fixture.bpy is None,"Run using Blender's Python")
class TrailFullAlphaBakeTests(unittest.TestCase):
    def setUp(self):
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=fixture.ChildControlPointBakeTests();self.base.setUp()
        self.base.material['sfm_particle_shader']='UnlitGeneric'

    def bake(self,oscillator=True):
        from particle_bake import bake
        d=definition()
        if not oscillator:d['modules']['operators'].pop()
        return bake(fixture.System(),{'definitions':[d],'control_points':[{'id':'cp0'}],'random_seed':1},
                    fixture.Shot(),self.base.scene,[4,7],[.25,.5],12.,
                    {'fixture.vmt':self.base.material},fixture.Curves,scale=1.)

    def snapshot(self):
        return [(o['sfm_baked_frame'],[tuple(v.co) for v in o.data.vertices],
                 [v.color[3] for v in o.data.color_attributes['sfm_particle_color'].data])
                for o in sorted((o for o in self.base.scene.objects if o.get('sfm_baked_frame') is not None),
                                key=lambda o:o['sfm_baked_frame'])]

    def test_trail_mesh_opacity_changes_without_changing_motion_or_shape(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        animated=self.snapshot();self.assertEqual(len(animated),2)
        for row,expected in zip(animated,(.75,.5)):
            self.assertTrue(row[2])
            for alpha in row[2]:self.assertAlmostEqual(alpha,expected,places=5)
        for obj in list(self.base.scene.objects):
            if obj.get('sfm_baked_frame') is not None:fixture.bpy.data.objects.remove(obj,do_unlink=True)
        records=self.bake(False);self.assertFalse(records[0].get('reason'),records)
        baseline=self.snapshot()
        self.assertEqual([row[:2] for row in animated],[row[:2] for row in baseline])
        self.assertTrue(all(alpha==1. for row in baseline for alpha in row[2]))

    def test_animated_trail_alpha_survives_save_reopen(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        expected=self.snapshot();name=self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'trail-alpha.blend')
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path);fixture.bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene=fixture.bpy.data.scenes[name]
            self.assertEqual(self.snapshot(),expected)


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
