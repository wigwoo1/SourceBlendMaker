"""Baked UVs must use both outputs of the installed reversed random range."""
import sys,json,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture

@unittest.skipIf(fixture.bpy is None,"Run using Blender's Python")
class ReversedSequenceBakeTests(unittest.TestCase):
    def test_actual_baker_preserves_both_reversed_range_atlas_choices_after_reopen(self):
        from particle_bake import bake
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        base=fixture.ChildControlPointBakeTests();base.setUp()
        sheet={str(i):{'clamp':False,'duration':1.,'frames':[{'duration':1.,'coordinates':[(i/10,0,i/10+.05,.1)]}]} for i in (2,3)}
        base.material['sfm_particle_sheet']=json.dumps(sheet)
        d=fixture.definition('reversed atlas fixture',0,None,fixture.module('emit_instantaneously',num_to_emit=20),[2,0,0])
        d['children']=[]
        d['modules']['initializers'].append(fixture.module('Sequence Random',sequence_min=3))
        records=bake(fixture.System(),{'definitions':[d],'control_points':[{'id':'cp0'}],'random_seed':7},
                     fixture.Shot(),base.scene,[4],[.25],12.,{'fixture.vmt':base.material},fixture.Curves,scale=1.)
        self.assertFalse(records[0].get('reason'),records)
        def choices():
            mesh=next(o.data for o in base.scene.objects if o.get('sfm_baked_frame')==4)
            self.assertEqual(len(mesh.polygons),20)
            uv=mesh.uv_layers.active.data
            return [round(min(uv[i].uv.x for i in p.loop_indices),3) for p in mesh.polygons]
        expected=choices();self.assertEqual(set(expected),{.2,.3})
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'reversed-sequence.blend');scene_name=base.scene.name
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path);fixture.bpy.ops.wm.open_mainfile(filepath=path)
            base.scene=fixture.bpy.data.scenes[scene_name]
            self.assertEqual(choices(),expected)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
