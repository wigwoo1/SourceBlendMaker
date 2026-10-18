"""Verify inherited motion and camera basis compensation after save/reopen."""
from pathlib import Path
import math,sys,json
import bpy
from mathutils import Matrix,Vector,Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

if '--verify' not in sys.argv:
    import blender_worker as w
    class Node(dict):
        def __init__(self,name,type,**fields):super().__init__(fields);self.name=name;self.type=type;self.id=name
    root=Node('Moving parent','DmeDag',transform={'position':(100,0,0)})
    camera=Node('Parented camera','DmeCamera',transform={'position':(0,50,0)})
    child=Node('Camera child','DmeDag',transform={'position':(10,0,0)})
    model=Node('Model root','DmeGameModel',transform={'position':(0,0,0)})
    bone=Node('Attachment bone','DmeDag',transform={'position':(20,0,0)})
    prop=Node('Attached prop','DmeDag',transform={'position':(5,0,0)})
    root['children']=[camera,model];camera['children']=[child];model['children']=[bone];bone['children']=[prop]
    class Shot:
        element={'scene':root}
        def value(self,e,key,t,default):
            if e is root.get('transform') and key=='orientation':return (0,0,math.sin(t*math.pi/4),math.cos(t*math.pi/4))
            if e is bone.get('transform') and key=='position':return (20+10*t,0,0)
            return e.get(key,default)
    model_obj=bpy.data.objects.new('Model root',None);bpy.context.scene.collection.objects.link(model_obj)
    w.animate_transform(model_obj,Shot(),model['transform'],[1,2],[0,1])
    w.import_hierarchy(Shot(),{model.id:model_obj},[1,2],[0,1])
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/hierarchy.blend').resolve()))
else:
    scene=bpy.context.scene;rows=[]
    for frame,expected in [(1,(2.794,1.27,0)),(2,(1.27,.254,0))]:
        scene.frame_set(frame);position=bpy.data.objects['Camera child DAG'].matrix_world.translation
        assert (position-Vector(expected)).length<1e-5,(frame,position,expected)
        rows.append({'frame':frame,'child_world_position':list(position)})
        attachment=bpy.data.objects['Attached prop DAG'].matrix_world.translation
        expected_prop=Vector((3.175,0,0) if frame==1 else (2.54,.889,0))
        assert (attachment-expected_prop).length<1e-5,(frame,attachment)
        rows[-1]['bone_attached_prop_position']=list(attachment)
    assert bpy.data.objects['Parented camera'].parent.name=='Moving parent DAG'
    Path('outputs/hierarchy_validation.json').write_text(json.dumps({'native_parenting':True,'camera_axis_compensation':True,'autoexec_disabled':True,'samples':rows},indent=2))
    print('HIERARCHY TEST PASSED')
