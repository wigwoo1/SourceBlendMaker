"""Native proof of repeated parent-vector updates and saved frame meshes."""
import sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as f
from particle_parent_update import NAME

@unittest.skipIf(f.bpy is None,"Run using Blender's Python")
class ParentUpdateBakeTests(unittest.TestCase):
    def setUp(self):
        f.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=f.ChildControlPointBakeTests();self.base.setUp()
    def bake(self,disabled=False):
        from particle_bake import bake
        m=f.module
        parent=f.definition('update parent',0,None,m('emit_instantaneously',num_to_emit=1),[2,0,0])
        child=f.definition('update child',1,0,m('emit_instantaneously',num_to_emit=1,emission_start_time=.5),[0,0,0])
        child['modules']['initializers'][0]=m('Position From Parent Particles',**{'Inherited Velocity Scale':0})
        child['modules']['operators'].extend(m(NAME,**{'Inherited Field':field,'operator enabled':not disabled}) for field in (0,2))
        records=bake(f.System(),{'definitions':[parent,child],'control_points':[{'id':'cp0'}],'random_seed':1},
                     f.Shot(),self.base.scene,[1,7,11],[0.,.6,1.],10.,{'fixture.vmt':self.base.material},f.Curves,
                     scale=1.,simulation_contexts={},retain_leaf_contexts=False)
        self.assertTrue(all(not r.get('reason') for r in records),records)
        return records
    def centers(self):
        return {o['sfm_baked_frame']:sum(v.co.x for v in o.data.vertices)/len(o.data.vertices)
                for o in self.base.scene.objects if o.get('sfm_baked_particle_effect')=='update child'}
    def test_child_follows_parent_at_each_sample_and_survives_save_reopen(self):
        records=self.bake()
        self.assertTrue(records[1]['parent_vector_updates'])
        self.assertAlmostEqual(self.centers()[7],1.2,places=4)
        self.assertAlmostEqual(self.centers()[11],2.,places=4)
        name=self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'parent-update.blend')
            f.bpy.ops.wm.save_as_mainfile(filepath=path);f.bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene=f.bpy.data.scenes[name]
            self.assertAlmostEqual(self.centers()[11],2.,places=4)
    def test_disabled_updates_leave_birth_position(self):
        self.bake(disabled=True)
        self.assertAlmostEqual(self.centers()[7],1.,places=4)
        self.assertAlmostEqual(self.centers()[11],1.,places=4)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
