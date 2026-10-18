"""Ordered noise birth motion and persistent native meshes, using Blender."""
import math,random,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture


def module(name,**p):return fixture.module(name,**p)


def definition(local=False,scalar=True):
    d=fixture.definition('velocity noise fixture',0,None,module('emit_instantaneously',num_to_emit=1),[0,0,0])
    d['children']=[]
    # Put overrides ahead of the ordinary spawn in the serialized file.
    p={'output minimum':[2,-3,1],'output maximum':[8,7,4],'Spatial Noise Coordinate Scale':.07,
       'Apply Velocity in Local Space (0/1)':local,'Control Point Number':1}
    d['modules']['initializers']=[module('Velocity Noise',**p),
        module('Position Modify Offset Random',**{'offset min':[5,0,0],'offset max':[5,0,0]}),
        module('Position Within Box Random',min=[1,2,3],max=[1,2,3]),
        module('Lifetime Random',lifetime_min=2,lifetime_max=2)]
    if scalar:d['modules']['initializers'].append(module('Remap Noise to Scalar',**{'output minimum':.1,'output maximum':.1}))
    else:d['modules']['initializers'].append(module('Radius Random',radius_min=.1,radius_max=.1))
    return d


@unittest.skipIf(fixture.bpy is None,"Run using Blender's Python")
class VelocityNoiseBakeTests(unittest.TestCase):
    def setUp(self):
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=fixture.ChildControlPointBakeTests();self.base.setUp()
        self.scene=self.base.scene
        self.scene.objects['child CP origin'].location=(10,20,30)
        cp=fixture.bpy.data.objects.new('second noise CP',None);cp['sfm_transform_id']='cp1'
        self.scene.collection.objects.link(cp);cp.location=(700,800,900)
        cp.rotation_euler=(0,0,math.pi/2)
        self.scene.view_layers[0].update()

    def bake(self,d):
        from particle_bake import bake
        records=bake(fixture.System(),{'definitions':[d],'control_points':[{'id':'cp0'},{'id':'cp1'}],'random_seed':1},
            fixture.Shot(),self.scene,[1,6],[0.,.5],10.,{'fixture.vmt':self.base.material},fixture.Curves,
            scale=1.,development_noise=True)
        self.assertFalse(records[0].get('reason'),records)
        self.assertIn('two-pass',records[0]['velocity_noise_initialization'])
        self.assertEqual(records[0]['initializer_execution_indices'],[2,3,4,0,1])
        return records

    def centers(self):
        from mathutils import Vector
        return {o['sfm_baked_frame']:tuple(sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices))
                for o in self.scene.objects if o.get('sfm_baked_particle_effect')=='velocity noise fixture'}

    def check_motion(self,d):
        from particle_velocity_noise import sample
        p=d['modules']['initializers'][0]['parameters']
        orientation=self.scene.objects['second noise CP'].rotation_euler.to_matrix()
        rotation=tuple(tuple(row) for row in orientation)
        v=sample(p,(11,22,33),0,rotation=rotation)
        actual=self.centers()
        self.assertEqual(set(actual),{1,6})
        for frame,age in ((1,0),(6,.5)):
            for component,start,velocity in zip(actual[frame],(16,22,33),v):
                self.assertAlmostEqual(component,start+velocity*age,places=4)
        return actual

    def test_noise_reads_spawn_before_later_offset_and_native_meshes_move(self):
        d=definition();self.bake(d);self.check_motion(d)

    def test_local_noise_uses_selected_birth_rotation_and_ignores_its_translation(self):
        d=definition(local=True);self.bake(d);self.check_motion(d)

    def test_velocity_noise_without_scalar_noise_uses_the_new_opt_in_path(self):
        d=definition(scalar=False);self.bake(d);self.check_motion(d)

    def test_velocity_adds_to_existing_spawn_motion(self):
        from particle_ordered_birth import sample
        from mathutils import Quaternion
        d=definition();d['modules']['initializers'][-1]=module('Radius Random',radius_min=.1,radius_max=.1)
        d['modules']['initializers'].append(module('Velocity Random',speed_min=0,speed_max=0,
            speed_in_local_coordinate_system_min=[1,2,3],speed_in_local_coordinate_system_max=[1,2,3]))
        state,history=sample(d,random.Random(1),1.,0.,0,lambda i:((10,20,30),Quaternion()),(0,0,0))
        from particle_velocity_noise import sample as noise
        expected=noise(d['modules']['initializers'][0]['parameters'],(11,22,33),0)
        for actual,a,b in zip(state['velocity'],expected,(1,2,3)):self.assertAlmostEqual(actual,a+b,places=5)
        self.assertEqual([s['index'] for s in history],[2,3,4,0,1,5])

    def test_baked_noise_motion_survives_save_and_reopen(self):
        d=definition(local=True);self.bake(d);expected=self.check_motion(d);name=self.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'velocity-noise.blend')
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path);fixture.bpy.ops.wm.open_mainfile(filepath=path)
            self.scene=fixture.bpy.data.scenes[name]
            self.assertEqual(self.centers(),expected)


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
