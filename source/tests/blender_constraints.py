"""Constraint evaluation must move real skinning bones after reopening."""
from pathlib import Path
import sys,math,json
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if '--verify' not in sys.argv:
    import blender_worker as w
    from constraints import bake
    class Node(dict):
        def __init__(self,name,type,**values):super().__init__(values);self.name=name;self.type=type;self.id=name
    root_transform=Node('bone 0 (Root)','DmeTransform',position=(0,0,0))
    child_transform=Node('bone 1 (Child)','DmeTransform',position=(0,1/w.SCALE,0))
    child=Node('Child DAG','DmeDag',transform=child_transform)
    root=Node('Root DAG','DmeDag',transform=root_transform,children=[child])
    gm=Node('Model','DmeGameModel',transform=Node('Model transform','DmeTransform'),children=[root],bones=[root_transform,child_transform])
    target_transform=Node('Target motion','DmeTransform',position=(100,0,0))
    target=Node('Rig target','DmeRigHandle',transform=target_transform)
    slave=Node('Slave','DmeConstraintSlave',target=root)
    entry=Node('Target','DmeConstraintTarget',target=target,targetWeight=1.)
    point=Node('Point','DmeRigPointConstraintOperator',mode=0,targets=[entry],slave=slave)
    orient=Node('Orient','DmeRigOrientConstraintOperator',mode=0,targets=[entry],slave=slave)
    static_transform=Node('bone 0 (Static)','DmeTransform',position=(0,0,0))
    static_joint=Node('Static DAG','DmeDag',transform=static_transform)
    static_gm=Node('Static model','DmeGameModel',transform=Node('Static model transform','DmeTransform',position=(50,0,0)),children=[static_joint],bones=[static_transform])
    static_slave=Node('Static slave','DmeConstraintSlave',target=static_joint)
    static_point=Node('Static point','DmeRigPointConstraintOperator',mode=0,targets=[entry],slave=static_slave)
    scene=Node('Scene','DmeDag',children=[gm,target,static_gm])
    class Shot:
        element=Node('Shot','DmeFilmClip',scene=scene,operators=[point,orient,static_point])
        def value(self,e,key,t,default):
            if e is target_transform and key=='orientation':return (0,0,math.sin(t*math.pi/4),math.cos(t*math.pi/4))
            return e.get(key,default) if e is not None else default
    model=bpy.data.objects.new('Model',None);bpy.context.scene.collection.objects.link(model)
    data=bpy.data.armatures.new('Test skeleton');arm=bpy.data.objects.new('Test skeleton',data);bpy.context.scene.collection.objects.link(arm);arm.parent=model
    bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    bone=data.edit_bones.new('Root');bone.head=(0,0,0);bone.tail=(0,1,0)
    bone=data.edit_bones.new('Child');bone.head=(0,1,0);bone.tail=(0,2,0);bone.parent=data.edit_bones['Root']
    bpy.ops.object.mode_set(mode='OBJECT')
    static_model=bpy.data.objects.new('Static model',None);bpy.context.scene.collection.objects.link(static_model)
    w.animate_transform(static_model,Shot(),static_gm['transform'],[1,2],[0,1])
    pivot=bpy.data.objects.new('Static pivot',None);bpy.context.scene.collection.objects.link(pivot);pivot.parent=static_model;pivot.rotation_mode='QUATERNION'
    pivot['sfm_bone_transform']=static_transform.id;pivot['sfm_rest_inverse']=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    objects={gm.id:model,static_gm.id:static_model};w.import_hierarchy(Shot(),objects,[1,2],[0,1])
    records=bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves)
    assert len(records)==3 and all(r['converted'] for r in records),records
    competing=Node('Competing point','DmeRigPointConstraintOperator',mode=0,targets=[entry],slave=slave)
    Shot.element['operators'].append(competing)
    collision_records=bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves)
    blocked=[r for r in collision_records if r['name'] in ('Point','Competing point')]
    assert len(blocked)==2 and all(not r['converted'] and 'Overlapping' in r['reason'] for r in blocked),collision_records
    assert all(r['converted'] for r in collision_records if r['name'] in ('Orient','Static point')),collision_records
    Shot.element['operators'].remove(competing)
    # An unsupported weight must be disclosed instead of baked as unit weight.
    entry['targetWeight']=.5
    assert all(not r['converted'] and 'Weighted' in r['reason'] for r in bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves))
    entry['targetWeight']=1.;entry['vecOffset']=(1,0,0)
    offset_records=bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves)
    assert all(r['converted'] if 'Orient' in r['type'] else not r['converted'] and 'offset' in r['reason'] for r in offset_records)
    entry['vecOffset']=(0,0,0);entry['target']=root
    assert all(not r['converted'] and 'Cyclic' in r['reason'] for r in bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves))
    entry['target']=target
    assert all(r['converted'] for r in bake(Shot(),objects,[1,2],[0,1],w.transform,w.AXIS,w.Curves))
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/constraints.blend').resolve()))
else:
    arm=bpy.data.objects['Test skeleton'];samples=[]
    for frame,expected in [(1,(2.54,1,0)),(2,(1.54,0,0))]:
        bpy.context.scene.frame_set(frame)
        root=arm.matrix_world@arm.pose.bones['Root'].matrix;child=arm.matrix_world@arm.pose.bones['Child'].matrix
        assert (root.translation-Vector((2.54,0,0))).length<1e-5
        assert (child.translation-Vector(expected)).length<1e-5,(frame,child.translation,expected)
        assert (bpy.data.objects['Static pivot'].matrix_world.translation-Vector((2.54,0,0))).length<1e-5
        assert not any(b.constraints for b in arm.pose.bones)
        samples.append({'frame':frame,'root':list(root.translation),'child':list(child.translation)})
    Path('outputs/constraints_validation.json').write_text(json.dumps({'point_and_orientation':True,'real_armature_baked':True,'no_scripted_drivers':True,'unsupported_weights_reported':True,'reopened':True,'samples':samples},indent=2))
    print('CONSTRAINT BAKE TEST PASSED')
