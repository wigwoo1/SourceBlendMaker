"""Native baker integration checks for shared plane-cull lifecycle."""
import sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
bpy=fixture.bpy;definition=fixture.definition;module=fixture.module
System=fixture.System;Shot=fixture.Shot;Curves=fixture.Curves

@unittest.skipIf(bpy is None,"Run using Blender's Python")
class PlaneCullBakeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ChildControlPointBakeTests();self.fixture.setUp()

    def run_bake(self,maintained=False,moving=False,burst=False):
        from particle_bake import bake
        emitter=module('emit to maintain count') if maintained else module('emit_continuously',emission_rate=4.)
        if burst:emitter=module('emit_instantaneously',num_to_emit=2,**{'maximum emission per frame':2})
        root=definition('culled parent',0,None,emitter,[0,0,0] if moving else [0,0,-4]);root['parameters']['max_particles']=1
        root['modules']['initializers'][1]['parameters'].update(lifetime_min=10.,lifetime_max=10.)
        root['modules']['operators'].append(module('Cull when crossing plane',**{'Cull plane offset':.1}))
        if burst:root['modules']['operators'][-1]['parameters']['Cull plane offset']=-1.
        if moving:
            from blender_worker import Curves as NativeCurves
            origin=next(o for o in self.fixture.scene.objects if o.get('sfm_transform_id')=='cp0')
            NativeCurves(origin,'Moving cull control').add('location',[1,9],[[0,0,0],[0,0,2]])
        contexts={}
        records=bake(System(),{'definitions':[root],'control_points':[{'id':'cp0'}],'control_models':[],'random_seed':1},Shot(),self.fixture.scene,
                     [1,3,4,5,7,9],[0.,.25,.375,.5,.75,1.],8.,{'fixture.vmt':self.fixture.material},Curves,scale=1.,simulation_contexts=contexts)
        return records,contexts

    def test_killed_particles_stay_hidden_and_capacity_refills(self):
        records,contexts=self.run_bake();self.assertTrue(all(not r.get('reason') for r in records),records)
        meshes=[o for o in self.fixture.scene.objects if o.get('sfm_baked_particle_effect')=='culled parent']
        self.assertFalse(any(o.get('sfm_baked_frame')==4 for o in meshes))
        final=[o for o in meshes if o.get('sfm_baked_frame')==9]
        self.assertEqual(len(final),1);self.assertEqual(len(final[0].data.polygons),1)
        self.assertEqual(records[0]['plane_culling']['killed_births'],3)

    def test_parent_snapshots_use_same_deaths_and_preserve_authored_lifetime(self):
        records,contexts=self.run_bake();self.assertFalse(records[0].get('reason'),records)
        parent=contexts[0]
        self.assertEqual(parent.snapshot(.9,1/120).particle_ids,())
        self.assertEqual(parent.snapshot(.5,1/120).particle_ids,(1,))
        self.assertEqual(parent.snapshot(.9,1/120).particle_ids,())
        self.assertEqual(set(parent.lifetimes.values()),{10.})

    def test_maintained_emission_fails_explicitly_without_lifecycle_feedback(self):
        records,_=self.run_bake(maintained=True)
        self.assertIn('maintained emission requires ordered birth feedback',records[0].get('reason',''))

    def test_moving_plane_uses_actual_blender_control_history(self):
        records,_=self.run_bake(moving=True)
        self.assertFalse(records[0].get('reason'),records)
        self.assertEqual(records[0]['plane_culling']['killed_births'],3)
        self.assertFalse(any(o.get('sfm_baked_particle_effect')=='culled parent' and o.get('sfm_baked_frame')==4 for o in self.fixture.scene.objects))

    def test_same_clock_births_do_not_reuse_a_slot_before_operator_dispatch(self):
        records,contexts=self.run_bake(burst=True)
        self.assertFalse(records[0].get('reason'),records)
        self.assertEqual(len(contexts[0].births),1)
        self.assertEqual(records[0]['plane_culling']['killed_births'],1)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
