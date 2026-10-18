"""Moving IK target/pole must animate actual bones without runtime scripts."""
from pathlib import Path
import math,sys,json
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if '--verify' not in sys.argv:
    import blender_worker as w
    from constraints import bake
    class Node(dict):
        def __init__(self,name,type,**fields):super().__init__(fields);self.name=name;self.type=type;self.id=name
    transforms=[Node(f'bone {i} ({name})','DmeTransform',position=(0,0 if i==0 else 1/w.SCALE,0)) for i,name in enumerate(('Start','Mid','End'))]
    joints=[Node(name,'DmeDag',transform=tr) for name,tr in zip(('Start DAG','Mid DAG','End DAG'),transforms)]
    joints[0]['children']=[joints[1]];joints[1]['children']=[joints[2]]
    gm=Node('IK model','DmeGameModel',transform={},bones=transforms,children=[joints[0]])
    target=Node('IK target','DmeRigHandle',transform=Node('Target transform','DmeTransform'))
    pole=Node('IK pole','DmeRigHandle',transform=Node('Pole transform','DmeTransform'))
    entry=Node('IK entry','DmeConstraintTarget',target=target,targetWeight=1.)
    offset=(0,0,-math.sin(math.pi/4),math.cos(math.pi/4))
    operator=Node('IK operator','DmeRigIKConstraintOperator',mode=0,targets=[entry],pvTarget=pole,startOffset=offset,midOffset=offset,
                  **{key:Node(key,'DmeConstraintSlave',target=j) for key,j in zip(('startJoint','midJoint','endJoint'),joints)})
    root=Node('Scene','DmeDag',children=[gm,target,pole])
    class Shot:
        element=Node('Shot','DmeFilmClip',scene=root,operators=[operator])
        def value(self,e,key,t,default):
            if e is target['transform'] and key=='position':return (1/w.SCALE,t/w.SCALE,0)
            if e is pole['transform'] and key=='position':return (0,2*(1-t)/w.SCALE,2*t/w.SCALE)
            return e.get(key,default) if e is not None else default
    model=bpy.data.objects.new('IK model',None);bpy.context.scene.collection.objects.link(model)
    arm=bpy.data.objects.new('IK armature',bpy.data.armatures.new('IK skeleton'));bpy.context.scene.collection.objects.link(arm);arm.parent=model
    bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for i,name in enumerate(('Start','Mid','End')):
        bone=arm.data.edit_bones.new(name);bone.head=(0,i,0);bone.tail=(0,i+1,0)
        if i:bone.parent=arm.data.edit_bones[('Start','Mid')[i-1]]
    bpy.ops.object.mode_set(mode='OBJECT');objects={gm.id:model}
    w.import_hierarchy(Shot(),objects,[1,2,3],[0,1,2])
    result=bake(Shot(),objects,[1,2,3],[0,1,2],w.transform,w.AXIS,w.Curves)
    assert len(result)==1 and result[0]['converted'],result
    assert result[0]['clamped_frames']==1,result
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/ik.blend').resolve()))
else:
    arm=bpy.data.objects['IK armature'];rows=[]
    for frame,target in [(1,(1,0,0)),(2,(1,1,0)),(3,(2/math.sqrt(5),4/math.sqrt(5),0))]:
        bpy.context.scene.frame_set(frame);matrices=[arm.matrix_world@arm.pose.bones[n].matrix for n in ('Start','Mid','End')]
        start,mid,end=[m.translation for m in matrices]
        assert (end-Vector(target)).length<1e-5,(frame,end,target)
        assert abs((mid-start).length-1)<1e-5 and abs((end-mid).length-1)<1e-5
        assert (matrices[0].to_quaternion()@Vector((0,1,0))-(mid-start).normalized()).length<1e-5
        assert (matrices[1].to_quaternion()@Vector((0,1,0))-(end-mid).normalized()).length<1e-5
        if frame==1:assert mid.y>.8
        if frame==2:assert mid.z>.7
        rows.append({'frame':frame,'mid':list(mid),'end':list(end)})
    Path('outputs/ik_bake_validation.json').write_text(json.dumps({'moving_target_and_pole':True,'offsets_applied':True,'real_armature_baked':True,'autoexec_disabled':True,'samples':rows},indent=2))
    print('IK BAKE TEST PASSED',rows)
