"""Run with Blender --background --python to verify the complete sprite bake."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import bpy
except ImportError:bpy=None

def module(function,**parameters):return {'function':function,'parameters':parameters}

class Curves:
    def __init__(self,*args):pass
    def add(self,*args,**kwargs):pass

class System:
    id='child-cp-system';name='child CP integration fixture'
    def get(self,key,default=None):return default

class Shot:
    start=0.;duration=1.2;curves={}
    def value(self,element,attribute,time,default):return default

def definition(name,identity,parent,emitter,velocity):
    return {'name':name,'instance_id':identity,'parent_instance_id':parent,
        'children':['child'] if parent is None else [],'parameters':{'material':'fixture.vmt','max_particles':20},
        'modules':{'renderers':[module('render_animated_sprites')],'emitters':[emitter],
            'initializers':[module('Position From Control Points',control_point_number=0),
                module('Lifetime Random',lifetime_min=2.,lifetime_max=2.),
                module('Radius Random',radius_min=.1,radius_max=.1),
                module('Velocity Random',speed_in_local_coordinate_system_min=velocity,
                       speed_in_local_coordinate_system_max=velocity)],
            'operators':[module('Movement Basic',gravity=[0,0,0],drag=0)],'forces':[],'constraints':[]}}

@unittest.skipIf(bpy is None,"Run using Blender's Python")
class ChildControlPointBakeTests(unittest.TestCase):
    def setUp(self):
        self.scene=bpy.data.scenes.new('child CP test scene')
        bpy.context.window.scene=self.scene
        origin=bpy.data.objects.new('child CP origin',None);origin['sfm_transform_id']='cp0'
        self.scene.collection.objects.link(origin)
        camera=bpy.data.objects.new('child CP camera',bpy.data.cameras.new('child CP camera'))
        self.scene.collection.objects.link(camera);camera.location=(0,0,10);self.scene.camera=camera
        self.material=bpy.data.materials.new('child CP test material')

    def run_bake(self,repeated=False,container=False,sibling=False):
        from particle_bake import bake
        emitter=(module('emit_continuously',emission_rate=2.,emission_duration=1.) if repeated
                 else module('emit_instantaneously',num_to_emit=1,emission_start_time=0.))
        parent=definition('parent',0,None,emitter,[10,0,0])
        parent['modules']['operators'].append(module('Set child control points from particle positions'))
        child=definition('child',1,0,module('emit_continuously',emission_rate=2.),[0,0,0])
        definitions=[parent,child]
        if container:
            middle={'name':'container','instance_id':1,'parent_instance_id':0,'children':['child'],
                    'parameters':{},'modules':{group:[] for group in ('renderers','emitters','initializers','operators','forces','constraints')}}
            child['instance_id']=2;child['parent_instance_id']=1
            definitions=[parent,middle,child]
        if sibling:
            definitions.append(definition('sibling',3,None,module('emit_instantaneously',num_to_emit=1),[0,0,0]))
        descriptor={'definitions':definitions,'control_points':[{'id':'cp0'}],
                    'control_models':[],'random_seed':1}
        return bake(System(),descriptor,Shot(),self.scene,[1,6,11],[0.,.5,1.],10.,
                    {'fixture.vmt':self.material},Curves,scale=1.,simulation_contexts={},retain_leaf_contexts=False)

    def test_child_births_follow_moving_parent_with_static_imported_origin(self):
        records=self.run_bake()
        self.assertEqual([record.get('reason') for record in records],[None,None],records)
        meshes=[o for o in self.scene.objects if o.get('sfm_baked_particle_effect')=='child' and o.get('sfm_baked_frame')==11]
        self.assertEqual(len(meshes),1)
        mesh=meshes[0].data
        centers=[sum(mesh.vertices[i].co.x for i in face.vertices)/len(face.vertices) for face in mesh.polygons]
        self.assertEqual(len(centers),2)
        self.assertAlmostEqual(centers[0],5.,places=4)
        self.assertAlmostEqual(centers[1],10.,places=4)

    def test_position_propagates_through_rendererless_container(self):
        records=self.run_bake(container=True)
        self.assertTrue(all(not r.get('reason') for r in records),records)
        mesh=next(o.data for o in self.scene.objects if o.get('sfm_baked_particle_effect')=='child' and o.get('sfm_baked_frame')==11)
        centers=[sum(mesh.vertices[i].co.x for i in face.vertices)/len(face.vertices) for face in mesh.polygons]
        self.assertAlmostEqual(centers[0],5.,places=4)
        self.assertAlmostEqual(centers[1],10.,places=4)

    def test_parent_cp_override_does_not_leak_into_independent_system_root(self):
        records=self.run_bake(sibling=True)
        self.assertTrue(all(not r.get('reason') for r in records),records)
        mesh=next(o.data for o in self.scene.objects if o.get('sfm_baked_particle_effect')=='sibling' and o.get('sfm_baked_frame')==11)
        self.assertAlmostEqual(sum(v.co.x for v in mesh.vertices)/len(mesh.vertices),0.,places=4)

    def test_repeated_birth_feedback_fails_instead_of_silently_using_origin(self):
        records=self.run_bake(repeated=True)
        self.assertIn('chronological integration',records[0].get('reason',''))
        self.assertIn('Parent child-control-point simulation failed',records[1].get('reason',''))
        self.assertFalse(any(o.get('sfm_baked_particle_effect')=='child' for o in self.scene.objects))

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
