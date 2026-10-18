"""Per-instance animated material overrides remain native after reopening."""
from pathlib import Path
import sys,json
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if '--verify' not in sys.argv:
    import blender_worker as w
    bpy.ops.mesh.primitive_cube_add();first=bpy.context.object;first.name='Override instance'
    second=first.copy();second.name='Unchanged instance';bpy.context.scene.collection.objects.link(second)
    material=bpy.data.materials.new('test');material.use_nodes=True;material['full_path']='models/test.vmt';first.data.materials.append(material)
    class Model(dict):name='Test model'
    override={'mtlName':'models/test','$color2':(1,0,0),'$alpha':1.}
    class Shot:
        def value(self,e,key,t,default):return ((1-t,t,0) if key=='$color2' else 1-.5*t)
    w.material_overrides([first],Model(materials=[override]),Shot(),[1,2],[0,1])
    assert not w.REPORT['warnings'],w.REPORT
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/material-overrides.blend').resolve()))
else:
    a=bpy.data.objects['Override instance'];b=bpy.data.objects['Unchanged instance']
    assert a.data==b.data and a.active_material!=b.active_material
    tree=a.active_material.node_tree;mix=next(n for n in tree.nodes if n.type=='MIX_RGB');alpha=next(n for n in tree.nodes if n.type=='MATH')
    states=[]
    for frame,color,opacity in [(1,(1,0,0),1),(2,(0,1,0),.5)]:
        bpy.context.scene.frame_set(frame)
        assert tuple(mix.inputs[2].default_value[:3])==color
        assert alpha.inputs[1].default_value==opacity
        states.append({'frame':frame,'color':list(color),'opacity':opacity})
    assert b.active_material.node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value==1
    Path('outputs/material_overrides_validation.json').write_text(json.dumps({'instance_isolation':True,'shared_geometry':True,'reopened_native_animation':True,'samples':states},indent=2))
    print('MATERIAL OVERRIDE TEST PASSED')
